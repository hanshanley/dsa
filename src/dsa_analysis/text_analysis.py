import csv
import hashlib
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .io import read_csv, write_csv
from .paths import ANALYSIS_DATA_DIR, MANUAL_DIR, OUTPUT_DIR, PROCESSED_DIR, REPORT_DIR

FIGURE_DIR = OUTPUT_DIR / "figures" / "text_analysis"
TABLE_DIR = OUTPUT_DIR / "tables" / "text_analysis"
CORPUS_PATH = ANALYSIS_DATA_DIR / "candidate_text_corpus.csv"
OFFICIAL_CORPUS_PATH = ANALYSIS_DATA_DIR / "organizational_context_text_corpus.csv"
STICKING_SNAPSHOT_PATH = ANALYSIS_DATA_DIR / "primary_sticking_points.csv"
CANDIDATE_SEGMENTS_PATH = PROCESSED_DIR / "candidate_document_analysis_segments.csv"
CANDIDATE_METADATA_PATH = PROCESSED_DIR / "candidate_document_metadata.csv"
OFFICIAL_SEGMENTS_PATH = PROCESSED_DIR / "organizational_context_analysis_segments.csv"
OFFICIAL_INVENTORY_PATH = PROCESSED_DIR / "organizational_context_inventory.csv"
ORGANIZATIONAL_SUMMARY_PATH = PROCESSED_DIR / "organizational_context_summary.json"
FULL_TEXT_QUEUE_SUMMARY_PATH = PROCESSED_DIR / "full_text_queue_summary.csv"
SUBSTANTIVE_MIN_TOKENS = 20
OFFICIAL_CATEGORY_GROUPS = {
    "dsa_national": "dsa",
    "dsa_state_local": "dsa",
    "dnc_national": "democratic",
    "state_democratic_party": "democratic",
}
POLICY_FEATURES = {
    "affordable_housing",
    "border",
    "business",
    "climate_change",
    "collective_bargaining",
    "corporate",
    "eviction",
    "green_new_deal",
    "healthcare",
    "human_right",
    "living_wage",
    "market",
    "medicare_for_all",
    "minimum_wage",
    "public_housing",
    "public_option",
    "rent",
    "rent_control",
    "single_payer",
    "small_business",
    "social_housing",
    "technology",
    "tenant",
    "training",
    "union",
    "universal_basic_income",
    "worker",
    "working_class",
}
SHARED_MECHANISM_FEATURES = {
    "affordable_housing",
    "collective_bargaining",
    "green_new_deal",
    "living_wage",
    "medicare_for_all",
    "minimum_wage",
    "public_housing",
    "public_option",
    "rent_control",
    "single_payer",
    "social_housing",
    "universal_basic_income",
}

