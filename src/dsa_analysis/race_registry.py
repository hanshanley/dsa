from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from .io import read_csv, write_csv
from .paths import ANALYSIS_DATA_DIR, MANUAL_DIR, PROCESSED_DIR

IN_SCOPE_KIND = "tracked_dsa_endorsed_democratic_primary"
OUT_OF_SCOPE_KIND = "other_corpus_race"
QUEUE_ROLES = {"endorsed", "opponent", "unopposed"}
HIGH_CONFIDENCE = "high"
VERIFIED_CONFIDENCE = "verified"
OFFICIAL_METADATA_SOURCE_TYPES = {"official_voter_guide", "filing"}
CANDIDATE_OWNED_SOURCE_TYPES = {
    "candidate_campaign_site",
    "campaign_page",
    "campaign_website",
    "campaign_issue_page",
    "campaign_platform",
    "campaign_policy",
    "campaign_release",
    "campaign_statement",
    "official_campaign_page",
    "official_statement",
    "policy_page",
    "press_release",
}
OFFICIAL_HOST_STATE_MAP = {
    "www.nyccfb.info": "NY",
    "www.nycvotes.org": "NY",
    "nycvotes.org": "NY",
    "voter.votewa.gov": "WA",
    "cdn.kingcounty.gov": "WA",
    "vigarchive.sos.ca.gov": "CA",
    "vig.cdn.sos.ca.gov": "CA",
    "acvote.alamedacountyca.gov": "CA",
    "electionstats.state.ma.us": "MA",
    "www.oregonvotes.gov": "OR",
}
STATE_NAME_BY_CODE = {
    "AK": "Alaska",
    "AL": "Alabama",
    "AR": "Arkansas",
    "AZ": "Arizona",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DC": "District of Columbia",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MS": "Mississippi",
    "MT": "Montana",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
}
KNOWN_PARTY_CODES = {"DEM", "REP", "NP", "NPP", "WFP", "PAF", "PF", "GP", "LIB", "IND"}
FIELD_STATUS_PRIORITY = {
    "manual_verified": 6,
    "resolution_verified": 5,
    "processed_verified": 4,
    "metadata_inferred": 3,
    "hint_parsed": 2,
    "source_unavailable": 1,
    "unresolved": 0,
}
SOURCE_CONFIDENCE_PRIORITY = {"verified": 2, "high": 1, "": 0}
SUPPORTING_SOURCE_STATUS_PRIORITY = {
    "manual_supporting": 4,
    "resolution_supporting": 3,
    "processed_supporting": 2,
    "metadata_supporting": 1,
    "unresolved": 0,
}
ELECTION_AUTHORITY_HOST_ALLOWLIST = {
    "acvote.alamedacountyca.gov",
    "albanycounty.com",
    "azsos.gov",
    "cl.ingham.org",
    "cdn.kingcounty.gov",
    "county.milwaukee.gov",
    "detroitmi.gov",
    "douglascountyks.org",
    "duluthmn.gov",
    "electionarchive.vermont.gov",
    "electionarchive.washtenaw.org",
    "electionstats.state.ma.us",
    "electionhistory.ct.gov",
    "electionresults.dcboe.org",
    "electionresults.mt.gov",
    "electionresults.sos.ca.gov",
    "electionresults.sos.nm.gov",
    "electionresults.sos.state.mn.us",
    "elections.cdn.sos.ca.gov",
    "elections.delaware.gov",
    "elections.il.gov",
    "elections.maryland.gov",
    "elections.ny.gov",
    "elections.sos.state.tx.us",
    "elections.wi.gov",
    "elect.ky.gov",
    "er.ncsbe.gov",
    "historicalelectiondata.coloradosos.gov",
    "historical.elections.virginia.gov",
    "harrisvotes.com",
    "kingcounty.gov",
    "larimer.org",
    "lehighcounty.org",
    "mielections.us",
    "mvic.sos.state.mi.us",
    "results.enr.clarityelections.com",
    "results.elections.maryland.gov",
    "results.elections.myflorida.com",
    "results.elections.ny.gov",
    "results.lavote.gov",
    "results.oregonvotes.gov",
    "results.vote.wa.gov",
    "secure.sos.state.or.us",
    "sos.mo.gov",
    "sos.oregon.gov",
    "sos.state.co.us",
    "sos.tn.gov",
    "teamrv-mvp.sos.texas.gov",
    "vote-results.phila.gov",
    "voterportal.sos.la.gov",
    "vig.cdn.sos.ca.gov",
    "vigarchive.sos.ca.gov",
    "www.albanycounty.com",
    "www.bloomfieldct.gov",
    "www.boston.gov",
    "www.coloradosos.gov",
    "www.dcboe.org",
    "www.douglascountyks.org",
    "www.electionreturns.pa.gov",
    "www.elections.il.gov",
    "www.elections.virginia.gov",
    "www.harrisvotes.com",
    "www.larimer.org",
    "www.lehighcounty.org",
    "www.monroecounty.gov",
    "www.nvsos.gov",
    "www.oregonvotes.gov",
    "www.rensco.com",
    "www.ri.gov",
    "www.sec.state.ma.us",
    "www.sos.mo.gov",
    "www.sos.ms.gov",
    "www.sos.state.co.us",
    "www.stlouis-mo.gov",
    "www.tucsonaz.gov",
    "www.vote.nyc",
    "www.votepinellas.com",
}
ELECTION_AUTHORITY_PATH_TOKENS = (
    "ballot",
    "board-election",
    "board-of-elections",
    "candidate",
    "campaign-finance",
    "cfdetail",
    "canvass",
    "contest",
    "election",
    "elect",
    "officialcanvass",
    "orestar",
    "poll",
    "primary",
    "result",
    "return",
    "vote",
    "voter",
)
OFFICIAL_SOURCE_EXCLUDED_HOST_SUFFIXES = (".house.gov", ".senate.gov")
OFFICIAL_SOURCE_EXCLUDED_HOSTS = {
    "housedems.com",
    "nyassembly.gov",
}


@dataclass(frozen=True)
class RaceRegistryPaths:
    candidate_corpus_path: Path
    manual_endorsements_path: Path
    manual_race_candidates_path: Path
    manual_resolution_paths: tuple[Path, ...]
    processed_race_rosters_path: Path
    output_dir: Path
    candidate_document_metadata_path: Path | None = None
    candidate_document_full_text_path: Path | None = None
    national_census_resolution_paths: tuple[Path, ...] = ()
    processed_opponent_queue_path: Path | None = None

    @classmethod
    def default(cls) -> "RaceRegistryPaths":
        return cls(
            candidate_corpus_path=ANALYSIS_DATA_DIR / "candidate_text_corpus.csv",
            manual_endorsements_path=MANUAL_DIR / "endorsements.csv",
            manual_race_candidates_path=MANUAL_DIR / "race_candidates.csv",
            manual_resolution_paths=tuple(
                sorted(MANUAL_DIR.glob("race_registry_resolutions_*.csv"))
            ),
            processed_race_rosters_path=PROCESSED_DIR / "race_rosters_discovered.csv",
            output_dir=PROCESSED_DIR,
            candidate_document_metadata_path=PROCESSED_DIR
            / "candidate_document_metadata.csv",
            candidate_document_full_text_path=PROCESSED_DIR
            / "candidate_document_full_text.jsonl",
            national_census_resolution_paths=tuple(
                sorted(MANUAL_DIR.glob("national_census_resolutions_*.csv"))
            ),
            processed_opponent_queue_path=PROCESSED_DIR
            / "opponent_research_queue.csv",
        )


@dataclass(frozen=True)
class RaceRegistryResult:
    race_rows: int
    in_scope_race_rows: int
    resolved_state_race_rows: int
    unresolved_race_rows: int
    represented_state_cycle_rows: int
    summary_path: Path
    registry_path: Path
    alias_mapping_path: Path
    unresolved_queue_path: Path
    represented_state_cycles_path: Path


@dataclass(frozen=True)
class ManualRacePackage:
    manual_race_id: str
    election_date: str
    endorsed_candidates: tuple[str, ...]
    opponent_candidates: tuple[str, ...]
    office: str
    jurisdiction: str
    state_code: str
    state: str
    official_election_source: str
    endorsing_bodies: tuple[str, ...]


@dataclass(frozen=True)
class ProcessedRacePackage:
    processed_race_id: str
    election_date: str
    endorsed_candidates: tuple[str, ...]
    opponent_candidates: tuple[str, ...]
    official_election_source: str
    office: str
    jurisdiction: str
    state_code: str
    state: str
    endorsing_bodies: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionPackage:
    race_id: str
    election_date: str
    office: str
    jurisdiction: str
    state: str
    state_code: str
    official_election_source: str
    verification_status: str
    notes: str
    source_key: str


@dataclass(frozen=True)
class SourceClassification:
    is_election_authority: bool
    invalid_type: str


class RaceRegistryError(ValueError):
    pass


