import csv
import hashlib
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .io import read_csv, write_csv
from .paths import MANUAL_DIR, OUTPUT_DIR, PROCESSED_DIR, REPORT_DIR

FIGURE_DIR = OUTPUT_DIR / "figures" / "text_analysis"
TABLE_DIR = OUTPUT_DIR / "tables" / "text_analysis"

DSA_RED = "#D9272E"
DEMOCRATIC_BLUE = "#2F6DB0"
DARK = "#20242A"
MID = "#65707C"
LIGHT = "#D9DEE5"
BACKGROUND = "#FAF8F4"

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "among",
    "and",
    "any",
    "are",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "but",
    "can",
    "could",
    "did",
    "does",
    "doing",
    "each",
    "for",
    "from",
    "had",
    "has",
    "have",
    "here",
    "how",
    "into",
    "its",
    "just",
    "more",
    "most",
    "not",
    "our",
    "out",
    "over",
    "should",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "too",
    "under",
    "very",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
}

DOMAIN_STOPWORDS = {
    "area",
    "bring",
    "candidate",
    "campaign",
    "cause",
    "city",
    "community",
    "county",
    "ensure",
    "focus",
    "help",
    "ill",
    "increase",
    "issue",
    "lead",
    "many",
    "must",
    "need",
    "new",
    "officer",
    "people",
    "plan",
    "policy",
    "president",
    "priority",
    "public",
    "right",
    "seek",
    "state",
    "support",
    "system",
    "want",
    "work",
    "year",
}

PHRASE_PATTERNS = [
    (r"\bmedicare\s+for\s+all\b", "medicare_for_all"),
    (r"\bgreen\s+new\s+deal\b", "green_new_deal"),
    (r"\buniversal\s+basic\s+income\b", "universal_basic_income"),
    (r"\bsingle[-\s]+payer\b", "single_payer"),
    (r"\bpublic\s+option\b", "public_option"),
    (r"\brent\s+control\b", "rent_control"),
    (r"\bsocial\s+housing\b", "social_housing"),
    (r"\baffordable\s+housing\b", "affordable_housing"),
    (r"\bpublic\s+housing\b", "public_housing"),
    (r"\bliving\s+wage\b", "living_wage"),
    (r"\bminimum\s+wage\b", "minimum_wage"),
    (r"\bworking[-\s]+class\b", "working_class"),
    (r"\bsmall\s+business(?:es)?\b", "small_business"),
    (r"\bcollective\s+bargaining\b", "collective_bargaining"),
    (r"\bclimate\s+change\b", "climate_change"),
    (r"\bcriminal\s+justice\b", "criminal_justice"),
    (r"\bpublic\s+safety\b", "public_safety"),
    (r"\bhuman\s+rights?\b", "human_right"),
    (r"\bhealth\s+care\b", "healthcare"),
]