DSA_RED = "#C85A3D"
DEMOCRATIC_BLUE = "#3D6F8C"
GOLD = "#C2993E"
GREEN = "#4A7C59"
DARK = "#1A1A1A"
MID = "#6B6B6B"
LIGHT = "#D6D3CC"
BACKGROUND = "#F7F5F0"
CARD = "#EFEDE8"

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
    "he",
    "he'd",
    "he'll",
    "he's",
    "her",
    "hers",
    "herself",
    "here",
    "him",
    "himself",
    "his",
    "how",
    "i'd",
    "i'll",
    "i'm",
    "i've",
    "into",
    "it",
    "it'd",
    "it'll",
    "it's",
    "itself",
    "its",
    "just",
    "more",
    "most",
    "my",
    "myself",
    "not",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "she",
    "she'd",
    "she'll",
    "she's",
    "should",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
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
    "we",
    "we'd",
    "we'll",
    "we're",
    "we've",
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
    "you'd",
    "you'll",
    "you're",
    "you've",
    "your",
    "yours",
    "yourself",
    "yourselves",
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
    "endorsement",
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
    "platform",
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
    "volunteer",
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
    comparisons_path = MANUAL_DIR / "platform_comparisons.csv"
    evidence, sticking_points = _load_or_export_analysis_data(
        evidence_path, sticking_path
    )
    excerpts = read_csv(excerpts_path)
    platform_comparisons = read_csv(comparisons_path)

    candidate_docs, candidate_rows = _candidate_segment_corpus()
    official_docs, official_rows = _official_segment_corpus()

    candidate_tfidf = group_tfidf(candidate_docs)
    candidate_mpif = mpif_rows(candidate_docs, "endorsed", "opponent")
    official_mpif = mpif_rows(official_docs, "dsa", "democratic")
    official_prevalence_rows = official_feature_prevalence(official_docs)
    official_document_counts = Counter(row["group"] for row in official_docs)
    official_category_counts = Counter(row["category"] for row in official_docs)
    official_segment_counts = Counter(row["group"] for row in official_rows)
    organizational_summary = json.loads(
        ORGANIZATIONAL_SUMMARY_PATH.read_text(encoding="utf-8")
    )
    prevalence_rows = feature_prevalence(candidate_docs)
    overlap_rows = policy_overlap_rows(prevalence_rows)
    shared_mechanism_rows = shared_affirmative_mechanisms()
    shared_mechanism_summary = _shared_mechanism_summary(shared_mechanism_rows)
    coverage_rows = candidate_record_coverage()
    volume_rows = verified_segment_volume(candidate_rows)
    source_type_rows = source_type_comparison(candidate_rows)
    explicit_cycle_rows = explicit_conflicts_by_cycle(sticking_points, candidate_rows)

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for old_figure in FIGURE_DIR.glob("*.svg"):
        if old_figure.name != "model_topic_emphasis_difference.svg":
            old_figure.unlink()
    for obsolete_table in (
        "candidate_topic_comparison.csv",
        "topic_excerpt_provenance.csv",
        "sticking_points_by_topic.csv",
        "sticking_points_by_cycle.csv",
    ):
        (TABLE_DIR / obsolete_table).unlink(missing_ok=True)
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
        official_mpif[:500],
        ["feature", "dsa_count", "democratic_count", "z_score", "favored_group"],
    )
    write_csv(
        TABLE_DIR / "official_platform_document_prevalence.csv",
        official_prevalence_rows,
        [
            "feature",
            "dsa_documents",
            "democratic_documents",
            "dsa_share",
            "democratic_share",
            "difference",
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
        TABLE_DIR / "candidate_policy_overlap.csv",
        overlap_rows,
        [
            "feature",
            "endorsed_share",
            "opponent_share",
            "shared_emphasis",
            "share_gap",
        ],
    )
    write_csv(
        TABLE_DIR / "shared_affirmative_policy_mechanisms.csv",
        shared_mechanism_rows,
        [
            "race_id",
            "feature",
            "endorsed_candidates",
            "opponent_candidates",
            "endorsed_example",
            "opponent_example",
        ],
    )
    write_csv(
        TABLE_DIR / "shared_affirmative_policy_mechanism_summary.csv",
        shared_mechanism_summary,
        ["feature", "race_count"],
    )
    write_csv(
        TABLE_DIR / "candidate_evidence_coverage.csv",
        coverage_rows,
        [
            "group",
            "candidate_race_records_with_extracted_text",
            "candidate_race_records_without_extracted_text",
            "extracted_share",
        ],
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
        TABLE_DIR / "verified_excerpt_volume_by_cycle.csv",
        volume_rows,
        ["cycle", "endorsed_segments", "opponent_segments", "total"],
    )
    write_csv(
        TABLE_DIR / "source_types_by_group.csv",
        source_type_rows,
        [
            "source_type",
            "endorsed_segments",
            "opponent_segments",
            "endorsed_share",
            "opponent_share",
            "difference",
        ],
    )
    write_csv(
        TABLE_DIR / "explicit_conflicts_by_cycle.csv",
        explicit_cycle_rows,
        ["cycle", "explicit_conflicts"],
    )

    _policy_language_chart(prevalence_rows)
    _policy_overlap_chart(overlap_rows)
    _shared_mechanism_chart(shared_mechanism_summary)
    _official_contrast_chart(platform_comparisons, excerpts)
    _official_platform_prevalence_chart(
        official_prevalence_rows,
        official_document_counts,
    )
    _volume_cycle_chart(volume_rows)
    _source_type_chart(source_type_rows)
    _coverage_chart(coverage_rows)
    _explicit_cycle_chart(explicit_cycle_rows)

    summary = {
        "candidate_documents": len(candidate_docs),
        "candidate_source_documents": len(
            {
                document_id
                for row in candidate_rows
                for document_id in _split_values(row["document_ids"])
            }
        ),
        "candidate_source_segments": sum(
            int(row["provenance_row_count"]) for row in candidate_rows
        ),
        "candidate_segments": len(candidate_rows),
        "official_documents": len(official_docs),
        "official_documents_by_group": dict(sorted(official_document_counts.items())),
        "official_documents_by_category": dict(sorted(official_category_counts.items())),
        "organizational_platform_gap_rows": organizational_summary["coverage"][
            "platform_gap_rows"
        ],
        "official_source_segments": sum(
            int(row["provenance_row_count"]) for row in official_rows
        ),
        "official_segments": len(official_rows),
        "official_segments_by_group": dict(sorted(official_segment_counts.items())),
        "candidate_tfidf_terms": len(candidate_tfidf),
        "candidate_mpif_features": len(candidate_mpif),
        "official_mpif_features": len(official_mpif),
        "prevalence_features": len(prevalence_rows),
        "sticking_points": len(sticking_points),
        "figure_count": len(list(FIGURE_DIR.glob("*.svg"))),
        "generated_figure_count": 9,
        "shared_affirmative_mechanism_rows": len(shared_mechanism_rows),
        "input_hashes": {
            str(path.relative_to(path.parents[2])): _sha256(path)
            for path in (
                CORPUS_PATH,
                OFFICIAL_CORPUS_PATH,
                FULL_TEXT_QUEUE_SUMMARY_PATH,
                STICKING_SNAPSHOT_PATH,
                excerpts_path,
                comparisons_path,
            )
        },
        "lineage": {
            "candidate_corpus": {
                "generated_from": [
                    "data/processed/candidate_document_analysis_segments.csv",
                    "data/processed/candidate_document_metadata.csv",
                ],
                "generator": "dsa_analysis.document_corpus.run_candidate_document_regather_batch",
                "analysis_snapshot": "data/analysis/candidate_text_corpus.csv",
                "eligibility": (
                    "nonempty segment; token_count >= 20; boilerplate_flag=false"
                ),
                "deduplication": (
                    "one exact-text segment per endorsed/opponent group and election cycle; "
                    "all candidate, race, document, locator, and source provenance retained"
                ),
            },
            "official_corpus": {
                "generated_from": (
                    "data/processed/organizational_context_analysis_segments.csv"
                ),
                "generator": (
                    "dsa_analysis.organizational_context_corpus."
                    "run_organizational_context_extraction_batch"
                ),
                "analysis_snapshot": (
                    "data/analysis/organizational_context_text_corpus.csv"
                ),
                "eligibility": (
                    "full_platform_categories present; at least one contributing context entry "
                    "currently verification_status=verified; nonempty segment; "
                    "token_count >= 20; boilerplate_flag=false; combined platform/governance "
                    "documents restricted to the platform section"
                ),
                "category_grouping": OFFICIAL_CATEGORY_GROUPS,
            },
            "candidate_coverage": {
                "generated_from": "data/processed/full_text_queue_summary.csv",
                "denominator": "registry-wide candidate/race records",
                "extracted_status": "verified",
                "without_extracted_text": "all statuses other than verified",
            },
            "sticking_points": {
                "generated_from": "data/processed/primary_sticking_points.csv",
                "generator": "dsa_analysis.sticking_points.analyze_sticking_points",
                "analysis_snapshot": "data/analysis/primary_sticking_points.csv",
            },
        },
        "parameters": {
            "tfidf_ngram": "unigram",
            "mpif_ngram": "unigram+bigrams",
            "mpif_prior_mass": 1000.0,
            "candidate_min_feature_count": 5,
            "official_min_feature_count": 1,
            "published_feature_row_limit": 500,
            "substantive_min_tokens": SUBSTANTIVE_MIN_TOKENS,
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
        official_prevalence_rows,
        prevalence_rows,
        overlap_rows,
        shared_mechanism_summary,
        coverage_rows,
        volume_rows,
        source_type_rows,
        explicit_cycle_rows,
    )
    return summary


def _load_or_export_analysis_data(
    evidence_path: Path, sticking_path: Path
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    ANALYSIS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if evidence_path.exists() and sticking_path.exists():
        evidence = _deduplicate_analysis_evidence(read_csv(evidence_path))
        sticking_points = list(
            {
                row["sticking_point_id"]: row
                for row in read_csv(sticking_path)
            }.values()
        )
        write_csv(
            STICKING_SNAPSHOT_PATH,
            sticking_points,
            [
                "sticking_point_id",
                "race_id",
                "topic",
                "subtopic",
                "candidate_a",
                "candidate_b",
                "contrast_type",
                "relationship_code",
                "candidate_a_quote",
                "candidate_b_quote",
                "candidate_a_source",
                "candidate_b_source",
            ],
        )
        return evidence, sticking_points
    sticking_points = (
        read_csv(sticking_path)
        if sticking_path.exists()
        else read_csv(STICKING_SNAPSHOT_PATH)
    )
    return [], sticking_points


def _deduplicate_analysis_evidence(
    evidence: list[dict[str, str]],
) -> list[dict[str, str]]:
    deduplicated = {}
    for row in evidence:
        group = "endorsed" if row["role"] in {"endorsed", "unopposed"} else "opponent"
        candidate = row["candidate_name"].strip().casefold()
        election_date = row["election_date"].strip()
        if row["evidence_status"] == "verified":
            key = (
                candidate,
                election_date,
                group,
                row["topic"],
                row["quote"].strip(),
            )
        else:
            key = (candidate, election_date, group, "source_unavailable")
        deduplicated.setdefault(key, row)
    return list(deduplicated.values())


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
        if token in STOPWORDS or token in DOMAIN_STOPWORDS:
            continue
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
    return sorted(
        rows,
        key=lambda row: (-abs(float(row["difference"])), row["term"]),
    )


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
    return sorted(
        rows,
        key=lambda row: (-abs(float(row["z_score"])), row["feature"]),
    )


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
    return sorted(
        rows,
        key=lambda row: (-abs(float(row["difference"])), row["feature"]),
    )


def official_feature_prevalence(
    documents: list[dict[str, str]],
    *,
    minimum_total_documents: int = 2,
) -> list[dict[str, str]]:
    group_documents = Counter(row["group"] for row in documents)
    document_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in documents:
        tokens = tokenize(row["text"])
        features = set(tokens)
        features.update(f"{a} {b}" for a, b in zip(tokens, tokens[1:], strict=False))
        document_counts[row["group"]].update(features & POLICY_FEATURES)
    rows = []
    for feature in sorted(POLICY_FEATURES):
        dsa_documents = document_counts["dsa"][feature]
        democratic_documents = document_counts["democratic"][feature]
        if dsa_documents + democratic_documents < minimum_total_documents:
            continue
        dsa_share = dsa_documents / max(group_documents["dsa"], 1)
        democratic_share = democratic_documents / max(group_documents["democratic"], 1)
        rows.append(
            {
                "feature": feature,
                "dsa_documents": str(dsa_documents),
                "democratic_documents": str(democratic_documents),
                "dsa_share": f"{dsa_share:.6f}",
                "democratic_share": f"{democratic_share:.6f}",
                "difference": f"{dsa_share - democratic_share:.6f}",
            }
        )
    return sorted(
        rows,
        key=lambda row: (-abs(float(row["difference"])), row["feature"]),
    )


def policy_overlap_rows(
    prevalence_rows: list[dict[str, str]],
    *,
    minimum_shared_share: float = 0.01,
) -> list[dict[str, str]]:
    rows = []
    for row in prevalence_rows:
        if row["feature"] not in POLICY_FEATURES:
            continue
        endorsed_share = float(row["endorsed_share"])
        opponent_share = float(row["opponent_share"])
        shared_emphasis = min(endorsed_share, opponent_share)
        if shared_emphasis < minimum_shared_share:
            continue
        rows.append(
            {
                "feature": row["feature"],
                "endorsed_share": f"{endorsed_share:.6f}",
                "opponent_share": f"{opponent_share:.6f}",
                "shared_emphasis": f"{shared_emphasis:.6f}",
                "share_gap": f"{abs(endorsed_share - opponent_share):.6f}",
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            -float(row["shared_emphasis"]),
            float(row["share_gap"]),
            row["feature"],
        ),
    )


def shared_affirmative_mechanisms(
    path: Path | None = None,
) -> list[dict[str, str]]:
    path = path or CANDIDATE_SEGMENTS_PATH
    indexed: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in read_csv(path):
        if not _eligible_segment(row):
            continue
        if row.get("source_type", "").strip() in {"filing", "official_election_source"}:
            continue
        role = row.get("role", "").strip()
        if role not in {"endorsed", "unopposed", "opponent"}:
            continue
        group = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
        text = row.get("text", "").strip()
        for pattern, feature in PHRASE_PATTERNS:
            if feature not in SHARED_MECHANISM_FEATURES:
                continue
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match or _is_negated_mechanism(text, match.start()):
                continue
            key = (row.get("race_id", "").strip(), feature, group)
            record = indexed.setdefault(
                key,
                {"candidates": set(), "example": ""},
            )
            record["candidates"].add(row.get("candidate_name", "").strip())
            if not record["example"]:
                record["example"] = _excerpt_around_match(text, match.start(), match.end())
    output = []
    race_features = {(race_id, feature) for race_id, feature, _ in indexed}
    for race_id, feature in sorted(race_features):
        endorsed = indexed.get((race_id, feature, "endorsed"))
        opponent = indexed.get((race_id, feature, "opponent"))
        if not endorsed or not opponent:
            continue
        output.append(
            {
                "race_id": race_id,
                "feature": feature,
                "endorsed_candidates": " | ".join(sorted(endorsed["candidates"])),
                "opponent_candidates": " | ".join(sorted(opponent["candidates"])),
                "endorsed_example": str(endorsed["example"]),
                "opponent_example": str(opponent["example"]),
            }
        )
    return output


def _is_negated_mechanism(text: str, match_start: int) -> bool:
    sentence_start = max(
        text.rfind(".", 0, match_start),
        text.rfind("!", 0, match_start),
        text.rfind("?", 0, match_start),
        text.rfind("\n", 0, match_start),
    )
    prefix = text[sentence_start + 1 : match_start].casefold()
    return bool(
        re.search(
            r"\b(?:against|oppose|opposed\s+to|reject|repeal)\s+"
            r"(?:(?:a|an|any|the|this)\s+)?$"
            r"|\b(?:eliminate|end)\s+(?:the\s+)?$"
            r"|\b(?:do not|does not|don't|doesn't|never|not)\s+"
            r"(?:(?:back|favor|support)\s+)?(?:(?:a|an|any|the|this)\s+)?$"
            r"|\b(?:no|without)\s+(?:(?:a|an|any|the|this)\s+)?$",
            prefix,
        )
    )


def _excerpt_around_match(text: str, start: int, end: int) -> str:
    excerpt = " ".join(text[max(0, start - 80) : min(len(text), end + 110)].split())
    if start > 80:
        excerpt = "..." + excerpt
    if end + 110 < len(text):
        excerpt += "..."
    return excerpt


def _shared_mechanism_summary(
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    counts = Counter(row["feature"] for row in rows)
    return [
        {"feature": feature, "race_count": str(count)}
        for feature, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def candidate_record_coverage() -> list[dict[str, str]]:
    summary_rows = read_csv(FULL_TEXT_QUEUE_SUMMARY_PATH)
    required_fields = {"queue_source", "group", "current_status", "candidate_count"}
    if not summary_rows or not required_fields.issubset(summary_rows[0]):
        raise ValueError(
            "full-text queue summary must contain registry group, status, and candidate counts"
        )
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in summary_rows:
        if row.get("queue_source", "").strip() != "registry":
            continue
        group = row.get("group", "").strip()
        if group not in {"endorsed", "opponent"}:
            raise ValueError(f"unexpected full-text queue group: {group!r}")
        candidate_count = int(row.get("candidate_count", "0") or 0)
        status = (
            "with_extracted_text"
            if row.get("current_status", "").strip() == "verified"
            else "without_extracted_text"
        )
        counts[group][status] += candidate_count
    rows = []
    for group in ("endorsed", "opponent"):
        verified = counts[group]["with_extracted_text"]
        unavailable = counts[group]["without_extracted_text"]
        rows.append(
            {
                "group": group,
                "candidate_race_records_with_extracted_text": str(verified),
                "candidate_race_records_without_extracted_text": str(unavailable),
                "extracted_share": f"{verified / max(verified + unavailable, 1):.6f}",
            }
        )
    return rows


def verified_segment_volume(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        cycle = row["cycle"] or "unknown"
        counts[cycle][row["group"]] += 1
    output = []
    for cycle, values in counts.items():
        endorsed = values["endorsed"]
        opponent = values["opponent"]
        output.append(
            {
                "cycle": cycle,
                "endorsed_segments": str(endorsed),
                "opponent_segments": str(opponent),
                "total": str(endorsed + opponent),
            }
        )
    return sorted(output, key=lambda row: row["cycle"])


def source_type_comparison(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    totals = Counter()
    for row in rows:
        source_type = row.get("source_types", row.get("source_type", "")) or "unspecified"
        counts[source_type][row["group"]] += 1
        totals[row["group"]] += 1
    output = []
    for source_type, values in counts.items():
        endorsed = values["endorsed"]
        opponent = values["opponent"]
        endorsed_share = endorsed / max(totals["endorsed"], 1)
        opponent_share = opponent / max(totals["opponent"], 1)
        output.append(
            {
                "source_type": source_type,
                "endorsed_segments": str(endorsed),
                "opponent_segments": str(opponent),
                "endorsed_share": f"{endorsed_share:.6f}",
                "opponent_share": f"{opponent_share:.6f}",
                "difference": f"{endorsed_share - opponent_share:.6f}",
            }
        )
    return sorted(output, key=lambda row: abs(float(row["difference"])), reverse=True)


def explicit_conflicts_by_cycle(
    rows: list[dict[str, str]], candidate_segments: list[dict[str, str]]
) -> list[dict[str, str]]:
    cycle_by_race = {}
    for row in candidate_segments:
        for race_id in _split_values(row["race_ids"]):
            cycle_by_race[race_id] = row["cycle"]
    counts = Counter(
        cycle_by_race.get(row["race_id"], "unknown")
        for row in rows
        if row["contrast_type"] == "explicit_conflict"
    )
    return [
        {"cycle": cycle, "explicit_conflicts": str(count)}
        for cycle, count in sorted(counts.items())
        if cycle != "unknown"
    ]


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


def _candidate_segment_corpus() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    metadata = {
        row["document_id"]: row for row in read_csv(CANDIDATE_METADATA_PATH)
    }
    eligible = []
    for row in read_csv(CANDIDATE_SEGMENTS_PATH):
        if not _eligible_segment(row):
            continue
        document = metadata.get(row["document_id"])
        if document is None:
            raise ValueError(
                f"candidate segment references unknown document {row['document_id']}"
            )
        role = row["role"].strip()
        group = "endorsed" if role in {"endorsed", "unopposed"} else "opponent"
        election_date = document.get("election_date", "").strip()
        eligible.append(
            {
                **row,
                "group": group,
                "cycle": election_date[:4] if election_date else "unknown",
                "election_date": election_date,
                "source_url": document.get("source_url", "").strip(),
                "archive_url": document.get("archive_url", "").strip(),
                "final_url": document.get("final_url", "").strip(),
                "publication_date": document.get("publication_date", "").strip(),
                "document_text_sha256": document.get("text_sha256", "").strip(),
            }
        )

    document_segments: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        document_key = (
            row["group"],
            row["cycle"],
            row["document_text_sha256"] or row["document_id"],
        )
        document_segments[document_key].append(row)
    documents = []
    for (group, cycle, document_hash), rows in sorted(document_segments.items()):
        documents.append(
            {
                "document_id": hashlib.sha256(
                    f"{group}\n{cycle}\n{document_hash}".encode()
                ).hexdigest()[:24],
                "group": group,
                "text": " ".join(
                    row["text"]
                    for row in sorted(rows, key=lambda item: int(item["segment_index"]))
                ),
            }
        )

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        grouped[(row["group"], row["cycle"], row["sha256"])].append(row)
    snapshot_rows = []
    for (group, cycle, text_hash), rows in sorted(grouped.items()):
        first = rows[0]
        snapshot_rows.append(
            {
                "corpus_segment_id": hashlib.sha256(
                    f"{group}\n{cycle}\n{text_hash}".encode()
                ).hexdigest()[:24],
                "source_analysis_segment_ids": _join_values(
                    row["analysis_segment_id"] for row in rows
                ),
                "document_ids": _join_values(row["document_id"] for row in rows),
                "candidate_slugs": _join_values(row["candidate_slug"] for row in rows),
                "candidate_names": _join_values(row["candidate_name"] for row in rows),
                "race_ids": _join_values(row["race_id"] for row in rows),
                "roles": _join_values(row["role"] for row in rows),
                "group": group,
                "cycle": cycle,
                "election_dates": _join_values(row["election_date"] for row in rows),
                "source_types": _join_values(row["source_type"] for row in rows),
                "source_urls": _join_values(row["source_url"] for row in rows),
                "archive_urls": _join_values(row["archive_url"] for row in rows),
                "final_urls": _join_values(row["final_url"] for row in rows),
                "publication_dates": _join_values(
                    row["publication_date"] for row in rows
                ),
                "locators": _join_values(row["locator"] for row in rows),
                "text": first["text"],
                "token_count": first["token_count"],
                "text_sha256": text_hash,
                "exact_duplicate_hash": first["exact_duplicate_hash"],
                "provenance_row_count": str(len(rows)),
            }
        )
    write_csv(
        CORPUS_PATH,
        snapshot_rows,
        [
            "corpus_segment_id",
            "source_analysis_segment_ids",
            "document_ids",
            "candidate_slugs",
            "candidate_names",
            "race_ids",
            "roles",
            "group",
            "cycle",
            "election_dates",
            "source_types",
            "source_urls",
            "archive_urls",
            "final_urls",
            "publication_dates",
            "locators",
            "text",
            "token_count",
            "text_sha256",
            "exact_duplicate_hash",
            "provenance_row_count",
        ],
    )
    return documents, snapshot_rows


def _official_segment_corpus() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    metadata_path = PROCESSED_DIR / "organizational_context_document_metadata.csv"
    metadata = {
        row["context_document_id"]: row for row in read_csv(metadata_path)
    }
    verified_context_ids = {
        row["context_entry_id"]
        for row in read_csv(OFFICIAL_INVENTORY_PATH)
        if row.get("verification_status", "").strip() == "verified"
    }
    source_rows = read_csv(OFFICIAL_SEGMENTS_PATH)
    platform_end_indices = _combined_document_platform_end_indices(source_rows, metadata)
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    document_segments: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        if not _eligible_segment(row) or not row["full_platform_categories"].strip():
            continue
        group = _official_group(row["full_platform_categories"])
        document = metadata.get(row["context_document_id"])
        if document is None:
            raise ValueError(
                "organizational segment references unknown document "
                f"{row['context_document_id']}"
            )
        context_entry_ids = _split_values(row.get("context_entry_ids", ""))
        if not verified_context_ids.intersection(context_entry_ids):
            continue
        platform_end_index = platform_end_indices.get(row["context_document_id"])
        if (
            platform_end_index is not None
            and int(row.get("segment_index", "0")) >= platform_end_index
        ):
            continue
        enriched = {
            **row,
            "group": group,
            "fetch_url": document.get("fetch_url", "").strip(),
            "source_urls": document.get("source_urls", "").strip(),
            "archive_urls": document.get("archive_urls", "").strip(),
            "final_url": document.get("final_url", "").strip(),
        }
        grouped[(group, row["sha256"])].append(enriched)
        document_segments[(group, row["context_document_id"])].append(enriched)

    snapshot_rows = []
    for (group, text_hash), rows in sorted(grouped.items()):
        first = rows[0]
        snapshot_rows.append(
            {
                "corpus_segment_id": hashlib.sha256(
                    f"{group}\n{text_hash}".encode()
                ).hexdigest()[:24],
                "source_analysis_segment_ids": _join_values(
                    row["analysis_segment_id"] for row in rows
                ),
                "context_document_ids": _join_values(
                    row["context_document_id"] for row in rows
                ),
                "fetch_ids": _join_values(row["fetch_id"] for row in rows),
                "context_entry_ids": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["context_entry_ids"])
                ),
                "group": group,
                "context_categories": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["context_categories"])
                ),
                "full_platform_categories": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["full_platform_categories"])
                ),
                "states": _join_values(
                    value for row in rows for value in _split_values(row["states"])
                ),
                "state_codes": _join_values(
                    value for row in rows for value in _split_values(row["state_codes"])
                ),
                "cycle_years": _join_values(
                    value for row in rows for value in _split_values(row["cycle_years"])
                ),
                "organizations": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["organizations"])
                ),
                "titles": _join_values(
                    value for row in rows for value in _split_values(row["titles"])
                ),
                "platform_types": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["platform_types"])
                ),
                "fetch_urls": _join_values(row["fetch_url"] for row in rows),
                "source_urls": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["source_urls"])
                ),
                "archive_urls": _join_values(
                    value
                    for row in rows
                    for value in _split_values(row["archive_urls"])
                ),
                "final_urls": _join_values(row["final_url"] for row in rows),
                "locators": _join_values(row["locator"] for row in rows),
                "text": first["text"],
                "token_count": first["token_count"],
                "text_sha256": text_hash,
                "exact_duplicate_hash": first["exact_duplicate_hash"],
                "provenance_row_count": str(len(rows)),
            }
        )
    write_csv(
        OFFICIAL_CORPUS_PATH,
        snapshot_rows,
        list(snapshot_rows[0]) if snapshot_rows else [
            "corpus_segment_id",
            "source_analysis_segment_ids",
            "context_document_ids",
            "fetch_ids",
            "context_entry_ids",
            "group",
            "context_categories",
            "full_platform_categories",
            "states",
            "state_codes",
            "cycle_years",
            "organizations",
            "titles",
            "platform_types",
            "fetch_urls",
            "source_urls",
            "archive_urls",
            "final_urls",
            "locators",
            "text",
            "token_count",
            "text_sha256",
            "exact_duplicate_hash",
            "provenance_row_count",
        ],
    )
    documents = []
    for (group, document_id), rows in sorted(document_segments.items()):
        seen_hashes = set()
        texts = []
        for row in sorted(rows, key=lambda item: int(item["segment_index"])):
            if row["sha256"] in seen_hashes:
                continue
            seen_hashes.add(row["sha256"])
            texts.append(row["text"])
        documents.append(
            {
                "document_id": document_id,
                "group": group,
                "category": _split_values(rows[0]["full_platform_categories"])[0],
                "text": " ".join(texts),
            }
        )
    return documents, snapshot_rows