def build_race_registry(paths: RaceRegistryPaths | None = None) -> RaceRegistryResult:
    paths = paths or RaceRegistryPaths.default()
    corpus_rows = read_csv(paths.candidate_corpus_path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in corpus_rows:
        race_id = row.get("race_id", "").strip()
        if not race_id:
            raise RaceRegistryError(f"{paths.candidate_corpus_path.name}: missing race_id")
        grouped[race_id].append(row)

    manual_packages = _manual_race_packages(
        paths.manual_endorsements_path,
        paths.manual_race_candidates_path,
    )
    manual_seeded_races = _seed_grouped_from_manual_packages(grouped, manual_packages)
    national_packages, national_seed_summary = _seed_grouped_from_national_census(
        grouped,
        paths.national_census_resolution_paths,
        paths.output_dir / "race_registry_national_endorsement_reconciliation.csv",
    )
    resolution_packages = _resolution_packages(
        paths.manual_resolution_paths,
        grouped,
    )
    for race_id, package in national_packages.items():
        resolution_packages.setdefault(race_id, package)
    processed_packages = _processed_race_packages(
        paths.processed_race_rosters_path,
        paths.processed_opponent_queue_path,
    )
    processed_seeded_races = _seed_grouped_from_processed_packages(
        grouped,
        processed_packages,
    )
    metadata_evidence_by_race = _candidate_document_evidence_by_race(
        paths.candidate_document_metadata_path,
        paths.candidate_document_full_text_path,
    )

    raw_registry_rows: list[dict[str, str]] = []
    reclassified_non_authority_resolution_rows = 0

    for race_id, rows in sorted(grouped.items()):
        election_dates = sorted({row.get("election_date", "").strip() for row in rows if row.get("election_date", "").strip()})
        if len(election_dates) != 1:
            raise RaceRegistryError(f"{race_id}: expected one election_date, found {election_dates}")
        election_date = election_dates[0]
        endorsed_candidates = sorted({row.get("candidate_name", "").strip() for row in rows if row.get("role", "").strip() == "endorsed"})
        unopposed_candidates = sorted({row.get("candidate_name", "").strip() for row in rows if row.get("role", "").strip() == "unopposed"})
        opponent_candidates = sorted({row.get("candidate_name", "").strip() for row in rows if row.get("role", "").strip() == "opponent"})
        all_candidates = sorted({row.get("candidate_name", "").strip() for row in rows if row.get("candidate_name", "").strip()})
        roles = sorted({row.get("role", "").strip() for row in rows if row.get("role", "").strip()})
        parties = sorted({row.get("party", "").strip() for row in rows if row.get("party", "").strip()})
        evidence_statuses = sorted({row.get("evidence_status", "").strip() for row in rows if row.get("evidence_status", "").strip()})

        scope_kind = (
            IN_SCOPE_KIND
            if any(
                row.get("party", "").strip() == "Democratic"
                and row.get("role", "").strip() in {"endorsed", "unopposed"}
                for row in rows
            )
            else OUT_OF_SCOPE_KIND
        )
        primary_party = "Democratic" if scope_kind == IN_SCOPE_KIND else (parties[0] if len(parties) == 1 else "")
        endorsed_name = " | ".join(endorsed_candidates or unopposed_candidates)

        manual_match = _match_manual_package(rows, manual_packages, election_date, endorsed_candidates, unopposed_candidates)
        resolution_match = resolution_packages.get(race_id)
        processed_match = _match_processed_package(rows, processed_packages, election_date, endorsed_candidates, unopposed_candidates)
        hint = _race_hint(rows)

        office = ""
        office_status = "unresolved"
        jurisdiction = ""
        jurisdiction_status = "unresolved"
        state = ""
        state_code = ""
        state_status = "unresolved"
        official_election_source = ""
        official_election_source_status = "unresolved"
        certified_opponents = ""
        certified_opponents_status = "unresolved"
        metadata_source = "corpus_only"
        source_reference = ""
        endorsing_bodies: list[str] = []
        office_source = ""
        office_confidence = ""
        jurisdiction_source = ""
        jurisdiction_confidence = ""
        state_source = ""
        state_confidence = ""
        official_election_source_source = ""
        official_election_source_confidence = ""
        supporting_source = ""
        supporting_source_status = "unresolved"
        supporting_source_type = ""
        supporting_source_source = ""
        supporting_source_confidence = ""

        if manual_match is not None:
            office = manual_match.office
            office_status = "manual_verified"
            office_source = manual_match.manual_race_id
            office_confidence = VERIFIED_CONFIDENCE
            jurisdiction = manual_match.jurisdiction
            jurisdiction_status = "manual_verified"
            jurisdiction_source = manual_match.manual_race_id
            jurisdiction_confidence = VERIFIED_CONFIDENCE
            state = manual_match.state
            state_code = manual_match.state_code
            state_status = "manual_verified"
            state_source = manual_match.manual_race_id
            state_confidence = VERIFIED_CONFIDENCE
            source_fields = _classified_source_fields(
                url=manual_match.official_election_source,
                verified_status="manual_verified",
                source_unavailable_status="source_unavailable",
                supporting_status="manual_supporting",
                source_key=manual_match.manual_race_id,
            )
            official_election_source = source_fields["official_election_source"]
            official_election_source_status = source_fields["official_election_source_status"]
            official_election_source_source = source_fields["official_election_source_source"]
            official_election_source_confidence = source_fields["official_election_source_confidence"]
            supporting_source = source_fields["supporting_source"]
            supporting_source_status = source_fields["supporting_source_status"]
            supporting_source_type = source_fields["supporting_source_type"]
            supporting_source_source = source_fields["supporting_source_source"]
            supporting_source_confidence = source_fields["supporting_source_confidence"]
            certified_opponents = " | ".join(manual_match.opponent_candidates)
            certified_opponents_status = "manual_verified"
            metadata_source = "manual_verified"
            source_reference = manual_match.manual_race_id
            endorsing_bodies = list(manual_match.endorsing_bodies)
        if resolution_match is not None:
            _validate_resolution_against_manual(resolution_match, manual_match)
            if manual_match is None:
                office = resolution_match.office
                office_status = (
                    f"resolution_{resolution_match.verification_status}"
                    if resolution_match.office
                    else "unresolved"
                )
                office_source = resolution_match.source_key if resolution_match.office else ""
                office_confidence = (
                    VERIFIED_CONFIDENCE
                    if resolution_match.verification_status == "verified" and resolution_match.office
                    else (HIGH_CONFIDENCE if resolution_match.office else "")
                )
                jurisdiction = resolution_match.jurisdiction
                jurisdiction_status = (
                    f"resolution_{resolution_match.verification_status}"
                    if resolution_match.jurisdiction
                    else "unresolved"
                )
                jurisdiction_source = (
                    resolution_match.source_key if resolution_match.jurisdiction else ""
                )
                jurisdiction_confidence = (
                    VERIFIED_CONFIDENCE
                    if resolution_match.verification_status == "verified" and resolution_match.jurisdiction
                    else (HIGH_CONFIDENCE if resolution_match.jurisdiction else "")
                )
                state = resolution_match.state
                state_code = resolution_match.state_code
                state_status = (
                    f"resolution_{resolution_match.verification_status}"
                    if resolution_match.state_code
                    else "unresolved"
                )
                state_source = resolution_match.source_key if resolution_match.state_code else ""
                state_confidence = (
                    VERIFIED_CONFIDENCE
                    if resolution_match.verification_status == "verified" and resolution_match.state_code
                    else (HIGH_CONFIDENCE if resolution_match.state_code else "")
                )
                source_fields = _classified_source_fields(
                    url=resolution_match.official_election_source,
                    verified_status="resolution_verified",
                    source_unavailable_status="source_unavailable",
                    supporting_status="resolution_supporting",
                    source_key=resolution_match.source_key,
                    verification_status=resolution_match.verification_status,
                )
                official_election_source = source_fields["official_election_source"]
                official_election_source_status = source_fields["official_election_source_status"]
                official_election_source_source = source_fields["official_election_source_source"]
                official_election_source_confidence = source_fields["official_election_source_confidence"]
                supporting_source = source_fields["supporting_source"]
                supporting_source_status = source_fields["supporting_source_status"]
                supporting_source_type = source_fields["supporting_source_type"]
                supporting_source_source = source_fields["supporting_source_source"]
                supporting_source_confidence = source_fields["supporting_source_confidence"]
                if (
                    resolution_match.verification_status == "verified"
                    and resolution_match.official_election_source
                    and not official_election_source
                    and supporting_source_status == "resolution_supporting"
                    and supporting_source_type
                    in {
                        "candidate_controlled",
                        "incumbent_office",
                        "legislator_site",
                        "party_or_caucus",
                    }
                ):
                    reclassified_non_authority_resolution_rows += 1
                metadata_source = f"resolution_{resolution_match.verification_status}"
                source_reference = resolution_match.source_key
        elif processed_match is not None:
            if not office and processed_match.office:
                office = processed_match.office
                office_status = "processed_verified"
                office_source = processed_match.processed_race_id
                office_confidence = VERIFIED_CONFIDENCE
            if not jurisdiction and processed_match.jurisdiction:
                jurisdiction = processed_match.jurisdiction
                jurisdiction_status = "processed_verified"
                jurisdiction_source = processed_match.processed_race_id
                jurisdiction_confidence = VERIFIED_CONFIDENCE
            if not state_code and processed_match.state_code:
                state_code = processed_match.state_code
                state = processed_match.state
                state_status = "processed_verified"
                state_source = processed_match.processed_race_id
                state_confidence = VERIFIED_CONFIDENCE
            source_fields = _classified_source_fields(
                url=processed_match.official_election_source,
                verified_status="processed_verified",
                source_unavailable_status="source_unavailable",
                supporting_status="processed_supporting",
                source_key=processed_match.processed_race_id,
            )
            official_election_source = source_fields["official_election_source"]
            official_election_source_status = source_fields["official_election_source_status"]
            official_election_source_source = source_fields["official_election_source_source"]
            official_election_source_confidence = source_fields["official_election_source_confidence"]
            supporting_source = source_fields["supporting_source"]
            supporting_source_status = source_fields["supporting_source_status"]
            supporting_source_type = source_fields["supporting_source_type"]
            supporting_source_source = source_fields["supporting_source_source"]
            supporting_source_confidence = source_fields["supporting_source_confidence"]
            certified_opponents = " | ".join(processed_match.opponent_candidates)
            certified_opponents_status = (
                "processed_verified" if certified_opponents else "unresolved"
            )
            metadata_source = "processed_verified"
            source_reference = processed_match.processed_race_id
            endorsing_bodies = list(processed_match.endorsing_bodies)
        if resolution_match is None and hint is not None:
            if not state_code:
                state_code = hint["state_code"]
                state = hint["state"]
                state_status = "hint_parsed"
                state_source = hint["race_code"]
                state_confidence = HIGH_CONFIDENCE
            if not office:
                office = hint["office"]
                office_status = hint["office_status"]
                if office:
                    office_source = hint["race_code"]
                    office_confidence = HIGH_CONFIDENCE
            if not jurisdiction and hint["jurisdiction"]:
                jurisdiction = hint["jurisdiction"]
                jurisdiction_status = hint["jurisdiction_status"]
                jurisdiction_source = hint["race_code"]
                jurisdiction_confidence = HIGH_CONFIDENCE
            if metadata_source == "corpus_only":
                metadata_source = "hint_parsed"
                source_reference = hint["race_code"]
        if resolution_match is None:
            local_inference = _infer_local_metadata(
                rows=rows,
                metadata_rows=metadata_evidence_by_race.get(race_id, []),
                election_date=election_date,
            )
            if office_status == "unresolved" and local_inference["office"]:
                office = local_inference["office"]
                office_status = "metadata_inferred"
                office_source = local_inference["office_source"]
                office_confidence = local_inference["office_confidence"]
            if jurisdiction_status == "unresolved" and local_inference["jurisdiction"]:
                jurisdiction = local_inference["jurisdiction"]
                jurisdiction_status = "metadata_inferred"
                jurisdiction_source = local_inference["jurisdiction_source"]
                jurisdiction_confidence = local_inference["jurisdiction_confidence"]
            if state_status == "unresolved" and local_inference["state_code"]:
                state_code = local_inference["state_code"]
                state = STATE_NAME_BY_CODE[state_code]
                state_status = "metadata_inferred"
                state_source = local_inference["state_source"]
                state_confidence = local_inference["state_confidence"]
            if (
                official_election_source_status == "unresolved"
                and local_inference["official_election_source"]
            ):
                official_election_source = local_inference["official_election_source"]
                official_election_source_status = "metadata_inferred"
                official_election_source_source = local_inference[
                    "official_election_source_source"
                ]
                official_election_source_confidence = local_inference[
                    "official_election_source_confidence"
                ]
            if metadata_source == "corpus_only" and any(
                (
                    office_status == "metadata_inferred",
                    jurisdiction_status == "metadata_inferred",
                    state_status == "metadata_inferred",
                    official_election_source_status == "metadata_inferred",
                )
            ):
                metadata_source = "metadata_inferred"
                source_reference = local_inference["source_reference"]
        if not certified_opponents and opponent_candidates:
            certified_opponents = " | ".join(opponent_candidates)
            certified_opponents_status = "corpus_candidate_set"
        if not endorsing_bodies and manual_match is not None:
            endorsing_bodies = list(manual_match.endorsing_bodies)

        unresolved_fields = [
            field
            for field, status in (
                ("office", office_status),
                ("jurisdiction", jurisdiction_status),
                ("state", state_status),
                ("official_election_source", official_election_source_status),
            )
            if status == "unresolved"
        ]
        if certified_opponents_status == "unresolved":
            unresolved_fields.append("certified_opponents")

        registry_row = {
            "race_id": race_id,
            "scope_kind": scope_kind,
            "election_date": election_date,
            "election_year": election_date[:4],
            "primary_party": primary_party,
            "endorsed_candidate": endorsed_name,
            "endorsed_candidates": " | ".join(endorsed_candidates),
            "unopposed_candidates": " | ".join(unopposed_candidates),
            "opponent_candidates": " | ".join(opponent_candidates),
            "all_candidates": " | ".join(all_candidates),
            "candidate_count": str(len(all_candidates)),
            "role_set": " | ".join(roles),
            "party_set": " | ".join(parties),
            "evidence_statuses": " | ".join(evidence_statuses),
            "office": office,
            "office_status": office_status,
            "office_source": office_source,
            "office_confidence": office_confidence,
            "jurisdiction": jurisdiction,
            "jurisdiction_status": jurisdiction_status,
            "jurisdiction_source": jurisdiction_source,
            "jurisdiction_confidence": jurisdiction_confidence,
            "state": state,
            "state_code": state_code,
            "state_status": state_status,
            "state_source": state_source,
            "state_confidence": state_confidence,
            "official_election_source": official_election_source,
            "official_election_source_status": official_election_source_status,
            "official_election_source_source": official_election_source_source,
            "official_election_source_confidence": official_election_source_confidence,
            "supporting_source": supporting_source,
            "supporting_source_status": supporting_source_status,
            "supporting_source_type": supporting_source_type,
            "supporting_source_source": supporting_source_source,
            "supporting_source_confidence": supporting_source_confidence,
            "certified_opponents": certified_opponents,
            "certified_opponents_status": certified_opponents_status,
            "endorsing_bodies": " | ".join(endorsing_bodies),
            "metadata_source": metadata_source,
            "source_reference": source_reference,
            "unresolved_fields": " | ".join(unresolved_fields),
        }
        raw_registry_rows.append(registry_row)

    registry_rows, alias_rows, duplicate_context_count, in_scope_duplicate_context_count = _canonicalize_registry_rows(
        raw_registry_rows
    )
    unresolved_rows = _unresolved_queue_rows(registry_rows)
    represented_rows = _represented_state_cycle_rows(registry_rows)
    national_reconciliation_rows = _national_endorsement_reconciliation_rows(
        paths.output_dir / "national_endorsement_archive.csv",
        registry_rows,
        paths.national_census_resolution_paths,
    )

    summary = {
        "canonical_races": len(registry_rows),
        "in_scope_races": sum(row["scope_kind"] == IN_SCOPE_KIND for row in registry_rows),
        "raw_total_races": len(raw_registry_rows),
        "manual_endorsement_seeded_races": manual_seeded_races,
        "processed_roster_seeded_races": processed_seeded_races,
        **national_seed_summary,
        "resolution_verified_rows": sum(
            package.verification_status == "verified"
            for package in resolution_packages.values()
        ),
        "resolution_source_unavailable_rows": sum(
            package.verification_status == "source_unavailable"
            for package in resolution_packages.values()
        ),
        "reclassified_non_authority_resolution_rows": reclassified_non_authority_resolution_rows,
        "resolved_state_races": sum(bool(row["state_code"]) for row in registry_rows if row["scope_kind"] == IN_SCOPE_KIND),
        "unresolved_races": len(unresolved_rows),
        "in_scope_unresolved_races": sum(
            row["scope_kind"] == IN_SCOPE_KIND for row in unresolved_rows
        ),
        "merged_alias_count": sum(max(int(row["merged_race_id_count"]) - 1, 0) for row in registry_rows),
        "duplicate_contest_contexts": duplicate_context_count,
        "in_scope_duplicate_contest_contexts": in_scope_duplicate_context_count,
        "valid_official_election_source_rows": sum(
            bool(row["official_election_source"]) for row in registry_rows
        ),
        "represented_states": sorted({row["state_code"] for row in represented_rows if row["state_code"]}),
        "represented_state_cycles": len(represented_rows),
        "national_candidate_endorsements": len(national_reconciliation_rows),
        "national_endorsements_absent_from_registry": sum(
            row["registry_status"] == "absent_from_registry"
            for row in national_reconciliation_rows
        ),
        "national_endorsements_matched_in_scope": sum(
            row["registry_status"] == "matched_in_scope"
            for row in national_reconciliation_rows
        ),
        "national_endorsements_matched_other_scope": sum(
            row["registry_status"] == "matched_other_scope"
            for row in national_reconciliation_rows
        ),
        "total_races": len(registry_rows),
    }

    paths.output_dir.mkdir(parents=True, exist_ok=True)
    registry_path = paths.output_dir / "race_registry.csv"
    alias_mapping_path = paths.output_dir / "race_registry_aliases.csv"
    unresolved_path = paths.output_dir / "race_registry_unresolved_queue.csv"
    represented_path = paths.output_dir / "race_registry_represented_state_cycles.csv"
    national_reconciliation_path = (
        paths.output_dir / "race_registry_national_endorsement_reconciliation.csv"
    )
    summary_path = paths.output_dir / "race_registry_summary.json"

    write_csv(
        registry_path,
        registry_rows,
        [
            "race_id",
            "scope_kind",
            "election_date",
            "election_year",
            "primary_party",
            "endorsed_candidate",
            "endorsed_candidates",
            "unopposed_candidates",
            "opponent_candidates",
            "all_candidates",
            "candidate_count",
            "role_set",
            "party_set",
            "evidence_statuses",
            "office",
            "office_status",
            "office_source",
            "office_confidence",
            "jurisdiction",
            "jurisdiction_status",
            "jurisdiction_source",
            "jurisdiction_confidence",
            "state",
            "state_code",
            "state_status",
            "state_source",
            "state_confidence",
            "official_election_source",
            "official_election_source_status",
            "official_election_source_source",
            "official_election_source_confidence",
            "supporting_source",
            "supporting_source_status",
            "supporting_source_type",
            "supporting_source_source",
            "supporting_source_confidence",
            "certified_opponents",
            "certified_opponents_status",
            "endorsing_bodies",
            "metadata_source",
            "source_reference",
            "canonical_candidate_aliases",
            "source_race_ids",
            "merged_race_id_count",
            "unresolved_fields",
        ],
    )
    write_csv(
        alias_mapping_path,
        alias_rows,
        [
            "canonical_race_id",
            "race_id",
            "is_canonical",
            "scope_kind",
            "election_date",
            "state_code",
            "office",
            "jurisdiction",
            "merge_group_size",
            "candidate_aliases",
        ],
    )
    write_csv(
        unresolved_path,
        unresolved_rows,
        [
            "race_id",
            "scope_kind",
            "election_date",
            "election_year",
            "primary_party",
            "endorsed_candidate",
            "endorsed_candidates",
            "unopposed_candidates",
            "opponent_candidates",
            "all_candidates",
            "candidate_count",
            "role_set",
            "party_set",
            "evidence_statuses",
            "office",
            "office_status",
            "office_source",
            "office_confidence",
            "jurisdiction",
            "jurisdiction_status",
            "jurisdiction_source",
            "jurisdiction_confidence",
            "state",
            "state_code",
            "state_status",
            "state_source",
            "state_confidence",
            "official_election_source",
            "official_election_source_status",
            "official_election_source_source",
            "official_election_source_confidence",
            "supporting_source",
            "supporting_source_status",
            "supporting_source_type",
            "supporting_source_source",
            "supporting_source_confidence",
            "certified_opponents",
            "certified_opponents_status",
            "endorsing_bodies",
            "metadata_source",
            "source_reference",
            "canonical_candidate_aliases",
            "source_race_ids",
            "merged_race_id_count",
            "unresolved_fields",
            "queue_reason",
        ],
    )
    write_csv(
        represented_path,
        represented_rows,
        [
            "state",
            "state_code",
            "cycle_year",
            "race_count",
            "race_ids",
            "endorsed_candidates",
            "endorsing_bodies",
            "local_endorsing_bodies",
        ],
    )
    write_csv(
        national_reconciliation_path,
        national_reconciliation_rows,
        [
            "record_id",
            "campaign",
            "office",
            "office_types",
            "election_date",
            "election_year",
            "endorsing_chapters",
            "primary_result",
            "census_classification",
            "census_primary_date",
            "census_verification_status",
            "registry_status",
            "matched_race_ids",
            "matched_scope_kinds",
            "review_status",
            "notes",
        ],
    )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return RaceRegistryResult(
        race_rows=len(registry_rows),
        in_scope_race_rows=summary["in_scope_races"],
        resolved_state_race_rows=summary["resolved_state_races"],
        unresolved_race_rows=len(unresolved_rows),
        represented_state_cycle_rows=len(represented_rows),
        summary_path=summary_path,
        registry_path=registry_path,
        alias_mapping_path=alias_mapping_path,
        unresolved_queue_path=unresolved_path,
        represented_state_cycles_path=represented_path,
    )


def _national_endorsement_reconciliation_rows(
    archive_path: Path,
    registry_rows: list[dict[str, str]],
    resolution_paths: tuple[Path, ...] = (),
) -> list[dict[str, str]]:
    if not archive_path.exists():
        return []
    resolutions_by_id = {
        row.get("record_id", ""): row
        for path in resolution_paths
        if path.exists()
        for row in read_csv(path)
    }

    output: list[dict[str, str]] = []
    for row in read_csv(archive_path):
        resolution = resolutions_by_id.get(row.get("record_id", ""), {})
        census_primary_date = resolution.get("primary_date", "")
        election_year = (
            census_primary_date[:4]
            if census_primary_date
            else row.get("election_date", "")[:4]
        )
        if not election_year or int(election_year) < 2016:
            continue
        office_types = _split_pipe_values(row.get("office_types", ""))
        if "Ballot Initiative" in office_types:
            continue
        matches = [
            registry_row
            for registry_row in registry_rows
            if registry_row.get("election_year", "") == election_year
            and any(
                _candidate_name_matches(name, row.get("campaign", ""))
                for name in _split_pipe_values(
                    " | ".join(
                        (
                            registry_row.get("endorsed_candidates", ""),
                            registry_row.get("unopposed_candidates", ""),
                        )
                    )
                )
            )
        ]
        scope_kinds = sorted({match["scope_kind"] for match in matches})
        if any(scope == IN_SCOPE_KIND for scope in scope_kinds):
            registry_status = "matched_in_scope"
            review_status = "resolved"
            notes = "Matched by normalized endorsed-candidate name and election year."
        elif matches:
            registry_status = "matched_other_scope"
            review_status = "needs_primary_scope_review"
            notes = "Candidate/year exists only in registry rows currently outside primary scope."
        else:
            registry_status = "absent_from_registry"
            review_status = "needs_primary_verification"
            notes = (
                "National endorsement is absent from the quotation-derived registry; verify "
                "whether a Democratic primary occurred and add its certified roster."
            )
        output.append(
            {
                "record_id": row.get("record_id", ""),
                "campaign": row.get("campaign", ""),
                "office": row.get("office", ""),
                "office_types": row.get("office_types", ""),
                "election_date": row.get("election_date", ""),
                "election_year": election_year,
                "endorsing_chapters": row.get("endorsing_chapters", ""),
                "primary_result": row.get("primary_result", ""),
                "census_classification": resolution.get("classification", ""),
                "census_primary_date": census_primary_date,
                "census_verification_status": resolution.get(
                    "verification_status", ""
                ),
                "registry_status": registry_status,
                "matched_race_ids": " | ".join(
                    sorted({match["race_id"] for match in matches})
                ),
                "matched_scope_kinds": " | ".join(scope_kinds),
                "review_status": review_status,
                "notes": notes,
            }
        )
    return sorted(
        output,
        key=lambda row: (
            row["election_date"],
            row["campaign"],
            row["record_id"],
        ),
    )


def _classified_source_fields(
    *,
    url: str,
    verified_status: str,
    source_unavailable_status: str,
    supporting_status: str,
    source_key: str,
    verification_status: str = "verified",
) -> dict[str, str]:
    if not url:
        return {
            "official_election_source": "",
            "official_election_source_status": (
                source_unavailable_status
                if verification_status == "source_unavailable"
                else "unresolved"
            ),
            "official_election_source_source": source_key if verification_status == "source_unavailable" else "",
            "official_election_source_confidence": "",
            "supporting_source": "",
            "supporting_source_status": "unresolved",
            "supporting_source_type": "",
            "supporting_source_source": "",
            "supporting_source_confidence": "",
        }
    classification = _classify_election_authority_source(url)
    if classification.is_election_authority:
        status = verified_status if verification_status == "verified" else source_unavailable_status
        confidence = (
            VERIFIED_CONFIDENCE
            if verification_status == "verified"
            else HIGH_CONFIDENCE
        )
        return {
            "official_election_source": url,
            "official_election_source_status": status,
            "official_election_source_source": source_key,
            "official_election_source_confidence": confidence,
            "supporting_source": "",
            "supporting_source_status": "unresolved",
            "supporting_source_type": "",
            "supporting_source_source": "",
            "supporting_source_confidence": "",
        }
    return {
        "official_election_source": "",
        "official_election_source_status": (
            source_unavailable_status
            if verification_status == "source_unavailable"
            else "unresolved"
        ),
        "official_election_source_source": source_key if verification_status == "source_unavailable" else "",
        "official_election_source_confidence": "",
        "supporting_source": url,
        "supporting_source_status": supporting_status,
        "supporting_source_type": classification.invalid_type,
        "supporting_source_source": source_key,
        "supporting_source_confidence": HIGH_CONFIDENCE,
    }


def _classify_election_authority_source(url: str) -> SourceClassification:
    parsed = urlparse(url.strip())
    host = parsed.netloc.casefold()
    path = parsed.path.casefold()
    query = parsed.query.casefold()
    combined = f"{host} {path} {query}"
    if not host:
        return SourceClassification(False, "invalid_url")
    if host.endswith(OFFICIAL_SOURCE_EXCLUDED_HOST_SUFFIXES):
        return SourceClassification(False, "incumbent_office")
    if host == "nyassembly.gov" and "/mem/" in path:
        return SourceClassification(False, "legislator_site")
    if host == "housedems.com":
        return SourceClassification(False, "party_or_caucus")
    if any(token in host for token in ("campaign", "forcongress", "forassembly", "forsenate")):
        return SourceClassification(False, "candidate_controlled")
    if host == "cityoffrederick.com" and "/documentcenter/view/" in path:
        return SourceClassification(True, "")
    if host in ELECTION_AUTHORITY_HOST_ALLOWLIST:
        if any(token in combined for token in ELECTION_AUTHORITY_PATH_TOKENS):
            return SourceClassification(True, "")
        if host in {
            "www.dcboe.org",
            "www.electionreturns.pa.gov",
            "www.vote.nyc",
            "results.elections.ny.gov",
            "elections.delaware.gov",
            "results.elections.maryland.gov",
            "www.nvsos.gov",
            "electionstats.state.ma.us",
        }:
            return SourceClassification(True, "")
        return SourceClassification(False, "generic_government")
    if host in OFFICIAL_SOURCE_EXCLUDED_HOSTS or re.search(
        r"/(?:mem|member|members|legislator|legislators)(?:/|$)",
        path,
    ):
        return SourceClassification(False, "legislator_site")
    if _candidate_controlled_host(host):
        return SourceClassification(False, "candidate_controlled")
    if host.endswith(".gov"):
        if any(token in combined for token in ELECTION_AUTHORITY_PATH_TOKENS):
            return SourceClassification(True, "")
        return SourceClassification(False, "generic_government")
    if any(token in combined for token in ELECTION_AUTHORITY_PATH_TOKENS) and any(
        marker in host for marker in ("votes", "vote", "election", "elections", "clerk", "boe", "sos")
    ):
        return SourceClassification(True, "")
    return SourceClassification(False, "candidate_controlled")


def _candidate_controlled_host(host: str) -> bool:
    if not host:
        return False
    if any(host.endswith(suffix) for suffix in OFFICIAL_SOURCE_EXCLUDED_HOST_SUFFIXES):
        return False
    if host in ELECTION_AUTHORITY_HOST_ALLOWLIST:
        return False
    return host.endswith((".com", ".org", ".net", ".us"))


def _canonicalize_registry_rows(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], int, int]:
    grouped: dict[tuple[str, str, str, str] | None, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = _contest_key(row)
        grouped[key].append(row)

    canonical_rows: list[dict[str, str]] = []
    alias_rows: list[dict[str, str]] = []
    duplicate_context_count = 0
    in_scope_duplicate_context_count = 0

    for key, members in grouped.items():
        if key is None:
            for row in members:
                candidate_aliases = " | ".join(sorted(_row_candidate_aliases(row)))
                canonical_row = _finalize_registry_row(
                    {
                        **row,
                        "canonical_candidate_aliases": candidate_aliases,
                        "source_race_ids": row["race_id"],
                        "merged_race_id_count": "1",
                    }
                )
                canonical_rows.append(canonical_row)
                alias_rows.append(_alias_row(row, row["race_id"], 1, candidate_aliases))
            continue
        for component in _duplicate_components(members):
            canonical = _merge_registry_component(component)
            canonical_rows.append(canonical)
            if len(component) > 1:
                duplicate_context_count += 1
                if any(row["scope_kind"] == IN_SCOPE_KIND for row in component):
                    in_scope_duplicate_context_count += 1
            for row in component:
                alias_rows.append(
                    _alias_row(
                        row,
                        canonical["race_id"],
                        len(component),
                        canonical["canonical_candidate_aliases"],
                    )
                )

    canonical_rows.sort(key=lambda row: row["race_id"])
    alias_rows.sort(key=lambda row: (row["canonical_race_id"], row["race_id"]))
    return canonical_rows, alias_rows, duplicate_context_count, in_scope_duplicate_context_count


def _contest_key(row: dict[str, str]) -> tuple[str, str, str, str] | None:
    election_date = row.get("election_date", "").strip()
    state_code = row.get("state_code", "").strip()
    office = row.get("office", "").strip()
    jurisdiction = row.get("jurisdiction", "").strip()
    if not all((election_date, state_code, office, jurisdiction)):
        return None
    return (
        election_date,
        state_code,
        _identity(office),
        _identity(jurisdiction),
    )


def _duplicate_components(
    rows: list[dict[str, str]],
) -> list[list[dict[str, str]]]:
    if len(rows) <= 1:
        return [rows]
    parents = list(range(len(rows)))
    alias_sets = [_row_candidate_aliases(row) for row in rows]

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            if alias_sets[left] & alias_sets[right]:
                union(left, right)

    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[find(index)].append(row)
    return list(grouped.values())


def _row_candidate_aliases(row: dict[str, str]) -> set[str]:
    names = _split_pipe_values(row.get("all_candidates", ""))
    aliases: set[str] = set()
    for name in names:
        aliases.update(_candidate_alias_family(name))
    return aliases


def _candidate_alias_family(name: str) -> set[str]:
    tokens = _candidate_tokens(name)
    if not tokens:
        return set()
    family = {" ".join(tokens)}
    if len(tokens) == 1:
        family.add(tokens[0])
        return family
    first = tokens[0]
    last = tokens[-1]
    family.add(f"{first} {last}")
    family.add(f"{first[:1]} {last}")
    family.add(f"{first[:3]} {last}")
    if len(tokens) >= 3:
        family.add(f"{first} {tokens[-2]}")
        family.add(f"{first[:1]} {tokens[-2]}")
        family.add(f"{first[:3]} {tokens[-2]}")
    return {value.strip() for value in family if value.strip()}


def _candidate_tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[\"“”‘’]", " ", text)
    text = re.sub(r"\b(jr|jr\.|sr|sr\.|ii|iii|iv)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [token for token in text.split() if token]


def _candidate_name_matches(left: str, right: str) -> bool:
    left_tokens = _candidate_tokens(left)
    right_tokens = _candidate_tokens(right)
    if not left_tokens or not right_tokens:
        return False
    if left_tokens == right_tokens:
        return True
    if len(left_tokens) < 2 or len(right_tokens) < 2:
        return False
    return (
        left_tokens[0] == right_tokens[0]
        and left_tokens[-1] == right_tokens[-1]
    )


def _merge_registry_component(rows: list[dict[str, str]]) -> dict[str, str]:
    component = [{**row} for row in rows]
    canonical_race_id = min(row["race_id"] for row in component)
    source_race_ids = sorted(row["race_id"] for row in component)
    candidate_aliases = sorted({alias for row in component for alias in _row_candidate_aliases(row)})
    endorsed_candidates = _merge_candidate_field_values(component, ("endorsed_candidates", "unopposed_candidates"))
    unopposed_candidates = _merge_candidate_field_values(component, ("unopposed_candidates",))
    opponent_candidates = _merge_candidate_field_values(component, ("opponent_candidates",))
    all_candidates = _merge_candidate_field_values(component, ("all_candidates",))
    certified_opponents = _merge_candidate_field_values(component, ("certified_opponents",))

    registry_row = {
        "race_id": canonical_race_id,
        "scope_kind": (
            IN_SCOPE_KIND
            if any(row["scope_kind"] == IN_SCOPE_KIND for row in component)
            else OUT_OF_SCOPE_KIND
        ),
        "election_date": _merge_scalar_values(component, "election_date"),
        "election_year": _merge_scalar_values(component, "election_year"),
        "primary_party": _merge_scalar_values(component, "primary_party"),
        "endorsed_candidate": " | ".join(endorsed_candidates),
        "endorsed_candidates": " | ".join(endorsed_candidates),
        "unopposed_candidates": " | ".join(unopposed_candidates),
        "opponent_candidates": " | ".join(opponent_candidates),
        "all_candidates": " | ".join(all_candidates),
        "candidate_count": str(len(all_candidates)),
        "role_set": " | ".join(_merge_pipe_values(component, "role_set")),
        "party_set": " | ".join(_merge_pipe_values(component, "party_set")),
        "evidence_statuses": " | ".join(_merge_pipe_values(component, "evidence_statuses")),
        "office": _merge_ranked_field(component, "office", "office_status", "office_source", "office_confidence")[0],
        "office_status": _merge_ranked_field(component, "office", "office_status", "office_source", "office_confidence")[1],
        "office_source": _merge_ranked_field(component, "office", "office_status", "office_source", "office_confidence")[2],
        "office_confidence": _merge_ranked_field(component, "office", "office_status", "office_source", "office_confidence")[3],
        "jurisdiction": _merge_ranked_field(component, "jurisdiction", "jurisdiction_status", "jurisdiction_source", "jurisdiction_confidence")[0],
        "jurisdiction_status": _merge_ranked_field(component, "jurisdiction", "jurisdiction_status", "jurisdiction_source", "jurisdiction_confidence")[1],
        "jurisdiction_source": _merge_ranked_field(component, "jurisdiction", "jurisdiction_status", "jurisdiction_source", "jurisdiction_confidence")[2],
        "jurisdiction_confidence": _merge_ranked_field(component, "jurisdiction", "jurisdiction_status", "jurisdiction_source", "jurisdiction_confidence")[3],
        "state": _merge_ranked_field(component, "state", "state_status", "state_source", "state_confidence")[0],
        "state_code": _merge_ranked_field(component, "state_code", "state_status", "state_source", "state_confidence")[0],
        "state_status": _merge_ranked_field(component, "state_code", "state_status", "state_source", "state_confidence")[1],
        "state_source": _merge_ranked_field(component, "state_code", "state_status", "state_source", "state_confidence")[2],
        "state_confidence": _merge_ranked_field(component, "state_code", "state_status", "state_source", "state_confidence")[3],
        "official_election_source": _merge_ranked_field(component, "official_election_source", "official_election_source_status", "official_election_source_source", "official_election_source_confidence")[0],
        "official_election_source_status": _merge_ranked_field(component, "official_election_source", "official_election_source_status", "official_election_source_source", "official_election_source_confidence")[1],
        "official_election_source_source": _merge_ranked_field(component, "official_election_source", "official_election_source_status", "official_election_source_source", "official_election_source_confidence")[2],
        "official_election_source_confidence": _merge_ranked_field(component, "official_election_source", "official_election_source_status", "official_election_source_source", "official_election_source_confidence")[3],
        "supporting_source": _merge_ranked_field(component, "supporting_source", "supporting_source_status", "supporting_source_source", "supporting_source_confidence")[0],
        "supporting_source_status": _merge_ranked_field(component, "supporting_source", "supporting_source_status", "supporting_source_source", "supporting_source_confidence")[1],
        "supporting_source_type": " | ".join(_merge_pipe_values(component, "supporting_source_type")),
        "supporting_source_source": _merge_ranked_field(component, "supporting_source", "supporting_source_status", "supporting_source_source", "supporting_source_confidence")[2],
        "supporting_source_confidence": _merge_ranked_field(component, "supporting_source", "supporting_source_status", "supporting_source_source", "supporting_source_confidence")[3],
        "certified_opponents": " | ".join(certified_opponents),
        "certified_opponents_status": _merge_scalar_values(component, "certified_opponents_status"),
        "endorsing_bodies": " | ".join(_merge_pipe_values(component, "endorsing_bodies")),
        "metadata_source": _merge_metadata_source(component),
        "source_reference": " | ".join(_merge_pipe_values(component, "source_reference")),
        "canonical_candidate_aliases": " | ".join(candidate_aliases),
        "source_race_ids": " | ".join(source_race_ids),
        "merged_race_id_count": str(len(source_race_ids)),
    }
    return _finalize_registry_row(registry_row)


def _merge_candidate_field_values(
    rows: list[dict[str, str]],
    field_names: tuple[str, ...],
) -> list[str]:
    candidate_groups: list[dict[str, object]] = []
    for field_name in field_names:
        for row in rows:
            for name in _split_pipe_values(row.get(field_name, "")):
                aliases = _candidate_alias_family(name)
                if not aliases:
                    continue
                matching_indexes = [
                    index
                    for index, group in enumerate(candidate_groups)
                    if aliases & group["aliases"]  # type: ignore[operator]
                ]
                if not matching_indexes:
                    candidate_groups.append({"aliases": set(aliases), "names": {name}})
                    continue
                target = candidate_groups[matching_indexes[0]]
                target["aliases"].update(aliases)  # type: ignore[union-attr]
                target["names"].add(name)  # type: ignore[union-attr]
                for extra_index in reversed(matching_indexes[1:]):
                    extra = candidate_groups.pop(extra_index)
                    target["aliases"].update(extra["aliases"])  # type: ignore[union-attr]
                    target["names"].update(extra["names"])  # type: ignore[union-attr]
    representatives = [
        _preferred_display_name(sorted(group["names"]))  # type: ignore[index]
        for group in candidate_groups
    ]
    return sorted({name for name in representatives if name})


def _preferred_display_name(names: list[str]) -> str:
    def key(value: str) -> tuple[int, int, str]:
        alnum = len(re.sub(r"[^A-Za-z0-9]", "", value))
        return (alnum, len(value), value)

    return max(names, key=key)


def _merge_pipe_values(rows: list[dict[str, str]], field_name: str) -> list[str]:
    values = {
        value
        for row in rows
        for value in _split_pipe_values(row.get(field_name, ""))
        if value
    }
    return sorted(values)


def _split_pipe_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(" | ") if part.strip()]


def _merge_scalar_values(rows: list[dict[str, str]], field_name: str) -> str:
    values = [row.get(field_name, "").strip() for row in rows if row.get(field_name, "").strip()]
    if not values:
        return ""
    counts = Counter(values)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _merge_ranked_field(
    rows: list[dict[str, str]],
    value_field: str,
    status_field: str,
    source_field: str,
    confidence_field: str,
) -> tuple[str, str, str, str]:
    populated = [row for row in rows if row.get(value_field, "").strip()]
    if populated:
        best_priority = max(
            _field_status_priority(row.get(status_field, ""), status_field) for row in populated
        )
        best_rows = [
            row
            for row in populated
            if _field_status_priority(row.get(status_field, ""), status_field) == best_priority
        ]
        values = sorted({row.get(value_field, "").strip() for row in best_rows if row.get(value_field, "").strip()})
        sources = sorted({row.get(source_field, "").strip() for row in best_rows if row.get(source_field, "").strip()})
        confidences = sorted(
            {row.get(confidence_field, "").strip() for row in best_rows if row.get(confidence_field, "").strip()},
            key=lambda value: -SOURCE_CONFIDENCE_PRIORITY.get(value, 0),
        )
        return (
            " | ".join(values),
            best_rows[0].get(status_field, "").strip(),
            " | ".join(sources),
            confidences[0] if confidences else "",
        )

    best_status = sorted(
        {row.get(status_field, "").strip() for row in rows if row.get(status_field, "").strip()},
        key=lambda value: (-_field_status_priority(value, status_field), value),
    )
    if not best_status:
        return "", "unresolved", "", ""
    chosen_status = best_status[0]
    sources = sorted(
        {
            row.get(source_field, "").strip()
            for row in rows
            if row.get(status_field, "").strip() == chosen_status and row.get(source_field, "").strip()
        }
    )
    return "", chosen_status, " | ".join(sources), ""


def _field_status_priority(status: str, field_name: str) -> int:
    mapping = (
        SUPPORTING_SOURCE_STATUS_PRIORITY
        if field_name == "supporting_source_status"
        else FIELD_STATUS_PRIORITY
    )
    return mapping.get(status.strip(), 0)


def _merge_metadata_source(rows: list[dict[str, str]]) -> str:
    priorities = {
        "manual_verified": 6,
        "resolution_verified": 5,
        "processed_verified": 4,
        "metadata_inferred": 3,
        "hint_parsed": 2,
        "resolution_source_unavailable": 1,
        "corpus_only": 0,
    }
    values = sorted(
        {row.get("metadata_source", "").strip() for row in rows if row.get("metadata_source", "").strip()},
        key=lambda value: (-priorities.get(value, 0), value),
    )
    return values[0] if values else "corpus_only"


def _finalize_registry_row(row: dict[str, str]) -> dict[str, str]:
    unresolved_fields = [
        field
        for field, status in (
            ("office", row.get("office_status", "")),
            ("jurisdiction", row.get("jurisdiction_status", "")),
            ("state", row.get("state_status", "")),
            ("official_election_source", row.get("official_election_source_status", "")),
        )
        if status == "unresolved"
    ]
    if row.get("certified_opponents_status", "") == "unresolved":
        unresolved_fields.append("certified_opponents")
    row["unresolved_fields"] = " | ".join(unresolved_fields)
    return row


def _alias_row(
    row: dict[str, str],
    canonical_race_id: str,
    merge_group_size: int,
    candidate_aliases: str,
) -> dict[str, str]:
    return {
        "canonical_race_id": canonical_race_id,
        "race_id": row["race_id"],
        "is_canonical": str(row["race_id"] == canonical_race_id).lower(),
        "scope_kind": row.get("scope_kind", ""),
        "election_date": row.get("election_date", ""),
        "state_code": row.get("state_code", ""),
        "office": row.get("office", ""),
        "jurisdiction": row.get("jurisdiction", ""),
        "merge_group_size": str(merge_group_size),
        "candidate_aliases": candidate_aliases,
    }


def _unresolved_queue_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    unresolved_rows: list[dict[str, str]] = []
    for row in rows:
        unresolved_fields = _split_pipe_values(row.get("unresolved_fields", ""))
        if not unresolved_fields:
            continue
        unresolved_rows.append(
            {
                **row,
                "queue_reason": "; ".join(f"resolve_{field}" for field in unresolved_fields),
            }
        )
    return unresolved_rows


def _represented_state_cycle_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    represented_state_cycles: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        if row.get("scope_kind", "") != IN_SCOPE_KIND:
            continue
        state_code = row.get("state_code", "").strip()
        election_date = row.get("election_date", "").strip()
        if not state_code or not election_date:
            continue
        key = (state_code, election_date[:4])
        represented_state_cycles[key]["race_ids"].add(row["race_id"])
        for candidate in _split_pipe_values(row.get("endorsed_candidate", "")):
            represented_state_cycles[key]["endorsed_candidates"].add(candidate)
        for body in _split_pipe_values(row.get("endorsing_bodies", "")):
            represented_state_cycles[key]["endorsing_bodies"].add(body)
            if _identity(body) != _identity("DSA National"):
                represented_state_cycles[key]["local_endorsing_bodies"].add(body)

    represented_rows = []
    for (state_code, cycle_year), values in sorted(represented_state_cycles.items()):
        represented_rows.append(
            {
                "state": STATE_NAME_BY_CODE.get(state_code, ""),
                "state_code": state_code,
                "cycle_year": cycle_year,
                "race_count": str(len(values["race_ids"])),
                "race_ids": " | ".join(sorted(values["race_ids"])),
                "endorsed_candidates": " | ".join(sorted(values["endorsed_candidates"])),
                "endorsing_bodies": " | ".join(sorted(values["endorsing_bodies"])),
                "local_endorsing_bodies": " | ".join(sorted(values["local_endorsing_bodies"])),
            }
        )
    return represented_rows


def _candidate_document_evidence_by_race(
    metadata_path: Path | None,
    full_text_path: Path | None,
) -> dict[str, list[dict[str, str]]]:
    if metadata_path is None or not metadata_path.exists():
        return {}
    text_by_document = _candidate_document_text_by_document(full_text_path)
    rows = read_csv(metadata_path)
    by_race: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        race_id = row.get("race_id", "").strip()
        if not race_id:
            continue
        document_id = row.get("document_id", "").strip()
        by_race[race_id].append(
            {
                "document_id": document_id,
                "candidate_name": row.get("candidate_name", "").strip(),
                "role": row.get("role", "").strip(),
                "election_date": row.get("election_date", "").strip(),
                "publication_date": row.get("publication_date", "").strip(),
                "campaign_window_status": row.get("campaign_window_status", "").strip(),
                "source_type": row.get("source_type", "").strip(),
                "source_url": row.get("source_url", "").strip(),
                "title": row.get("title", "").strip(),
                "analysis_scope": row.get("analysis_scope", "").strip() or "analysis",
                "coverage_status": row.get("coverage_status", "").strip(),
                "extraction_status": row.get("extraction_status", "").strip(),
                "text": text_by_document.get(document_id, ""),
            }
        )
    return by_race


def _candidate_document_text_by_document(
    full_text_path: Path | None,
) -> dict[str, str]:
    if full_text_path is None or not full_text_path.exists():
        return {}
    output: dict[str, str] = {}
    with full_text_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            row = json.loads(line)
            document_id = str(row.get("document_id", "")).strip()
            if document_id:
                output[document_id] = str(row.get("text", "")).strip()
    return output


def _infer_local_metadata(
    *,
    rows: list[dict[str, str]],
    metadata_rows: list[dict[str, str]],
    election_date: str,
) -> dict[str, str]:
    del election_date  # race grouping already constrains evidence to one election date.
    state_evidence: list[tuple[int, str, str, str]] = []
    office_evidence: list[tuple[int, str, str, str]] = []
    jurisdiction_evidence: list[tuple[int, str, str, str]] = []
    official_url_evidence: list[tuple[int, str, str, str]] = []

    for row in metadata_rows:
        priority = _metadata_priority(row)
        if priority <= 0:
            continue
        for state_code, evidence_kind in _extract_state_codes(row):
            source = _metadata_evidence_source(row, evidence_kind)
            state_evidence.append((priority, state_code, source, HIGH_CONFIDENCE))
        office, jurisdiction, evidence_kind = _extract_office_and_jurisdiction(row)
        if office:
            office_evidence.append(
                (
                    priority,
                    office,
                    _metadata_evidence_source(row, evidence_kind or "title_url"),
                    HIGH_CONFIDENCE,
                )
            )
        if jurisdiction:
            jurisdiction_evidence.append(
                (
                    priority,
                    jurisdiction,
                    _metadata_evidence_source(row, evidence_kind or "title_url"),
                    HIGH_CONFIDENCE,
                )
            )
        official_url = _official_metadata_url(row)
        if official_url:
            official_priority = priority + (1 if row.get("role") == "endorsed" else 0)
            official_url_evidence.append(
                (
                    official_priority,
                    official_url,
                    _metadata_evidence_source(row, "official_url"),
                    HIGH_CONFIDENCE,
                )
            )

    state_code, state_source, state_confidence = _choose_unambiguous_metadata_value(
        state_evidence
    )
    office, office_source, office_confidence = _choose_unambiguous_metadata_value(
        office_evidence
    )
    jurisdiction, jurisdiction_source, jurisdiction_confidence = (
        _choose_unambiguous_metadata_value(jurisdiction_evidence)
    )
    (
        official_election_source,
        official_election_source_source,
        official_election_source_confidence,
    ) = _choose_deterministic_official_url(official_url_evidence)
    return {
        "state_code": state_code,
        "state_source": state_source,
        "state_confidence": state_confidence,
        "office": office,
        "office_source": office_source,
        "office_confidence": office_confidence,
        "jurisdiction": jurisdiction,
        "jurisdiction_source": jurisdiction_source,
        "jurisdiction_confidence": jurisdiction_confidence,
        "official_election_source": official_election_source,
        "official_election_source_source": official_election_source_source,
        "official_election_source_confidence": official_election_source_confidence,
        "source_reference": " | ".join(
            sorted(
                {
                    value
                    for value in (
                        state_source,
                        office_source,
                        jurisdiction_source,
                        official_election_source_source,
                    )
                    if value
                }
            )
        ),
    }


def _metadata_priority(row: dict[str, str]) -> int:
    if row.get("analysis_scope", "analysis") == "context_only":
        return 0
    if row.get("coverage_status", "") == "shared_document_unscoped":
        return 0
    if row.get("extraction_status", "").strip() not in {"", "extracted"}:
        return 0
    source_type = row.get("source_type", "").strip().casefold()
    if _official_metadata_url(row) or source_type in OFFICIAL_METADATA_SOURCE_TYPES:
        return 4
    if row.get("campaign_window_status", "").strip() == "out_of_window":
        return 0
    if source_type in CANDIDATE_OWNED_SOURCE_TYPES:
        return 1 if row.get("campaign_window_status", "").strip() == "undated" else 2
    return 3


def _official_host(host: str) -> bool:
    return host in OFFICIAL_HOST_STATE_MAP or host.endswith(".gov")


def _extract_state_codes(row: dict[str, str]) -> list[tuple[str, str]]:
    host = urlparse(row.get("source_url", "")).netloc.casefold()
    combined = _metadata_combined_text(row)
    evidence: list[tuple[str, str]] = []
    if host in OFFICIAL_HOST_STATE_MAP:
        evidence.append((OFFICIAL_HOST_STATE_MAP[host], "official_host"))

    patterns = [
        ("DC", r"\bDC\b|District of Columbia"),
        ("NY", r"\bNew York\b|\bNYC\b|\bQueens\b|\bBrooklyn\b|\bBronx\b|\bManhattan\b|\bStaten Island\b"),
        ("MD", r"\bMaryland\b|\bMontgomery County\b|\bBaltimore\b|\bPrince George'?s\b"),
        ("PA", r"\bPennsylvania\b|\bPhiladelphia\b|\bPittsburgh\b|\bPhilly\b"),
        ("NV", r"\bNevada\b|\bClark County\b|\bLas Vegas\b"),
        ("TX", r"\bTexas\b|Austin, TX|\bAustin\b|\bHouston\b|\bTravis County\b"),
        ("OH", r"\bOhio\b|\bCleveland\b"),
        ("MI", r"\bMichigan\b|\bDetroit\b|\bAnn Arbor\b|\bYpsilanti\b"),
        ("CA", r"\bCalifornia\b|\bAlameda County\b|\bOakland\b|\bLos Angeles\b|\bSan Francisco\b"),
        ("CO", r"\bColorado\b|\bDenver\b"),
        ("OR", r"\bOregon\b|\bPortland\b"),
        ("WI", r"\bWisconsin\b|\bMilwaukee\b"),
        ("VA", r"\bVirginia\b|\bFairfax\b|\bAlexandria\b"),
        ("DE", r"\bDelaware\b|\bWilmington\b"),
        ("LA", r"\bLouisiana\b|\bNew Orleans\b"),
        ("MT", r"\bMontana\b"),
        ("NM", r"\bNew Mexico\b"),
        ("VT", r"\bVermont\b"),
        ("KY", r"\bKentucky\b|\bLouisville\b"),
    ]
    found = {
        state_code
        for state_code, pattern in patterns
        if re.search(pattern, combined, re.IGNORECASE)
    }
    if len(found) == 1:
        evidence.append((next(iter(found)), "title_url_text"))
    if not evidence and any(token in host for token in ("nyc", "queens", "brooklyn")):
        evidence.append(("NY", "campaign_domain"))
    return evidence


def _extract_office_and_jurisdiction(
    row: dict[str, str],
) -> tuple[str, str, str]:
    combined = _metadata_combined_text(row)
    lower = combined.casefold()

    patterns: list[tuple[str, str, str | None]] = [
        ("Lieutenant Governor", r"\blieutenant governor\b", None),
        ("Governor", r"\bgovernor\b", None),
        ("District Attorney", r"\bdistrict attorney\b", None),
        ("State Delegate", r"\bstate delegate\b|\bhouse of delegates\b", r"district[\s\-]*(\d+)"),
        ("State Senate", r"\bstate senate\b|\bfor senate\b|\bnew york state senate\b|\bvirginia state senate\b", r"district[\s\-]*(\d+)"),
        ("State Assembly", r"\bstate assembly\b|\bmember-of-the-assembly\b|\bnew york state assembly\b|\bnys assembly\b|\bfor assembly\b", r"assembly(?: district)?[\s\-]*(\d+)"),
        ("State Representative", r"\bstate representative\b|\bfor state representative\b", r"district[\s\-]*(\d+)"),
        ("US House", r"\brepresentative-in-congress\b|\bfor congress\b|\bcongressional district\b|\bu\.s\. representative\b|\bu\.s\. rep\b|\brun for congress\b", r"(\d+)(?:st|nd|rd|th)\s+congressional district|congressional-district-(\d+)|district[\s\-]*(\d+)"),
        ("County Council", r"\bcounty council\b", r"district[\s\-]*(\d+)"),
        ("City Council", r"\bcity council\b|\bcouncilmember\b|\bmetro council\b", r"(district|ward)[\s\-]*(\d+)"),
        ("Mayor", r"\bmayor(?:al)?\b", None),
    ]

    office = ""
    jurisdiction = ""
    for office_name, office_pattern, district_pattern in patterns:
        if not re.search(office_pattern, lower, re.IGNORECASE):
            continue
        office = office_name
        if office_name == "Mayor":
            jurisdiction = _extract_mayor_jurisdiction(combined)
        elif district_pattern:
            match = re.search(district_pattern, combined, re.IGNORECASE)
            if match:
                groups = [group for group in match.groups() if group]
                if office_name == "City Council" and len(groups) >= 2:
                    jurisdiction = f"{groups[0].title()} {groups[1]}"
                elif groups:
                    jurisdiction = f"District {groups[-1]}"
        break

    if not office:
        domain_specific = _domain_specific_office_and_jurisdiction(row)
        if domain_specific != ("", ""):
            office, jurisdiction = domain_specific
    if not office:
        office, jurisdiction = _title_fallback_office_and_jurisdiction(combined)
    evidence_kind = "title_url_text" if office or jurisdiction else ""
    return office, jurisdiction, evidence_kind


def _domain_specific_office_and_jurisdiction(row: dict[str, str]) -> tuple[str, str]:
    source_url = unquote(row.get("source_url", ""))
    lower = source_url.casefold()
    if "congressional-district-" in lower:
        match = re.search(r"congressional-district-(\d+)", lower)
        return "US House", f"District {match.group(1)}" if match else ""
    if "assembly-district-" in lower:
        match = re.search(r"assembly-district-(\d+)", lower)
        return "State Assembly", f"District {match.group(1)}" if match else ""
    if "member-of-the-assembly" in lower:
        match = re.search(r"geoareaabbr=(\d+)", lower)
        return "State Assembly", f"District {match.group(1)}" if match else ""
    if "/mayor/" in lower:
        return "Mayor", ""
    if "state-house/district-" in lower:
        match = re.search(r"state-house/district-(\d+)", lower)
        return "State Delegate", f"District {match.group(1)}" if match else ""
    return "", ""


def _title_fallback_office_and_jurisdiction(combined: str) -> tuple[str, str]:
    fallbacks = [
        ("City Council", r"\bcouncil district[\s\-]*(\d+)", "District {value}"),
        ("City Council", r"\bward[\s\-]*(\d+)\s+council", "Ward {value}"),
        ("State Assembly", r"\bassembly district[\s\-]*(\d+)", "District {value}"),
        ("State Senate", r"\bsenate district[\s\-]*(\d+)", "District {value}"),
        ("State Delegate", r"\bdelegate district[\s\-]*(\d+)", "District {value}"),
        ("US House", r"\b(\d+)(?:st|nd|rd|th)\s+district\b", "District {value}"),
    ]
    for office, pattern, template in fallbacks:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            return office, template.format(value=match.group(1))
    return "", ""


def _extract_mayor_jurisdiction(combined: str) -> str:
    patterns = [
        r"\b([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*) mayoral candidate\b",
        r"\bfor ([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*) mayor\b",
        r"\b([A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*) mayor\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" -|")
            if candidate and len(candidate.split()) <= 4:
                return candidate
    return ""


def _official_metadata_url(row: dict[str, str]) -> str:
    source_url = row.get("source_url", "").strip()
    if not source_url:
        return ""
    source_type = row.get("source_type", "").strip().casefold()
    if source_type in OFFICIAL_METADATA_SOURCE_TYPES:
        return source_url
    if _classify_election_authority_source(source_url).is_election_authority:
        return source_url
    return ""


def _metadata_combined_text(row: dict[str, str]) -> str:
    text = row.get("text", "").strip()
    snippet = text[:800] if text else ""
    return " | ".join(
        part
        for part in (
            row.get("title", "").strip(),
            unquote(row.get("source_url", "").strip()),
            snippet,
        )
        if part
    )


def _metadata_evidence_source(row: dict[str, str], evidence_kind: str) -> str:
    document_id = row.get("document_id", "").strip()
    if document_id:
        return f"{evidence_kind}:{document_id}"
    source_url = row.get("source_url", "").strip()
    return f"{evidence_kind}:{source_url}" if source_url else evidence_kind


def _choose_unambiguous_metadata_value(
    evidence_rows: list[tuple[int, str, str, str]],
) -> tuple[str, str, str]:
    grouped: dict[int, list[tuple[str, str, str]]] = defaultdict(list)
    for priority, value, source, confidence in evidence_rows:
        normalized_value = re.sub(r"\s+", " ", value).strip()
        if normalized_value:
            grouped[priority].append((normalized_value, source, confidence))
    for priority in sorted(grouped, reverse=True):
        values = grouped[priority]
        unique_values = {value for value, _, _ in values}
        if len(unique_values) != 1:
            return "", "", ""
        chosen_value = next(iter(unique_values))
        sources = sorted({source for _, source, _ in values if source})
        confidences = sorted({confidence for _, _, confidence in values if confidence})
        return chosen_value, " | ".join(sources), (confidences[0] if confidences else "")
    return "", "", ""


def _choose_deterministic_official_url(
    evidence_rows: list[tuple[int, str, str, str]],
) -> tuple[str, str, str]:
    grouped: dict[int, list[tuple[str, str, str]]] = defaultdict(list)
    for priority, value, source, confidence in evidence_rows:
        normalized_value = value.strip()
        if normalized_value:
            grouped[priority].append((normalized_value, source, confidence))
    for priority in sorted(grouped, reverse=True):
        values = sorted(grouped[priority], key=lambda item: item[0])
        if not values:
            continue
        chosen_value, chosen_source, chosen_confidence = values[0]
        return chosen_value, chosen_source, chosen_confidence
    return "", "", ""


def _manual_race_packages(
    endorsements_path: Path,
    race_candidates_path: Path,
) -> list[ManualRacePackage]:
    if not endorsements_path.exists() or not race_candidates_path.exists():
        return []
    endorsements = read_csv(endorsements_path)
    race_candidates = read_csv(race_candidates_path)
    race_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in race_candidates:
        race_rows[row.get("race_id", "").strip()].append(row)

    grouped_endorsements: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in endorsements:
        grouped_endorsements[row.get("race_id", "").strip()].append(row)

    packages = []
    for race_id, rows in grouped_endorsements.items():
        election_dates = sorted({row.get("election_date", "").strip() for row in rows if row.get("election_date", "").strip()})
        if len(election_dates) != 1:
            continue
        roster = race_rows.get(race_id, [])
        endorsed_candidates = sorted({row.get("candidate_name", "").strip() for row in roster if row.get("role", "").strip() in {"endorsed", "unopposed"}})
        opponent_candidates = sorted({row.get("candidate_name", "").strip() for row in roster if row.get("role", "").strip() == "opponent"})
        sample = rows[0]
        jurisdiction = sample.get("jurisdiction", "").strip()
        state_code, state = _state_from_jurisdiction(jurisdiction)
        official_sources = sorted({row.get("source_url", "").strip() for row in roster if row.get("source_url", "").strip()})
        packages.append(
            ManualRacePackage(
                manual_race_id=race_id,
                election_date=election_dates[0],
                endorsed_candidates=tuple(endorsed_candidates),
                opponent_candidates=tuple(opponent_candidates),
                office=sample.get("office", "").strip(),
                jurisdiction=jurisdiction,
                state_code=state_code,
                state=state,
                official_election_source=official_sources[0] if official_sources else "",
                endorsing_bodies=tuple(sorted({row.get("endorsing_body", "").strip() for row in rows if row.get("endorsing_body", "").strip()})),
            )
        )
    return packages


def _seed_grouped_from_manual_packages(
    grouped: dict[str, list[dict[str, str]]],
    packages: list[ManualRacePackage],
) -> int:
    seeded = 0
    for package in packages:
        if package.manual_race_id in grouped:
            continue
        matching_existing_races = {
            race_id
            for race_id, rows in grouped.items()
            if any(
                row.get("election_date", "") == package.election_date
                and _identity(row.get("candidate_name", ""))
                in {_identity(name) for name in package.endorsed_candidates}
                for row in rows
            )
        }
        if len(matching_existing_races) == 1:
            continue
        rows = _synthetic_candidate_rows(
            race_id=package.manual_race_id,
            election_date=package.election_date,
            endorsed_candidate=(
                package.endorsed_candidates[0]
                if package.endorsed_candidates
                else ""
            ),
            opponents=package.opponent_candidates,
            evidence_status="verified",
            source_url=package.official_election_source,
            notes="Seeded from verified manual endorsement and certified race roster.",
        )
        if rows:
            grouped[package.manual_race_id].extend(rows)
            seeded += 1
    return seeded


def _seed_grouped_from_national_census(
    grouped: dict[str, list[dict[str, str]]],
    paths: tuple[Path, ...],
    reconciliation_path: Path,
) -> tuple[dict[str, ResolutionPackage], dict[str, int]]:
    expected_fields = [
        "record_id",
        "campaign",
        "endorsement_election_date",
        "office",
        "classification",
        "primary_date",
        "primary_party",
        "state",
        "state_code",
        "jurisdiction",
        "official_election_source",
        "opponents",
        "verification_status",
        "notes",
    ]
    matched_race_ids: dict[str, list[str]] = {}
    if reconciliation_path.exists():
        matched_race_ids = {
            row.get("record_id", ""): _split_pipe_values(
                row.get("matched_race_ids", "")
            )
            for row in read_csv(reconciliation_path)
        }

    packages: dict[str, ResolutionPackage] = {}
    seen_record_ids: set[str] = set()
    classification_counts: Counter[str] = Counter()
    seeded_race_ids: set[str] = set()
    skipped_missing_primary_date = 0

    for path in paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if fieldnames != expected_fields:
                raise RaceRegistryError(
                    f"{path.name}: expected header {expected_fields}, found {fieldnames}"
                )
            for number, row in enumerate(reader, start=2):
                normalized = {
                    str(key): str(value or "").strip()
                    for key, value in row.items()
                }
                record_id = normalized["record_id"]
                if not record_id:
                    raise RaceRegistryError(f"{path.name}:{number}: missing record_id")
                if record_id in seen_record_ids:
                    raise RaceRegistryError(
                        f"{path.name}:{number}: duplicate national record_id {record_id}"
                    )
                seen_record_ids.add(record_id)
                classification = normalized["classification"]
                classification_counts[classification] += 1
                if classification != "democratic_primary":
                    continue
                primary_date = normalized["primary_date"]
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", primary_date):
                    skipped_missing_primary_date += 1
                    continue

                race_id = next(
                    (
                        candidate_race_id
                        for candidate_race_id in matched_race_ids.get(record_id, [])
                        if candidate_race_id in grouped
                        and any(
                            _candidate_name_matches(
                                member.get("candidate_name", ""),
                                normalized["campaign"],
                            )
                            for member in grouped[candidate_race_id]
                        )
                    ),
                    "",
                )
                if not race_id:
                    race_id = _find_candidate_year_race(
                        grouped,
                        normalized["campaign"],
                        primary_date[:4],
                    )
                if not race_id:
                    race_id = f"national-{record_id}-dem-primary"

                source_url = _first_source_url(
                    normalized["official_election_source"]
                )
                opponents = _candidate_list(normalized["opponents"])
                existing_in_scope_endorsed = {
                    _identity(member.get("candidate_name", ""))
                    for member in grouped.get(race_id, [])
                    if member.get("role", "") in {"endorsed", "unopposed"}
                    and member.get("party", "") == "Democratic"
                }
                if (
                    _identity(normalized["campaign"])
                    not in existing_in_scope_endorsed
                ):
                    grouped[race_id].extend(
                        _synthetic_candidate_rows(
                            race_id=race_id,
                            election_date=primary_date,
                            endorsed_candidate=normalized["campaign"],
                            opponents=opponents,
                            evidence_status=normalized["verification_status"],
                            source_url=source_url,
                            notes=(
                                f"Seeded from national census resolution {record_id}: "
                                f"{normalized['notes']}"
                            ),
                        )
                    )
                    seeded_race_ids.add(race_id)

                source_classification = _classify_election_authority_source(
                    source_url
                )
                packages[race_id] = ResolutionPackage(
                    race_id=race_id,
                    election_date=primary_date,
                    office=normalized["office"],
                    jurisdiction=normalized["jurisdiction"],
                    state=normalized["state"],
                    state_code=normalized["state_code"],
                    official_election_source=source_url,
                    verification_status=(
                        "verified"
                        if source_classification.is_election_authority
                        else "source_unavailable"
                    ),
                    notes=normalized["notes"],
                    source_key=f"{path.name}:{number}:{record_id}",
                )

    return packages, {
        "national_census_resolution_rows": len(seen_record_ids),
        "national_democratic_primary_resolution_rows": classification_counts[
            "democratic_primary"
        ],
        "national_democratic_primary_seeded_races": len(seeded_race_ids),
        "national_democratic_primary_missing_date_rows": skipped_missing_primary_date,
    }


def _synthetic_candidate_rows(
    *,
    race_id: str,
    election_date: str,
    endorsed_candidate: str,
    opponents: tuple[str, ...],
    evidence_status: str,
    source_url: str,
    notes: str,
) -> list[dict[str, str]]:
    if not endorsed_candidate:
        return []
    rows = [
        {
            "race_id": race_id,
            "candidate_name": endorsed_candidate,
            "election_date": election_date,
            "party": "Democratic",
            "role": "endorsed",
            "evidence_status": evidence_status,
            "source_url": source_url,
            "source_type": "official_voter_guide" if source_url else "",
            "notes": notes,
        }
    ]
    rows.extend(
        {
            "race_id": race_id,
            "candidate_name": opponent,
            "election_date": election_date,
            "party": "Democratic",
            "role": "opponent",
            "evidence_status": evidence_status,
            "source_url": source_url,
            "source_type": "official_voter_guide" if source_url else "",
            "notes": notes,
        }
        for opponent in opponents
    )
    return rows


def _find_candidate_year_race(
    grouped: dict[str, list[dict[str, str]]],
    candidate_name: str,
    election_year: str,
) -> str:
    matches = sorted(
        race_id
        for race_id, rows in grouped.items()
        if any(
            row.get("election_date", "")[:4] == election_year
            and _candidate_name_matches(
                row.get("candidate_name", ""),
                candidate_name,
            )
            for row in rows
        )
    )
    return matches[0] if len(matches) == 1 else ""


def _candidate_list(value: str) -> tuple[str, ...]:
    placeholders = {
        "april general field",
        "democratic primary field",
        "district democratic field",
        "none listed",
    }
    candidates = [
        candidate.strip()
        for candidate in re.split(r"\s*[;|]\s*", value)
        if candidate.strip()
    ]
    return tuple(
        candidate
        for candidate in candidates
        if _identity(candidate) not in placeholders
    )


def _first_source_url(value: str) -> str:
    return re.split(r"\s*;\s*", value, maxsplit=1)[0].strip()


def _resolution_packages(
    paths: tuple[Path, ...],
    corpus_rows_by_race: dict[str, list[dict[str, str]]],
) -> dict[str, ResolutionPackage]:
    expected_fields = [
        "race_id",
        "election_date",
        "office",
        "jurisdiction",
        "state",
        "state_code",
        "official_election_source",
        "verification_status",
        "notes",
    ]
    packages: dict[str, ResolutionPackage] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            if fieldnames != expected_fields:
                raise RaceRegistryError(
                    f"{path.name}: expected header {expected_fields}, found {fieldnames}"
                )
            for number, row in enumerate(reader, start=2):
                normalized = {str(key): str(value or "").strip() for key, value in row.items()}
                race_id = normalized.get("race_id", "")
                if not race_id:
                    raise RaceRegistryError(f"{path.name}:{number}: missing race_id")
                if race_id in packages:
                    raise RaceRegistryError(
                        f"{path.name}:{number}: duplicate race_id already defined by "
                        f"{packages[race_id].source_key}"
                    )
                election_date = normalized.get("election_date", "")
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", election_date):
                    raise RaceRegistryError(
                        f"{path.name}:{number}: invalid election_date {election_date!r}"
                    )
                verification_status = normalized.get("verification_status", "")
                if verification_status not in {"verified", "source_unavailable"}:
                    raise RaceRegistryError(
                        f"{path.name}:{number}: invalid verification_status {verification_status!r}"
                    )
                if not normalized.get("notes", ""):
                    raise RaceRegistryError(f"{path.name}:{number}: missing notes")
                state = normalized.get("state", "")
                state_code = normalized.get("state_code", "")
                if bool(state) != bool(state_code):
                    raise RaceRegistryError(
                        f"{path.name}:{number}: state and state_code must both be blank or both be populated"
                    )
                if state_code:
                    if state_code not in STATE_NAME_BY_CODE:
                        raise RaceRegistryError(
                            f"{path.name}:{number}: unknown state_code {state_code!r}"
                        )
                    if state != STATE_NAME_BY_CODE[state_code]:
                        raise RaceRegistryError(
                            f"{path.name}:{number}: state/state_code mismatch {state!r}/{state_code!r}"
                        )
                if verification_status == "verified":
                    for field in (
                        "office",
                        "state",
                        "state_code",
                        "official_election_source",
                    ):
                        if not normalized.get(field, ""):
                            raise RaceRegistryError(
                                f"{path.name}:{number}: verified row missing {field}"
                            )
                corpus_rows = corpus_rows_by_race.get(race_id)
                if corpus_rows is None:
                    raise RaceRegistryError(
                        f"{path.name}:{number}: race_id {race_id} is not present in candidate_text_corpus"
                    )
                corpus_dates = {
                    member.get("election_date", "").strip()
                    for member in corpus_rows
                    if member.get("election_date", "").strip()
                }
                if corpus_dates != {election_date}:
                    raise RaceRegistryError(
                        f"{path.name}:{number}: election_date {election_date} does not match corpus dates {sorted(corpus_dates)}"
                    )
                file_years = [int(value) for value in re.findall(r"20\d{2}", path.stem)]
                if file_years:
                    year = int(election_date[:4])
                    if not min(file_years) <= year <= max(file_years):
                        raise RaceRegistryError(
                            f"{path.name}:{number}: election year {year} is outside file range"
                        )
                packages[race_id] = ResolutionPackage(
                    race_id=race_id,
                    election_date=election_date,
                    office=normalized.get("office", ""),
                    jurisdiction=normalized.get("jurisdiction", ""),
                    state=state,
                    state_code=state_code,
                    official_election_source=normalized.get("official_election_source", ""),
                    verification_status=verification_status,
                    notes=normalized.get("notes", ""),
                    source_key=f"{path.name}:{number}",
                )
    return packages


def _seed_grouped_from_processed_packages(
    grouped: dict[str, list[dict[str, str]]],
    packages: list[ProcessedRacePackage],
) -> int:
    seeded = 0
    for package in packages:
        if package.processed_race_id in grouped:
            continue
        matching_race = _find_existing_race_for_package(grouped, package)
        if matching_race:
            continue
        rows = _synthetic_candidate_rows(
            race_id=package.processed_race_id,
            election_date=package.election_date,
            endorsed_candidate=(
                package.endorsed_candidates[0]
                if package.endorsed_candidates
                else ""
            ),
            opponents=package.opponent_candidates,
            evidence_status="verified",
            source_url=package.official_election_source,
            notes="Seeded from verified local primary roster research.",
        )
        if rows:
            grouped[package.processed_race_id].extend(rows)
            seeded += 1
    return seeded


def _find_existing_race_for_package(
    grouped: dict[str, list[dict[str, str]]],
    package: ProcessedRacePackage,
) -> str:
    candidate_keys = {
        _identity(name)
        for name in package.endorsed_candidates
    }
    matches = sorted(
        race_id
        for race_id, rows in grouped.items()
        if any(
            row.get("election_date", "") == package.election_date
            and _identity(row.get("candidate_name", "")) in candidate_keys
            for row in rows
        )
    )
    return matches[0] if len(matches) == 1 else ""


def _processed_race_packages(
    path: Path,
    queue_path: Path | None = None,
) -> list[ProcessedRacePackage]:
    if not path.exists():
        return []
    queue_by_id = {
        row.get("queue_id", ""): row
        for row in read_csv(queue_path)
    } if queue_path and queue_path.exists() else {}
    rows = read_csv(path)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("resolution_status", "").strip() != "verified":
            continue
        grouped[row.get("race_id", "").strip()].append(row)
    packages = []
    for race_id, members in grouped.items():
        election_dates = sorted({row.get("election_date", "").strip() for row in members if row.get("election_date", "").strip()})
        if len(election_dates) != 1:
            continue
        official_sources = sorted({row.get("official_election_source", "").strip() for row in members if row.get("official_election_source", "").strip()})
        queue_rows = [
            queue_by_id[row.get("queue_id", "")]
            for row in members
            if row.get("queue_id", "") in queue_by_id
        ]
        sample_queue = queue_rows[0] if queue_rows else {}
        state_code = sample_queue.get("state", "").strip()
        if state_code not in STATE_NAME_BY_CODE:
            state_code = ""
        packages.append(
            ProcessedRacePackage(
                processed_race_id=race_id,
                election_date=election_dates[0],
                endorsed_candidates=tuple(sorted({row.get("candidate_name", "").strip() for row in members if row.get("role", "").strip() in {"endorsed", "unopposed"}})),
                opponent_candidates=tuple(sorted({row.get("candidate_name", "").strip() for row in members if row.get("role", "").strip() == "opponent"})),
                official_election_source=official_sources[0] if official_sources else "",
                office=sample_queue.get("office_text", "").strip(),
                jurisdiction=sample_queue.get("office_text", "").strip(),
                state_code=state_code,
                state=STATE_NAME_BY_CODE.get(state_code, ""),
                endorsing_bodies=tuple(
                    sorted(
                        {
                            body.strip()
                            for queue_row in queue_rows
                            for body in queue_row.get("chapter", "").split(" | ")
                            if body.strip()
                        }
                    )
                ),
            )
        )
    return packages


def _validate_resolution_against_manual(
    resolution: ResolutionPackage,
    manual_match: ManualRacePackage | None,
) -> None:
    if manual_match is None:
        return
    field_pairs = [
        ("election_date", resolution.election_date, manual_match.election_date),
        ("office", resolution.office, manual_match.office),
        ("jurisdiction", resolution.jurisdiction, manual_match.jurisdiction),
        ("state", resolution.state, manual_match.state),
        ("state_code", resolution.state_code, manual_match.state_code),
        (
            "official_election_source",
            resolution.official_election_source,
            manual_match.official_election_source,
        ),
    ]
    for field, resolution_value, manual_value in field_pairs:
        if (
            resolution_value.strip()
            and manual_value.strip()
            and _identity(resolution_value) != _identity(manual_value)
        ):
            raise RaceRegistryError(
                f"{resolution.source_key}: {field} conflicts with verified manual race "
                f"{manual_match.manual_race_id}"
            )
    if (
        resolution.verification_status == "source_unavailable"
        and manual_match.official_election_source
    ):
        raise RaceRegistryError(
            f"{resolution.source_key}: source_unavailable conflicts with verified manual "
            f"official_election_source on {manual_match.manual_race_id}"
        )


def _match_manual_package(
    rows: list[dict[str, str]],
    packages: list[ManualRacePackage],
    election_date: str,
    endorsed_candidates: list[str],
    unopposed_candidates: list[str],
) -> ManualRacePackage | None:
    candidate_keys = {_identity(name) for name in endorsed_candidates + unopposed_candidates}
    candidates = sorted(
        package
        for package in packages
        if package.election_date == election_date
        and candidate_keys & {_identity(name) for name in package.endorsed_candidates}
    )
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    corpus_candidates = {_identity(row.get("candidate_name", "")) for row in rows}
    return max(
        candidates,
        key=lambda package: len(
            corpus_candidates
            & {_identity(name) for name in package.endorsed_candidates + package.opponent_candidates}
        ),
    )


def _match_processed_package(
    rows: list[dict[str, str]],
    packages: list[ProcessedRacePackage],
    election_date: str,
    endorsed_candidates: list[str],
    unopposed_candidates: list[str],
) -> ProcessedRacePackage | None:
    candidate_keys = {_identity(name) for name in endorsed_candidates + unopposed_candidates}
    candidates = [
        package
        for package in packages
        if package.election_date == election_date
        and candidate_keys & {_identity(name) for name in package.endorsed_candidates}
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    corpus_candidates = {_identity(row.get("candidate_name", "")) for row in rows}
    return max(
        candidates,
        key=lambda package: len(
            corpus_candidates
            & {_identity(name) for name in package.endorsed_candidates + package.opponent_candidates}
        ),
    )


def _race_hint(rows: list[dict[str, str]]) -> dict[str, str] | None:
    hints = []
    for row in rows:
        note = row.get("notes", "")
        match = re.search(r"\((20\d{2})-([A-Z]{2})-([A-Za-z0-9-]+)\)", note)
        if not match:
            match = re.search(r"\b(20\d{2})-([A-Z]{2})-([A-Za-z0-9-]+(?:-[A-Za-z0-9]+)*)\b", note)
        if not match:
            continue
        year, state_code, code = match.groups()
        if state_code not in STATE_NAME_BY_CODE:
            continue
        parsed = _parse_race_code(code, state_code)
        hints.append((year, state_code, code, parsed))
    if not hints:
        return None
    year, state_code, code, parsed = Counter(hints).most_common(1)[0][0]
    return {
        "state_code": state_code,
        "state": STATE_NAME_BY_CODE[state_code],
        "race_code": f"{year}-{state_code}-{code}",
        "office": parsed[0],
        "office_status": parsed[1],
        "jurisdiction": parsed[2],
        "jurisdiction_status": parsed[3],
    }


def _parse_race_code(code: str, state_code: str) -> tuple[str, str, str, str]:
    tokens = [token for token in code.split("-") if token]
    if tokens and tokens[-1] in KNOWN_PARTY_CODES:
        tokens = tokens[:-1]
    if not tokens:
        return "", "unresolved", "", "unresolved"
    office = " ".join(tokens).title()
    office_status = "hint_parsed"
    jurisdiction = ""
    jurisdiction_status = "unresolved"

    def district_text(value: str) -> str:
        if re.fullmatch(r"D\d+", value):
            return f"District {value[1:]}"
        if re.fullmatch(r"W\d+", value):
            return f"Ward {value[1:]}"
        if re.fullmatch(r"HD\d+", value):
            return f"District {value[2:]}"
        if re.fullmatch(r"SD\d+", value):
            return f"District {value[2:]}"
        return value.replace("_", " ").title()

    if tokens[:2] == ["US", "HOUSE"]:
        office = "US House"
        rest = tokens[2:]
        if rest:
            jurisdiction = district_text(rest[0])
            jurisdiction_status = "hint_parsed"
    elif tokens[:2] == ["US", "SENATE"]:
        office = "US Senate"
        jurisdiction = STATE_NAME_BY_CODE[state_code]
        jurisdiction_status = "hint_parsed"
    elif tokens[:2] == ["NYC", "COUNCIL"]:
        office = "New York City Council"
        rest = tokens[2:]
        if rest:
            jurisdiction = district_text(rest[0])
            jurisdiction_status = "hint_parsed"
    elif "COUNCIL" in tokens:
        office = "City Council"
        council_index = tokens.index("COUNCIL")
        rest = tokens[council_index + 1 :]
        locality = " ".join(token.title() for token in tokens[:council_index])
        if rest:
            jurisdiction = district_text(rest[0])
            if locality and jurisdiction:
                jurisdiction = f"{locality} {jurisdiction}"
            elif locality:
                jurisdiction = locality
            jurisdiction_status = "hint_parsed"
        elif locality:
            jurisdiction = locality
            jurisdiction_status = "hint_parsed"
    elif tokens[0] == "COUNCIL":
        office = "City Council"
        rest = tokens[1:]
        if rest:
            jurisdiction = district_text(rest[0])
            jurisdiction_status = "hint_parsed"
    elif tokens[0] == "HOUSE":
        office = "State House"
        rest = tokens[1:]
        if rest:
            jurisdiction = " ".join(district_text(token) for token in rest)
            jurisdiction_status = "hint_parsed"
    elif tokens[0] == "SENATE":
        office = "State Senate"
        rest = tokens[1:]
        if rest:
            jurisdiction = " ".join(district_text(token) for token in rest)
            jurisdiction_status = "hint_parsed"
    elif tokens[0] == "ASSEMBLY":
        office = "State Assembly"
        rest = tokens[1:]
        if rest:
            jurisdiction = " ".join(district_text(token) for token in rest)
            jurisdiction_status = "hint_parsed"
    elif re.fullmatch(r"HD\d+", tokens[0]):
        office = "State House"
        jurisdiction = district_text(tokens[0])
        jurisdiction_status = "hint_parsed"
    elif re.fullmatch(r"SD\d+", tokens[0]):
        office = "State Senate"
        jurisdiction = district_text(tokens[0])
        jurisdiction_status = "hint_parsed"
    elif tokens[0] == "MAYOR":
        office = "Mayor"
        jurisdiction = STATE_NAME_BY_CODE[state_code]
        jurisdiction_status = "hint_parsed"
    elif tokens[0] == "GOVERNOR":
        office = "Governor"
        jurisdiction = STATE_NAME_BY_CODE[state_code]
        jurisdiction_status = "hint_parsed"
    elif tokens[0] == "MPS":
        office = "School Board"
        rest = tokens[1:]
        if rest:
            jurisdiction = f"Milwaukee Public Schools {district_text(rest[0])}"
            jurisdiction_status = "hint_parsed"
    elif len(tokens) >= 2 and tokens[-2:] == ["AT", "LARGE"]:
        jurisdiction = "At-Large"
        jurisdiction_status = "hint_parsed"
    return office, office_status, jurisdiction, jurisdiction_status


def _state_from_jurisdiction(jurisdiction: str) -> tuple[str, str]:
    jurisdiction = jurisdiction.strip()
    if jurisdiction == "New York City":
        return "NY", "New York"
    for code, name in STATE_NAME_BY_CODE.items():
        if jurisdiction == name or jurisdiction.startswith(f"{name} "):
            return code, name
    return "", ""


def _identity(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
