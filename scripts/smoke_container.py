"""Exercise a local container over HTTP and the actual MCP client transport."""
import asyncio
import json
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from scripts.check_public_artifact import FORBIDDEN


async def smoke(base: str) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=20) as client:
        page = await client.get("/")
        assert page.status_code == 200 and "Gemesis Vault — Demo" in page.text
        catalog = await client.get("/api/catalog")
        assert catalog.status_code == 200
        nodes = catalog.json()["nodes"]
        resources = [node for node in nodes if node["id"].startswith("url:")]
        assert len(resources) == 20
        for node in resources:
            assert ".example" in node["id"]
        assert not any(signature in catalog.text for signature in FORBIDDEN.values())
        chat = await client.post("/api/chat", json={"messages": [{"role": "user", "content": "Аэролит"}]})
        assert chat.status_code == 200 and chat.json().get("scripted") is True
        for route in ("/admin", "/api/session", "/api/admin/sync-status", "/docs", "/.env"):
            assert (await client.get(route)).status_code in (403, 404)
        assert (await client.post("/mcp", content=b"{}")).status_code == 401

    async with httpx.AsyncClient(headers={"Authorization": "Bearer demo-readonly"}, timeout=20) as client:
        async with streamable_http_client(base + "/mcp", http_client=client,
                                          terminate_on_close=False) as (reader, writer, _):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "search_messages", "search_resources", "get_resource", "list_topics", "top_resources",
                }
                calls = (
                    ("search_messages", {"query": "аэролит"}),
                    ("search_resources", {"query": "аэролит"}),
                    ("get_resource", {"key": "url:https://aerolith-01.example/guide"}),
                    ("list_topics", {}),
                    ("top_resources", {}),
                )
                for tool, arguments in calls:
                    result = await session.call_tool(tool, arguments)
                    assert not result.isError and result.content
                    payload = json.loads(result.content[0].text)
                    assert payload, f"empty fictional result: {tool}"
                    if tool == "get_resource":
                        assert payload["key"] == arguments["key"]
    print("Demo smoke: catalogue, scripted chat, denied owner routes and all five MCP tools OK.")


if __name__ == "__main__":
    try:
        asyncio.run(smoke(sys.argv[1].rstrip("/") if len(sys.argv) == 2 else "http://127.0.0.1:18765"))
    except Exception as exc:
        print(f"Container smoke failed ({type(exc).__name__}); no response contents logged.")
        raise SystemExit(1)