def _combined_document_platform_end_indices(
    rows: list[dict[str, str]],
    metadata: dict[str, dict[str, str]],
) -> dict[str, int]:
    by_document: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_document[row["context_document_id"]].append(row)

    cutoffs = {}
    for document_id, document_rows in by_document.items():
        document = metadata.get(document_id, {})
        title = (document.get("titles") or document.get("title", "")).casefold()
        if "platform" not in title or not (
            "constitution" in title or "bylaw" in title or "by-law" in title
        ):
            continue
        ordered = sorted(document_rows, key=lambda row: int(row.get("segment_index", "0")))
        platform_position = next(
            (
                position
                for position, row in enumerate(ordered)
                if "platform of " in row.get("text", "").casefold()
            ),
            None,
        )
        boundary_position = next(
            (
                position
                for position, row in enumerate(ordered)
                if "constitution of " in row.get("text", "").casefold()
                or "bylaws of " in row.get("text", "").casefold()
                or "by-laws of " in row.get("text", "").casefold()
            ),
            None,
        )
        if (
            platform_position is not None
            and boundary_position is not None
            and platform_position < boundary_position
        ):
            cutoffs[document_id] = int(ordered[boundary_position]["segment_index"])
    return cutoffs


def _eligible_segment(row: dict[str, str]) -> bool:
    return (
        bool(row.get("text", "").strip())
        and row.get("boilerplate_flag", "false").strip().casefold() != "true"
        and int(row.get("token_count", "0") or 0) >= SUBSTANTIVE_MIN_TOKENS
    )


