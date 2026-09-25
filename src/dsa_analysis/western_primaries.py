"""Recover official congressional primary results for AK, AZ, NV, and UT."""

import argparse
import csv
import hashlib
import html
import re
from collections import defaultdict
from pathlib import Path

from .io import write_csv
from .paths import ANALYSIS_DATA_DIR, RAW_DIR
from .state_results import FIELDS

RAW_SUBDIR = "western_primaries"
RESULT_FILENAME = "western_primary_results.csv"
PARTIAL_RESULT_FILENAME = "western/partial_primary_results.csv"
MANIFEST_SUBDIR = "western"

SOURCE_MANIFEST_FIELDS = [
    "source_id", "state_code", "election_date", "stage", "artifact_kind", "authority",
    "publication_url", "source_url", "acquisition_url", "raw_filename", "sha256",
    "acquisition_status", "verification_status", "certification_status",
    "provisional_status", "candidate_rows", "contests", "coverage", "source_locators",
    "notes",
]
ATTEMPT_FIELDS = [
    "attempt_id", "attempted_on", "state_code", "cycle", "source_url", "method",
    "outcome", "raw_evidence", "notes",
]
COVERAGE_FIELDS = [
    "state_code", "cycle", "election_date", "stage", "chamber", "district",
    "primary_party", "coverage_status", "candidate_rows", "source_ids", "notes",
]
GAP_FIELDS = [
    "gap_id", "state_code", "cycle", "stage", "chamber", "coverage_status",
    "recovered_scope", "missing_scope", "blocker", "next_authoritative_step",
    "source_urls",
]
NV_COUNTY_INVENTORY_FIELDS = [
    "cycle", "county", "status", "source_id", "raw_filename", "source_url", "notes",
]

NV_COUNTIES = (
    "Carson City", "Churchill", "Clark", "Douglas", "Elko", "Esmeralda",
    "Eureka", "Humboldt", "Lander", "Lincoln", "Lyon", "Mineral", "Nye",
    "Pershing", "Storey", "Washoe", "White Pine",
)

NV_CAPTURED_COUNTY_SOURCES = {
    ("2024", "Humboldt"): {
        "source_id": "nv-2024-humboldt-final-summary",
        "raw_filename": "nv/2024/nv-2024-humboldt-final-summary.pdf",
        "source_url": "https://www.humboldtcountynv.gov/DocumentCenter/View/7426",
    },
    ("2026", "Storey"): {
        "source_id": "nv-2026-storey-final-summary",
        "raw_filename": "nv/2026/nv-2026-storey-final-summary.pdf",
        "source_url": "https://www.storeycounty.org/DocumentCenter/View/23105",
    },
    ("2026", "Eureka"): {
        "source_id": "nv-2026-eureka-final-summary",
        "raw_filename": "nv/2026/nv-2026-eureka-final-summary.pdf",
        "source_url": (
            "https://www.eurekacountynv.gov/media/hafnpn3j/"
            "eureka2026primarysummaryfinal.pdf"
        ),
    },
    ("2026", "Clark"): {
        "source_id": "nv-2026-clark-official-results",
        "raw_filename": "nv/2026/nv-2026-clark-official-results.html",
        "source_url": (
            "https://elections.clarkcountynv.gov/ElectionResults_NV/ENR/EnrMain"
        ),
    },
    ("2026", "Churchill"): {
        "source_id": "nv-2026-churchill-final-summary",
        "raw_filename": "nv/2026/nv-2026-churchill-final-summary.pdf",
        "source_url": "https://www.churchillcountynv.gov/Archive.aspx?ADID=1412",
    },
    ("2024", "Churchill"): {
        "source_id": "nv-2024-churchill-final-summary",
        "raw_filename": "nv/2024/nv-2024-churchill-final-summary.pdf",
        "source_url": "https://www.churchillcountynv.gov/Archive.aspx?ADID=1392",
    },
    ("2026", "Humboldt"): {
        "source_id": "nv-2026-humboldt-canvass-sov",
        "raw_filename": "nv/2026/nv-2026-humboldt-canvass-sov.pdf",
        "source_url": "https://www.humboldtcountynv.gov/DocumentCenter/View/8700",
    },
    ("2024", "Lyon"): {
        "source_id": "nv-2024-lyon-final-results",
        "raw_filename": "nv/2024/nv-2024-lyon-final-results.pdf",
        "source_url": "https://www.lyon-county.org/DocumentCenter/View/12792",
    },
    ("2026", "Lyon"): {
        "source_id": "nv-2026-lyon-final-results",
        "raw_filename": "nv/2026/nv-2026-lyon-final-results.pdf",
        "source_url": "https://www.lyon-county.org/DocumentCenter/View/14189",
    },
    ("2024", "Eureka"): {
        "source_id": "nv-2024-eureka-final-summary",
        "raw_filename": "nv/2024/nv-2024-eureka-final-summary.pdf",
        "source_url": (
            "https://www.eurekacountynv.gov/media/zgonh0ih/"
            "eureka2024primarysummaryfinal.pdf"
        ),
    },
    ("2024", "Nye"): {
        "source_id": "nv-2024-nye-final-results",
        "raw_filename": "nv/2024/nv-2024-nye-final-results.pdf",
        "source_url": "https://www.nyecountynv.gov/DocumentCenter/View/46792/",
    },
    ("2026", "Nye"): {
        "source_id": "nv-2026-nye-final-results",
        "raw_filename": "nv/2026/nv-2026-nye-final-results.pdf",
        "source_url": "https://www.nyecountynv.gov/DocumentCenter/View/51331/",
    },
    ("2024", "White Pine"): {
        "source_id": "nv-2024-white-pine-canvass",
        "raw_filename": "nv/2024/nv-2024-white-pine-canvass.pdf",
        "source_url": (
            "https://www.whitepinecounty.net/DocumentCenter/View/10150/"
            "2024-Primary-Canvass"
        ),
    },
}

