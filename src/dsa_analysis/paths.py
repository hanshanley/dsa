from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


ROOT = project_root()
CONFIG_DIR = ROOT / "config"
MANUAL_DIR = ROOT / "data" / "manual"
ANALYSIS_DATA_DIR = ROOT / "data" / "analysis"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "figures"
REPORT_DIR = ROOT / "docs" / "reports"
DB_PATH = PROCESSED_DIR / "research.sqlite3"