def analyze_text() -> dict[str, int | float]:
    evidence_path = PROCESSED_DIR / "candidate_statement_evidence.csv"
    sticking_path = PROCESSED_DIR / "primary_sticking_points.csv"
    excerpts_path = MANUAL_DIR / "excerpts.csv"
    evidence = read_csv(evidence_path)
    sticking_points = list(
        {
            row["sticking_point_id"]: row
            for row in read_csv(sticking_path)
        }.values()
    )
    excerpts = read_csv(excerpts_path)

    candidate_docs, candidate_rows = _candidate_corpus(evidence)
    official_docs = _official_corpus(excerpts)

    candidate_tfidf = group_tfidf(candidate_docs)
    candidate_mpif = mpif_rows(candidate_docs, "endorsed", "opponent")
    official_mpif = mpif_rows(official_docs, "dsa", "democratic")
    topic_rows = topic_comparison(candidate_rows)
    prevalence_rows = feature_prevalence(candidate_docs)
    coverage_rows = evidence_coverage(evidence)
    cycle_rows = sticking_point_cycles(sticking_points, evidence)
    sticking_rows = sticking_point_topics(sticking_points)

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        TABLE_DIR / "candidate_group_tfidf.csv",
        candidate_tfidf[:500],
        ["term", "endorsed_score", "opponent_score", "difference"],
    )
    write_csv(
        TABLE_DIR / "candidate_group_mpif.csv",
        candidate_mpif[:500],
        ["feature", "endorsed_count", "opponent_count", "z_score", "favored_group"],
    )
    write_csv(
        TABLE_DIR / "official_dsa_democratic_mpif.csv",
        official_mpif,
        ["feature", "dsa_count", "democratic_count", "z_score", "favored_group"],
    )
    write_csv(
        TABLE_DIR / "candidate_topic_comparison.csv",
        topic_rows,
        [
            "topic",
            "endorsed_excerpts",
            "opponent_excerpts",
            "endorsed_share",
            "opponent_share",
            "cosine_similarity",
        ],
    )
    write_csv(
        TABLE_DIR / "candidate_feature_prevalence.csv",
        prevalence_rows[:500],
        [
            "feature",
            "endorsed_documents",
            "opponent_documents",
            "endorsed_share",
            "opponent_share",
            "difference",
        ],
    )
    write_csv(
        TABLE_DIR / "candidate_evidence_coverage.csv",
        coverage_rows,
        ["group", "verified_documents", "source_unavailable_documents", "verified_share"],
    )
    write_csv(
        TABLE_DIR / "normalization_rules.csv",
        [
            {"pattern": pattern, "canonical_feature": feature}
            for pattern, feature in PHRASE_PATTERNS
        ],
        ["pattern", "canonical_feature"],
    )
    write_csv(
        TABLE_DIR / "sticking_points_by_topic.csv",
        sticking_rows,
        ["topic", "explicit_conflict", "coded_divergence", "total"],
    )
    write_csv(
        TABLE_DIR / "sticking_points_by_cycle.csv",
        cycle_rows,
        ["cycle", "explicit_conflict", "coded_divergence", "total"],
    )

    _candidate_tfidf_chart(candidate_tfidf)
    _mpif_chart(
        candidate_mpif,
        FIGURE_DIR / "candidate_mpif_terms.svg",
        "Most informative candidate language",
        "DSA-endorsed candidates compared with their Democratic primary opponents",
        "endorsed",
        "opponent",
    )
    _mpif_chart(
        official_mpif,
        FIGURE_DIR / "official_dsa_democratic_mpif.svg",
        "Most informative official language",
        "Official DSA statements compared with Democratic Party platform excerpts",
        "dsa",
        "democratic",
    )
    _topic_share_chart(topic_rows)
    _topic_difference_chart(topic_rows)
    _similarity_chart(topic_rows)
    _prevalence_chart(prevalence_rows)
    _coverage_chart(coverage_rows)
    _stacked_chart(
        sticking_rows[:14],
        FIGURE_DIR / "sticking_points_by_topic.svg",
        "Primary sticking points by issue",
        "Source-supported contrasts in the completed nationwide census",
        "topic",
    )
    _stacked_chart(
        cycle_rows,
        FIGURE_DIR / "sticking_points_by_cycle.svg",
        "Primary sticking points by election cycle",
        "Explicit conflicts and coded policy divergences",
        "cycle",
    )

    summary = {
        "candidate_documents": len(candidate_docs),
        "candidate_verified_excerpts": len(candidate_rows),
        "official_documents": len(official_docs),
        "candidate_tfidf_terms": len(candidate_tfidf),
        "candidate_mpif_features": len(candidate_mpif),
        "official_mpif_features": len(official_mpif),
        "prevalence_features": len(prevalence_rows),
        "topics": len(topic_rows),
        "sticking_points": len(sticking_points),
        "figure_count": 10,
        "input_hashes": {
            str(path.relative_to(path.parents[2])): _sha256(path)
            for path in (evidence_path, sticking_path, excerpts_path)
        },
        "parameters": {
            "tfidf_ngram": "unigram",
            "mpif_ngram": "unigram+bigrams",
            "mpif_prior_mass": 1000.0,
            "candidate_min_feature_count": 5,
            "official_min_feature_count": 1,
            "phrase_rules": len(PHRASE_PATTERNS),
            "domain_stopwords": len(DOMAIN_STOPWORDS),
        },
    }
    (TABLE_DIR / "analysis_manifest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_text_report(
        summary,
        candidate_mpif,
        official_mpif,
        topic_rows,
        prevalence_rows,
        coverage_rows,
        cycle_rows,
    )
    return summary


def tokenize(text: str) -> list[str]:
    normalized = (
        text.casefold()
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
    )
    for pattern, replacement in PHRASE_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized)
    tokens = re.findall(r"[a-z][a-z_'-]{1,}", normalized)
    cleaned = []
    for token in tokens:
        token = token.strip("-'")
        if token.endswith("'s"):
            token = token[:-2]
        token = _lemmatize(token)
        if len(token) > 2 and token not in STOPWORDS and token not in DOMAIN_STOPWORDS:
            cleaned.append(token)
    return cleaned