def _official_group(categories_value: str) -> str:
    categories = _split_values(categories_value)
    unsupported = [category for category in categories if category not in OFFICIAL_CATEGORY_GROUPS]
    if unsupported:
        raise ValueError(f"unsupported full-platform categories: {unsupported}")
    groups = {OFFICIAL_CATEGORY_GROUPS[category] for category in categories}
    if len(groups) != 1:
        raise ValueError(f"mixed full-platform category groups: {categories}")
    return groups.pop()


def _split_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(" | ") if part.strip()]


def _join_values(values) -> str:
    return " | ".join(sorted({value.strip() for value in values if value.strip()}))


def _write_text_report(
    summary: dict[str, int | float],
    candidate_mpif: list[dict[str, str]],
    official_mpif: list[dict[str, str]],
    official_prevalence_rows: list[dict[str, str]],
    prevalence_rows: list[dict[str, str]],
    overlap_rows: list[dict[str, str]],
    shared_mechanism_summary: list[dict[str, str]],
    coverage_rows: list[dict[str, str]],
    volume_rows: list[dict[str, str]],
    source_type_rows: list[dict[str, str]],
    explicit_cycle_rows: list[dict[str, str]],
) -> None:
    prevalence_by_feature = {row["feature"]: row for row in prevalence_rows}
    prevalence_positive = [
        row for row in prevalence_rows if float(row["difference"]) > 0
    ][:8]
    prevalence_negative = [
        row for row in prevalence_rows if float(row["difference"]) < 0
    ][:8]
    strongest_overlap = overlap_rows[:8]
    strongest_shared_mechanisms = shared_mechanism_summary[:8]
    official_positive = [
        row for row in official_prevalence_rows if float(row["difference"]) > 0
    ][:6]
    official_negative = [
        row for row in official_prevalence_rows if float(row["difference"]) < 0
    ][:6]
    official_document_counts = summary["official_documents_by_group"]
    official_category_counts = summary["official_documents_by_category"]
    official_segment_counts = summary["official_segments_by_group"]
    largest_volume_cycles = sorted(
        volume_rows, key=lambda row: int(row["total"]), reverse=True
    )[:5]
    largest_explicit_cycles = sorted(
        explicit_cycle_rows,
        key=lambda row: int(row["explicit_conflicts"]),
        reverse=True,
    )[:5]
    source_type_differences = source_type_rows[:8]
    coverage_total = sum(
        int(row["candidate_race_records_with_extracted_text"])
        + int(row["candidate_race_records_without_extracted_text"])
        for row in coverage_rows
    )
    text = f"""# DSA-versus-Democratic text analysis

This analysis is generated by `uv run dsa-analysis analyze-text` from the current canonical
registry and recoverable full-text corpus.

## Corpus

- Deduplicated candidate analysis documents: {summary["candidate_documents"]}
- Underlying eligible candidate source documents: {summary["candidate_source_documents"]}
- Eligible candidate source segments: {summary["candidate_source_segments"]}
- Candidate segments after shared-text deduplication: {summary["candidate_segments"]}
- Eligible full-platform organizational documents: {summary["official_documents"]}
- DSA official documents: {official_document_counts.get("dsa", 0)}; Democratic official
  documents: {official_document_counts.get("democratic", 0)}
- Documents by category: DSA national {official_category_counts.get("dsa_national", 0)},
  DSA state/local {official_category_counts.get("dsa_state_local", 0)}, DNC national
  {official_category_counts.get("dnc_national", 0)}, and state Democratic Party
  {official_category_counts.get("state_democratic_party", 0)}
- Eligible official-platform source segments: {summary["official_source_segments"]}
- Official-platform segments after exact-text deduplication: {summary["official_segments"]}
- DSA official segments after deduplication: {official_segment_counts.get("dsa", 0)};
  Democratic official segments: {official_segment_counts.get("democratic", 0)}
- Unique source-supported primary contrasts: {summary["sticking_points"]}

Exact candidate passage text is counted once per DSA-endorsed/other-Democrat group and election cycle.
This prevents a shared national platform from being multiplied across state races while retaining
all contributing candidates, races, source documents, URLs, and locators in the snapshot.

## Source data and lineage

- `data/analysis/candidate_text_corpus.csv` is the generated candidate-segment snapshot. Every
  row retains exact extracted text plus its candidate, race, document, URL, and locator lineage.
- `data/analysis/organizational_context_text_corpus.csv` is the generated official-platform
  snapshot used for the DSA-versus-Democratic MPIF comparison.
- `data/analysis/primary_sticking_points.csv` is the committed deduplicated contrast input.
- Candidate text comes from `data/processed/candidate_document_analysis_segments.csv` and joins
  `candidate_document_metadata.csv` for source and election provenance.
- Official text comes from the generated organizational-context analysis-segment path and is
  restricted to rows with a full-platform category.
- The public charts use exact words, source types, evidence statuses, election dates, and
  explicitly named conflicts. They do not use analyst-created topic totals.

## Methods

- **TF-IDF:** mean unigram TF-IDF by candidate group.
- **MPIF:** weighted log-odds z-scores with an informative Dirichlet prior, using unigrams and
  adjacent bigrams. Positive values favor DSA-endorsed candidates or DSA; negative values favor
  other Democrats or the DNC.
- **Document prevalence:** difference in the share of candidate/election documents containing a
  normalized feature. This prevents a few candidates who repeat a phrase many times from
  dominating the result.
- **Official-platform document prevalence:** the same calculation at the organizational-document
  level. Each platform contributes once per feature, so a long state-party platform cannot gain
  weight by repeating a phrase.
- **Source mix:** direct counts of source-type metadata attached to eligible segments.
- **Evidence volume:** direct counts of deduplicated eligible segments by election cycle.
- **Explicit conflicts:** unique rows marked `explicit_conflict`; analyst-coded divergences are
  excluded from the public conflict chart.

## Main language differences

- **Rights and labor:** DSA-endorsed documents mention human rights
  ({float(prevalence_by_feature["human_right"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["human_right"]["opponent_share"]):.0%}), working class
  ({float(prevalence_by_feature["working_class"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["working_class"]["opponent_share"]):.0%}), workers
  ({float(prevalence_by_feature["worker"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["worker"]["opponent_share"]):.0%}), and unions
  ({float(prevalence_by_feature["union"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["union"]["opponent_share"]):.0%}) more often.
- **Housing, health, and climate:** DSA-endorsed documents more often mention health care
  ({float(prevalence_by_feature["healthcare"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["healthcare"]["opponent_share"]):.0%}), tenants
  ({float(prevalence_by_feature["tenant"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["tenant"]["opponent_share"]):.0%}), the Green New Deal
  ({float(prevalence_by_feature["green_new_deal"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["green_new_deal"]["opponent_share"]):.0%}), and rent
  ({float(prevalence_by_feature["rent"]["endorsed_share"]):.0%} versus
  {float(prevalence_by_feature["rent"]["opponent_share"]):.0%}).
- **Business and development:** other-Democrat documents more often mention business
  ({float(prevalence_by_feature["business"]["opponent_share"]):.0%} versus
  {float(prevalence_by_feature["business"]["endorsed_share"]):.0%}), small business
  ({float(prevalence_by_feature["small_business"]["opponent_share"]):.0%} versus
  {float(prevalence_by_feature["small_business"]["endorsed_share"]):.0%}), technology
  ({float(prevalence_by_feature["technology"]["opponent_share"]):.0%} versus
  {float(prevalence_by_feature["technology"]["endorsed_share"]):.0%}), markets
  ({float(prevalence_by_feature["market"]["opponent_share"]):.0%} versus
  {float(prevalence_by_feature["market"]["endorsed_share"]):.0%}), and training
  ({float(prevalence_by_feature["training"]["opponent_share"]):.0%} versus
  {float(prevalence_by_feature["training"]["endorsed_share"]):.0%}).
- Official-platform MPIF remains available in the generated tables. The strongest broad
  organizational distinction is working-class, worker, union, and movement language in DSA
  texts versus family, nation, access, and institutional-party language in Democratic texts.

## Official DSA and Democratic platforms

This is the separate 44-document organizational lexical corpus, not a proxy for candidate
positions. It contains
{official_document_counts.get("dsa", 0)} recoverable DSA platform documents and
{official_document_counts.get("democratic", 0)} recoverable Democratic platform documents.
The unequal document inventory makes raw segment totals descriptive rather than directly
comparable. MPIF adjusts for token totals; the document-prevalence table additionally gives each
platform one observation per policy feature.

The largest DSA-side document-prevalence differences are
{", ".join(f'{_label(row["feature"])} ({float(row["dsa_share"]):.0%} versus {float(row["democratic_share"]):.0%})' for row in official_positive)}.
The largest Democratic-side differences are
{", ".join(f'{_label(row["feature"])} ({float(row["democratic_share"]):.0%} versus {float(row["dsa_share"]):.0%})' for row in official_negative)}.
These are differences in whether a document mentions a normalized feature, not evidence that
every organization takes the same position or proposes the same mechanism.

The four hand-reviewed platform contrasts are qualitative examples selected to make exact
language visible; they are not a representative sample of all platform differences. Sparse
recoverable DSA state/local platforms and {summary["organizational_platform_gap_rows"]}
explicit platform-gap rows limit generalization beyond the documents actually collected.

![Difference in policy language](../outputs/figures/text_analysis/policy_language_difference.svg)

![Official policy mechanism contrasts](../outputs/figures/text_analysis/official_policy_contrasts.svg)

![Official-platform document prevalence](../outputs/figures/text_analysis/official_platform_document_prevalence.svg)

The separate [official-platform semantic-density report](official_platform_kde_analysis.md)
applies a separate platform-coverage and text-quality gate, then uses equal-size,
document-stratified UMAP fitting and equal-platform-weighted KDE. It reports the exact eligible
corpus, passage flow, parameter sensitivity, and underlying HDBSCAN regions.

The candidate comparison especially distinguishes rights-based housing and labor language
(`rent`, `human right`, `rent control`, `social housing`, `living wage`) from other-Democrat language
that more often emphasizes business, opportunity, public-option mechanisms, technology,
training, and border administration.

## Shared policy emphasis

The difference chart intentionally excludes features whose prevalence gap is below 0.5
percentage points. Shared emphasis is reported separately rather than displaying a rounded
`0.00` difference as if it were substantively distinctive.

- Highest shared-emphasis features:
  {", ".join(_label(row["feature"]) for row in strongest_overlap)}.

![Shared policy emphasis](../outputs/figures/text_analysis/policy_language_overlap.svg)

Both groups discussing a feature does not establish identical policy positions. This chart
identifies common agenda space; the exact texts and reviewed mechanism comparisons are required
to determine agreement, disagreement, or different proposed means.

## Shared affirmative mechanism language within primaries

As a stricter agreement-oriented check, we identify races where an endorsed candidate and
another Democrat both use the same concrete normalized policy-mechanism phrase. Mentions preceded by
oppositional or negating language are excluded. The most common shared mechanisms are:

{chr(10).join(f'- **{_label(row["feature"])}:** {row["race_count"]} races' for row in strongest_shared_mechanisms)}

![Shared affirmative policy mechanisms](../outputs/figures/text_analysis/shared_affirmative_policy_mechanisms.svg)

This is stronger evidence of common policy language than topic overlap, but it is still not a
complete stance classifier. The generated table retains both sides' exact source excerpts for
review.

## Document-prevalence robustness check

- More common across DSA-endorsed candidate documents:
  {", ".join(_label(row["feature"]) for row in prevalence_positive)}.
- More common across other-Democrat documents:
  {", ".join(_label(row["feature"]) for row in prevalence_negative)}.

When MPIF and document prevalence point in the same direction, the result is less likely to be
driven by one unusually repetitive campaign.

## First-party source mix

The largest differences in the kinds of real sources recovered are:

{chr(10).join(f'- **{_label(row["source_type"])}:** {float(row["difference"]):+.1%}' for row in source_type_differences)}

Positive values indicate a larger share of DSA-endorsed excerpts; negative values indicate a
larger share of other-Democrat excerpts.

![Source type difference](../outputs/figures/text_analysis/source_type_difference.svg)

## Evidence volume by election cycle

{chr(10).join(f'- **{row["cycle"]}:** {row["endorsed_segments"]} DSA-endorsed and {row["opponent_segments"]} other-Democrat passages' for row in largest_volume_cycles)}

![Verified evidence by cycle](../outputs/figures/text_analysis/verified_evidence_by_cycle.svg)

These are direct counts of eligible exact-text segments, not estimates of issue importance.

## Explicitly stated conflicts

{chr(10).join(f'- **{row["cycle"]}:** {row["explicit_conflicts"]} explicit conflicts' for row in largest_explicit_cycles)}

![Explicit conflicts by cycle](../outputs/figures/text_analysis/explicit_conflicts_by_cycle.svg)

This chart excludes analyst-coded divergences and retains only direct, source-supported conflict
records.

## Evidence coverage

The denominator is the registry-wide {coverage_total} candidate/race records summarized in
`data/processed/full_text_queue_summary.csv`; only `verified` is counted as extracted.

{chr(10).join(f'- **{"Other Democrats" if row["group"] == "opponent" else _label(row["group"])}:** {row["candidate_race_records_with_extracted_text"]} candidate/race records with extracted text, {row["candidate_race_records_without_extracted_text"]} without extracted text ({float(row["extracted_share"]):.1%} extracted).' for row in coverage_rows)}

## Limitations

The official DSA-versus-Democratic MPIF corpus includes only extracted documents classified as
full platforms; other organizational statements and process documents are excluded.
`source_unavailable` findings remain unknowns rather than evidence of no position. Lexical
distinctiveness measures language, not ideology, sincerity, policy feasibility, or causal
importance in election outcomes. Phrase normalization can combine uses that differ in context;
the exact segment text and provenance in the generated analysis snapshots remain authoritative.
"""
    (REPORT_DIR / "text_analysis.md").write_text(text, encoding="utf-8")


