import sqlite3
import unittest

from dsa_analysis.database import initialize_database
from dsa_analysis.paths import DB_PATH


class DatabaseTests(unittest.TestCase):
    def test_database_loads_seed_tables(self) -> None:
        tables, rows = initialize_database()
        self.assertEqual(tables, 9)
        self.assertGreaterEqual(rows, 10)
        with sqlite3.connect(DB_PATH) as connection:
            count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        self.assertGreaterEqual(count, 10)


if __name__ == "__main__":
    unittest.main()
