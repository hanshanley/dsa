from collections import Counter
from dataclasses import dataclass
from datetime import date

from .document_corpus import candidate_slug
from .io import read_csv, read_json
from .paths import CONFIG_DIR, MANUAL_DIR, PROCESSED_DIR
from .schema import (
    ANALYSIS_SCOPES,
    CONTRAST_TYPES,
    ORGANIZATIONAL_CONTEXT_STATUSES,
    SCHEMAS,
    STANCE_CODES,
    VERIFICATION_STATUSES,
)


@dataclass(frozen=True)
class AuditResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(strict: bool = False) -> AuditResult:
    errors: list[str] = []
    warnings: list[str] = []
    tables = {
        name: read_csv(MANUAL_DIR / f"{name}.csv")
        for name in SCHEMAS
    }

    for name, schema in SCHEMAS.items():
        rows = tables[name]
        keys = [row.get(schema.primary_key, "").strip() for row in rows]
        duplicates = [key for key, count in Counter(keys).items() if key and count > 1]
        if duplicates:
            errors.append(f"{name}: duplicate {schema.primary_key}: {duplicates}")
        for number, row in enumerate(rows, start=2):
            for field in schema.required:
                if not row.get(field, "").strip():
                    errors.append(f"{name}.csv:{number}: missing {field}")

    document_ids = {row["document_id"] for row in tables["documents"]}
    excerpt_ids = {row["excerpt_id"] for row in tables["excerpts"]}
    race_candidates = tables["race_candidates"]
    race_ids = {row["race_id"] for row in race_candidates}
    candidate_races = {
        (row["race_id"], row["candidate_id"])
        for row in race_candidates
    }
    registry_path = PROCESSED_DIR / "race_registry.csv"
    if registry_path.exists():
        for row in read_csv(registry_path):
            race_id = row.get("race_id", "").strip()
            if not race_id:
                continue
            race_ids.add(race_id)
            for field in (
                "endorsed_candidates",
                "unopposed_candidates",
                "opponent_candidates",
            ):
                for candidate_name in row.get(field, "").split(" | "):
                    if candidate_name.strip():
                        candidate_races.add(
                            (race_id, candidate_slug(candidate_name))
                        )
    candidate_document_rows = tables["candidate_documents"]
    organizational_context_rows = tables["organizational_context_sources"]
    taxonomy = read_json(CONFIG_DIR / "taxonomy.json")
    topics = set(taxonomy["topics"])
    subtopics = {
        subtopic
        for values in taxonomy["topics"].values()
        for subtopic in values
    }

    for number, row in enumerate(tables["documents"], start=2):
        if row["verification_status"] not in VERIFICATION_STATUSES:
            errors.append(f"documents.csv:{number}: invalid verification_status")
        tier = row["source_tier"]
        if tier not in {"1", "2", "3", "4"}:
            errors.append(f"documents.csv:{number}: source_tier must be 1-4")

    for number, row in enumerate(candidate_document_rows, start=2):
        if row["verification_status"] not in VERIFICATION_STATUSES:
            errors.append(f"candidate_documents.csv:{number}: invalid verification_status")
        tier = row["source_tier"]
        if tier not in {"1", "2", "3", "4"}:
            errors.append(f"candidate_documents.csv:{number}: source_tier must be 1-4")
        if row["role"] not in {"endorsed", "opponent", "unopposed"}:
            errors.append(f"candidate_documents.csv:{number}: invalid role")
        scope = row.get("analysis_scope", "").strip() or "analysis"
        if scope not in ANALYSIS_SCOPES:
            errors.append(f"candidate_documents.csv:{number}: invalid analysis_scope")
        if row["race_id"] not in race_ids:
            errors.append(f"candidate_documents.csv:{number}: unknown race_id")
        if (row["race_id"], row["candidate_id"]) not in candidate_races:
            errors.append(
                f"candidate_documents.csv:{number}: candidate missing from race roster"
            )

    for number, row in enumerate(organizational_context_rows, start=2):
        status = row["verification_status"]
        if status not in ORGANIZATIONAL_CONTEXT_STATUSES:
            errors.append(
                f"organizational_context_sources.csv:{number}: invalid verification_status"
            )
        if row["organization_level"] not in {"national", "state", "local"}:
            errors.append(
                f"organizational_context_sources.csv:{number}: invalid organization_level"
            )
        if row["context_category"] not in {
            "dnc_national",
            "state_democratic_party",
            "dsa_national",
            "dsa_state_local",
        }:
            errors.append(
                f"organizational_context_sources.csv:{number}: invalid context_category"
            )
        if status == "verified" and not (
            row.get("source_url", "").strip() or row.get("archive_url", "").strip()
        ):
            errors.append(
                "organizational_context_sources.csv:"
                f"{number}: verified row requires source_url or archive_url"
            )
        if row["context_category"] == "dsa_state_local":
            if not row.get("endorsing_body", "").strip():
                errors.append(
                    "organizational_context_sources.csv:"
                    f"{number}: dsa_state_local row requires endorsing_body"
                )
        elif row.get("endorsing_body", "").strip():
            errors.append(
                "organizational_context_sources.csv:"
                f"{number}: endorsing_body only allowed for dsa_state_local rows"
            )

    for number, row in enumerate(tables["endorsements"], start=2):
        if row["endorsement_source_document_id"] not in document_ids:
            errors.append(f"endorsements.csv:{number}: unknown source document")
        if row["primary_party"].lower() != "democratic":
            warnings.append(f"endorsements.csv:{number}: primary party is not Democratic")
        if row["verification_status"] not in VERIFICATION_STATUSES:
            errors.append(f"endorsements.csv:{number}: invalid verification_status")
        if row["race_id"] not in race_ids:
            errors.append(f"endorsements.csv:{number}: unknown race_id")
        if (row["race_id"], row["candidate_id"]) not in candidate_races:
            errors.append(
                f"endorsements.csv:{number}: endorsed candidate missing from race roster"
            )

    race_sizes = Counter(row["race_id"] for row in race_candidates)
    for race_id, size in race_sizes.items():
        if size < 2:
            errors.append(f"race_candidates: {race_id} has fewer than two candidates")
    for number, row in enumerate(race_candidates, start=2):
        if row["role"] not in {"endorsed", "opponent"}:
            errors.append(f"race_candidates.csv:{number}: invalid role")
        if row["evidence_status"] not in VERIFICATION_STATUSES:
            errors.append(f"race_candidates.csv:{number}: invalid evidence_status")

    for number, row in enumerate(tables["excerpts"], start=2):
        if row["document_id"] not in document_ids:
            errors.append(f"excerpts.csv:{number}: unknown document_id")
        if row["stance"] not in STANCE_CODES:
            errors.append(f"excerpts.csv:{number}: invalid stance")
        if row["topic"] not in topics:
            errors.append(f"excerpts.csv:{number}: unknown topic")
        if row["subtopic"] not in subtopics:
            errors.append(f"excerpts.csv:{number}: unknown subtopic")
        if row["reviewed"].lower() not in {"true", "false"}:
            errors.append(f"excerpts.csv:{number}: reviewed must be true or false")
        if len(row["quote"].strip()) < 20:
            warnings.append(f"excerpts.csv:{number}: unusually short quote")

    relationships = set(taxonomy["relationship_codes"])
    for number, row in enumerate(tables["platform_comparisons"], start=2):
        for field in ("dsa_excerpt_id", "democratic_excerpt_id"):
            if row[field] not in excerpt_ids:
                errors.append(f"platform_comparisons.csv:{number}: unknown {field}")
        if row["relationship_code"] not in relationships:
            errors.append(
                f"platform_comparisons.csv:{number}: invalid relationship_code"
            )
        if row["topic"] not in topics or row["subtopic"] not in subtopics:
            errors.append(f"platform_comparisons.csv:{number}: unknown topic code")
        if row["reviewed"].lower() not in {"true", "false"}:
            errors.append(
                f"platform_comparisons.csv:{number}: reviewed must be true or false"
            )

    for number, row in enumerate(tables["contrasts"], start=2):
        if row["contrast_type"] not in CONTRAST_TYPES:
            errors.append(f"contrasts.csv:{number}: invalid contrast_type")
        if row["relationship_code"] not in relationships:
            errors.append(f"contrasts.csv:{number}: invalid relationship_code")
        if row["topic"] not in topics or row["subtopic"] not in subtopics:
            errors.append(f"contrasts.csv:{number}: unknown topic code")
        if row["reviewed"].lower() not in {"true", "false"}:
            errors.append(f"contrasts.csv:{number}: reviewed must be true or false")
        for field in ("candidate_excerpt_id", "opponent_excerpt_id"):
            value = row[field].strip()
            if value and value not in excerpt_ids:
                errors.append(f"contrasts.csv:{number}: unknown {field}")

    cutoff = date.fromisoformat(read_json(CONFIG_DIR / "sources.json")["research_cutoff"])
    if cutoff > date.today():
        warnings.append("research cutoff is in the future relative to the runtime clock")

    if not tables["endorsements"]:
        warnings.append("verified Democratic-primary endorsements have not yet been populated")
    if not tables["coverage"] and not (PROCESSED_DIR / "coverage_ledger.csv").exists():
        warnings.append("chapter-year coverage ledger has not yet been populated")
    if not (PROCESSED_DIR / "candidate_statement_evidence.csv").exists():
        incomplete_opponents = sum(
            row["role"] == "opponent" and row["evidence_status"] != "verified"
            for row in race_candidates
        )
        if incomplete_opponents:
            warnings.append(
                f"{incomplete_opponents} other-Democrat records still need verified first-party evidence"
            )
    else:
        _validate_statement_evidence(errors, warnings, taxonomy)
    if not tables["contrasts"]:
        warnings.append("candidate/opponent contrasts have not yet been populated")

    if strict:
        coverage_path = PROCESSED_DIR / "coverage_ledger.csv"
        if not coverage_path.exists():
            errors.append("strict census: coverage_ledger.csv has not been generated")
        else:
            coverage_rows = read_csv(coverage_path)
            unresolved = [
                row
                for row in coverage_rows
                if row["status"] in {"not_searched", "found_unverified"}
            ]
            if unresolved:
                errors.append(
                    f"strict census: {len(unresolved)} chapter-year rows remain unresolved"
                )
        verified_path = PROCESSED_DIR / "local_endorsements_verified.csv"
        rejected_path = PROCESSED_DIR / "local_endorsements_rejected.csv"
        candidates_path = PROCESSED_DIR / "local_endorsement_candidates.csv"
        if not verified_path.exists() or not rejected_path.exists():
            errors.append(
                "strict census: second-pass local endorsement verification is incomplete"
            )
        opponent_queue_path = PROCESSED_DIR / "opponent_research_queue.csv"
        if not opponent_queue_path.exists():
            errors.append("strict census: opponent research queue has not been generated")
        else:
            unresolved_opponent_rows = [
                row
                for row in read_csv(opponent_queue_path)
                if any(
                    row[field]
                    not in {
                        "verified",
                        "source_unavailable",
                        "not_a_primary",
                        "not_applicable",
                    }
                    for field in (
                        "race_resolution_status",
                        "opponent_roster_status",
                        "candidate_statement_status",
                        "opponent_statement_status",
                    )
                )
            ]
            if unresolved_opponent_rows:
                errors.append(
                    "strict census: "
                    f"{len(unresolved_opponent_rows)} endorsed candidacies still lack "
                    "complete race/opponent evidence"
                )

    return AuditResult(tuple(errors), tuple(warnings))


