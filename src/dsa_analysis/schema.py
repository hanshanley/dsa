from dataclasses import dataclass


@dataclass(frozen=True)
class TableSchema:
    name: str
    primary_key: str
    required: tuple[str, ...]


SCHEMAS = {
    "documents": TableSchema(
        "documents",
        "document_id",
        (
            "document_id",
            "organization",
            "title",
            "document_type",
            "url",
            "source_tier",
            "verification_status",
        ),
    ),
    "candidate_documents": TableSchema(
        "candidate_documents",
        "candidate_document_id",
        (
            "candidate_document_id",
            "race_id",
            "candidate_id",
            "candidate_name",
            "role",
            "election_date",
            "title",
            "source_type",
            "source_tier",
            "source_url",
            "verification_status",
        ),
    ),
    "organizational_context_sources": TableSchema(
        "organizational_context_sources",
        "context_entry_id",
        (
            "context_entry_id",
            "state",
            "state_code",
            "cycle_year",
            "organization_level",
            "context_category",
            "organization",
            "title",
            "platform_type",
            "verification_status",
        ),
    ),
    "endorsements": TableSchema(
        "endorsements",
        "endorsement_id",
        (
            "endorsement_id",
            "race_id",
            "candidate_id",
            "candidate_name",
            "office",
            "jurisdiction",
            "election_date",
            "primary_party",
            "endorsing_body",
            "endorsement_source_document_id",
            "verification_status",
        ),
    ),
    "race_candidates": TableSchema(
        "race_candidates",
        "race_candidate_id",
        (
            "race_candidate_id",
            "race_id",
            "candidate_id",
            "candidate_name",
            "party",
            "role",
            "ballot_status",
            "evidence_status",
            "source_url",
        ),
    ),
    "excerpts": TableSchema(
        "excerpts",
        "excerpt_id",
        (
            "excerpt_id",
            "document_id",
            "speaker",
            "quote",
            "locator",
            "claim_type",
            "stance",
            "topic",
            "subtopic",
            "cycle",
            "reviewed",
        ),
    ),
    "contrasts": TableSchema(
        "contrasts",
        "contrast_id",
        (
            "contrast_id",
            "race_id",
            "candidate_id",
            "opponent_id",
            "topic",
            "contrast_type",
            "relationship_code",
            "reviewed",
        ),
    ),
    "platform_comparisons": TableSchema(
        "platform_comparisons",
        "comparison_id",
        (
            "comparison_id",
            "cycle",
            "topic",
            "subtopic",
            "dsa_excerpt_id",
            "democratic_excerpt_id",
            "relationship_code",
            "reviewed",
        ),
    ),
    "coverage": TableSchema(
        "coverage",
        "coverage_id",
        ("coverage_id", "chapter", "election_year", "status"),
    ),
}

VERIFICATION_STATUSES = {
    "not_searched",
    "searched_not_found",
    "source_unavailable",
    "found_unverified",
    "verified",
}
ORGANIZATIONAL_CONTEXT_STATUSES = VERIFICATION_STATUSES | {"not_applicable"}
ANALYSIS_SCOPES = {"analysis", "context_only"}
STANCE_CODES = {"support", "oppose", "mixed", "unclear"}
CONTRAST_TYPES = {"explicit_conflict", "coded_divergence"}
