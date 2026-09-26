"""Public HTTP surface contains no production/admin mutations."""
import os
from pathlib import Path
import tempfile
import unittest

from demo.seed import build_demo_database

ROOT = Path(__file__).resolve().parents[1]


class DemoApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = Path(cls.tmp.name) / "fixture.db"
        build_demo_database(cls.db)
        cls.old_path = os.environ.get("DEMO_DB_PATH")
        os.environ["DEMO_DB_PATH"] = str(cls.db)
        if not (ROOT / "demo/app.py").is_file():
            cls.client = None
            return
        from fastapi.testclient import TestClient
        from demo.app import app
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        if cls.client is not None:
            cls.client_context.__exit__(None, None, None)
        if cls.old_path is None:
            os.environ.pop("DEMO_DB_PATH", None)
        else:
            os.environ["DEMO_DB_PATH"] = cls.old_path
        cls.tmp.cleanup()

    def test_synthetic_catalogue_and_overview_are_browsable(self):
        self.assertIsNotNone(self.client, "missing demo-only HTTP app")
        catalog = self.client.get("/api/catalog")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(sum(n["id"].startswith("url:") for n in catalog.json()["nodes"]), 20)
        self.assertEqual(self.client.get("/api/digest").json()["stats"]["messages"], 100)
        self.assertTrue(self.client.get("/api/features").json()["chat"])
        self.assertTrue(self.client.get("/api/updates").json()[0]["changes"])
        details = self.client.get("/api/resource", params={"key": "url:https://aerolith-01.example/guide"})
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()["key"], "url:https://aerolith-01.example/guide")
        self.assertIn("sender", details.json()["mentions"][0])
        self.assertEqual(details.json()["mentions"][0]["media"], [])

    def test_chat_is_scripted_and_does_not_echo_untrusted_input(self):
        self.assertIsNotNone(self.client, "missing demo-only HTTP app")
        question = {"messages": [{"role": "user", "content": "Подскажи про аэролит"}]}
        response = self.client.post("/api/chat", json=question)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["scripted"])
        self.assertTrue(response.json()["refs"])
        self.assertIn("reply", response.json())
        untrusted = "<script>alert('unsafe')</script> неизвестный вопрос"
        response = self.client.post("/api/chat", json={"messages": [{"role": "user", "content": untrusted}]})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>", response.json()["reply"])
        self.assertEqual(response.json()["refs"], [])
        self.assertIn(self.client.post("/api/chat", json={"messages": [{"role": "user", "content": "x" * 1000}]}).status_code, (413, 422))

    def test_chat_limit_and_untrusted_host_are_enforced(self):
        self.assertIsNotNone(self.client, "missing demo-only HTTP app")
        from demo.app import app
        from rate_limit import RequestRateLimiter

        original = app.state.chat_limiter
        app.state.chat_limiter = RequestRateLimiter(limit=1, window_seconds=60)
        try:
            question = {"messages": [{"role": "user", "content": "аэролит"}]}
            self.assertEqual(self.client.post("/api/chat", json=question).status_code, 200)
            limited = self.client.post("/api/chat", json=question)
            self.assertEqual(limited.status_code, 429)
            self.assertTrue(limited.headers.get("Retry-After"))
            self.assertEqual(self.client.get("/api/catalog", headers={"Host": "untrusted.example"}).status_code, 400)
        finally:
            app.state.chat_limiter = original

    def test_owner_and_write_routes_do_not_exist_even_with_demo_bearer(self):
        self.assertIsNotNone(self.client, "missing demo-only HTTP app")
        headers = {"Authorization": "Bearer demo-readonly"}
        for method, path in (("GET", "/admin"), ("GET", "/api/admin/sync-status"),
                             ("POST", "/api/rebuild"), ("POST", "/api/session"),
                             ("POST", "/api/invites"), ("POST", "/api/chat/feedback"),
                             ("GET", "/docs"), ("GET", "/openapi.json")):
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path, headers=headers, json={})
                self.assertIn(response.status_code, (403, 404, 405))
        self.assertEqual(self.client.post("/mcp", json={}).status_code, 401)
        self.assertEqual(self.client.post("/mcp", json={}, headers={"Authorization": "Bearer wrong"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