def _lemmatize(token: str) -> str:
    if "_" in token:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("sses"):
        return token[:-2]
    if token.endswith("s") and not token.endswith(("ss", "us", "is")) and len(token) > 4:
        return token[:-1]
    return token


def group_tfidf(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    tokenized = [tokenize(row["text"]) for row in documents]
    document_frequency = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    document_count = max(len(documents), 1)
    group_sums: dict[str, Counter[str]] = defaultdict(Counter)
    group_counts = Counter(row["group"] for row in documents)
    for row, tokens in zip(documents, tokenized, strict=True):
        counts = Counter(tokens)
        total = max(sum(counts.values()), 1)
        for term, count in counts.items():
            tf = count / total
            idf = math.log((1 + document_count) / (1 + document_frequency[term])) + 1
            group_sums[row["group"]][term] += tf * idf
    rows = []
    terms = set(group_sums["endorsed"]) | set(group_sums["opponent"])
    for term in terms:
        endorsed = group_sums["endorsed"][term] / max(group_counts["endorsed"], 1)
        opponent = group_sums["opponent"][term] / max(group_counts["opponent"], 1)
        rows.append(
            {
                "term": term,
                "endorsed_score": f"{endorsed:.8f}",
                "opponent_score": f"{opponent:.8f}",
                "difference": f"{endorsed - opponent:.8f}",
            }
        )
    return sorted(rows, key=lambda row: abs(float(row["difference"])), reverse=True)


def mpif_rows(
    documents: list[dict[str, str]],
    group_a: str,
    group_b: str,
    minimum_total: int | None = None,
) -> list[dict[str, str]]:
    counts = {group_a: Counter(), group_b: Counter()}
    for row in documents:
        if row["group"] not in counts:
            continue
        tokens = tokenize(row["text"])
        features = [*tokens, *(f"{a} {b}" for a, b in zip(tokens, tokens[1:], strict=False))]
        counts[row["group"]].update(features)
    pooled = counts[group_a] + counts[group_b]
    if minimum_total is None:
        minimum_total = 1 if {group_a, group_b} == {"dsa", "democratic"} else 5
    prior_mass = 1000.0
    pooled_total = max(sum(pooled.values()), 1)
    total_a = sum(counts[group_a].values())
    total_b = sum(counts[group_b].values())
    rows = []
    for feature, pooled_count in pooled.items():
        if pooled_count < minimum_total:
            continue
        alpha = prior_mass * pooled_count / pooled_total
        count_a = counts[group_a][feature]
        count_b = counts[group_b][feature]
        denominator_a = max(total_a + prior_mass - count_a - alpha, 1e-9)
        denominator_b = max(total_b + prior_mass - count_b - alpha, 1e-9)
        delta = math.log((count_a + alpha) / denominator_a) - math.log(
            (count_b + alpha) / denominator_b
        )
        variance = 1 / (count_a + alpha) + 1 / (count_b + alpha)
        z_score = delta / math.sqrt(variance)
        rows.append(
            {
                "feature": feature,
                f"{group_a}_count": str(count_a),
                f"{group_b}_count": str(count_b),
                "z_score": f"{z_score:.6f}",
                "favored_group": group_a if z_score >= 0 else group_b,
            }
        )
    return sorted(rows, key=lambda row: abs(float(row["z_score"])), reverse=True)


def topic_comparison(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    texts: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    totals = Counter()
    for row in rows:
        group = row["group"]
        topic = row["topic"] or "uncoded"
        counts[topic][group] += 1
        totals[group] += 1
        texts[topic][group].append(row["text"])
    output = []
    for topic in counts:
        endorsed_count = counts[topic]["endorsed"]
        opponent_count = counts[topic]["opponent"]
        output.append(
            {
                "topic": topic,
                "endorsed_excerpts": str(endorsed_count),
                "opponent_excerpts": str(opponent_count),
                "endorsed_share": f"{endorsed_count / max(totals['endorsed'], 1):.6f}",
                "opponent_share": f"{opponent_count / max(totals['opponent'], 1):.6f}",
                "cosine_similarity": f"{cosine_similarity(' '.join(texts[topic]['endorsed']), ' '.join(texts[topic]['opponent'])):.6f}",
            }
        )
    return sorted(
        output,
        key=lambda row: int(row["endorsed_excerpts"]) + int(row["opponent_excerpts"]),
        reverse=True,
    )


def feature_prevalence(documents: list[dict[str, str]]) -> list[dict[str, str]]:
    group_documents = Counter(row["group"] for row in documents)
    document_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in documents:
        tokens = tokenize(row["text"])
        features = set(tokens)
        features.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:], strict=False))
        document_counts[row["group"]].update(features)
    features = set(document_counts["endorsed"]) | set(document_counts["opponent"])
    rows = []
    for feature in features:
        endorsed_documents = document_counts["endorsed"][feature]
        opponent_documents = document_counts["opponent"][feature]
        total_documents = endorsed_documents + opponent_documents
        if total_documents < 10:
            continue
        endorsed_share = endorsed_documents / max(group_documents["endorsed"], 1)
        opponent_share = opponent_documents / max(group_documents["opponent"], 1)
        rows.append(
            {
                "feature": feature,
                "endorsed_documents": str(endorsed_documents),
                "opponent_documents": str(opponent_documents),
                "endorsed_share": f"{endorsed_share:.6f}",
                "opponent_share": f"{opponent_share:.6f}",
                "difference": f"{endorsed_share - opponent_share:.6f}",
            }
        )
    return sorted(rows, key=lambda row: abs(float(row["difference"])), reverse=True)