def _policy_language_chart(rows: list[dict[str, str]]) -> None:
    by_feature = {row["feature"]: row for row in rows}
    sections = [
        (
            "Rights and labor",
            "DSA-endorsed campaigns use class, worker, union, and rights language more often.",
            ["human_right", "working_class", "worker", "union"],
        ),
        (
            "Housing, health, and climate",
            "The largest issue-specific DSA gaps concern health care, tenants, climate, and rent.",
            ["healthcare", "tenant", "green_new_deal", "rent"],
        ),
        (
            "Business and economic development",
            "Other Democrats more often frame policy through business, technology, markets, and training.",
            ["business", "small_business", "technology", "market", "training"],
        ),
    ]
    selected_sections = [
        (title, takeaway, [by_feature[feature] for feature in features if feature in by_feature])
        for title, takeaway, features in sections
    ]
    selected_sections = [
        (title, takeaway, section_rows)
        for title, takeaway, section_rows in selected_sections
        if section_rows
    ]
    width = 1240
    card_top = 218
    row_height = 44
    card_gap = 22
    card_heights = [112 + len(section_rows) * row_height for _, _, section_rows in selected_sections]
    height = card_top + sum(card_heights) + card_gap * max(len(card_heights) - 1, 0) + 72
    plot_left = 400
    plot_right = 1110
    plot_width = plot_right - plot_left
    maximum = 0.5
    body = [
        _svg_header(
            width,
            height,
            "What distinguishes candidate campaign language?",
            (
                "Share of candidate-year campaign documents mentioning each phrase; "
                "lines compare actual prevalence, not just the gap"
            ),
        ),
        _rect(48, 96, 1144, 92, CARD),
        _text(68, 120, "BOTTOM LINE", color=MID, size="10px", weight="700"),
        _text(
            68,
            145,
            "DSA-endorsed campaigns foreground rights, labor, tenants, and broad public programs;",
            color=DARK,
            size="14px",
            weight="700",
        ),
        _text(
            68,
            168,
            "other Democrats foreground business and economic-development language.",
            color=DARK,
            size="14px",
            weight="700",
        ),
        _legend(876, 135, DSA_RED, "DSA-endorsed"),
        _legend(1042, 135, DEMOCRATIC_BLUE, "Other Democrats"),
    ]
    card_y = card_top
    for section_index, (title, takeaway, section_rows) in enumerate(selected_sections):
        card_height = card_heights[section_index]
        body.append(_rect(48, card_y, 1144, card_height, "#FCFBF8"))
        body.append(_text(68, card_y + 30, title, color=DARK, size="18px", weight="700"))
        body.append(_text(68, card_y + 54, takeaway, color=MID, size="12px"))
        axis_y = card_y + 80
        for tick in range(6):
            value = maximum * tick / 5
            x = plot_left + plot_width * tick / 5
            body.append(_line(x, axis_y, x, card_y + card_height - 18, LIGHT))
            body.append(_text(x, axis_y - 8, f"{value:.0%}", "middle", MID, "10px"))
        for row_index, row in enumerate(section_rows):
            y = axis_y + 27 + row_index * row_height
            endorsed = float(row["endorsed_share"])
            opponent = float(row["opponent_share"])
            difference = endorsed - opponent
            x_endorsed = plot_left + plot_width * endorsed / maximum
            x_opponent = plot_left + plot_width * opponent / maximum
            favored_color = DSA_RED if difference > 0 else DEMOCRATIC_BLUE
            body.append(
                _text(72, y + 5, _label(row["feature"]), color=DARK, size="13px", weight="700")
            )
            body.append(
                _text(
                    270,
                    y + 5,
                    f"{abs(difference) * 100:.1f} pts more",
                    "start",
                    favored_color,
                    "11px",
                    "700",
                )
            )
            body.append(_line(x_endorsed, y, x_opponent, y, "#B8B6B0"))
            body.append(_circle(x_endorsed, y, 7, DSA_RED))
            body.append(_circle(x_opponent, y, 7, DEMOCRATIC_BLUE))
            body.append(
                _text(
                    x_endorsed,
                    y - 12,
                    f"{endorsed:.0%}",
                    "middle",
                    DSA_RED,
                    "10px",
                    "700",
                )
            )
            body.append(
                _text(
                    x_opponent,
                    y + 20,
                    f"{opponent:.0%}",
                    "middle",
                    DEMOCRATIC_BLUE,
                    "10px",
                    "700",
                )
            )
        card_y += card_height + card_gap
    body.append(
        _svg_footer(
            width,
            height,
            (
                "Interpretation: mention rates measure emphasis, not support or opposition. "
                "Exact text is retained in candidate_text_corpus.csv; repeated shared text is "
                "deduplicated within candidate group and election year."
            ),
        )
    )
    _write_svg(
        FIGURE_DIR / "policy_language_difference.svg",
        width,
        height,
        body,
    )


