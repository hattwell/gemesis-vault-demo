"""The public code must never default to a production-like database or group."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DemoIsolationTests(unittest.TestCase):
    def test_url_normalization_uses_pure_demo_module(self):
        self.assertTrue((ROOT / "demo/url.py").is_file(), "missing pure URL normalizer")
        self.assertFalse((ROOT / "resource_names.py").exists(), "crawler module must not ship")
        from demo.url import normalize_url
        self.assertEqual(normalize_url("https://AEROLITH-01.example/guide?utm_source=fake"), "https://aerolith-01.example/guide")

    def test_database_import_fails_without_explicit_demo_path(self):
        env = dict(os.environ)
        env.pop("DEMO_DB_PATH", None)
        result = subprocess.run([sys.executable, "-c", "import common"], cwd=ROOT, env=env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((ROOT / "gemesis.db").exists())

    def test_mcp_reads_only_fictional_database(self):
        from demo.seed import build_demo_database

        source = (ROOT / "mcp_server.py").read_text("utf-8").casefold()
        self.assertFalse("закрытой телеграм-группы" in source, "private-group instruction must not ship")
        self.assertFalse("e:\\\\gemesis-graph" in source, "local production path must not ship")
        self.assertTrue("вымышлен" in source, "demo must identify the fictional corpus")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fictional.db"
            build_demo_database(path)
            env = dict(os.environ, DEMO_DB_PATH=str(path))
            code = '''
import sqlite3
from mcp_server import _db
con = _db()
try:
    con.execute("UPDATE resources SET title='wrong'")
except sqlite3.OperationalError:
    pass
else:
    raise AssertionError('MCP opened writable DB')
finally:
    con.close()
'''
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, "MCP must use a read-only DB handle")

    def test_read_only_queries_and_no_telegram_permalinks(self):
        from demo.seed import build_demo_database

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fictional.db"
            build_demo_database(path)
            env = dict(os.environ, DEMO_DB_PATH=str(path), GROUP="-1001234567890")
            code = '''
import sqlite3
from common import telegram_message_url
from tools_search import cmd_search, db
assert telegram_message_url(1, '-1001234567890') is None
assert telegram_message_url(1, 'fictional_group') is None
assert cmd_search('аэролит')
assert all(row['telegram_url'] is None for row in cmd_search('аэролит'))
con = db()
try:
    con.execute("INSERT INTO messages (id,date,sender_name,text,urls) VALUES (500,'x','x','x','[]')")
except sqlite3.OperationalError:
    pass
else:
    raise AssertionError('runtime DB is writable')
finally:
    con.close()
'''
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, "runtime must be read-only and link-free")
            self.assertFalse((ROOT / "gemesis.db").exists())


if __name__ == "__main__":
    unittest.main()
