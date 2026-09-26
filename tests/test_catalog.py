"""The demo graph and overview reuse the search model on fake, read-only data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from demo.seed import build_demo_database

ROOT = Path(__file__).resolve().parents[1]


class CatalogueTests(unittest.TestCase):
    def test_graph_and_digest_are_real_read_only_results(self):
        self.assertTrue((ROOT / "demo/catalog.py").is_file(), "missing read-only graph adapter")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.db"
            build_demo_database(path)
            before = hashlib.sha256(path.read_bytes()).digest()
            script = '''
import json
from demo.catalog import build_graph, build_digest
from common import DB_PATH
print(json.dumps({"graph": build_graph(DB_PATH), "digest": build_digest(DB_PATH)}, ensure_ascii=False))
'''
            result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                                    env=dict(os.environ, DEMO_DB_PATH=str(path)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, "read-only catalogue must build")
            data = json.loads(result.stdout)
            graph = data["graph"]
            resources = [node for node in graph["nodes"] if node.get("id", "").startswith("url:")]
            self.assertEqual(len(resources), 20)
            self.assertGreaterEqual(len([n for n in graph["nodes"] if n["group"] == "Тема"]), 3)
            self.assertTrue(any(edge["kind"] == "cooccur" for edge in graph["links"]))
            self.assertTrue(any(edge["kind"] == "shared" for edge in graph["links"]))
            self.assertTrue(all(item["url"].startswith("https://aerolith-") for item in resources))
            digest = data["digest"]
            self.assertEqual(set(digest), {"period", "stats", "topics", "new_resources", "active_resources"})
            self.assertEqual(digest["stats"]["messages"], 100)
            self.assertTrue(all(item["latest_mention"]["telegram_url"] is None for item in digest["active_resources"]))
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).digest())
            self.assertFalse(Path(str(path) + "-journal").exists())
            self.assertFalse(Path(str(path) + "-wal").exists())

    def test_five_tools_find_only_fictional_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fake.db"
            build_demo_database(path)
            code = '''
import json
from mcp_server import search_messages, search_resources, get_resource, list_topics, top_resources
from common import DB_PATH
key = 'url:https://aerolith-01.example/guide'
print(json.dumps({
 'messages': json.loads(search_messages('аэролит')),
 'resources': json.loads(search_resources('аэролит')),
 'resource': json.loads(get_resource(key)),
 'topics': json.loads(list_topics()),
 'top': json.loads(top_resources()),
 'unknown': json.loads(get_resource('url:https://missing.example/')),
}, ensure_ascii=False))
'''
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                                    env=dict(os.environ, DEMO_DB_PATH=str(path)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, "five read-only MCP functions must work")
            data = json.loads(result.stdout)
            self.assertTrue(data["messages"])
            self.assertTrue(all(item["telegram_url"] is None for item in data["messages"]))
            self.assertTrue(data["resources"])
            self.assertEqual(data["resource"]["key"], "url:https://aerolith-01.example/guide")
            self.assertGreaterEqual(len(data["topics"]), 3)
            self.assertTrue(data["top"])
            self.assertIn("error", data["unknown"])


if __name__ == "__main__":
    unittest.main()
