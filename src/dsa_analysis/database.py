import sqlite3

from .io import read_csv
from .paths import DB_PATH, MANUAL_DIR
from .schema import SCHEMAS


def initialize_database() -> tuple[int, int]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    table_count = 0
    row_count = 0
    with sqlite3.connect(DB_PATH) as connection:
        for table_name, schema in SCHEMAS.items():
            rows = read_csv(MANUAL_DIR / f"{table_name}.csv")
            fieldnames = list(rows[0]) if rows else _headers(MANUAL_DIR / f"{table_name}.csv")
            columns = ", ".join(f'"{name}" TEXT' for name in fieldnames)
            connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            connection.execute(f'CREATE TABLE "{table_name}" ({columns})')
            if rows:
                placeholders = ", ".join("?" for _ in fieldnames)
                quoted = ", ".join(f'"{name}"' for name in fieldnames)
                connection.executemany(
                    f'INSERT INTO "{table_name}" ({quoted}) VALUES ({placeholders})',
                    [[row.get(name, "") for name in fieldnames] for row in rows],
                )
                row_count += len(rows)
            connection.execute(
                f'CREATE UNIQUE INDEX "{table_name}_pk" '
                f'ON "{table_name}" ("{schema.primary_key}")'
            )
            table_count += 1
    return table_count, row_count


def _headers(path) -> list[str]:
    with path.open(encoding="utf-8") as handle:
        return handle.readline().rstrip("\n").split(",")