def _policy_overlap_chart(rows: list[dict[str, str]]) -> None:
    by_feature = {row["feature"]: row for row in rows}
    selected = [
        by_feature[feature]
        for feature in (
            "healthcare",
            "worker",
            "business",
            "affordable_housing",
            "union",
            "training",
            "climate_change",
            "rent",
        )
        if feature in by_feature
    ]
    width = 1240
    height = 250 + len(selected) * 52
    plot_left = 370
    plot_width = 730
    maximum = 0.5
    body = [
        _svg_header(
            width,
            height,
            "Where the two groups discuss the same issues",
            (
                "Actual mention rates reveal common agenda space even when the proposed "
                "solutions may differ"
            ),
        ),
        _rect(48, 96, 1144, 92, CARD),
        _text(68, 120, "BOTTOM LINE", color=MID, size="10px", weight="700"),
        _text(
            68,
            146,
            "Health care, workers, business, housing, and climate appear in both camps;",
            color=DARK,
            size="14px",
            weight="700",
        ),
        _text(
            68,
            169,
            "overlap in attention is not proof of agreement.",
            color=DARK,
            size="14px",
            weight="700",
        ),
        _legend(870, 138, DSA_RED, "DSA-endorsed"),
        _legend(1038, 138, DEMOCRATIC_BLUE, "Other Democrats"),
    ]
    for tick in range(6):
        value = maximum * tick / 5
        x = plot_left + plot_width * tick / 4
        x = plot_left + plot_width * tick / 5
        body.append(_line(x, 202, x, height - 60, LIGHT))
        body.append(_text(x, 190, f"{value:.0%}", "middle", MID, "10px"))
    for index, row in enumerate(selected):
        y = 220 + index * 52
        endorsed = float(row["endorsed_share"])
        opponent = float(row["opponent_share"])
        x_endorsed = plot_left + plot_width * endorsed / maximum
        x_opponent = plot_left + plot_width * opponent / maximum
        body.append(
            _text(72, y + 5, _label(row["feature"]), "start", DARK, "13px", "700")
        )
        body.append(_line(x_endorsed, y, x_opponent, y, "#B8B6B0"))
        body.append(_circle(x_endorsed, y, 7, DSA_RED))
        body.append(_circle(x_opponent, y, 7, DEMOCRATIC_BLUE))
        body.append(_text(x_endorsed, y - 12, f"{endorsed:.0%}", "middle", DSA_RED, "10px", "700"))
        body.append(_text(x_opponent, y + 20, f"{opponent:.0%}", "middle", DEMOCRATIC_BLUE, "10px", "700"))
    body.extend(
        [
            _svg_footer(
                width,
                height,
                (
                    "Shared mention indicates overlapping agenda attention. Consult exact text "
                    "to distinguish agreement from different mechanisms or opposing stances."
                ),
            ),
        ]
    )
    _write_svg(
        FIGURE_DIR / "policy_language_overlap.svg",
        width,
        height,
        body,
    )


def _official_platform_prevalence_chart(
    rows: list[dict[str, str]],
    document_counts: Counter[str],
) -> None:
    selected = sorted(
        rows,
        key=lambda row: abs(float(row["difference"])),
        reverse=True,
    )[:12]
    width = 1240
    height = 272 + len(selected) * 48
    plot_left = 390
    plot_width = 690
    body = [
        _svg_header(
            width,
            height,
            "Policy language across official platforms",
            "Document-level mention rates; every recoverable platform contributes once per feature",
        ),
        _rect(48, 96, 1144, 104, CARD),
        _text(68, 121, "WHAT THIS CONTROLS", color=MID, size="10px", weight="700"),
        _text(
            68,
            148,
            (
                "Rates compare documents, not passage volume, so longer Democratic platforms "
                "do not receive extra weight."
            ),
            color=DARK,
            size="14px",
            weight="700",
        ),
        _text(
            68,
            174,
            (
                f"Recoverable corpus: {document_counts.get('dsa', 0)} DSA and "
                f"{document_counts.get('democratic', 0)} Democratic platform documents."
            ),
            color=MID,
            size="12px",
        ),
        _legend(845, 176, DSA_RED, "Official DSA"),
        _legend(1017, 176, DEMOCRATIC_BLUE, "Official Democratic"),
    ]
    for tick in range(6):
        value = tick / 5
        x = plot_left + plot_width * value
        body.append(_line(x, 220, x, height - 62, LIGHT))
        body.append(_text(x, 215, f"{value:.0%}", "middle", MID, "10px"))
    for index, row in enumerate(selected):
        y = 245 + index * 48
        dsa_share = float(row["dsa_share"])
        democratic_share = float(row["democratic_share"])
        x_dsa = plot_left + plot_width * dsa_share
        x_democratic = plot_left + plot_width * democratic_share
        body.append(
            _text(72, y + 5, _label(row["feature"]), "start", DARK, "13px", "700")
        )
        body.append(_line(x_dsa, y, x_democratic, y, "#B8B6B0"))
        body.append(_circle(x_dsa, y, 7, DSA_RED))
        body.append(_circle(x_democratic, y, 7, DEMOCRATIC_BLUE))
        body.append(
            _text(x_dsa, y - 12, f"{dsa_share:.0%}", "middle", DSA_RED, "10px", "700")
        )
        body.append(
            _text(
                x_democratic,
                y + 20,
                f"{democratic_share:.0%}",
                "middle",
                DEMOCRATIC_BLUE,
                "10px",
                "700",
            )
        )
    body.append(
        _svg_footer(
            width,
            height,
            (
                "Mention rates show agenda emphasis, not policy direction. The unequal number "
                "of recoverable platforms remains a coverage limitation."
            ),
        )
    )
    _write_svg(
        FIGURE_DIR / "official_platform_document_prevalence.svg",
        width,
        height,
        body,
    )


def _shared_mechanism_chart(rows: list[dict[str, str]]) -> None:
    selected = rows[:10]
    _horizontal_svg(
        FIGURE_DIR / "shared_affirmative_policy_mechanisms.svg",
        "Shared affirmative policy mechanisms",
        (
            "Number of primaries where both sides affirmatively use the same normalized "
            "mechanism phrase"
        ),
        [_label(row["feature"]) for row in selected],
        [float(row["race_count"]) for row in selected],
        GREEN,
        value_format=".0f",
        footer=(
            "Negated or oppositional mentions are excluded. Exact paired excerpts are retained "
            "in shared_affirmative_policy_mechanisms.csv."
        ),
    )