NV_ROUTE_FAILURES = {
    ("2024", "Clark"): {
        "source_url": (
            "https://www.clarkcountynv.gov/government/departments/elections/24p-info"
        ),
        "notes": (
            "Official 2024 index returns 200 but its result link resolves to the current "
            "2026 ENR; tested 24PE/24P final CVR URL variants return HTTP 404."
        ),
    },
    ("2024", "Esmeralda"): {
        "source_url": "https://www.accessesmeralda.com/",
        "notes": (
            "Current official site returns 200 but exposes no election/results links; "
            "legacy esmeraldacountynv.org connection fails and indexed official search "
            "found no 2024 final document."
        ),
    },
    ("2026", "Esmeralda"): {
        "source_url": "https://www.accessesmeralda.com/",
        "notes": (
            "Current official site returns 200 but exposes no election/results links; "
            "legacy esmeraldacountynv.org connection fails and indexed official search "
            "found no 2026 final document."
        ),
    },
    ("2024", "Lander"): {
        "source_url": "https://www.landercountynv.org/government/county-clerk/elections",
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2026", "Lander"): {
        "source_url": "https://www.landercountynv.org/government/county-clerk/elections",
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2024", "Lincoln"): {
        "source_url": "https://lincolncountynv.org/government/county-clerk/elections/",
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2026", "Lincoln"): {
        "source_url": "https://lincolncountynv.org/government/county-clerk/elections/",
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2024", "Mineral"): {
        "source_url": (
            "https://www.mineralcountynv.us/government/clerk_treasurer/elections.php"
        ),
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2026", "Mineral"): {
        "source_url": (
            "https://www.mineralcountynv.us/government/clerk_treasurer/elections.php"
        ),
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2024", "Pershing"): {
        "source_url": (
            "https://pershingcountynv.gov/government/county-clerk-treasurer/elections/"
        ),
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2026", "Pershing"): {
        "source_url": (
            "https://pershingcountynv.gov/government/county-clerk-treasurer/elections/"
        ),
        "notes": "Official elections route returns HTTP 404; indexed official search found no final.",
    },
    ("2024", "Storey"): {
        "source_url": "https://www.storeycounty.org/208/Election-Information",
        "notes": (
            "Official page returns 200 but links only 2026 final summary/CVR/canvass; "
            "indexed official search found only 2024 canvass meeting notices, no result file."
        ),
    },
    ("2026", "White Pine"): {
        "source_url": "https://www.whitepinecounty.net/689/2026-Election",
        "notes": (
            "Requested year route redirects to the 2024 election page; alternate /710 route "
            "redirects to CivicPlus authentication/Paused Projects; indexed search found "
            "only a canvass agenda and no final result document."
        ),
    },
    ("2024", "Carson City"): {
        "source_url": (
            "https://www.carsoncity.gov/home/showpublisheddocument/"
            "89709/638556160788800000"
        ),
        "notes": (
            "Official 2024 summary document returns HTTP 403; official history page also "
            "returns 403 to direct acquisition; Wayback CDX returned no PDF capture."
        ),
    },
    ("2026", "Carson City"): {
        "source_url": (
            "https://www.carsoncity.gov/government/departments-a-f/"
            "clerk-recorder/elections-department/"
            "election-results-and-historical-information"
        ),
        "notes": (
            "Official results/history page returns HTTP 403 and indexed official search "
            "exposes no 2026 final document route."
        ),
    },
    ("2024", "Douglas"): {
        "source_url": "https://cltr.douglascountynv.gov/elections/results-and-resources",
        "notes": (
            "Two official 2024 primary page variants returned HTTP 404; current official "
            "results/resources page returned 200 but exposed no 2024 final export."
        ),
    },
    ("2026", "Douglas"): {
        "source_url": "https://cltr.douglascountynv.gov/elections/results-and-resources",
        "notes": (
            "Official 2026 primary and results/resources pages returned 200 but page source "
            "contained no final results, canvass, SOV, CVR, PDF, CSV, or ZIP export."
        ),
    },
    ("2024", "Elko"): {
        "source_url": (
            "https://www.elkocountynv.net/departments/clerk/election_results.php"
        ),
        "notes": (
            "Official election-results and elections paths returned HTTP 404; indexed "
            "official-site search exposed no 2024 primary final document."
        ),
    },
    ("2026", "Elko"): {
        "source_url": (
            "https://www.elkocountynv.net/departments/clerk/election_results.php"
        ),
        "notes": (
            "Official election-results and elections paths returned HTTP 404; indexed "
            "official-site search exposed no 2026 primary final document."
        ),
    },
    ("2024", "Washoe"): {
        "source_url": (
            "https://www.washoecounty.gov/voters/results/resultsdata/"
            "2024primaryresults.pdf"
        ),
        "notes": (
            "Exact official PDF route now returns HTTP 404. Wayback CDX identifies a "
            "2026-02-28 PDF capture, but all replay modifiers return HTTP 404; alternate "
            "resultsfiles route has no capture."
        ),
    },
    ("2026", "Washoe"): {
        "source_url": (
            "https://www.washoecounty.gov/voters/results/resultsdata/"
            "2026primaryresults.pdf"
        ),
        "notes": (
            "Official resultsdata and resultsfiles PDF patterns return HTTP 404; legacy "
            "2026data and election-results pages also return HTTP 404."
        ),
    },
}

AK_SOURCES = (
    {
        "source_id": "ak-2024-primary-precinct",
        "state": "AK",
        "date": "2024-08-20",
        "filename": "ak/2024/ak-2024-primary-precinct.csv",
        "url": "https://www.elections.alaska.gov/results/24PRIM/ENRbyPrecinct.csv",
        "publication": "https://www.elections.alaska.gov/election-results/e/?id=24prim",
    },
    {
        "source_id": "ak-2026-primary-precinct",
        "state": "AK",
        "date": "2026-08-18",
        "filename": "ak/2026/ak-2026-primary-precinct.csv",
        "url": (
            "https://www.elections.alaska.gov/enr26/results/"
            "GA_ENR_Precinct_State_of_Alaska.csv"
        ),
        "publication": "https://www.elections.alaska.gov/election-results/e/?id=26prim",
    },
)

AZ_2024_SOURCE = {
    "source_id": "az-2024-primary-official-canvass",
    "state": "AZ",
    "date": "2024-07-30",
    "filename": "az/2024/az-2024-primary-official-canvass.pdf",
    "url": (
        "https://azsos.gov/sites/default/files/docs/"
        "2024_Primary_Election_Official_Canvass_0815b.pdf"
    ),
    "acquisition_url": (
        "https://web.archive.org/web/20240817161358id_/https://azsos.gov/"
        "sites/default/files/docs/2024_Primary_Election_Official_Canvass_0815b.pdf"
    ),
    "publication": "https://azsos.gov/elections/election-information/2024-election-info",
}

AZ_2026_SOURCE = {
    "source_id": "az-2026-primary-official-canvass",
    "state": "AZ",
    "date": "2026-07-21",
    "filename": "az/2026/az-2026-primary-official-canvass.pdf",
    "url": "https://apps.azsos.gov/election/2026/canvass/20260806_Primary_Canvass.pdf",
    "acquisition_url": (
        "https://web.archive.org/web/20260807005831id_/https://apps.azsos.gov/"
        "election/2026/canvass/20260806_Primary_Canvass.pdf"
    ),
    "publication": "https://azsos.gov/elections/election-information/2026-election-info",
}

NV_2026_ROSTER_SOURCE = {
    "source_id": "nv-2026-primary-contests-candidates",
    "state": "NV",
    "date": "2026-06-09",
    "filename": "nv/2026/nv-2026-primary-contests-candidates.pdf",
    "url": "https://www.nvsos.gov/home/showpublisheddocument/18368/639135026079800000",
    "acquisition_url": (
        "https://web.archive.org/web/20260522225332id_/https://www.nvsos.gov/"
        "home/showpublisheddocument/18368/639135026079800000"
    ),
    "publication": (
        "https://www.clarkcountynv.gov/government/departments/elections/26p-info"
    ),
}

NV_2026_CLARK_SOURCE = {
    "source_id": "nv-2026-clark-official-results",
    "state": "NV",
    "date": "2026-06-09",
    "filename": "nv/2026/nv-2026-clark-official-results.html",
    "url": "https://elections.clarkcountynv.gov/ElectionResults_NV/ENR/EnrMain",
    "publication": (
        "https://www.clarkcountynv.gov/government/departments/elections/"
        "election-night-results"
    ),
}

NV_2026_CLARK_CVR_SOURCE = {
    "source_id": "nv-2026-clark-final-cvr",
    "state": "NV",
    "date": "2026-06-09",
    "filename": "nv/2026/nv-2026-clark-final-cvr.zip",
    "url": (
        "https://elections.clarkcountynv.gov/electionresultsTV/cvr/26PE/"
        "26PE_CC_CVR_Export_JUN_Final_Confidential.zip"
    ),
    "publication": (
        "https://www.clarkcountynv.gov/government/departments/elections/26p-info"
    ),
}

