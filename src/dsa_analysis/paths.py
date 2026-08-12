from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


ROOT = project_root()
CONFIG_DIR = ROOT / "config"
MANUAL_DIR = ROOT / "data" / "manual"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "report"
DB_PATH = PROCESSED_DIR / "research.sqlite3"
