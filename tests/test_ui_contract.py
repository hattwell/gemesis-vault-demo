"""Public frontend must label simulation and never solicit a production owner key."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UiContractTests(unittest.TestCase):
    def test_existing_catalogue_ui_is_present_and_honest_about_fiction(self):
        app = ROOT / "app/src/App.tsx"
        self.assertTrue(app.is_file(), "missing the actual Gemesis catalogue UI")
        source = app.read_text("utf-8")
        self.assertIn("Демо · вымышленные данные", source)
        self.assertIn("Сценарный чат", source)
        self.assertNotIn("/api/chat/feedback", source)
        self.assertNotIn("Telegram", source)
        self.assertNotIn("Ассистент группы", source)
        self.assertNotIn("истории группы", source)
        self.assertNotIn("/admin", source)

    def test_html_title_identifies_public_fictional_demo(self):
        page = (ROOT / "app/index.html").read_text("utf-8")
        self.assertTrue("Gemesis Vault — Demo" in page, "title must identify demo")
        self.assertTrue("вымышлен" in page, "HTML must disclose fictional data")

    def test_demo_mcp_page_does_not_request_or_store_an_owner_key(self):
        page = ROOT / "app/src/McpPage.tsx"
        self.assertTrue(page.is_file(), "missing demo-only MCP instructions")
        source = page.read_text("utf-8")
        self.assertIn("demo-readonly", source)
        self.assertIn("вымышленные данные", source)
        self.assertNotIn("/api/access/check", source)
        self.assertNotIn("/api/session", source)
        self.assertNotIn("/admin", source)
        self.assertNotIn("GEMESIS_MCP_TOKEN", source)
        self.assertNotIn("закрытой", source.casefold())


if __name__ == "__main__":
    unittest.main()
