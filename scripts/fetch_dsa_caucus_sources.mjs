import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || "playwright");
const ledger = JSON.parse(await readFile(`${root}/data/manual/dsa_caucus_sources.json`, "utf8"));
const output = `${root}/data/raw/dsa_caucuses`;
await mkdir(output, { recursive: true });
const hash = value => createHash("sha256").update(value).digest("hex");
const browser = await chromium.launch({ headless: true });
const records = [];
try {
  for (const source of [...ledger.sources, ...ledger.discovery_sources]) {
    const page = await browser.newPage();
    try {
      const response = await page.goto(source.source_url, {
        waitUntil: "domcontentloaded", timeout: 60000,
      });
      if (!response.ok()) throw new Error(`HTTP ${response.status()}`);
      const html = await page.content();
      const text = await page.evaluate(() => {
        const candidates = [...document.querySelectorAll(
          "article .entry-content, article .gh-content, .post-content, .entry-content, main, article"
        )].filter(el => el.innerText.trim().length > 500);
        const element = candidates[0] || document.body;
        const clone = element.cloneNode(true);
        clone.querySelectorAll(
          "script, style, nav, header, footer, form, figcaption, button, .sharedaddy, .post-navigation, .comments-area"
        ).forEach(el => el.remove());
        clone.querySelectorAll("p,li,h1,h2,h3,h4,h5,h6,blockquote,div,section,br").forEach(el => {
          el.appendChild(document.createTextNode("\n\n"));
        });
        return clone.textContent.replace(/\u00a0/g, " ").split("\n")
          .map(line => line.trim().replace(/[ \t]+/g, " ")).join("\n")
          .replace(/\n{3,}/g, "\n\n").trim();
      });
      if (text.length < 500 || /SITUS SLOT|Browser or app blocked/.test(text)) {
        throw new Error("Missing or unrelated source text");
      }
      const record = {
        ...source, final_url: page.url(), retrieved_at: new Date().toISOString(),
        html_sha256: hash(html), complete_text_sha256: hash(text),
        raw_html: `data/raw/dsa_caucuses/${source.document_id}.html`,
        text_file: `data/raw/dsa_caucuses/${source.document_id}.txt`,
        status: "retrieved",
      };
      await writeFile(`${root}/${record.raw_html}`, html);
      await writeFile(`${root}/${record.text_file}`, text);
      records.push(record);
      console.log(`${source.document_id}: ${text.split(/\s+/).length} words`);
    } catch (error) {
      records.push({ ...source, status: "retrieval_failed", error: String(error) });
      console.error(`${source.document_id}: ${error}`);
    } finally { await page.close(); }
  }
  await writeFile(`${output}/retrieval.json`, JSON.stringify(records, null, 2) + "\n");
  if (records.some(record => record.status !== "retrieved")) process.exitCode = 1;
} finally { await browser.close(); }