def evidence_coverage(evidence: list[dict[str, str]]) -> list[dict[str, str]]:
    statuses: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in evidence:
        group = "endorsed" if row["role"] in {"endorsed", "unopposed"} else "opponent"
        key = (
            row["candidate_name"].strip().casefold(),
            row["election_date"].strip(),
            group,
        )
        statuses[key].add(row["evidence_status"])
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for (*_, group), values in statuses.items():
        status = "verified" if "verified" in values else "source_unavailable"
        counts[group][status] += 1
    rows = []
    for group in ("endorsed", "opponent"):
        verified = counts[group]["verified"]
        unavailable = counts[group]["source_unavailable"]
        rows.append(
            {
                "group": group,
                "verified_documents": str(verified),
                "source_unavailable_documents": str(unavailable),
                "verified_share": f"{verified / max(verified + unavailable, 1):.6f}",
            }
        )
    return rows


def cosine_similarity(text_a: str, text_b: str) -> float:
    counts_a = Counter(tokenize(text_a))
    counts_b = Counter(tokenize(text_b))
    terms = set(counts_a) | set(counts_b)
    dot = sum(counts_a[term] * counts_b[term] for term in terms)
    norm_a = math.sqrt(sum(value * value for value in counts_a.values()))
    norm_b = math.sqrt(sum(value * value for value in counts_b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def sticking_point_topics(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[row["topic"]][row["contrast_type"]] += 1
    output = []
    for topic, values in counts.items():
        explicit = values["explicit_conflict"]
        coded = values["coded_divergence"]
        output.append(
            {
                "topic": topic,
                "explicit_conflict": str(explicit),
                "coded_divergence": str(coded),
                "total": str(explicit + coded),
            }
        )
    return sorted(output, key=lambda row: int(row["total"]), reverse=True)


def sticking_point_cycles(
    rows: list[dict[str, str]], evidence: list[dict[str, str]]
) -> list[dict[str, str]]:
    cycle_by_race = {}
    for row in evidence:
        if row["race_id"] and row["election_date"]:
            cycle_by_race[row["race_id"]] = row["election_date"][:4]
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        cycle = cycle_by_race.get(row["race_id"], "unknown")
        counts[cycle][row["contrast_type"]] += 1
    output = []
    for cycle, values in counts.items():
        explicit = values["explicit_conflict"]
        coded = values["coded_divergence"]
        output.append(
            {
                "cycle": cycle,
                "explicit_conflict": str(explicit),
                "coded_divergence": str(coded),
                "total": str(explicit + coded),
            }
        )
    return sorted(output, key=lambda row: row["cycle"])


def _candidate_corpus(
    evidence: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    quotes_by_document: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    seen_quotes = set()
    excerpt_rows = []
    for row in evidence:
        if row["evidence_status"] != "verified" or not row["quote"].strip():
            continue
        group = "endorsed" if row["role"] in {"endorsed", "unopposed"} else "opponent"
        candidate = row["candidate_name"].strip()
        election_date = row["election_date"].strip()
        quote_key = (candidate.casefold(), election_date, group, row["quote"].strip())
        if quote_key in seen_quotes:
            continue
        seen_quotes.add(quote_key)
        quotes_by_document[(candidate, election_date, group)].append(row["quote"].strip())
        excerpt_rows.append(
            {
                "group": group,
                "topic": row["topic"],
                "text": row["quote"].strip(),
            }
        )
    documents = [
        {
            "document_id": hashlib.sha256(
                f"{candidate}\n{election_date}\n{group}".encode()
            ).hexdigest()[:24],
            "group": group,
            "text": " ".join(quotes),
        }
        for (candidate, election_date, group), quotes in quotes_by_document.items()
    ]
    return documents, excerpt_rows


def _write_text_report(
    summary: dict[str, int | float],
    candidate_mpif: list[dict[str, str]],
    official_mpif: list[dict[str, str]],
    topic_rows: list[dict[str, str]],
    prevalence_rows: list[dict[str, str]],
    coverage_rows: list[dict[str, str]],
    cycle_rows: list[dict[str, str]],
) -> None:
    endorsed_terms = [
        row["feature"] for row in candidate_mpif if row["favored_group"] == "endorsed"
    ][:10]
    opponent_terms = [
        row["feature"] for row in candidate_mpif if row["favored_group"] == "opponent"
    ][:10]
    dsa_terms = [row["feature"] for row in official_mpif if row["favored_group"] == "dsa"][:8]
    democratic_terms = [
        row["feature"] for row in official_mpif if row["favored_group"] == "democratic"
    ][:8]
    lowest_similarity = sorted(
        topic_rows, key=lambda row: float(row["cosine_similarity"])
    )[:5]
    topic_differences = sorted(
        topic_rows,
        key=lambda row: abs(
            float(row["endorsed_share"]) - float(row["opponent_share"])
        ),
        reverse=True,
    )[:7]
    prevalence_positive = [
        row for row in prevalence_rows if float(row["difference"]) > 0
    ][:8]
    prevalence_negative = [
        row for row in prevalence_rows if float(row["difference"]) < 0
    ][:8]
    largest_cycles = sorted(cycle_rows, key=lambda row: int(row["total"]), reverse=True)[:5]
    text = f"""# DSA-versus-Democratic text analysis

This analysis is generated by `uv run dsa-analysis analyze-text` from the completed,
strictly validated census.

## Corpus

- Candidate/election documents: {summary["candidate_documents"]}
- Deduplicated verified candidate excerpts: {summary["candidate_verified_excerpts"]}
- Reviewed official DSA/DNC excerpts: {summary["official_documents"]}
- Unique source-supported primary contrasts: {summary["sticking_points"]}

Identical candidate quotations repeated through multiple chapter or National endorsement queues
are counted once per candidate and election.

## Methods

- **TF-IDF:** mean unigram TF-IDF by candidate group.
- **MPIF:** weighted log-odds z-scores with an informative Dirichlet prior, using unigrams and
  adjacent bigrams. Positive values favor DSA-endorsed candidates or DSA; negative values favor
  Democratic opponents or the DNC.
- **Document prevalence:** difference in the share of candidate/election documents containing a
  normalized feature. This prevents a few candidates who repeat a phrase many times from
  dominating the result.
- **Cosine similarity:** term-frequency similarity between endorsed-candidate and opponent
  language within each coded topic.
- **Sticking-point counts:** unique contrast IDs, separated into direct explicit conflicts and
  analyst-coded policy divergences.

## Main language differences

- DSA-endorsed candidate features: {", ".join(_label(term) for term in endorsed_terms)}.
- Democratic opponent features: {", ".join(_label(term) for term in opponent_terms)}.
- Official DSA features: {", ".join(_label(term) for term in dsa_terms)}.
- Official Democratic platform features: {", ".join(_label(term) for term in democratic_terms)}.

![Candidate MPIF terms](../outputs/figures/text_analysis/candidate_mpif_terms.svg)

![Candidate TF-IDF terms](../outputs/figures/text_analysis/candidate_tfidf_terms.svg)

![Official DSA and Democratic Party MPIF terms](../outputs/figures/text_analysis/official_dsa_democratic_mpif.svg)

The candidate comparison especially distinguishes rights-based housing and labor language
(`rent`, `human right`, `rent control`, `social housing`, `living wage`) from opponent language
that more often emphasizes business, opportunity, public-option mechanisms, technology,
training, and border administration.

## Document-prevalence robustness check

- More common across DSA-endorsed candidate documents:
  {", ".join(_label(row["feature"]) for row in prevalence_positive)}.
- More common across opponent documents:
  {", ".join(_label(row["feature"]) for row in prevalence_negative)}.

![Candidate feature prevalence](../outputs/figures/text_analysis/candidate_feature_prevalence.svg)

When MPIF and document prevalence point in the same direction, the result is less likely to be
driven by one unusually repetitive campaign.

## Issue emphasis

![Candidate topic shares](../outputs/figures/text_analysis/candidate_topic_shares.svg)

The largest group differences in excerpt share are:

{chr(10).join(f'- **{_label(row["topic"])}:** {(float(row["endorsed_share"]) - float(row["opponent_share"])):+.1%}' for row in topic_differences)}

Positive values indicate more emphasis among DSA-endorsed candidates.

![Topic emphasis difference](../outputs/figures/text_analysis/topic_emphasis_difference.svg)

## Topics with the least shared language

{chr(10).join(f'- **{_label(row["topic"])}:** {float(row["cosine_similarity"]):.2f}' for row in lowest_similarity)}

![Topic cosine similarity](../outputs/figures/text_analysis/topic_cosine_similarity.svg)

Low similarity identifies different vocabulary within an issue; it does not by itself prove
opposing policy positions.

## Cycles with the most recorded contrasts

{chr(10).join(f'- **{row["cycle"]}:** {row["total"]}' for row in largest_cycles)}

![Sticking points by topic](../outputs/figures/text_analysis/sticking_points_by_topic.svg)

![Sticking points by cycle](../outputs/figures/text_analysis/sticking_points_by_cycle.svg)

Counts depend on recoverable first-party material and the number of identified primaries in each
cycle. They are not measures of voter salience.

## Evidence coverage

{chr(10).join(f'- **{_label(row["group"])}:** {row["verified_documents"]} verified candidate/election documents, {row["source_unavailable_documents"]} documented source gaps ({float(row["verified_share"]):.1%} verified).' for row in coverage_rows)}

![Candidate evidence coverage](../outputs/figures/text_analysis/candidate_evidence_coverage.svg)

## Limitations

The official DSA-versus-DNC MPIF corpus is intentionally restricted to manually reviewed exact
excerpts, so it is much smaller than the candidate corpus. `source_unavailable` findings remain
unknowns rather than evidence of no position. Lexical distinctiveness measures language, not
ideology, sincerity, policy feasibility, or causal importance in election outcomes. Phrase
normalization reduces superficial variants, but it can also combine uses that differ in context;
the exact source quotations remain the authoritative evidence.
"""
    (REPORT_DIR / "text_analysis.md").write_text(text, encoding="utf-8")


def _official_corpus(excerpts: list[dict[str, str]]) -> list[dict[str, str]]:
    documents = []
    for row in excerpts:
        if row["reviewed"].casefold() != "true":
            continue
        if row["speaker"] == "DSA":
            group = "dsa"
        elif row["speaker"] == "Democratic National Committee":
            group = "democratic"
        else:
            continue
        documents.append(
            {
                "document_id": row["excerpt_id"],
                "group": group,
                "text": row["quote"],
            }
        )
    return documents


def _candidate_tfidf_chart(rows: list[dict[str, str]]) -> None:
    endorsed = sorted(
        (row for row in rows if float(row["difference"]) > 0),
        key=lambda row: float(row["difference"]),
        reverse=True,
    )[:12]
    opponent = sorted(
        (row for row in rows if float(row["difference"]) < 0),
        key=lambda row: float(row["difference"]),
    )[:12]
    selected = [*reversed(endorsed), *opponent]
    labels = [row["term"] for row in selected]
    values = [float(row["difference"]) for row in selected]
    _diverging_svg(
        FIGURE_DIR / "candidate_tfidf_terms.svg",
        "Distinctive TF-IDF terms",
        "Mean document TF-IDF: DSA-endorsed candidates versus Democratic opponents",
        labels,
        values,
        "DSA-endorsed",
        "Democratic opponents",
    )


def _mpif_chart(
    rows: list[dict[str, str]],
    path: Path,
    title: str,
    subtitle: str,
    positive_label: str,
    negative_label: str,
) -> None:
    positive = [row for row in rows if float(row["z_score"]) > 0][:12]
    negative = [row for row in rows if float(row["z_score"]) < 0][:12]
    selected = [*reversed(positive), *negative]
    _diverging_svg(
        path,
        title,
        subtitle,
        [row["feature"] for row in selected],
        [float(row["z_score"]) for row in selected],
        positive_label.replace("_", " ").title(),
        negative_label.replace("_", " ").title(),
    )


def _topic_share_chart(rows: list[dict[str, str]]) -> None:
    selected = rows[:13]
    width = 1100
    height = 180 + len(selected) * 42
    plot_left = 285
    plot_width = 720
    max_value = max(
        (
            max(float(row["endorsed_share"]), float(row["opponent_share"]))
            for row in selected
        ),
        default=1,
    )
    body = [_svg_header(width, height, "Issue emphasis by candidate group", "Share of verified excerpts coded to each topic")]
    for index, row in enumerate(selected):
        y = 120 + index * 42
        endorsed = float(row["endorsed_share"])
        opponent = float(row["opponent_share"])
        body.append(_text(270, y + 13, _label(row["topic"]), "end"))
        body.append(_rect(plot_left, y, plot_width * endorsed / max_value, 13, DSA_RED))
        body.append(_rect(plot_left, y + 17, plot_width * opponent / max_value, 13, DEMOCRATIC_BLUE))
    body.extend(
        [
            _legend(790, 72, DSA_RED, "DSA-endorsed"),
            _legend(925, 72, DEMOCRATIC_BLUE, "Democratic opponents"),
            _svg_footer(width, height, "Source: verified first-party candidate statements; duplicate queue copies removed."),
        ]
    )
    _write_svg(FIGURE_DIR / "candidate_topic_shares.svg", width, height, body)


def _similarity_chart(rows: list[dict[str, str]]) -> None:
    selected = sorted(rows, key=lambda row: float(row["cosine_similarity"]), reverse=True)[:14]
    _horizontal_svg(
        FIGURE_DIR / "topic_cosine_similarity.svg",
        "Language similarity within issues",
        "Cosine similarity between endorsed-candidate and opponent wording",
        [_label(row["topic"]) for row in selected],
        [float(row["cosine_similarity"]) for row in selected],
        DEMOCRATIC_BLUE,
        maximum=1.0,
    )


def _topic_difference_chart(rows: list[dict[str, str]]) -> None:
    selected = sorted(
        rows,
        key=lambda row: abs(
            float(row["endorsed_share"]) - float(row["opponent_share"])
        ),
        reverse=True,
    )[:13]
    _diverging_svg(
        FIGURE_DIR / "topic_emphasis_difference.svg",
        "Difference in issue emphasis",
        "Share of verified excerpts: DSA-endorsed candidates minus Democratic opponents",
        [_label(row["topic"]) for row in selected],
        [
            float(row["endorsed_share"]) - float(row["opponent_share"])
            for row in selected
        ],
        "More endorsed-candidate emphasis",
        "More opponent emphasis",
    )


def _prevalence_chart(rows: list[dict[str, str]]) -> None:
    positive = [row for row in rows if float(row["difference"]) > 0][:12]
    negative = [row for row in rows if float(row["difference"]) < 0][:12]
    selected = [*reversed(positive), *negative]
    _diverging_svg(
        FIGURE_DIR / "candidate_feature_prevalence.svg",
        "Distinctive feature prevalence",
        "Difference in the share of candidate/election documents containing each feature",
        [_label(row["feature"]) for row in selected],
        [float(row["difference"]) for row in selected],
        "More DSA-endorsed documents",
        "More opponent documents",
    )


def _coverage_chart(rows: list[dict[str, str]]) -> None:
    width = 900
    height = 300
    plot_left = 210
    plot_width = 590
    maximum = max(
        (
            int(row["verified_documents"]) + int(row["source_unavailable_documents"])
            for row in rows
        ),
        default=1,
    )
    body = [
        _svg_header(
            width,
            height,
            "First-party evidence coverage",
            "Candidate/election documents with verified text versus documented source gaps",
        )
    ]
    for index, row in enumerate(rows):
        y = 115 + index * 65
        verified = int(row["verified_documents"])
        unavailable = int(row["source_unavailable_documents"])
        verified_width = plot_width * verified / maximum
        unavailable_width = plot_width * unavailable / maximum
        body.append(_text(195, y + 16, _label(row["group"]), "end"))
        body.append(_rect(plot_left, y, verified_width, 24, DSA_RED))
        body.append(_rect(plot_left + verified_width, y, unavailable_width, 24, LIGHT))
        body.append(_text(plot_left + verified_width - 7, y + 17, str(verified), "end", "#FFFFFF"))
        body.append(
            _text(
                plot_left + verified_width + unavailable_width + 8,
                y + 17,
                f"{float(row['verified_share']):.0%} verified",
            )
        )
    body.extend(
        [
            _legend(555, 72, DSA_RED, "Verified text"),
            _legend(670, 72, LIGHT, "Source unavailable"),
            _svg_footer(width, height, "Coverage status is explicit; unavailable text is not treated as no position."),
        ]
    )
    _write_svg(FIGURE_DIR / "candidate_evidence_coverage.svg", width, height, body)


def _stacked_chart(
    rows: list[dict[str, str]], path: Path, title: str, subtitle: str, label_key: str
) -> None:
    width = 1100
    height = 170 + len(rows) * 38
    plot_left = 270
    plot_width = 725
    maximum = max((int(row["total"]) for row in rows), default=1)
    body = [_svg_header(width, height, title, subtitle)]
    for index, row in enumerate(rows):
        y = 115 + index * 38
        explicit = int(row["explicit_conflict"])
        coded = int(row["coded_divergence"])
        explicit_width = plot_width * explicit / maximum
        coded_width = plot_width * coded / maximum
        body.append(_text(255, y + 14, _label(row[label_key]), "end"))
        body.append(_rect(plot_left, y, explicit_width, 18, DSA_RED))
        body.append(_rect(plot_left + explicit_width, y, coded_width, 18, DEMOCRATIC_BLUE))
        body.append(_text(plot_left + explicit_width + coded_width + 8, y + 14, row["total"]))
    body.extend(
        [
            _legend(805, 72, DSA_RED, "Explicit conflict"),
            _legend(935, 72, DEMOCRATIC_BLUE, "Coded divergence"),
            _svg_footer(width, height, "Counts are source-supported contrasts, not inferred positions."),
        ]
    )
    _write_svg(path, width, height, body)


def _diverging_svg(
    path: Path,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[float],
    positive_label: str,
    negative_label: str,
) -> None:
    width = 1100
    height = 170 + len(labels) * 32
    center = 550
    half_width = 390
    maximum = max((abs(value) for value in values), default=1)
    body = [_svg_header(width, height, title, subtitle), _line(center, 102, center, height - 48, LIGHT)]
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 112 + index * 32
        bar_width = half_width * abs(value) / maximum
        if value >= 0:
            body.append(_rect(center, y, bar_width, 18, DSA_RED))
            body.append(_text(center - 10, y + 14, label, "end"))
        else:
            body.append(_rect(center - bar_width, y, bar_width, 18, DEMOCRATIC_BLUE))
            body.append(_text(center + 10, y + 14, label))
    body.extend(
        [
            _text(center + 200, 86, positive_label, "middle", DSA_RED, "12px"),
            _text(center - 200, 86, negative_label, "middle", DEMOCRATIC_BLUE, "12px"),
            _svg_footer(width, height, "Positive scores favor the red group; negative scores favor the blue group."),
        ]
    )
    _write_svg(path, width, height, body)


def _horizontal_svg(
    path: Path,
    title: str,
    subtitle: str,
    labels: list[str],
    values: list[float],
    color: str,
    maximum: float | None = None,
) -> None:
    width = 1050
    height = 170 + len(labels) * 36
    plot_left = 280
    plot_width = 650
    maximum = maximum or max(values, default=1)
    body = [_svg_header(width, height, title, subtitle)]
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 110 + index * 36
        body.append(_text(265, y + 14, label, "end"))
        body.append(_rect(plot_left, y, plot_width * value / maximum, 18, color))
        body.append(_text(plot_left + plot_width * value / maximum + 8, y + 14, f"{value:.2f}"))
    body.append(_svg_footer(width, height, "Similarity ranges from 0 (no shared vocabulary) to 1 (identical term proportions)."))
    _write_svg(path, width, height, body)


def _svg_header(width: int, height: int, title: str, subtitle: str) -> str:
    return (
        _rect(0, 0, width, height, BACKGROUND)
        + _text(42, 42, title, color=DARK, size="24px", weight="700")
        + _text(42, 68, subtitle, color=MID, size="13px")
    )


def _svg_footer(width: int, height: int, text: str) -> str:
    return _text(42, height - 20, text, color=MID, size="11px")


def _rect(x: float, y: float, width: float, height: float, color: str) -> str:
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(width, 0):.2f}" '
        f'height="{height:.2f}" fill="{color}" rx="2"/>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, color: str) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"/>'


def _text(
    x: float,
    y: float,
    value: str,
    anchor: str = "start",
    color: str = DARK,
    size: str = "12px",
    weight: str = "400",
) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}">{html.escape(str(value))}</text>'
    )


def _legend(x: float, y: float, color: str, label: str) -> str:
    return _rect(x, y - 10, 12, 12, color) + _text(x + 18, y, label, size="11px")


def _write_svg(path: Path, width: int, height: int, body: list[str]) -> None:
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">{"".join(body)}</svg>\n',
        encoding="utf-8",
    )


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
