"""Fictional corpus is created from code, never imported from any real group."""
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SyntheticCorpusTests(unittest.TestCase):
    def test_corpus_is_reproducible_and_fts_complete(self):
        self.assertTrue((ROOT / "demo/seed.py").is_file(), "missing synthetic seed generator")
        from demo.seed import build_demo_database

        with tempfile.TemporaryDirectory() as directory:
            first, second = (Path(directory) / name for name in ("first.db", "second.db"))
            build_demo_database(first)
            build_demo_database(second)
            self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), hashlib.sha256(second.read_bytes()).digest())
            con = sqlite3.connect(f"file:{first}?mode=ro", uri=True)
            self.assertEqual(con.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM messages").fetchone()[0], 100)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM messages_fts_docsize").fetchone()[0], 100)
            self.assertEqual(con.execute("SELECT COUNT(DISTINCT key) FROM resources").fetchone()[0], 20)
            self.assertGreaterEqual(con.execute("SELECT COUNT(*) FROM messages_fts WHERE messages_fts MATCH 'аэролит'").fetchone()[0], 1)
            authors = {r[0] for r in con.execute("SELECT DISTINCT sender_name FROM messages")}
            self.assertEqual(authors, {"Ника Искра", "Лев Маяк", "Мира Ветер", "Оля Луч", "Ян Орбит"})
            for (urls,) in con.execute("SELECT urls FROM messages"):
                self.assertTrue(all(url.startswith("https://") and ".example/" in url for url in json.loads(urls)))
            con.close()

    def test_fictional_resources_have_distinct_human_readable_cards(self):
        from demo.seed import build_demo_database

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fictional.db"
            build_demo_database(path)
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            cards = con.execute("SELECT display_name, description FROM resources ORDER BY key").fetchall()
            con.close()
            self.assertGreaterEqual(sum(not name.startswith("Аэролит ") for name, _ in cards), 15)
            self.assertTrue(all(description and "Вымышленный справочник" not in description for _, description in cards))

    def test_seed_never_overwrites_an_existing_database(self):
        self.assertTrue((ROOT / "demo/seed.py").is_file(), "missing synthetic seed generator")
        from demo.seed import build_demo_database

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.db"
            path.write_bytes(b"existing data stays untouched")
            with self.assertRaises(FileExistsError):
                build_demo_database(path)
            self.assertEqual(path.read_bytes(), b"existing data stays untouched")


if __name__ == "__main__":
    unittest.main()