def _official_contrast_chart(
    comparisons: list[dict[str, str]], excerpts: list[dict[str, str]]
) -> None:
    excerpts_by_id = {row["excerpt_id"]: row for row in excerpts}
    rows = [row for row in comparisons if row["reviewed"].casefold() == "true"]
    width = 1320
    row_height = 145
    height = 165 + len(rows) * row_height
    body = [
        _svg_header(
            width,
            height,
            "Official DSA and Democratic policy mechanisms",
            "Direct comparison of manually reviewed official texts",
        ),
        _text(285, 108, "DSA", "middle", DSA_RED, "13px", "700"),
        _text(660, 108, "Issue", "middle", MID, "12px", "700"),
        _text(1035, 108, "Democratic Party", "middle", DEMOCRATIC_BLUE, "13px", "700"),
    ]
    for index, row in enumerate(rows):
        y = 132 + index * row_height
        dsa = excerpts_by_id[row["dsa_excerpt_id"]]
        democratic = excerpts_by_id[row["democratic_excerpt_id"]]
        body.append(_rect(48, y, 490, 112, _tint(DSA_RED, 0.88)))
        body.append(_rect(782, y, 490, 112, _tint(DEMOCRATIC_BLUE, 0.88)))
        body.append(_line(660, y + 4, 660, y + 108, LIGHT))
        body.append(_wrapped_text(68, y + 28, dsa["quote"], 54, DSA_RED))
        body.append(
            _wrapped_text(802, y + 28, democratic["quote"], 54, DEMOCRATIC_BLUE)
        )
        body.append(
            _text(
                660,
                y + 43,
                _label(row["topic"]),
                "middle",
                DARK,
                "14px",
                "700",
            )
        )
        body.append(
            _text(
                660,
                y + 66,
                row["cycle"],
                "middle",
                MID,
                "11px",
            )
        )
        body.append(
            _text(
                660,
                y + 88,
                _label(row["relationship_code"]),
                "middle",
                MID,
                "10px",
                "700",
            )
        )
    body.append(
        _svg_footer(
            width,
            height,
            "Source: reviewed official DSA statements and Democratic Party platforms; quotations shortened only by line wrapping.",
        )
    )
    _write_svg(FIGURE_DIR / "official_policy_contrasts.svg", width, height, body)


def _cycle_line_chart(rows: list[dict[str, str]]) -> None:
    rows = [row for row in rows if row["cycle"] != "unknown"]
    width = 1200
    height = 620
    plot_left = 105
    plot_right = 1080
    plot_top = 125
    plot_bottom = 520
    maximum = max(
        (
            max(int(row["explicit_conflict"]), int(row["coded_divergence"]))
            for row in rows
        ),
        default=1,
    )
    body = [
        _svg_header(
            width,
            height,
            "Primary sticking points by election cycle",
            "Unique explicit conflicts and analyst-coded policy divergences",
        )
    ]
    for tick in range(5):
        value = maximum * tick / 4
        y = plot_bottom - (plot_bottom - plot_top) * tick / 4
        body.append(_line(plot_left, y, plot_right, y, LIGHT))
        body.append(_text(plot_left - 14, y + 4, f"{value:.0f}", "end", MID, "11px"))
    x_positions = []
    for index, row in enumerate(rows):
        x = plot_left + (plot_right - plot_left) * index / max(len(rows) - 1, 1)
        x_positions.append(x)
        body.append(_text(x, plot_bottom + 28, row["cycle"], "middle", MID, "11px"))
    for key, color, label in (
        ("explicit_conflict", DSA_RED, "Explicit conflict"),
        ("coded_divergence", DEMOCRATIC_BLUE, "Coded divergence"),
    ):
        points = []
        for x, row in zip(x_positions, rows, strict=True):
            value = int(row[key])
            y = plot_bottom - (plot_bottom - plot_top) * value / maximum
            points.append((x, y, value))
        body.append(
            f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)}" '
            f'fill="none" stroke="{color}" stroke-width="4" stroke-linejoin="round"/>'
        )
        for x, y, value in points:
            body.append(_circle(x, y, 6, color))
        x, y, _ = points[-1]
        body.append(_text(x + 14, y + 4, label, color=color, size="12px", weight="700"))
    body.append(
        _svg_footer(
            width,
            height,
            "Counts reflect recoverable first-party evidence and the number of identified primaries in each cycle.",
        )
    )
    _write_svg(FIGURE_DIR / "sticking_points_by_cycle.svg", width, height, body)


def _volume_cycle_chart(rows: list[dict[str, str]]) -> None:
    width = 1200
    height = 620
    plot_left = 105
    plot_right = 1080
    plot_top = 125
    plot_bottom = 520
    maximum = max(
        (
            max(int(row["endorsed_segments"]), int(row["opponent_segments"]))
            for row in rows
        ),
        default=1,
    )
    body = [
        _svg_header(
            width,
            height,
            "Eligible first-party text by election cycle",
            "Count of deduplicated substantive candidate segments",
        )
    ]
    for tick in range(5):
        value = maximum * tick / 4
        y = plot_bottom - (plot_bottom - plot_top) * tick / 4
        body.append(_line(plot_left, y, plot_right, y, LIGHT))
        body.append(_text(plot_left - 14, y + 4, f"{value:.0f}", "end", MID, "11px"))
    group_width = (plot_right - plot_left) / max(len(rows), 1)
    bar_width = min(28, group_width * 0.28)
    for index, row in enumerate(rows):
        center = plot_left + group_width * (index + 0.5)
        endorsed = int(row["endorsed_segments"])
        opponent = int(row["opponent_segments"])
        endorsed_height = (plot_bottom - plot_top) * endorsed / maximum
        opponent_height = (plot_bottom - plot_top) * opponent / maximum
        body.append(
            _rect(
                center - bar_width - 2,
                plot_bottom - endorsed_height,
                bar_width,
                endorsed_height,
                DSA_RED,
            )
        )
        body.append(
            _rect(
                center + 2,
                plot_bottom - opponent_height,
                bar_width,
                opponent_height,
                DEMOCRATIC_BLUE,
            )
        )
        body.append(_text(center, plot_bottom + 28, row["cycle"], "middle", MID, "11px"))
    body.extend(
        [
            _legend(800, 72, DSA_RED, "DSA-endorsed"),
            _legend(945, 72, DEMOCRATIC_BLUE, "Other Democrats"),
            _svg_footer(
                width,
                height,
                "Source: data/analysis/candidate_text_corpus.csv; substantive non-boilerplate segments; shared exact text deduplicated within group and cycle.",
            ),
        ]
    )
    _write_svg(FIGURE_DIR / "verified_evidence_by_cycle.svg", width, height, body)


def _source_type_chart(rows: list[dict[str, str]]) -> None:
    selected = rows[:12]
    _diverging_svg(
        FIGURE_DIR / "source_type_difference.svg",
        "Difference in first-party source mix",
        "Share of eligible exact-text segments by source type",
        [_label(row["source_type"]) for row in selected],
        [float(row["difference"]) for row in selected],
        "More DSA-endorsed segments",
        "More other-Democrat passages",
        (
            "Source: data/analysis/candidate_text_corpus.csv; source types and exact "
            "source provenance are retained for every segment."
        ),
    )


def _explicit_cycle_chart(rows: list[dict[str, str]]) -> None:
    width = 1200
    height = 600
    plot_left = 105
    plot_right = 1080
    plot_top = 125
    plot_bottom = 500
    maximum = max((int(row["explicit_conflicts"]) for row in rows), default=1)
    body = [
        _svg_header(
            width,
            height,
            "Explicitly stated primary conflicts by cycle",
            "Only direct, source-supported candidate contrasts; coded divergences excluded",
        )
    ]
    for tick in range(5):
        value = maximum * tick / 4
        y = plot_bottom - (plot_bottom - plot_top) * tick / 4
        body.append(_line(plot_left, y, plot_right, y, LIGHT))
        body.append(_text(plot_left - 14, y + 4, f"{value:.0f}", "end", MID, "11px"))
    points = []
    for index, row in enumerate(rows):
        x = plot_left + (plot_right - plot_left) * index / max(len(rows) - 1, 1)
        value = int(row["explicit_conflicts"])
        y = plot_bottom - (plot_bottom - plot_top) * value / maximum
        points.append((x, y, value))
        body.append(_text(x, plot_bottom + 28, row["cycle"], "middle", MID, "11px"))
    body.append(
        f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)}" '
        f'fill="none" stroke="{DSA_RED}" stroke-width="4" stroke-linejoin="round"/>'
    )
    for x, y, value in points:
        body.append(_circle(x, y, 7, DSA_RED))
        body.append(_text(x, y - 14, str(value), "middle", DARK, "11px", "700"))
    body.append(
        _svg_footer(
            width,
            height,
            "Source: data/analysis/primary_sticking_points.csv; contrast_type=explicit_conflict; unique sticking_point_id rows.",
        )
    )
    _write_svg(FIGURE_DIR / "explicit_conflicts_by_cycle.svg", width, height, body)


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
        "Mean document TF-IDF: DSA-endorsed candidates versus other Democrats",
        labels,
        values,
        "DSA-endorsed",
        "Other Democrats",
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
    width = 1200
    height = 205 + len(selected) * 42
    plot_left = 315
    plot_width = 760
    max_value = max(
        (
            max(float(row["endorsed_share"]), float(row["opponent_share"]))
            for row in selected
        ),
        default=1,
    )
    body = [
        _svg_header(
            width,
            height,
            "Issue emphasis by candidate group",
            "Share of verified excerpts coded to each topic",
        )
    ]
    for tick in range(5):
        value = max_value * tick / 4
        x = plot_left + plot_width * tick / 4
        body.append(_line(x, 106, x, height - 58, LIGHT))
        body.append(_text(x, 94, f"{value:.0%}", "middle", MID, "11px"))
    for index, row in enumerate(selected):
        y = 120 + index * 42
        endorsed = float(row["endorsed_share"])
        opponent = float(row["opponent_share"])
        x_endorsed = plot_left + plot_width * endorsed / max_value
        x_opponent = plot_left + plot_width * opponent / max_value
        body.append(_text(plot_left - 22, y + 9, _label(row["topic"]), "end", DARK, "13px"))
        body.append(_line(min(x_endorsed, x_opponent), y + 5, max(x_endorsed, x_opponent), y + 5, LIGHT))
        body.append(_circle(x_endorsed, y + 5, 6, DSA_RED))
        body.append(_circle(x_opponent, y + 5, 6, DEMOCRATIC_BLUE))
    body.extend(
        [
            _legend(770, 70, DSA_RED, "DSA-endorsed"),
            _legend(930, 70, DEMOCRATIC_BLUE, "Other Democrats"),
            _svg_footer(width, height, "Source: verified first-party candidate statements; duplicate queue copies removed."),
        ]
    )
    _write_svg(FIGURE_DIR / "candidate_topic_shares.svg", width, height, body)


