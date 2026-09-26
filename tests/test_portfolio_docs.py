"""GitHub landing page must explain the real demo and link reviewed fictional screenshots."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ("overview", "catalog", "chat")


class PortfolioDocsTests(unittest.TestCase):
    def test_readme_explains_features_and_demo_limitations_in_both_languages(self):
        text = (ROOT / "README.md").read_text("utf-8")
        for item in ("SQLite", "FastAPI", "React", "FTS5", "Render Free", "MCP", "read-only",
                     "вымышлен", "fictional", "сценар", "scripted"):
            with self.subTest(item=item):
                self.assertTrue(item.casefold() in text.casefold(), f"missing capability: {item}")
        for shot in SHOTS:
            with self.subTest(shot=shot):
                self.assertTrue(f"screenshots/{shot}.png" in text, f"missing screenshot reference: {shot}")
                self.assertTrue((ROOT / f"screenshots/{shot}.png").is_file())
        self.assertNotIn("gemesis-vault" + ".duckdns.org", text)
        self.assertNotIn("screenshots/graph.png", text)
        self.assertNotIn("граф", text.casefold())
        self.assertIn("ИИ-чат", text)
        self.assertIn("AI chat", text)
        self.assertIn("https://gemesis-vault-demo.onrender.com/", text)
        self.assertIn("https://gemesis-vault-demo.onrender.com/mcp", text)

    def test_only_three_reviewed_pngs_and_no_embedded_image_metadata(self):
        self.assertEqual({path.name for path in (ROOT / "screenshots").iterdir()},
                         {f"{shot}.png" for shot in SHOTS})
        from scripts.check_public_artifact import valid_screenshot
        for shot in SHOTS:
            with self.subTest(shot=shot):
                data = (ROOT / f"screenshots/{shot}.png").read_bytes()
                self.assertTrue(valid_screenshot(data))
                self.assertFalse(valid_screenshot(data + b"unreviewed metadata"))
                damaged = bytearray(data)
                damaged[len(damaged) // 2] ^= 1
                self.assertFalse(valid_screenshot(bytes(damaged)))


if __name__ == "__main__":
    unittest.main()