NV_2024_ROSTER_SOURCES = (
    {
        "source_id": "nv-2024-primary-contests-candidates",
        "state": "NV",
        "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-primary-contests-candidates.pdf",
        "url": (
            "https://www.clarkcountynv.gov/adobe/assets/urn:aaid:aem:"
            "8b9dfb6e-c6b8-400a-a8fe-b68d6e4d4859/original/as/"
            "contests-candidates-web-all-2024.pdf"
        ),
        "publication": (
            "https://www.clarkcountynv.gov/government/departments/elections/24p-info"
        ),
    },
    {
        "source_id": "nv-2024-primary-contests-not-on-ballot",
        "state": "NV",
        "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-primary-contests-not-on-ballot.pdf",
        "url": (
            "https://www.clarkcountynv.gov/adobe/assets/urn:aaid:aem:"
            "575d8d98-7e2e-4bd2-994e-8c9c914f88ba/original/as/"
            "contests-not-on-ballot-24p.pdf"
        ),
        "publication": (
            "https://www.clarkcountynv.gov/government/departments/elections/24p-info"
        ),
    },
)

NV_SUPPORTING_SUMMARY_SOURCES = (
    {
        "source_id": "nv-2024-humboldt-final-summary",
        "state": "NV",
        "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-humboldt-final-summary.pdf",
        "url": "https://www.humboldtcountynv.gov/DocumentCenter/View/7426",
        "publication": "https://www.humboldtcountynv.gov/317/Elections",
        "coverage": (
            "confirms the District 2 Republican primary candidate set and county-final format"
        ),
        "notes": "Supporting county artifact only; its partial vote totals are not published.",
    },
    {
        "source_id": "nv-2026-storey-final-summary",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-storey-final-summary.pdf",
        "url": "https://www.storeycounty.org/DocumentCenter/View/23105",
        "publication": "https://www.storeycounty.org/208/Election-Information",
        "coverage": (
            "confirms the final-summary schema and aggregate Unresolved Write-In option"
        ),
        "notes": "Supporting county artifact only; its partial vote totals are not published.",
    },
    {
        "source_id": "nv-2026-eureka-final-summary",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-eureka-final-summary.pdf",
        "url": (
            "https://www.eurekacountynv.gov/media/hafnpn3j/"
            "eureka2026primarysummaryfinal.pdf"
        ),
        "publication": (
            "https://www.eurekacountynv.gov/departments/clerk-recorder/elections/"
        ),
        "coverage": "Eureka County final candidate summary",
        "notes": "Supporting county artifact only; its partial vote totals are not published.",
    },
    {
        "source_id": "nv-2026-eureka-canvass-abstract",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-eureka-canvass-abstract.pdf",
        "url": (
            "https://www.eurekacountynv.gov/media/peghggky/"
            "2026-primary-election-canvass-and-abstract.pdf"
        ),
        "publication": (
            "https://www.eurekacountynv.gov/departments/clerk-recorder/elections/"
        ),
        "coverage": "Eureka County signed canvass and abstract certification",
        "notes": "Certification companion; no partial statewide totals are published.",
    },
    {
        "source_id": "nv-2026-churchill-final-summary",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-churchill-final-summary.pdf",
        "url": "https://www.churchillcountynv.gov/Archive.aspx?ADID=1412",
        "publication": "https://www.churchillcountynv.gov/Archive.aspx?AMID=89",
        "coverage": "Churchill County final candidate summary",
        "notes": "Supporting county artifact only; partial district totals are not published.",
    },
    {
        "source_id": "nv-2026-churchill-sov",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-churchill-sov.pdf",
        "url": "https://www.churchillcountynv.gov/Archive.aspx?ADID=1413",
        "publication": "https://www.churchillcountynv.gov/Archive.aspx?AMID=89",
        "coverage": "Churchill County final precinct Statement of Votes Cast",
        "notes": "Verification companion; partial district totals are not published.",
    },
    {
        "source_id": "nv-2024-churchill-final-summary",
        "state": "NV",
        "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-churchill-final-summary.pdf",
        "url": "https://www.churchillcountynv.gov/Archive.aspx?ADID=1392",
        "publication": "https://www.churchillcountynv.gov/Archive.aspx?AMID=88",
        "coverage": "Churchill County 2024 final candidate summary",
        "notes": "Supporting county artifact only; partial statewide totals are not published.",
    },
    {
        "source_id": "nv-2024-churchill-sov",
        "state": "NV",
        "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-churchill-sov.pdf",
        "url": "https://www.churchillcountynv.gov/Archive.aspx?ADID=1393",
        "publication": "https://www.churchillcountynv.gov/Archive.aspx?AMID=88",
        "coverage": "Churchill County 2024 final precinct Statement of Votes Cast",
        "notes": "Verification companion; partial statewide totals are not published.",
    },
    {
        "source_id": "nv-2026-humboldt-canvass-sov",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-humboldt-canvass-sov.pdf",
        "url": "https://www.humboldtcountynv.gov/DocumentCenter/View/8700",
        "publication": "https://www.humboldtcountynv.gov/317/Elections",
        "coverage": "Humboldt County signed canvass and final Statement of Votes Cast",
        "notes": "Supporting county artifact only; partial district totals are not published.",
    },
    {
        "source_id": "nv-2024-lyon-final-results",
        "state": "NV",
        "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-lyon-final-results.pdf",
        "url": "https://www.lyon-county.org/DocumentCenter/View/12792",
        "publication": "https://www.lyon-county.org/801/Elections",
        "coverage": "Lyon County 2024 final primary results",
        "notes": "Split congressional district portions retained; no partial totals published.",
    },
    {
        "source_id": "nv-2026-lyon-final-results",
        "state": "NV",
        "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-lyon-final-results.pdf",
        "url": "https://www.lyon-county.org/DocumentCenter/View/14189",
        "publication": "https://www.lyon-county.org/801/Elections",
        "coverage": "Lyon County 2026 final primary results for District 2/4 precinct portions",
        "notes": "Split congressional district portions retained; no partial totals published.",
    },
    {
        "source_id": "nv-2024-eureka-final-summary",
        "state": "NV", "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-eureka-final-summary.pdf",
        "url": (
            "https://www.eurekacountynv.gov/media/zgonh0ih/"
            "eureka2024primarysummaryfinal.pdf"
        ),
        "publication": "https://www.eurekacountynv.gov/departments/clerk-recorder/elections/",
        "coverage": "Eureka County 2024 final candidate summary",
        "notes": "Supporting county artifact only; partial statewide totals are not published.",
    },
    {
        "source_id": "nv-2024-nye-final-results",
        "state": "NV", "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-nye-final-results.pdf",
        "url": "https://www.nyecountynv.gov/DocumentCenter/View/46792/",
        "publication": "https://www.nyecountynv.gov/1144/Past-Elections",
        "coverage": "Nye County 2024 final results",
        "notes": "Supporting county artifact only; partial statewide totals are not published.",
    },
    {
        "source_id": "nv-2026-nye-final-results",
        "state": "NV", "date": "2026-06-09",
        "filename": "nv/2026/nv-2026-nye-final-results.pdf",
        "url": "https://www.nyecountynv.gov/DocumentCenter/View/51331/",
        "publication": "https://www.nyecountynv.gov/1144/Past-Elections",
        "coverage": "Nye County 2026 final results",
        "notes": "Supporting county artifact only; partial district totals are not published.",
    },
    {
        "source_id": "nv-2024-white-pine-canvass",
        "state": "NV", "date": "2024-06-11",
        "filename": "nv/2024/nv-2024-white-pine-canvass.pdf",
        "url": (
            "https://www.whitepinecounty.net/DocumentCenter/View/10150/"
            "2024-Primary-Canvass"
        ),
        "publication": "https://www.whitepinecounty.net/689/2024-Election",
        "coverage": "White Pine County 2024 signed primary canvass",
        "notes": "Supporting county artifact only; partial statewide totals are not published.",
    },
)

