import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .io import read_csv, read_json, write_csv
from .paths import ANALYSIS_DATA_DIR, CONFIG_DIR, OUTPUT_DIR, REPORT_DIR
from .text_analysis import _diverging_svg

MODEL_OUTPUT = ANALYSIS_DATA_DIR / "model_topic_classifications.csv"
MODEL_SUMMARY = ANALYSIS_DATA_DIR / "model_topic_validation.json"
MODEL_EMPHASIS = OUTPUT_DIR / "tables" / "text_analysis" / "model_topic_emphasis.csv"
MODEL_FIGURE = (
    OUTPUT_DIR / "figures" / "text_analysis" / "model_topic_emphasis_difference.svg"
)


@dataclass(frozen=True, slots=True)
class Topic:
    code: int
    name: str
    description: str
    seeds: tuple[str, ...]

    @property
    def embedding_text(self) -> str:
        return f"{self.name}. {self.description} Examples: {', '.join(self.seeds)}."


def classify_model_topics() -> dict[str, int | float | str]:
    corpus_path = ANALYSIS_DATA_DIR / "candidate_text_corpus.csv"
    if not corpus_path.exists():
        raise FileNotFoundError("Run `dsa-analysis analyze-text` first")
    corpus = [
        row
        for row in read_csv(corpus_path)
        if row["evidence_status"] == "verified" and row["quote"].strip()
    ]
    config = read_json(CONFIG_DIR / "cap_topics.json")
    topics = [
        Topic(
            code=int(row["code"]),
            name=row["name"],
            description=row["description"],
            seeds=tuple(row["seeds"]),
        )
        for row in config["topics"]
    ]
    minimum_similarity = float(config["minimum_similarity"])
    model_name = config["model"]
    model, device = _load_model(model_name)
    topic_vectors = model.encode(
        [topic.embedding_text for topic in topics],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    texts = [row["quote"] for row in corpus]
    vectors = model.encode(
        texts,
        batch_size=64,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )
    similarities = vectors @ topic_vectors.T
    keyword_patterns = _keyword_patterns(topics)
    rows = []
    for source, scores in zip(corpus, similarities, strict=True):
        order = scores.argsort()[::-1]
        best_index = int(order[0])
        second_index = int(order[1])
        similarity = float(scores[best_index])
        runner_up_similarity = float(scores[second_index])
        topic = topics[best_index] if similarity >= minimum_similarity else None
        keyword_code, keyword_score = _keyword_predict(
            source["quote"], topics, keyword_patterns
        )
        rows.append(
            {
                "statement_key": source["statement_key"],
                "race_id": source["race_id"],
                "candidate_name": source["candidate_name"],
                "election_date": source["election_date"],
                "group": (
                    "endorsed"
                    if source["role"] in {"endorsed", "unopposed"}
                    else "opponent"
                ),
                "quote": source["quote"],
                "source_url": source["source_url"],
                "model_name": model_name,
                "device": device,
                "topic_code": str(topic.code) if topic else "",
                "topic_name": topic.name if topic else "Unclassified",
                "similarity": f"{similarity:.6f}",
                "runner_up_code": str(topics[second_index].code),
                "runner_up_name": topics[second_index].name,
                "runner_up_similarity": f"{runner_up_similarity:.6f}",
                "margin": f"{similarity - runner_up_similarity:.6f}",
                "keyword_topic_code": str(keyword_code or ""),
                "keyword_score": f"{keyword_score:.6f}",
                "keyword_agrees": str(
                    bool(topic and keyword_code == topic.code)
                ).lower(),
                "reviewed_topic": source["topic"],
            }
        )
    write_csv(
        MODEL_OUTPUT,
        rows,
        [
            "statement_key",
            "race_id",
            "candidate_name",
            "election_date",
            "group",
            "quote",
            "source_url",
            "model_name",
            "device",
            "topic_code",
            "topic_name",
            "similarity",
            "runner_up_code",
            "runner_up_name",
            "runner_up_similarity",
            "margin",
            "keyword_topic_code",
            "keyword_score",
            "keyword_agrees",
            "reviewed_topic",
        ],
    )
    validation = _validation_summary(rows)
    emphasis = _topic_emphasis(rows)
    write_csv(
        MODEL_EMPHASIS,
        emphasis,
        [
            "topic_code",
            "topic_name",
            "endorsed_quotes",
            "opponent_quotes",
            "endorsed_share",
            "opponent_share",
            "difference",
            "mean_similarity",
            "mean_margin",
        ],
    )
    selected = sorted(
        emphasis, key=lambda row: abs(float(row["difference"])), reverse=True
    )[:14]
    _diverging_svg(
        MODEL_FIGURE,
        "Difference in model-classified policy emphasis",
        (
            "Local all-MiniLM-L6-v2 classification using Comparative Agendas "
            "Project topic descriptions"
        ),
        [row["topic_name"] for row in selected],
        [float(row["difference"]) for row in selected],
        "More DSA-endorsed quotation share",
        "More opponent quotation share",
        (
            "Source: data/analysis/model_topic_classifications.csv; local model only; "
            f"minimum cosine similarity {minimum_similarity:.2f}; exact quotes and URLs retained."
        ),
    )
    summary = {
        **validation,
        "model_name": model_name,
        "device": device,
        "minimum_similarity": minimum_similarity,
        "classified_rows": sum(bool(row["topic_code"]) for row in rows),
        "unclassified_rows": sum(not row["topic_code"] for row in rows),
        "total_rows": len(rows),
    }
    MODEL_SUMMARY.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_model_report(summary, emphasis)
    return summary


def _load_model(model_name: str):
    try:
        import torch
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "Install local model dependencies with `uv sync --extra models`"
        ) from error
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    return SentenceTransformer(model_name, device=device), device


