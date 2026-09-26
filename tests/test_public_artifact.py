"""Fail-closed checks before any demo source can be published."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PublicArtifactTests(unittest.TestCase):
    def test_only_explicit_source_modules_are_selected(self):
        for name in ("common.py", "demo/url.py", "demo/seed.py", "tools_search.py", "mcp_server.py", "fts_index.py", "rate_limit.py"):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file(), f"missing allowlisted source: {name}")

    def test_private_state_is_not_in_demo(self):
        for name in (".env", "gemesis.db", "access.db", "gemesis.session", "server.py", "fetch.py", "sync.py", "media", "backups"):
            with self.subTest(name=name):
                self.assertFalse((ROOT / name).exists(), f"private file or directory: {name}")

    def test_checker_catches_secret_file_even_if_gitignore_would_hide_it(self):
        self.assertTrue((ROOT / "scripts/check_public_artifact.py").is_file(), "missing fail-closed checker")
        from scripts.check_public_artifact import check_repo
        fake_secret_file = ROOT / "gemesis.db"
        try:
            fake_secret_file.write_text("fictional-test-only", encoding="ascii")
            self.assertIn("gemesis.db", check_repo(ROOT))
        finally:
            fake_secret_file.unlink(missing_ok=True)

    def test_checker_catches_production_domain_in_source(self):
        self.assertTrue((ROOT / "scripts/check_public_artifact.py").is_file(), "missing fail-closed checker")
        from scripts.check_public_artifact import check_repo
        candidate = ROOT / "app/src/UNSAFE_TEST.ts"
        created_directory = not candidate.parent.exists()
        candidate.parent.mkdir(parents=True, exist_ok=True)
        try:
            candidate.write_text("gemesisvault" + ".duckdns.org", encoding="ascii")
            self.assertIn("app/src/UNSAFE_TEST.ts", check_repo(ROOT))
        finally:
            candidate.unlink(missing_ok=True)
            if created_directory:
                candidate.parent.rmdir()
                candidate.parent.parent.rmdir()

    def test_commit_uses_public_noreply_identity(self):
        email = subprocess.check_output(["git", "log", "-1", "--format=%ae"], cwd=ROOT, text=True).strip()
        self.assertTrue(email.endswith("@users.noreply.github.com"), "commit must not publish local machine identity")

    def test_demo_has_no_private_repository_remote(self):
        remotes = subprocess.check_output(["git", "remote"], cwd=ROOT, text=True)
        self.assertEqual(remotes.strip(), "")


if __name__ == "__main__":
    unittest.main()
