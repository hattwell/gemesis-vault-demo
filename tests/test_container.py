"""Fail-closed Docker context and Render Free declaration checks."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContainerContractTests(unittest.TestCase):
    def test_container_uses_explicit_demo_only_multistage_build(self):
        docker = (ROOT / "Dockerfile").read_text("utf-8")
        self.assertIn(" AS frontend", docker)
        self.assertIn("COPY --from=frontend", docker)
        self.assertIn("--frozen-lockfile", docker)
        self.assertIn("USER 10001", docker)
        self.assertIn("demo.launch", docker)
        self.assertNotIn("COPY . ", docker)
        self.assertNotIn("ADD . ", docker)
        for forbidden in ("server.py", "sync.py", "fetch.py"):
            self.assertNotIn(f"COPY {forbidden}", docker)
        for forbidden in ("Telegram", "Codex", "master_key"):
            self.assertNotIn(forbidden, docker)

    def test_build_context_denylist_by_default(self):
        patterns = (ROOT / ".dockerignore").read_text("utf-8").splitlines()
        self.assertEqual(patterns[0], "**")
        for forbidden in ("!.env", "!media", "!backups", "!.git", "!*.db", "!*.session"):
            self.assertNotIn(forbidden, patterns)
        self.assertIn("!app/public/gemesislogo.jpg", patterns)
        self.assertIn("**/__pycache__/", patterns)
        self.assertIn("**/*.pyc", patterns)

    def test_render_only_has_one_free_web_service_without_secrets_or_storage(self):
        text = (ROOT / "render.yaml").read_text("utf-8")
        self.assertEqual(text.count("plan: free"), 1)
        self.assertEqual(text.count("type: web"), 1)
        for forbidden in ("disk:", "envVars:", "plan: starter", "plan: standard", "DATABASE_URL", "MASTER_KEY"):
            self.assertNotIn(forbidden, text)

    def test_minimal_pinned_runtime_only(self):
        deps = (ROOT / "requirements-demo.txt").read_text("utf-8").splitlines()
        self.assertGreaterEqual(len(deps), 3)
        self.assertTrue(all("==" in line for line in deps))
        self.assertTrue(any(line.startswith("mcp==") for line in deps))
        self.assertTrue(any(line.startswith("fastapi==") for line in deps))
        for forbidden in ("telethon", "openai", "python-dotenv", "torch", "llama"):
            self.assertFalse(any(forbidden in line.lower() for line in deps))


if __name__ == "__main__":
    unittest.main()
