import argparse
from pathlib import Path

from .airtable import collect_chapters, collect_national_endorsements
from .adjudication import (
    build_opponent_queue,
    finalize_verification,
    import_chapter_history,
    enrich_verified_endorsement_years,
    merge_reviews,
)
from .archive_pages import fetch_archived_pages
from .analysis import analyze
from .audit import validate
from .chapter_crawler import crawl_all_chapters
from .census import audit_census
from .congressional import build_congressional_inventory
from .state_results import collect_state_primaries
from .coverage import build_coverage_ledger
from .collector import collect_sources
from .database import initialize_database
from .document_corpus import run_candidate_document_regather_batch, rebuild_candidate_analysis_segments
from .endorsement_mentions import extract_mentions
from .full_text_audit import build_full_text_sufficiency_audit
from .fec_presidential import (
    import_2016_presidential_primaries,
    import_2020_presidential_primaries,
)
from .organizational_context import (
    build_organizational_context_inventory,
    run_organizational_context_fetch_pass,
)
from .organizational_context_corpus import run_organizational_context_extraction_batch
from .opponent_batches import merge_opponent_reviews, prepare_opponent_batches
from .official_platform_kde import run_official_platform_kde
from .priorities import build_priority_queues
from .provisional_kde import run_provisional_kde
from .queue import build_research_queue
from .race_registry import build_race_registry
from .structured_leads import extract_structured_leads
from .statement_batches import (
    merge_statement_reviews,
    prepare_partial_statement_batches,
    prepare_statement_batches,
)
from .sticking_points import analyze_sticking_points
from .text_analysis import analyze_text
from .model_topics import classify_model_topics
from .jev_topics import benchmark_jev
from .voter_guides import collect_voter_guides
from .wayback_crawler import discover_wayback_urls, filter_existing_wayback_urls


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dsa-analysis",
        description="Collect and audit source-first DSA research data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("collect", help="Fetch registered sources and append to the manifest.")
    subparsers.add_parser(
        "collect-endorsements",
        help="Download DSA National's current and past endorsement Airtable views.",
    )
    subparsers.add_parser(
        "collect-chapters",
        help="Download DSA National's current chapter-directory Airtable view.",
    )
    subparsers.add_parser(
        "build-queue",
        help="Build candidate-verification and chapter-year coverage queues.",
    )
    crawl_parser = subparsers.add_parser(
        "crawl-chapters",
        help="Discover official local chapter endorsement pages.",
    )
    crawl_parser.add_argument("--workers", type=int, default=12)
    crawl_parser.add_argument("--pages-per-site", type=int, default=40)
    mentions_parser = subparsers.add_parser(
        "extract-endorsement-mentions",
        help="Extract reviewable endorsement statements from discovered chapter pages.",
    )
    wayback_parser = subparsers.add_parser(
        "crawl-wayback",
        help="Discover historical endorsement URLs in the Wayback CDX index.",
    )
    wayback_parser.add_argument("--workers", type=int, default=8)
    wayback_parser.add_argument("--limit", type=int)
    wayback_parser.add_argument("--timeout", type=int, default=60)
    subparsers.add_parser(
        "filter-wayback",
        help="Remove static assets and false-positive historical URLs.",
    )
    archive_parser = subparsers.add_parser(
        "fetch-archive-pages",
        help="Fetch a resumable batch of historical endorsement pages.",
    )
    archive_parser.add_argument("--limit", type=int, default=500)
    archive_parser.add_argument("--workers", type=int, default=4)
    subparsers.add_parser(
        "extract-local-leads",
        help="Parse high-confidence candidate and office leads from endorsement mentions.",
    )
    subparsers.add_parser(
        "build-coverage-ledger",
        help="Merge current-site, social-source, and Wayback chapter-year coverage.",
    )
    subparsers.add_parser(
        "merge-endorsement-reviews",
        help="Validate and merge all adjudicated endorsement batches.",
    )
    subparsers.add_parser(
        "build-opponent-queue",
        help="Create a race/opponent research queue from reviewed local endorsements.",
    )
    subparsers.add_parser(
        "collect-voter-guides",
        help="Extract structured candidates from official DSA voter-guide applications.",
    )
    subparsers.add_parser(
        "finalize-endorsement-verification",
        help="Merge independent second-pass endorsement verification.",
    )
    history_parser = subparsers.add_parser(
        "import-chapter-history",
        help="Import a verified chapter endorsement-history CSV.",
    )
    history_parser.add_argument("--path", required=True)
    history_parser.add_argument("--chapter", required=True)
    history_parser.add_argument("--state", required=True)
    history_parser.add_argument("--replace", action="store_true")
    subparsers.add_parser(
        "enrich-endorsement-years",
        help="Backfill years only when linked source mentions unanimously identify one.",
    )
    opponent_batch_parser = subparsers.add_parser(
        "prepare-opponent-batches",
        help="Split endorsed candidacies into race-roster research batches.",
    )
    opponent_batch_parser.add_argument("--count", type=int, default=8)
    merge_opponents_parser = subparsers.add_parser(
        "merge-opponent-reviews",
        help="Merge verified official primary ballot rosters.",
    )
    merge_opponents_parser.add_argument("--partial", action="store_true")
    statement_batch_parser = subparsers.add_parser(
        "prepare-statement-batches",
        help="Split all primary candidates into first-party evidence research batches.",
    )
    statement_batch_parser.add_argument("--count", type=int, default=16)
    partial_statement_parser = subparsers.add_parser(
        "prepare-partial-statement-batches",
        help="Start statement research from completed roster batches.",
    )
    partial_statement_parser.add_argument("--count", type=int, default=4)
    merge_statements_parser = subparsers.add_parser(
        "merge-statement-reviews",
        help="Merge exact candidate statements and source-unavailable findings.",
    )
    merge_statements_parser.add_argument("--partial", action="store_true")
    subparsers.add_parser(
        "analyze-sticking-points",
        help="Derive explicit conflicts and coded policy divergences by primary.",
    )
    subparsers.add_parser(
        "build-priorities",
        help="Rank unresolved chapter histories and candidacy evidence gaps.",
    )
    subparsers.add_parser("init-db", help="Load manual CSVs into the SQLite research database.")
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate schemas, provenance, and coding values.",
    )
    validate_parser.add_argument("--strict", action="store_true")
    subparsers.add_parser(
        "audit-census",
        help="Account for every known race and source gap, including pre-2016 evidence.",
    )
    congress_parser = subparsers.add_parser(
        "collect-congressional",
        help="Inventory all-party House/Senate results, independently of DSA endorsements.",
    )
    congress_parser.add_argument("--download", action="store_true")
    state_parser = subparsers.add_parser(
        "collect-state-primaries",
        help="Import registered official state primary returns with complete candidate provenance.",
    )
    state_parser.add_argument("--download", action="store_true")
    subparsers.add_parser("analyze", help="Generate summary tables and the draft report.")
    subparsers.add_parser(
        "analyze-text",
        help="Generate TF-IDF, MPIF, similarity, topic, and sticking-point graphs.",
    )
    subparsers.add_parser(
        "rebuild-analysis-segments",
        help="Rebuild candidate model passages from retained paragraphs without fetching or renumbering sources.",
    )
    subparsers.add_parser(
        "classify-topics",
        help="Classify eligible exact-text candidate segments with a pinned local embedding model.",
    )
    jev_parser = subparsers.add_parser(
        "benchmark-jev",
        help="Prepare an isolated Jev topic pilot; hosted requests require explicit opt-in.",
    )
    jev_parser.add_argument("--limit", type=int, default=220)
    jev_parser.add_argument("--execute", action="store_true")
    jev_parser.add_argument("--allow-hosted", action="store_true")
    jev_parser.add_argument("--gold", type=Path)
    jev_parser.add_argument("--output-dir", type=Path)
    subparsers.add_parser(
        "build-race-registry",
        help="Build the canonical nationwide DSA-endorsed primary race registry.",
    )
    subparsers.add_parser(
        "import-2016-presidential-primaries",
        help="Import official FEC state rosters for DSA-endorsed Bernie Sanders.",
    )
    subparsers.add_parser(
        "import-2020-presidential-primaries",
        help="Import official FEC state rosters for DSA-endorsed Bernie Sanders.",
    )
    regather_parser = subparsers.add_parser(
        "regather-candidate-documents",
        help="Fetch and extract the highest-priority incomplete campaign documents.",
    )
    regather_parser.add_argument("--limit", type=int)
    subparsers.add_parser(
        "audit-full-text",
        help="Audit full-document and paired-race sufficiency before narrative analysis.",
    )
    subparsers.add_parser(
        "build-organizational-context",
        help="Build national and state official-platform coverage for represented cycles.",
    )
    context_fetch_parser = subparsers.add_parser(
        "fetch-organizational-context",
        help="Fetch queued official party and DSA organizational documents.",
    )
    context_fetch_parser.add_argument("--limit", type=int)
    subparsers.add_parser(
        "extract-organizational-context",
        help="Extract and segment fetched official organizational documents.",
    )
    kde_parser = subparsers.add_parser(
        "provisional-kde",
        help="Run provisional GTE multilingual UMAP/KDE analysis on candidate segments.",
    )
    kde_parser.add_argument("--batch-size", type=int, default=48)
    kde_parser.add_argument("--max-length", type=int, default=256)
    kde_parser.add_argument("--force-embeddings", action="store_true")
    official_kde_parser = subparsers.add_parser(
        "official-platform-kde",
        help=(
            "Run document-stratified, equal-platform-weighted GTE UMAP/KDE analysis "
            "on official platform text."
        ),
    )
    official_kde_parser.add_argument("--batch-size", type=int, default=48)
    official_kde_parser.add_argument("--max-length", type=int, default=256)
    official_kde_parser.add_argument("--force-embeddings", action="store_true")
    args = parser.parse_args()

    if args.command == "rebuild-analysis-segments":
        count = rebuild_candidate_analysis_segments()
        print(f"Rebuilt {count} candidate analysis segments; original source paragraphs preserved.")
        return
    if args.command == "collect":
        successes, failures = collect_sources()
        print(f"Collected {successes} sources; {failures} failed.")
        raise SystemExit(1 if failures else 0)
    if args.command == "collect-endorsements":
        count = collect_national_endorsements()
        print(f"Collected {count} unique national endorsement records.")
        return
    if args.command == "collect-chapters":
        count = collect_chapters()
        print(f"Collected {count} current/historical chapter-directory records.")
        return
    if args.command == "build-queue":
        candidates, coverage = build_research_queue()
        print(
            f"Built {candidates} candidate review rows and "
            f"{coverage} chapter-year coverage rows."
        )
        return
    if args.command == "crawl-chapters":
        chapters, pages = crawl_all_chapters(args.workers, args.pages_per_site)
        print(f"Crawled {chapters} chapters; found {pages} endorsement-like pages.")
        return
    if args.command == "extract-endorsement-mentions":
        mentions, pages = extract_mentions()
        print(f"Extracted {mentions} mentions from {pages} pages.")
        return
    if args.command == "crawl-wayback":
        chapters, urls = discover_wayback_urls(
            args.workers, limit=args.limit, timeout=args.timeout,
        )
        print(
            f"Attempted {chapters} chapter domains; retained {urls} historical URLs. "
            "See wayback_crawl_status.csv for failures and truncated searches."
        )
        return
    if args.command == "filter-wayback":
        before, after = filter_existing_wayback_urls()
        print(f"Filtered Wayback URLs from {before} to {after}.")
        return
    if args.command == "fetch-archive-pages":
        attempted, found, remaining = fetch_archived_pages(args.limit, args.workers)
        print(
            f"Fetched {attempted} archived URLs; found {found} endorsement pages; "
            f"{remaining} remain."
        )
        return
    if args.command == "extract-local-leads":
        count = extract_structured_leads()
        print(f"Extracted {count} high-confidence local endorsement leads.")
        return
    if args.command == "build-coverage-ledger":
        rows, unresolved = build_coverage_ledger()
        print(f"Built {rows} coverage rows; {unresolved} remain unresolved.")
        return
    if args.command == "merge-endorsement-reviews":
        mentions, candidates, rejects = merge_reviews()
        print(
            f"Merged {mentions} adjudicated mentions into {candidates} "
            f"candidate endorsements; {rejects} rows rejected."
        )
        return
    if args.command == "build-opponent-queue":
        count = build_opponent_queue()
        print(f"Built {count} endorsed-candidate opponent research rows.")
        return
    if args.command == "collect-voter-guides":
        nyc, la = collect_voter_guides()
        print(f"Collected {nyc} NYC and {la} Los Angeles voter-guide records.")
        return
    if args.command == "finalize-endorsement-verification":
        reviewed, verified, rejected = finalize_verification()
        print(
            f"Finalized {reviewed} candidates: {verified} verified, "
            f"{rejected} rejected."
        )
        return
    if args.command == "import-chapter-history":
        imported, gaps = import_chapter_history(
            Path(args.path),
            args.chapter,
            args.state,
            replace_chapter=args.replace,
        )
        print(f"Imported {imported} endorsements; recorded {gaps} gaps.")
        return
    if args.command == "enrich-endorsement-years":
        enriched, unresolved = enrich_verified_endorsement_years()
        print(f"Enriched {enriched} endorsement years; {unresolved} remain ambiguous.")
        return
    if args.command == "prepare-opponent-batches":
        rows, count = prepare_opponent_batches(args.count)
        print(f"Prepared {rows} candidacies in {count} opponent batches.")
        return
    if args.command == "merge-opponent-reviews":
        rows, resolved, unavailable = merge_opponent_reviews(
            require_complete=not args.partial
        )
        print(
            f"Merged {rows} race reviews: {resolved} verified, "
            f"{unavailable} source unavailable."
        )
        return
    if args.command == "prepare-statement-batches":
        rows, count = prepare_statement_batches(args.count)
        print(f"Prepared {rows} primary candidates in {count} statement batches.")
        return
    if args.command == "prepare-partial-statement-batches":
        rows, count = prepare_partial_statement_batches(args.count)
        print(
            f"Found {rows} candidates in available rosters; wrote {count} new "
            "statement batches."
        )
        return
    if args.command == "merge-statement-reviews":
        rows, verified, unavailable = merge_statement_reviews(
            require_complete=not args.partial
        )
        print(
            f"Merged {rows} candidate evidence reviews: {verified} verified excerpts, "
            f"{unavailable} source unavailable."
        )
        return
    if args.command == "analyze-sticking-points":
        explicit, coded = analyze_sticking_points()
        print(
            f"Generated {explicit} explicit conflicts and {coded} coded divergences."
        )
        return
    if args.command == "build-priorities":
        chapters, candidacies = build_priority_queues()
        print(
            f"Ranked {chapters} chapter-history gaps and "
            f"{candidacies} incomplete candidacies."
        )
        return
    if args.command == "init-db":
        tables, rows = initialize_database()
        print(f"Initialized {tables} tables with {rows} rows.")
        return
    if args.command == "validate":
        result = validate(strict=args.strict)
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        for error in result.errors:
            print(f"ERROR: {error}")
        if not result.ok:
            raise SystemExit(1)
        print("Validation passed.")
        return
    if args.command == "audit-census":
        stats = audit_census()
        print(
            f"Census audit: complete={stats['complete']}, "
            f"races={stats['registry_races']}, gaps={stats['gaps']}. "
            "See data/analysis/census_gaps.csv."
        )
        return
    if args.command == "collect-congressional":
        stats = build_congressional_inventory(download=args.download)
        print(
            f"Congressional inventory: source_rows={stats['source_result_rows']}, "
            f"regular_seats={stats['regular_seat_inventory_rows']}, "
            f"gaps={stats['gap_records']}, complete={stats['complete']}."
        )
        return
    if args.command == "collect-state-primaries":
        stats = collect_state_primaries(download=args.download)
        print(
            f"State primary returns: sources={stats['source_count']}, "
            f"contests={stats['contests']}, candidate_rows={stats['candidate_rows']}."
        )
        return
    if args.command == "analyze":
        stats = analyze()
        print(
            "Analysis complete: "
            + ", ".join(f"{name}={value}" for name, value in stats.items())
        )
        return
    if args.command == "analyze-text":
        stats = analyze_text()
        model_stats = classify_model_topics()
        print(
            "Text analysis complete: "
            f"candidate_documents={stats['candidate_documents']}, "
            f"candidate_segments={stats['candidate_segments']}, "
            f"official_segments={stats['official_segments']}, "
            f"model_classified={model_stats['classified_rows']}, "
            f"figures={stats['figure_count'] + 1}."
        )
        return
    if args.command == "classify-topics":
        stats = classify_model_topics()
        print(
            "Model topic classification complete: "
            f"rows={stats['total_rows']}, classified={stats['classified_rows']}, "
            f"unclassified={stats['unclassified_rows']}."
        )
        return
    if args.command == "benchmark-jev":
        kwargs = {"output_dir": args.output_dir} if args.output_dir else {}
        stats = benchmark_jev(
            limit=args.limit, execute=args.execute, allow_hosted=args.allow_hosted,
            gold_path=args.gold, **kwargs,
        )
        print(
            f"Jev pilot: status={stats['status']}, sample={stats['sample_rows']}, "
            f"predictions={stats['prediction_rows']}, reviewed={stats['reviewed_rows']}. "
            "Canonical local classifications are unchanged."
        )
        return
    if args.command == "build-race-registry":
        result = build_race_registry()
        print(
            "Race registry complete: "
            f"in_scope_races={result.in_scope_race_rows}, "
            f"resolved_states={result.resolved_state_race_rows}, "
            f"represented_state_cycles={result.represented_state_cycle_rows}, "
            f"unresolved_fields={result.unresolved_race_rows}."
        )
        return
    if args.command == "import-2016-presidential-primaries":
        endorsements, candidates = import_2016_presidential_primaries()
        print(
            "2016 presidential primaries imported: "
            f"races={endorsements}, candidate_rows={candidates}."
        )
        return
    if args.command == "import-2020-presidential-primaries":
        endorsements, candidates = import_2020_presidential_primaries()
        print(
            "2020 presidential primaries imported: "
            f"races={endorsements}, candidate_rows={candidates}."
        )
        return
    if args.command == "regather-candidate-documents":
        result = run_candidate_document_regather_batch(limit=args.limit)
        batch = result.batch_result
        print(
            "Candidate document regather complete: "
            f"selected_urls={result.plan.selected_unique_urls}, "
            f"processed={batch.processed_documents}, "
            f"successful={batch.successful_documents}, "
            f"fetch_errors={batch.fetch_errors}, "
            f"extraction_errors={batch.extraction_errors}."
        )
        return
    if args.command == "audit-full-text":
        result = build_full_text_sufficiency_audit()
        print(
            "Full-text audit complete: "
            f"corpus_rows={result.corpus_rows}, "
            f"eligible_races={result.eligible_races}, "
            f"retryable_gaps={result.retryable_gaps}, "
            f"sufficient={str(result.sufficient).lower()}."
        )
        if not result.sufficient:
            print("Failed gates: " + ", ".join(result.failed_gates))
            raise SystemExit(1)
        return
    if args.command == "build-organizational-context":
        result = build_organizational_context_inventory()
        print(
            "Organizational context inventory complete: "
            f"state_cycles={result.represented_state_cycle_rows}, "
            f"coverage_rows={result.coverage_rows}, "
            f"platform_gaps={result.platform_gap_rows}, "
            f"all_categories_resolved="
            f"{str(result.all_represented_state_cycles_have_status).lower()}."
        )
        return
    if args.command == "fetch-organizational-context":
        result = run_organizational_context_fetch_pass(limit=args.limit)
        print(
            "Organizational context fetch complete: "
            f"attempted={result.queued_urls}, fetched={result.fetched_urls}, "
            f"failed={result.failed_urls}."
        )
        raise SystemExit(1 if result.failed_urls else 0)
    if args.command == "extract-organizational-context":
        result = run_organizational_context_extraction_batch()
        print(
            "Organizational context extraction complete: "
            f"processed={result.processed_documents}, "
            f"successful={result.successful_documents}, "
            f"extraction_errors={result.extraction_errors}."
        )
        raise SystemExit(1 if result.extraction_errors else 0)
    if args.command == "provisional-kde":
        result = run_provisional_kde(
            batch_size=args.batch_size,
            max_length=args.max_length,
            force_embeddings=args.force_embeddings,
        )
        print(
            "Provisional KDE complete: "
            f"segments={result.retained_segments}, "
            f"endorsed={result.endorsed_segments}, "
            f"opponent={result.opponent_segments}, "
            f"dimensions={result.selected_dimensions}, "
            f"output={result.output_directory}."
        )
        return
    if args.command == "official-platform-kde":
        result = run_official_platform_kde(
            batch_size=args.batch_size,
            max_length=args.max_length,
            force_embeddings=args.force_embeddings,
        )
        print(
            "Official-platform KDE complete: "
            f"segments={result.retained_segments}, "
            f"dsa={result.dsa_segments}, "
            f"democratic={result.democratic_segments}, "
            f"dimensions={result.selected_dimensions}, "
            f"output={result.output_directory}."
        )
        return