def _validate_statement_evidence(
    errors: list[str],
    warnings: list[str],
    taxonomy: dict,
) -> None:
    rows = read_csv(PROCESSED_DIR / "candidate_statement_evidence.csv")
    topics = set(taxonomy["topics"])
    for number, row in enumerate(rows, start=2):
        if row["evidence_status"] not in {"verified", "source_unavailable"}:
            errors.append(
                f"candidate_statement_evidence.csv:{number}: invalid evidence_status"
            )
            continue
        if row["evidence_status"] != "verified":
            continue
        if not row["source_url"].strip() or not row["quote"].strip():
            errors.append(
                f"candidate_statement_evidence.csv:{number}: verified evidence "
                "requires source_url and quote"
            )
        if len(row["quote"].strip()) < 20:
            warnings.append(
                f"candidate_statement_evidence.csv:{number}: unusually short quote"
            )
        topic = row["topic"]
        subtopic = row["subtopic"]
        if topic not in topics or subtopic not in taxonomy["topics"].get(topic, []):
            errors.append(
                f"candidate_statement_evidence.csv:{number}: invalid topic/subtopic"
            )
        if row["stance"] not in STANCE_CODES:
            errors.append(
                f"candidate_statement_evidence.csv:{number}: invalid stance"
            )
        published = row["published_date"].strip()
        election = row["election_date"].strip()
        if published and election:
            try:
                if _parse_evidence_date(published) > date.fromisoformat(election):
                    errors.append(
                        f"candidate_statement_evidence.csv:{number}: source published "
                        "after the primary election"
                    )
            except ValueError:
                warnings.append(
                    f"candidate_statement_evidence.csv:{number}: non-ISO evidence date"
                )


def _parse_evidence_date(value: str) -> date:
    if len(value) == 4:
        value = f"{value}-01-01"
    if len(value) == 7:
        value = f"{value}-01"
    return date.fromisoformat(value)