def _keyword_patterns(topics: list[Topic]):
    return {
        topic.code: [
            re.compile(rf"\b{re.escape(seed)}\b", re.IGNORECASE)
            for seed in topic.seeds
        ]
        for topic in topics
    }


def _keyword_predict(text: str, topics: list[Topic], patterns):
    best_code = None
    best_score = 0.0
    for topic in topics:
        hits = sum(bool(pattern.search(text)) for pattern in patterns[topic.code])
        score = hits / max(len(patterns[topic.code]), 1) ** 0.5
        if score > best_score:
            best_code = topic.code
            best_score = score
    return best_code, best_score


def _validation_summary(rows: list[dict[str, str]]) -> dict[str, int | float]:
    crosswalk = {
        key: int(value)
        for key, value in read_json(CONFIG_DIR / "topic_crosswalk.json")[
            "mapping"
        ].items()
    }
    comparable = [
        row
        for row in rows
        if row["reviewed_topic"] in crosswalk and row["topic_code"]
    ]
    correct = sum(
        int(row["topic_code"]) == crosswalk[row["reviewed_topic"]]
        for row in comparable
    )
    keyword_comparable = [row for row in rows if row["keyword_topic_code"]]
    keyword_agreement = sum(
        row["keyword_agrees"] == "true" for row in keyword_comparable
    )
    return {
        "crosswalk_rows": len(comparable),
        "crosswalk_agreement": correct / max(len(comparable), 1),
        "keyword_rows": len(keyword_comparable),
        "model_keyword_agreement": keyword_agreement
        / max(len(keyword_comparable), 1),
        "low_margin_rows": sum(float(row["margin"]) < 0.03 for row in rows),
    }


def _topic_emphasis(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    similarities: dict[tuple[str, str], list[float]] = defaultdict(list)
    margins: dict[tuple[str, str], list[float]] = defaultdict(list)
    totals = Counter()
    for row in rows:
        if not row["topic_code"]:
            continue
        key = (row["topic_code"], row["topic_name"])
        counts[key][row["group"]] += 1
        totals[row["group"]] += 1
        similarities[key].append(float(row["similarity"]))
        margins[key].append(float(row["margin"]))
    output = []
    for (code, name), values in counts.items():
        endorsed = values["endorsed"]
        opponent = values["opponent"]
        endorsed_share = endorsed / max(totals["endorsed"], 1)
        opponent_share = opponent / max(totals["opponent"], 1)
        output.append(
            {
                "topic_code": code,
                "topic_name": name,
                "endorsed_quotes": str(endorsed),
                "opponent_quotes": str(opponent),
                "endorsed_share": f"{endorsed_share:.6f}",
                "opponent_share": f"{opponent_share:.6f}",
                "difference": f"{endorsed_share - opponent_share:.6f}",
                "mean_similarity": f"{sum(similarities[(code, name)]) / len(similarities[(code, name)]):.6f}",
                "mean_margin": f"{sum(margins[(code, name)]) / len(margins[(code, name)]):.6f}",
            }
        )
    return output


def _write_model_report(summary: dict, emphasis: list[dict[str, str]]) -> None:
    largest = sorted(
        emphasis, key=lambda row: abs(float(row["difference"])), reverse=True
    )[:10]
    text = f"""# Local-model topic analysis

This analysis is generated by `uv run dsa-analysis analyze-text` using the pinned local model
`{summary["model_name"]}` on `{summary["device"]}`.

## Real source input

- Every classified row comes from `data/analysis/candidate_text_corpus.csv`.
- Every row retains the exact candidate quotation and source URL.
- The model sees the quotation text; it does not generate replacement text or factual claims.
- Full outputs, similarity scores, runner-up topics and margins are committed at
  `data/analysis/model_topic_classifications.csv`.

## Model and taxonomy

- Taxonomy: Comparative Agendas Project major topic codes in `config/cap_topics.json`.
- Classified rows: {summary["classified_rows"]:,}
- Unclassified below the {summary["minimum_similarity"]:.2f} threshold:
  {summary["unclassified_rows"]:,}
- Rows with runner-up margin below 0.03: {summary["low_margin_rows"]:,}
- Agreement with the existing reviewed-code crosswalk:
  {summary["crosswalk_agreement"]:.1%} across {summary["crosswalk_rows"]:,} comparable rows.
- Agreement with the transparent keyword baseline:
  {summary["model_keyword_agreement"]:.1%} across {summary["keyword_rows"]:,} rows with a keyword
  prediction.

The crosswalk comparison is a diagnostic, not an independent gold-standard accuracy estimate.
Every classification remains inspectable at row level.

## Largest modeled emphasis differences

{chr(10).join(f'- **{row["topic_name"]}:** {float(row["difference"]):+.1%} ({row["endorsed_quotes"]} endorsed-candidate quotations; {row["opponent_quotes"]} opponent quotations; mean similarity {float(row["mean_similarity"]):.2f}; mean margin {float(row["mean_margin"]):.2f})' for row in largest)}

![Model-classified policy emphasis](../outputs/figures/text_analysis/model_topic_emphasis_difference.svg)

Positive differences indicate a larger share of classified DSA-endorsed quotations. Negative
differences indicate a larger share of classified opponent quotations.

## Limitations

This is a descriptive local embedding classifier. Similarity to a topic description does not
establish support, opposition, sincerity, importance, or causality. Low-similarity and low-margin
rows should be treated cautiously and can be filtered directly from the committed output.
"""
    (REPORT_DIR / "model_topic_analysis.md").write_text(text, encoding="utf-8")
