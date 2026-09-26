"""A real MCP SDK client can call exactly five read-only fictional tools."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class McpTransportTests(unittest.TestCase):
    def test_sdk_connects_with_only_demo_bearer(self):
        code = '''
import asyncio, json, os, tempfile
from pathlib import Path
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from demo.seed import build_demo_database

async def check():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'fictional.db'
        build_demo_database(path)
        os.environ['DEMO_DB_PATH'] = str(path)
        from demo.app import app
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         headers={'Authorization': 'Bearer demo-readonly'},
                                         base_url='http://testserver', timeout=20) as client:
                async with streamable_http_client('http://testserver/mcp', http_client=client,
                                                  terminate_on_close=False) as (reader, writer, _):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        assert {t.name for t in tools.tools} == {
                            'search_messages', 'search_resources', 'get_resource',
                            'list_topics', 'top_resources'
                        }
                        result = await session.call_tool('search_messages', {'query': 'аэролит'})
                        assert not result.isError
                        content = json.loads(result.content[0].text)
                        assert content and content[0]['telegram_url'] is None
asyncio.run(check())
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                                env={k: v for k, v in os.environ.items() if k != "DEMO_DB_PATH"},
                                capture_output=True, timeout=40)
        self.assertEqual(result.returncode, 0, "actual MCP SDK handshake and query must work")


if __name__ == "__main__":
    unittest.main()