NV_OPEN_CONTESTS = (
    ("2024", "2024-06-11", "Senate", "S", "Democratic", 4),
    ("2024", "2024-06-11", "Senate", "S", "Republican", 13),
    ("2024", "2024-06-11", "House", "01", "Republican", 5),
    ("2024", "2024-06-11", "House", "02", "Republican", 2),
    ("2024", "2024-06-11", "House", "03", "Democratic", 2),
    ("2024", "2024-06-11", "House", "03", "Republican", 7),
    ("2024", "2024-06-11", "House", "04", "Democratic", 2),
    ("2024", "2024-06-11", "House", "04", "Republican", 3),
    # Each 2026 county summary reports an aggregate Unresolved Write-In option.
    ("2026", "2026-06-09", "House", "02", "Democratic", 12),
    ("2026", "2026-06-09", "House", "02", "Republican", 14),
    ("2026", "2026-06-09", "House", "04", "Republican", 4),
)

NV_NO_PRIMARY_CONTESTS = (
    ("2024", "2024-06-11", "House", "01", "Democratic"),
    ("2024", "2024-06-11", "House", "02", "Democratic"),
    ("2026", "2026-06-09", "House", "04", "Democratic"),
)

UT_SOURCES = (
    {
        "source_id": "ut-2024-primary-statewide-canvass",
        "state": "UT",
        "date": "2024-06-25",
        "filename": "ut/2024/ut-2024-primary-statewide-canvass.pdf",
        "url": (
            "https://vote.utah.gov/wp-content/uploads/2024/07/"
            "2024-Primary-Election-State-Canvass-Final-Signed.pdf"
        ),
        "publication": "https://vote.utah.gov/2024-election-information/",
    },
    {
        "source_id": "ut-2026-primary-statewide-certification",
        "state": "UT",
        "date": "2026-06-23",
        "filename": "ut/2026/ut-2026-primary-statewide-certification.pdf",
        "url": "https://www.utah.gov/pmn/files/1464329.pdf",
        "publication": "https://www.utah.gov/pmn/sitemap/notice/1095127.html",
    },
    {
        "source_id": "ut-2026-salt-lake-official-summary",
        "state": "UT",
        "date": "2026-06-23",
        "filename": "ut/2026/ut-2026-salt-lake-official-summary.pdf",
        "url": (
            "https://electionresults.utah.gov/cdn/results/"
            "a7510980-7b10-4aca-a2d8-ff92951aca1c/"
            "FINAL%20OFFICIAL%20ElectionSummaryReportRPT_"
            "4f4ea355-06ab-4d3e-aa2d-13e063024886.pdf"
        ),
        "publication": (
            "https://electionresults.utah.gov/results/public/Utah/elections/"
            "Primary06232026/reports"
        ),
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _party_name(code: str) -> str:
    return {
        "AIP": "Alaskan Independence",
        "DEM": "Democratic",
        "GRN": "Green",
        "LIB": "Libertarian",
        "NOL": "No Labels",
        "NON": "Nonpartisan",
        "RAP": "Republican Alliance",
        "REP": "Republican",
        "UND": "Undeclared",
    }.get(code.strip(), code.strip())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _result_row(
    source: dict,
    *,
    chamber: str,
    district: str,
    primary_party: str,
    candidate_name: str,
    votes: int,
    party: str | None = None,
    candidate_id: str | None = None,
    write_in: bool = False,
    election_system: str = "partisan_primary",
    locator: str,
    reporting_units: int = 1,
) -> dict:
    path = RAW_DIR / RAW_SUBDIR / source["filename"]
    contest_id = "-".join((
        source["state"].casefold(), source["date"], chamber.casefold(),
        district.casefold(), "regular", _slug(primary_party) or "all",
    ))
    return {
        "contest_id": contest_id,
        "cycle": source["date"][:4],
        "election_date": source["date"],
        "stage": "primary",
        "state_code": source["state"],
        "chamber": chamber,
        "district": district,
        "term": "regular",
        "election_system": election_system,
        "primary_party": primary_party,
        "candidate_name": candidate_name,
        "candidate_source_id": candidate_id or candidate_name,
        "party": party if party is not None else primary_party,
        "write_in": write_in,
        "votes": votes,
        "source_id": source["source_id"],
        "source_url": source["url"],
        "source_sha256": _sha256(path),
        "source_locators": locator,
        "reporting_units": reporting_units,
    }


def parse_alaska(path: Path, source: dict) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {
            "Precinct_name", "Contest_Id", "Contest_title", "candidate_id",
            "candidate_name", "Candidate_Type", "Party_Code", "total_votes",
        }
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Alaska precinct export schema changed")
        for line_number, row in enumerate(reader, 2):
            title = row["Contest_title"].strip()
            if title not in {"U.S. Senator", "U.S. Representative"}:
                continue
            candidate_id = row["candidate_id"].strip()
            unit = row["Precinct_name"].strip()
            key = (row["Contest_Id"], candidate_id, unit)
            if key in seen:
                raise ValueError(f"Duplicate Alaska candidate/precinct row: {key}")
            seen.add(key)
            votes = int(row["total_votes"])
            if votes < 0:
                raise ValueError("Negative Alaska vote total")
            groups[(row["Contest_Id"], candidate_id)].append({
                "name": row["candidate_name"].strip(),
                "party": _party_name(row["Party_Code"]),
                "write_in": row["Candidate_Type"].strip().upper() == "W"
                or "write-in" in row["candidate_name"].casefold(),
                "votes": votes,
                "unit": unit,
                "line": line_number,
                "chamber": "Senate" if title == "U.S. Senator" else "House",
            })
    output = []
    for (_, candidate_id), rows in groups.items():
        identities = {(row["name"], row["party"], row["chamber"]) for row in rows}
        if len(identities) != 1:
            raise ValueError(f"Inconsistent Alaska candidate identity: {identities}")
        name, party, chamber = next(iter(identities))
        lines = sorted(row["line"] for row in rows)
        output.append(_result_row(
            source,
            chamber=chamber,
            district="S" if chamber == "Senate" else "00",
            primary_party="",
            candidate_name=name,
            candidate_id=candidate_id,
            party=party,
            write_in=rows[0]["write_in"],
            votes=sum(row["votes"] for row in rows),
            election_system="nonpartisan_top_four",
            locator=f"{path.name}:{lines[0]}-{lines[-1]}",
            reporting_units=len(rows),
        ))
    expected = {"2024": (12, {"House"}), "2026": (31, {"House", "Senate"})}
    count, chambers = expected[source["date"][:4]]
    if len(output) != count or {row["chamber"] for row in output} != chambers:
        raise ValueError("Alaska federal primary coverage differs from the official summary")
    return sorted(output, key=lambda row: (row["chamber"], row["candidate_name"]))


AZ_2024_RESULTS = {
    ("Senate", "S", "Republican"): [
        ("Kari Lake", 409339, False), ("Mark Lamb", 292888, False),
        ("Elizabeth Jean Reye", 38208, False), ("Dustin Paul Williams", 184, True),
    ],
    ("Senate", "S", "Democratic"): [("Ruben Gallego", 498927, False)],
    ("Senate", "S", "Green"): [
        ("Arturo Hernandez", 108, False), ("Michael Norton", 180, False),
        ("Eduardo Quintana", 282, True),
    ],
    ("House", "01", "Republican"): [
        ("Robert Backie", 9854, False), ("Kim George", 27587, False),
        ("David Schweikert", 62811, False),
    ],
    ("House", "01", "Democratic"): [
        ("Andrei Cherny", 15596, False), ("Marlene Galán-Woods", 15490, False),
        ("Andrew Horne", 8991, False), ("Kurt Kroemer", 2356, False),
        ("Conor O'Callaghan", 13539, False), ("Amish Shah", 17214, False),
    ],
    ("House", "02", "Republican"): [
        ("Eli Crane", 89480, False), ("Jack Smith", 21637, False),
    ],
    ("House", "02", "Democratic"): [("Jonathan Nez", 62033, False)],
    ("House", "03", "Republican"): [
        ("Jesus David Mendoza", 4840, False), ("Jeff Zink", 9243, False),
        ("Nicholas N. Glenn", 37, True),
    ],
    ("House", "03", "Democratic"): [
        ("Yassamin Ansari", 19087, False), ("Raquel Terán", 19045, False),
        ("Duane M. Wooten", 4687, False),
    ],
    ("House", "03", "Green"): [("Alan Aversa", 29, False)],
    ("House", "04", "Republican"): [
        ("Kelly Cooper", 18902, False), ("Jerome Davison", 10664, False),
        ("Dave Giles", 13575, False), ("Zuhdi Jasser", 15929, False),
    ],
    ("House", "04", "Democratic"): [("Greg Stanton", 49178, False)],
    ("House", "04", "Green"): [("Vincent Beck-Jones", 31, True)],
    ("House", "05", "Republican"): [("Andy Biggs", 91820, False)],
    ("House", "05", "Democratic"): [("Katrina Schaffner", 42396, False)],
    ("House", "06", "Republican"): [
        ("Juan Ciscomani", 59021, False), ("Kathleen Winn", 40625, False),
    ],
    ("House", "06", "Democratic"): [("Kirsten Engel", 78178, False)],
    ("House", "06", "Green"): [("Athena Eastwood", 26, True)],
    ("House", "07", "Republican"): [("Daniel Francis Butierez Sr.", 24425, False)],
    ("House", "07", "Democratic"): [("Raúl M. Grijalva", 55133, False)],
    ("House", "08", "Republican"): [
        ("Patrick \"Pat\" Briody", 2336, False), ("Trent Franks", 16714, False),
        ("Abraham \"Abe\" Hamadeh", 30686, False), ("Anthony Kern", 4922, False),
        ("Blake Masters", 26422, False), ("Ben Toma", 21549, False),
        ("Isiah Gallegos", 35, True),
    ],
    ("House", "08", "Democratic"): [("Gregory Whitten", 47406, False)],
    ("House", "09", "Republican"): [("Paul Gosar", 89308, False)],
    ("House", "09", "Democratic"): [("Quacy Smith", 33784, False)],
}

AZ_2026_RESULTS = {
    ("House", "01", "Republican"): [
        ("Joseph Chaplik", 31347, False), ('Thomas "Jay" Feely IV', 43709, False),
        ("John Trobough", 12718, False),
    ],
    ("House", "01", "Democratic"): [
        ("Marlene Galán-Woods", 25267, False), ("Rick McCartney", 6248, False),
        ("Amish Shah", 29002, False), ("Jonathan Treble", 13006, False),
    ],
    ("House", "01", "Libertarian"): [("Monica Alponte", 289, False)],
    ("House", "02", "Republican"): [("Eli Crane", 89205, False)],
    ("House", "02", "Democratic"): [("Jonathan Nez", 65118, False)],
    ("House", "02", "Libertarian"): [
        ("Curtis Goodwin", 318, False), ("Alex Flores", 10, True),
    ],
    ("House", "03", "Republican"): [("Nicholas N Glenn", 437, True)],
    ("House", "03", "Democratic"): [("Yassamin Ansari", 37553, False)],
    ("House", "03", "Green"): [("David Redkey", 5, True)],
    ("House", "03", "No Labels"): [("Alan Aversa", 571, False)],
    ("House", "04", "Republican"): [("Zuhdi Jasser", 39431, False)],
    ("House", "04", "Democratic"): [
        ("Kai Newkirk", 21544, False), ("Greg Stanton", 35551, False),
    ],
    ("House", "04", "No Labels"): [
        ("Tisha Benoit", 981, False), ("John Fillmore", 519, False),
    ],
    ("House", "05", "Republican"): [
        ("Daniel Keenan", 36854, False), ("Mark Lamb", 52352, False),
    ],
    ("House", "05", "Democratic"): [
        ("Brian Hualde", 6171, False), ("Chris James", 9703, False),
        ("Elizabeth Lee", 30857, False),
    ],
    ("House", "06", "Republican"): [("Juan Ciscomani", 76481, False)],
    ("House", "06", "Democratic"): [("JoAnna Mendoza", 78310, False)],
    ("House", "06", "Libertarian"): [("Jereme Lance Peters", 277, False)],
    ("House", "06", "Green"): [("Gary Swing", 29, True)],
    ("House", "07", "Republican"): [
        ("Daniel Francis Butierez Sr.", 21934, False),
    ],
    ("House", "07", "Democratic"): [("Adelita Grijalva", 59304, False)],
    ("House", "08", "Republican"): [
        ('Abraham "Abe" Hamadeh', 69182, False),
    ],
    ("House", "08", "Democratic"): [
        ("Bernadette Greene-Placentia", 31312, False),
        ('Raymond "Ray" Keeler', 16324, False),
    ],
    ("House", "09", "Republican"): [("Paul Gosar", 79336, False)],
    ("House", "09", "Democratic"): [
        ('Danielle "Dani" Sterbinsky', 35700, False),
    ],
}

UT_RESULTS = {
    "2024": {
        ("Senate", "S", "Republican"): [
            ("JOHN CURTIS", 206094), ("JASON J. WALTON", 25604),
            ("BRAD WILSON", 53134), ("TRENT STAGGS", 138143),
        ],
        ("House", "01", "Republican"): [
            ("BLAKE D. MOORE", 72702), ("PAUL MILLER", 29640),
        ],
        ("House", "02", "Republican"): [
            ("COLBY C. JENKINS", 53534), ("CELESTE MALOY", 53748),
        ],
        ("House", "03", "Republican"): [
            ("JR BIRD", 17207), ("MIKE KENNEDY", 43618),
            ("CASE LAWRENCE", 24884), ("STEWART PEAY", 15954),
            ("JOHN \"FRUGAL\" DOUGALL", 10800),
        ],
    },
    "2026": {
        ("House", "01", "Democratic"): [
            ("BEN MCADAMS", 29737), ("NATE BLOUIN", 15771),
            ("LIBAN MOHAMED", 9542), ("MICHAEL FARRELL", 2245),
        ],
        ("House", "02", "Republican"): [
            ("BLAKE D. MOORE", 52673), ("KARIANNE LISONBEE", 40271),
        ],
        ("House", "03", "Republican"): [
            ("CELESTE MALOY", 67135), ("PHIL LYMAN", 35034),
        ],
    },
}


def parse_reviewed_totals(source: dict, results: dict, locator: str) -> list[dict]:
    output = []
    for (chamber, district, party), candidates in results.items():
        for candidate_name, votes, *write_in in candidates:
            output.append(_result_row(
                source,
                chamber=chamber,
                district=district,
                primary_party=party,
                candidate_name=candidate_name,
                votes=votes,
                write_in=bool(write_in and write_in[0]),
                locator=locator,
            ))
    return output


def parse_arizona_2026(source: dict) -> list[dict]:
    output = []
    for page, districts in ((1, {"01"}), (2, {"02", "03", "04", "05", "06", "07"}),
                            (3, {"08", "09"})):
        subset = {
            key: candidates
            for key, candidates in AZ_2026_RESULTS.items()
            if key[1] in districts
        }
        output.extend(parse_reviewed_totals(source, subset, f"page {page}"))
    if len(output) != 37 or len({row["contest_id"] for row in output}) != 25:
        raise ValueError("Arizona 2026 federal canvass extraction is incomplete")
    return output


def parse_nevada_clark_2026(path: Path, source: dict) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    starts = [
        match.start()
        for match in re.finditer(r'<div class="turnout-container no-break">', text)
    ]
    starts.append(len(text))
    contests = {}
    for start, end in zip(starts, starts[1:]):
        block = text[start:end]
        header = re.search(
            r'<div class="turnout-header">\s*<strong>([^<]+)</strong>', block,
        )
        if header is None:
            continue
        match = re.fullmatch(
            r"REPRESENTATIVE IN CONGRESS DISTRICT ([13]) - (DEM|REP)",
            header[1].strip(),
        )
        if match is None:
            continue
        candidates = [
            (html.unescape(name), int(votes.replace(",", "")))
            for name, votes in re.findall(
                r'title="([^"]+?) - ([\d,]+) vote\(s\)', block,
            )
        ]
        contests[(match[1].zfill(2), match[2])] = candidates
    expected = {
        ("01", "REP"): {
            "Arnold, Marie Encar", "Blockey, Jim", "Boris, Michael",
            "Buck, Carrie Ann", 'Saga, Rick "indicted"',
        },
        ("01", "DEM"): {
            "Cornejo, Gabriel", "Hoover, Joy", "Paniagua, Luis", "Titus, Dina",
        },
        ("03", "REP"): {
            "Anderson, Tera", "Gunter, Jeff", "Nagy, Aury", "O'Donnell, Marty",
        },
        ("03", "DEM"): {
            "Lally, James A.", "Lee, Susie", "Robinson, Terrill", "West, Brandon",
        },
    }
    if set(contests) != set(expected):
        raise ValueError("Clark federal contest set changed")
    output = []
    for (district, code), candidates in sorted(contests.items()):
        if {name for name, _ in candidates} != expected[(district, code)]:
            raise ValueError(f"Clark candidate set changed: {district} {code}")
        party = {"DEM": "Democratic", "REP": "Republican"}[code]
        for index, (name, votes) in enumerate(candidates):
            output.append(_result_row(
                source,
                chamber="House", district=district, primary_party=party,
                candidate_name=name, candidate_id=f"{district}:{code}:{index}",
                party=party, votes=votes, locator=f"HTML contest block:{district}:{code}",
            ))
    if len(output) != 17 or len({row["contest_id"] for row in output}) != 4:
        raise ValueError("Clark single-county congressional coverage is incomplete")
    return output


def _manifest_row(source: dict, path: Path, rows: list[dict], **overrides: str) -> dict:
    defaults = {
        "artifact_kind": "official_results",
        "authority": {
            "AK": "Alaska Division of Elections",
            "AZ": "Arizona Secretary of State",
            "NV": "Nevada Secretary of State",
            "UT": "Utah Lieutenant Governor Elections Office",
        }[source["state"]],
        "acquisition_url": source.get("acquisition_url", source["url"]),
        "acquisition_status": "captured",
        "verification_status": "verified_official",
        "certification_status": "official",
        "provisional_status": "final_certified_totals",
        "coverage": "all recovered federal candidate rows in the registered source",
        "source_locators": "source row/page locators recorded per result row",
        "notes": "",
    }
    defaults.update(overrides)
    return {
        "source_id": source["source_id"],
        "state_code": source["state"],
        "election_date": source["date"],
        "stage": "primary",
        "artifact_kind": defaults["artifact_kind"],
        "authority": defaults["authority"],
        "publication_url": source["publication"],
        "source_url": source["url"],
        "acquisition_url": defaults["acquisition_url"],
        "raw_filename": source["filename"],
        "sha256": _sha256(path),
        "acquisition_status": defaults["acquisition_status"],
        "verification_status": defaults["verification_status"],
        "certification_status": defaults["certification_status"],
        "provisional_status": defaults["provisional_status"],
        "candidate_rows": len(rows),
        "contests": len({row["contest_id"] for row in rows}),
        "coverage": defaults["coverage"],
        "source_locators": defaults["source_locators"],
        "notes": defaults["notes"],
    }


def collect_western_primaries() -> dict:
    raw_root = RAW_DIR / RAW_SUBDIR
    output_root = ANALYSIS_DATA_DIR / "congressional"
    manifest_root = output_root / MANIFEST_SUBDIR
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)

    results = []
    manifest = []
    for source in AK_SOURCES:
        path = raw_root / source["filename"]
        rows = parse_alaska(path, source)
        results.extend(rows)
        manifest.append(_manifest_row(
            source, path, rows,
            artifact_kind="official_precinct_csv",
            coverage="all federal contests and candidates; actual zero precinct totals retained",
        ))

    az_path = raw_root / AZ_2024_SOURCE["filename"]
    az_rows = parse_reviewed_totals(AZ_2024_SOURCE, AZ_2024_RESULTS, "pages 1-3")
    results.extend(az_rows)
    manifest.append(_manifest_row(
        AZ_2024_SOURCE, az_path, az_rows,
        artifact_kind="official_statewide_canvass_pdf",
        acquisition_url=AZ_2024_SOURCE["acquisition_url"],
        coverage="all U.S. Senate and U.S. House primary ballot options",
        notes="Archived capture of the exact official PDF; totals were visually reviewed by page.",
    ))
    az_2026_path = raw_root / AZ_2026_SOURCE["filename"]
    az_2026_rows = parse_arizona_2026(AZ_2026_SOURCE)
    results.extend(az_2026_rows)
    manifest.append(_manifest_row(
        AZ_2026_SOURCE, az_2026_path, az_2026_rows,
        artifact_kind="official_statewide_canvass_pdf",
        acquisition_url=AZ_2026_SOURCE["acquisition_url"],
        coverage="all U.S. House districts, primary parties, named write-ins, and candidates",
        source_locators="official canvass pages 1-3",
        notes=(
            "Totals were transcribed from rendered certified-canvass pages and checked "
            "against coordinate-aware Vision OCR plus the official candidate/write-in lists."
        ),
    ))
    nv_2026_path = raw_root / NV_2026_ROSTER_SOURCE["filename"]
    manifest.append(_manifest_row(
        NV_2026_ROSTER_SOURCE, nv_2026_path, [],
        artifact_kind="official_candidate_roster_pdf",
        authority="Nevada Secretary of State",
        acquisition_url=NV_2026_ROSTER_SOURCE["acquisition_url"],
        verification_status="verified_official_roster",
        certification_status="filing_roster",
        provisional_status="not_a_vote_result",
        coverage="statewide 2026 candidate/contest roster; not used as vote totals",
        source_locators="PDF pages and extracted text lines",
        notes="Political affiliation is preserved only as the official ballot/filing category.",
    ))
    clark_path = raw_root / NV_2026_CLARK_SOURCE["filename"]
    clark_rows = parse_nevada_clark_2026(clark_path, NV_2026_CLARK_SOURCE)
    manifest.append(_manifest_row(
        NV_2026_CLARK_SOURCE, clark_path, clark_rows,
        artifact_kind="official_county_results_html",
        authority="Clark County Election Department",
        verification_status="verified_official",
        certification_status="final_official",
        provisional_status="complete_single_county_districts",
        coverage="complete U.S. House Districts 1 and 3 Democratic/Republican primaries",
        source_locators="server-rendered contest blocks",
        notes=(
            "Districts 1 and 3 are filed/administered by Clark County in the official roster; "
            "District 4 totals remain withheld pending all county portions."
        ),
    ))
    clark_cvr_path = raw_root / NV_2026_CLARK_CVR_SOURCE["filename"]
    manifest.append(_manifest_row(
        NV_2026_CLARK_CVR_SOURCE, clark_cvr_path, [],
        artifact_kind="official_cast_vote_record_zip",
        authority="Clark County Election Department",
        verification_status="verified_official_supporting_source",
        certification_status="final_official",
        provisional_status="not_used_without_enr_reconciliation",
        coverage="ballot-level Clark County final CVR for all 2026 primary contests",
        source_locators="federal candidate columns in contained CSV",
        notes="Privacy-marked CVR cells are reconciled to the official server-rendered totals.",
    ))
    for source in NV_2024_ROSTER_SOURCES:
        path = raw_root / source["filename"]
        manifest.append(_manifest_row(
            source, path, [],
            artifact_kind="official_candidate_roster_pdf",
            authority="Clark County Election Department",
            verification_status="verified_official_roster",
            certification_status="ballot_roster",
            provisional_status="not_a_vote_result",
            coverage="2024 federal primary and no-primary contest accounting",
            source_locators="PDF pages and extracted text lines",
            notes="Used only to define expected contests and official no-primary nominations.",
        ))
    for source in NV_SUPPORTING_SUMMARY_SOURCES:
        path = raw_root / source["filename"]
        manifest.append(_manifest_row(
            source, path, [],
            artifact_kind=(
                "official_county_canvass_pdf"
                if any(token in source["source_id"] for token in ("sov", "canvass", "abstract"))
                else "official_county_final_summary_pdf"
            ),
            authority=(
                "Humboldt County Clerk"
                if "humboldt" in source["source_id"]
                else "Eureka County Clerk"
                if "eureka" in source["source_id"]
                else "Churchill County Clerk-Treasurer"
                if "churchill" in source["source_id"]
                else "Lyon County Clerk-Treasurer"
                if "lyon" in source["source_id"]
                else "Nye County Clerk"
                if "nye" in source["source_id"]
                else "White Pine County Clerk"
                if "white-pine" in source["source_id"]
                else "Storey County Clerk-Treasurer"
            ),
            verification_status="verified_official_supporting_source",
            certification_status="county_final",
            provisional_status="not_used_for_partial_statewide_totals",
            coverage=source["coverage"],
            source_locators="federal contest pages in the county final summary",
            notes=source["notes"],
        ))

    for source in UT_SOURCES:
        year = source["date"][:4]
        if source["source_id"].endswith("salt-lake-official-summary"):
            subset = {key: value for key, value in UT_RESULTS[year].items() if key[1] == "01"}
            locator = "page 1"
        elif year == "2026":
            subset = {key: value for key, value in UT_RESULTS[year].items() if key[1] != "01"}
            locator = "pages 3-4"
        else:
            subset = UT_RESULTS[year]
            locator = "pages 3-5"
        rows = parse_reviewed_totals(source, subset, locator)
        results.extend(rows)
        path = raw_root / source["filename"]
        manifest.append(_manifest_row(
            source, path, rows,
            artifact_kind=(
                "official_county_summary_pdf"
                if "salt-lake" in source["source_id"]
                else "official_statewide_canvass_pdf"
            ),
            coverage=(
                "Salt Lake County single-county U.S. House District 1 Democratic primary"
                if "salt-lake" in source["source_id"]
                else "all numeric multi-county federal primary contests in the canvass"
            ),
            notes=(
                "The statewide certification labels U.S. House District 1 a single-county "
                "race, certified at county level; this final Salt Lake summary is therefore "
                "the complete district result."
                if "salt-lake" in source["source_id"] else ""
            ),
        ))

    results.sort(key=lambda row: (
        row["state_code"], row["cycle"], row["chamber"], row["district"],
        row["primary_party"], row["candidate_name"],
    ))
    keys = [(row["contest_id"], row["candidate_source_id"]) for row in results]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate western primary candidate identity")
    if any(set(row) != set(FIELDS) for row in results):
        raise ValueError("Western primary output differs from canonical schema")

    coverage = []
    grouped = defaultdict(list)
    for row in results:
        grouped[(
            row["state_code"], row["cycle"], row["election_date"], row["stage"],
            row["chamber"], row["district"], row["primary_party"],
        )].append(row)
    for key, rows in sorted(grouped.items()):
        state, cycle, date, stage, chamber, district, party = key
        coverage.append({
            "state_code": state, "cycle": cycle, "election_date": date,
            "stage": stage, "chamber": chamber, "district": district,
            "primary_party": party,
            "coverage_status": "complete_certified_results",
            "candidate_rows": len(rows),
            "source_ids": "|".join(sorted({row["source_id"] for row in rows})),
            "notes": (
                "Nonpartisan top-four ballot; primary_party intentionally blank."
                if state == "AK" else ""
            ),
        })
        if (
            state == "NV" and cycle == "2026" and chamber == "House"
            and district in {"01", "03"}
        ):
            coverage[-1]["coverage_status"] = (
                "official_results_partial_missing_aggregate_write_in"
            )
            coverage[-1]["notes"] = (
                "Clark final ENR supplies all named candidate totals but no aggregate "
                "Unresolved Write-In ballot option. No zero is inferred."
            )
        if state == "UT" and cycle == "2026" and district == "01":
            coverage[-1]["notes"] = (
                "Utah's statewide certification explicitly identifies U.S. House District 1 "
                "as a single-county race certified at county level; Salt Lake County's final "
                "summary covers the entire primary contest."
            )
    coverage.extend([
        {
            "state_code": "AK", "cycle": "2024", "election_date": "2024-08-20",
            "stage": "primary", "chamber": "Senate", "district": "S",
            "primary_party": "", "coverage_status": "not_regularly_scheduled",
            "candidate_rows": 0, "source_ids": "ak-2024-primary-precinct",
            "notes": "No U.S. Senate contest appears in the official primary export.",
        },
        {
            "state_code": "AZ", "cycle": "2026", "election_date": "2026-07-21",
            "stage": "primary", "chamber": "Senate", "district": "S",
            "primary_party": "", "coverage_status": "not_regularly_scheduled",
            "candidate_rows": 0, "source_ids": "az-2026-primary-official-canvass",
            "notes": "No U.S. Senate contest appears in the official statewide canvass.",
        },
        {
            "state_code": "NV", "cycle": "2026", "election_date": "2026-06-09",
            "stage": "primary", "chamber": "Senate", "district": "S",
            "primary_party": "", "coverage_status": "not_regularly_scheduled",
            "candidate_rows": 0, "source_ids": "",
            "notes": "No U.S. Senate seat was scheduled in the 2026 cycle.",
        },
        {
            "state_code": "UT", "cycle": "2026", "election_date": "2026-06-23",
            "stage": "primary", "chamber": "Senate", "district": "S",
            "primary_party": "", "coverage_status": "not_regularly_scheduled",
            "candidate_rows": 0, "source_ids": "ut-2026-primary-statewide-certification",
            "notes": "No U.S. Senate contest appears in the certified statewide canvass.",
        },
    ])
    for cycle, date, chamber, district, party, candidate_rows in NV_OPEN_CONTESTS:
        coverage.append({
            "state_code": "NV", "cycle": cycle, "election_date": date,
            "stage": "primary", "chamber": chamber, "district": district,
            "primary_party": party,
            "coverage_status": "open_official_results_unrecovered",
            "candidate_rows": candidate_rows,
            "source_ids": (
                (
                    "nv-2024-primary-contests-candidates|"
                    "nv-2024-humboldt-final-summary"
                    if cycle == "2024" and district == "02"
                    else "nv-2024-primary-contests-candidates"
                )
                if cycle == "2024"
                else (
                    "nv-2026-primary-contests-candidates|"
                    "nv-2026-storey-final-summary"
                )
            ),
            "notes": (
                "Expected ballot-option count includes aggregate Unresolved Write-In."
                if cycle == "2026" else
                "Expected count includes None of These Candidates where printed on the ballot."
            ),
        })
    for cycle, date, chamber, district, party in NV_NO_PRIMARY_CONTESTS:
        coverage.append({
            "state_code": "NV", "cycle": cycle, "election_date": date,
            "stage": "primary", "chamber": chamber, "district": district,
            "primary_party": party,
            "coverage_status": "official_no_primary_contest",
            "candidate_rows": 0,
            "source_ids": (
                "nv-2024-primary-contests-not-on-ballot"
                if cycle == "2024" else "nv-2026-primary-contests-candidates"
            ),
            "notes": "Official roster marks the nomination as not appearing in the primary.",
        })

    gaps = [
        {
            "gap_id": "nv-2024-federal-primary-results",
            "state_code": "NV", "cycle": "2024", "stage": "primary",
            "chamber": "House|Senate", "coverage_status": "official_results_unrecovered",
            "recovered_scope": (
                "official rosters identify 8 numeric contests and 38 ballot options"
            ),
            "missing_scope": (
                "certified statewide aggregation for Senate DEM/REP and House "
                "01 REP, 02 REP, 03 DEM/REP, 04 DEM/REP"
            ),
            "blocker": "state result host returns an Imperva challenge to non-browser acquisition",
            "next_authoritative_step": (
                "aggregate all 17 county final canvasses; no partial county sample may publish"
            ),
            "source_urls": (
                "https://silverstateelection.nv.gov/|"
                "https://www.clarkcountynv.gov/government/departments/elections/24p-info"
            ),
        },
        {
            "gap_id": "nv-2026-federal-primary-results",
            "state_code": "NV", "cycle": "2026", "stage": "primary",
            "chamber": "House", "coverage_status": "official_county_results_partial",
            "recovered_scope": (
                "Clark County final ENR supplies named-candidate totals for House 01 DEM/REP "
                "and House 03 DEM/REP; statewide roster fixes remaining candidate sets"
            ),
            "missing_scope": (
                "aggregate write-in ballot options for Clark House 01/03 party contests, "
                "plus all county portions for House 02 DEM/REP and House 04 REP"
            ),
            "blocker": "statewide host remains shielded and remaining county finals are incomplete",
            "next_authoritative_step": (
                "aggregate all 17 county final canvasses; no partial county sample may publish"
            ),
            "source_urls": (
                "https://silverstateelection.nv.gov/|"
                "https://www.nvsos.gov/home/showpublisheddocument/18368/639135026079800000"
            ),
        },
    ]
    attempts = [
        {
            "attempt_id": "ak-2026-legacy-path", "attempted_on": "2026-09-22",
            "state_code": "AK", "cycle": "2026",
            "source_url": "https://www.elections.alaska.gov/results/26PRIM/",
            "method": "direct_http", "outcome": "superseded_by_official_enr26_path",
            "raw_evidence": "", "notes": "Used the official detail page's linked enr26 CSV instead.",
        },
        {
            "attempt_id": "az-origin-canvass-downloads", "attempted_on": "2026-09-22",
            "state_code": "AZ", "cycle": "2024|2026",
            "source_url": "https://azsos.gov/;https://apps.azsos.gov/",
            "method": "direct_http", "outcome": "403_then_archived_official_capture",
            "raw_evidence": "az/2024 and az/2026 official PDF snapshots",
            "notes": "Did not loop on blocked origins; used exact archived official URLs.",
        },
        {
            "attempt_id": "nv-state-results", "attempted_on": "2026-09-22",
            "state_code": "NV", "cycle": "2024|2026",
            "source_url": "https://silverstateelection.nv.gov/",
            "method": "direct_http_archive_indexes_and_legacy_app",
            "outcome": "imperva_challenge_no_result_payload",
            "raw_evidence": "nv/2024 and nv/2026 official roster PDFs",
            "notes": (
                "Results.NV.gov redirects to the shielded host. Official county final-summary "
                "format was verified, but partial county totals remain excluded."
            ),
        },
    ]

    write_csv(output_root / RESULT_FILENAME, results, FIELDS)
    write_csv(output_root / PARTIAL_RESULT_FILENAME, clark_rows, FIELDS)
    write_csv(manifest_root / "source_manifest.csv", manifest, SOURCE_MANIFEST_FIELDS)
    write_csv(manifest_root / "attempt_ledger.csv", attempts, ATTEMPT_FIELDS)
    write_csv(manifest_root / "contest_coverage.csv", coverage, COVERAGE_FIELDS)
    write_csv(manifest_root / "unresolved_gaps.csv", gaps, GAP_FIELDS)
    county_inventory = []
    for cycle in ("2024", "2026"):
        for county in NV_COUNTIES:
            source = NV_CAPTURED_COUNTY_SOURCES.get((cycle, county))
            failure = NV_ROUTE_FAILURES.get((cycle, county))
            county_inventory.append({
                "cycle": cycle,
                "county": county,
                "status": (
                    "captured_final" if source else
                    "route_exhausted_no_artifact" if failure else "open"
                ),
                "source_id": source["source_id"] if source else "",
                "raw_filename": source["raw_filename"] if source else "",
                "source_url": (
                    source["source_url"] if source else
                    failure["source_url"] if failure else ""
                ),
                "notes": (
                    "Supporting final county source captured; statewide totals remain "
                    "suppressed until all 17 county finals for the cycle are present."
                    if source else failure["notes"] if failure else
                    "Required for atomic statewide Senate and district-part aggregation."
                ),
            })
    write_csv(
        manifest_root / "nv_county_source_inventory.csv",
        county_inventory, NV_COUNTY_INVENTORY_FIELDS,
    )
    return {
        "candidate_rows": len(results),
        "contests": len({row["contest_id"] for row in results}),
        "sources": len(manifest),
        "remaining_gaps": len(gaps),
        "nv_county_slots": len(county_inventory),
        "partial_candidate_rows": len(clark_rows),
        "partial_contests": len({row["contest_id"] for row in clark_rows}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(collect_western_primaries())


if __name__ == "__main__":
    main()