def _similarity_chart(rows: list[dict[str, str]]) -> None:
    selected = sorted(rows, key=lambda row: float(row["cosine_similarity"]), reverse=True)[:14]
    _horizontal_svg(
        FIGURE_DIR / "topic_cosine_similarity.svg",
        "Language similarity within issues",
        "Cosine similarity between DSA-endorsed and other-Democrat wording",
        [_label(row["topic"]) for row in selected],
        [float(row["cosine_similarity"]) for row in selected],
        DEMOCRATIC_BLUE,
        maximum=1.0,
        footer=(
            "Source: candidate_statement_evidence.csv topic codes and exact quotes; "
            "cosine similarity uses normalized token-frequency vectors."
        ),
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
        "Share of verified excerpts: DSA-endorsed candidates minus other Democrats",
        [_label(row["topic"]) for row in selected],
        [
            float(row["endorsed_share"]) - float(row["opponent_share"])
            for row in selected
        ],
        "More endorsed-candidate emphasis",
        "More other-Democrat emphasis",
        (
            "Source: candidate_statement_evidence.csv topic codes; verified exact quotes; "
            "shares use deduplicated excerpts within each group."
        ),
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
        "More other-Democrat documents",
    )


def _coverage_chart(rows: list[dict[str, str]]) -> None:
    width = 1100
    height = 365
    plot_left = 230
    plot_width = 720
    maximum = max(
        (
            int(row["candidate_race_records_with_extracted_text"])
            + int(row["candidate_race_records_without_extracted_text"])
            for row in rows
        ),
        default=1,
    )
    body = [
        _svg_header(
            width,
            height,
            "Candidate/race text coverage",
            "Registry-wide candidate/race records with versus without extracted text",
        )
    ]
    for tick in range(5):
        value = maximum * tick / 4
        x = plot_left + plot_width * tick / 4
        body.append(_line(x, 112, x, 270, LIGHT))
        body.append(_text(x, 100, f"{value:.0f}", "middle", MID, "11px"))
    for index, row in enumerate(rows):
        y = 132 + index * 82
        verified = int(row["candidate_race_records_with_extracted_text"])
        unavailable = int(row["candidate_race_records_without_extracted_text"])
        verified_width = plot_width * verified / maximum
        unavailable_width = plot_width * unavailable / maximum
        group_label = (
            "Other Democrats" if row["group"] == "opponent" else _label(row["group"])
        )
        body.append(_text(plot_left - 24, y + 20, group_label, "end", DARK, "14px", "700"))
        body.append(_rect(plot_left, y, verified_width, 30, DSA_RED))
        body.append(_rect(plot_left + verified_width, y, unavailable_width, 30, "#C9CED3"))
        if verified_width > 45:
            body.append(_text(plot_left + verified_width - 9, y + 20, str(verified), "end", "#FFFFFF", "12px", "700"))
        body.append(
            _text(
                plot_left + verified_width + unavailable_width + 8,
                y + 20,
                f"{float(row['extracted_share']):.0%} extracted",
                size="12px",
            )
        )
    body.extend(
        [
            _legend(710, 72, DSA_RED, "Extracted text"),
            _legend(845, 72, "#C9CED3", "No extracted text"),
            _svg_footer(
                width,
                height,
                "Source: full_text_queue_summary.csv; verified is extracted; all other statuses are not extracted.",
            ),
        ]
    )
    _write_svg(FIGURE_DIR / "candidate_evidence_coverage.svg", width, height, body)


def _stacked_chart(
    rows: list[dict[str, str]], path: Path, title: str, subtitle: str, label_key: str
) -> None:
    width = 1200
    height = 205 + len(rows) * 42
    plot_left = 315
    plot_width = 760
    maximum = max((int(row["total"]) for row in rows), default=1)
    body = [_svg_header(width, height, title, subtitle)]
    for tick in range(5):
        value = maximum * tick / 4
        x = plot_left + plot_width * tick / 4
        body.append(_line(x, 106, x, height - 58, LIGHT))
        body.append(_text(x, 94, f"{value:.0f}", "middle", MID, "11px"))
    for index, row in enumerate(rows):
        y = 120 + index * 42
        explicit = int(row["explicit_conflict"])
        coded = int(row["coded_divergence"])
        explicit_width = plot_width * explicit / maximum
        coded_width = plot_width * coded / maximum
        body.append(_text(plot_left - 22, y + 17, _label(row[label_key]), "end", DARK, "13px"))
        body.append(_rect(plot_left, y, explicit_width, 24, DSA_RED))
        body.append(_rect(plot_left + explicit_width, y, coded_width, 24, DEMOCRATIC_BLUE))
        body.append(_text(plot_left + explicit_width + coded_width + 9, y + 17, row["total"], size="12px", weight="700"))
    body.extend(
        [
            _legend(805, 70, DSA_RED, "Explicit conflict"),
            _legend(955, 70, DEMOCRATIC_BLUE, "Coded divergence"),
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
    footer: str = "Positive scores favor the red group; negative scores favor the blue group.",
) -> None:
    width = 1240
    height = 215 + len(labels) * 36
    plot_left = 320
    plot_right = 1160
    center = 740
    half_width = 400
    maximum = max((abs(value) for value in values), default=1)
    body = [_svg_header(width, height, title, subtitle)]
    for fraction in (-1, -0.5, 0, 0.5, 1):
        x = center + half_width * fraction
        body.append(_line(x, 112, x, height - 60, LIGHT if fraction else MID))
        if fraction:
            body.append(_text(x, 99, f"{abs(maximum * fraction):.2f}", "middle", MID, "10px"))
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 126 + index * 36
        bar_width = half_width * abs(value) / maximum
        body.append(_text(plot_left - 20, y + 17, _label(label), "end", DARK, "13px"))
        if value >= 0:
            body.append(_rect(center, y, bar_width, 24, DSA_RED))
            body.append(_text(center + bar_width + 8, y + 17, f"{value:.2f}", size="11px"))
        else:
            body.append(_rect(center - bar_width, y, bar_width, 24, DEMOCRATIC_BLUE))
            body.append(_text(center - bar_width - 8, y + 17, f"{abs(value):.2f}", "end", size="11px"))
    body.extend(
        [
            _text((center + plot_right) / 2, 84, positive_label, "middle", DSA_RED, "12px", "700"),
            _text((plot_left + center) / 2, 84, negative_label, "middle", DEMOCRATIC_BLUE, "12px", "700"),
            _svg_footer(width, height, footer),
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
    value_format: str = ".2f",
    footer: str = (
        "Similarity ranges from 0 (no shared vocabulary) to 1 "
        "(identical term proportions)."
    ),
) -> None:
    width = 1150
    height = 205 + len(labels) * 40
    plot_left = 315
    plot_width = 740
    maximum = maximum or max(values, default=1)
    body = [_svg_header(width, height, title, subtitle)]
    for tick in range(5):
        x = plot_left + plot_width * tick / 4
        body.append(_line(x, 106, x, height - 58, LIGHT))
        body.append(
            _text(
                x,
                94,
                format(maximum * tick / 4, value_format),
                "middle",
                MID,
                "10px",
            )
        )
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        y = 120 + index * 40
        body.append(_text(plot_left - 22, y + 17, label, "end", DARK, "13px"))
        body.append(_rect(plot_left, y, plot_width * value / maximum, 24, color))
        body.append(
            _text(
                plot_left + plot_width * value / maximum + 9,
                y + 17,
                format(value, value_format),
                size="11px",
                weight="700",
            )
        )
    body.append(_svg_footer(width, height, footer))
    _write_svg(path, width, height, body)


def _svg_header(width: int, height: int, title: str, subtitle: str) -> str:
    return (
        _rect(0, 0, width, height, BACKGROUND)
        + _text(48, 47, title, color=DARK, size="27px", weight="700")
        + _text(48, 74, subtitle, color=MID, size="14px")
    )


def _svg_footer(width: int, height: int, text: str) -> str:
    return _text(48, height - 24, text, color=MID, size="10px", style="italic")


def _rect(x: float, y: float, width: float, height: float, color: str) -> str:
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(width, 0):.2f}" '
        f'height="{height:.2f}" fill="{color}" rx="3"/>'
    )


def _circle(x: float, y: float, radius: float, color: str) -> str:
    return (
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
        f'fill="{color}" stroke="{BACKGROUND}" stroke-width="2"/>'
    )


def _tint(color: str, amount: float) -> str:
    color = color.lstrip("#")
    channels = [int(color[index : index + 2], 16) for index in (0, 2, 4)]
    mixed = [round(channel + (255 - channel) * amount) for channel in channels]
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


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
    style: str = "normal",
) -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" fill="{color}" '
        f'font-family="Inter, Arial, Helvetica, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" font-style="{style}">{html.escape(str(value))}</text>'
    )


def _legend(x: float, y: float, color: str, label: str) -> str:
    return _circle(x + 6, y - 5, 6, color) + _text(x + 19, y, label, size="11px")


def _wrapped_text(
    x: float, y: float, value: str, width: int, color: str, max_lines: int = 4
) -> str:
    words = value.split()
    lines = []
    current = []
    for word in words:
        proposed = " ".join([*current, word])
        if len(proposed) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return "".join(
        _text(x, y + index * 20, line, color=color, size="12px")
        for index, line in enumerate(lines)
    )


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
