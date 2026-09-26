"""Read-only MCP tools over a fully fictional Gemesis demonstration corpus."""
import json
import sqlite3

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from common import DB_PATH, collect_resources, resource_display_name
from tools_search import cmd_resource, cmd_resources, cmd_search, display_name_column

mcp = FastMCP(
    "gemesis-demo",
    instructions="Вымышленная демонстрационная база Gemesis: сообщения и ресурсы "
    "не относятся к реальным людям или закрытым группам. Пять инструментов только для чтения.",
    stateless_http=True,  # простые HTTP-запросы без сессий — легче подключаться
    # Dedicated demo adapter limits hosts, Bearer scope and call rates; no owner route exists.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


@mcp.tool()
def search_messages(query: str) -> str:
    """Полнотекстовый поиск по вымышленным сообщениям: до 15 датированных цитат."""
    return json.dumps(cmd_search(query), ensure_ascii=False, indent=1)


@mcp.tool()
def search_resources(
    query: str = "",
    topic: str = "",
    kind: str = "",
    facet: str = "",
) -> str:
    """Поиск ресурсов по тексту и строгим фильтрам topic, kind и facet."""
    return json.dumps(
        cmd_resources(query, topic=topic, kind=kind, facet=facet),
        ensure_ascii=False,
        indent=1,
    )


@mcp.tool()
def get_resource(key: str) -> str:
    """Детали вымышленного ресурса по key: URL .example, описание и цитаты."""
    return json.dumps(cmd_resource(key), ensure_ascii=False, indent=1)


@mcp.tool()
def list_topics() -> str:
    """Список тем базы с количеством ресурсов в каждой."""
    con = _db()
    from collections import Counter
    c: Counter = Counter()
    for (t,) in con.execute(
        "SELECT topics FROM resources "
        "WHERE topics IS NOT NULL AND COALESCE(useless, 0)=0"
    ):
        for topic in json.loads(t):
            c[topic] += 1
    con.close()
    return json.dumps(dict(c.most_common()), ensure_ascii=False, indent=1)


@mcp.tool()
def top_resources(
    topic: str = "",
    kind: str = "",
    facet: str = "",
    limit: int = 15,
) -> str:
    """Самые обсуждаемые ресурсы с опциональными фильтрами topic, kind и facet."""
    con = _db()
    resources, _, _ = collect_resources(con)
    metadata = {
        row["key"]: row
        for row in con.execute(
            "SELECT key, description, web_title, web_desc, topics, facets, kind, folder, "
            f"{display_name_column(con)} FROM resources "
            "WHERE COALESCE(useless, 0)=0"
        ).fetchall()
    }
    items = []
    for key, resource in resources.items():
        meta = metadata.get(key)
        if meta is None:
            continue
        topics = json.loads(meta["topics"] or "[]")
        facets = json.loads(meta["facets"] or "[]")
        resource_kind = meta["kind"] or meta["folder"]
        if topic and topic.casefold() not in {value.casefold() for value in topics}:
            continue
        if kind and kind.casefold() != resource_kind.casefold():
            continue
        if facet and facet.casefold() not in {value.casefold() for value in facets}:
            continue
        items.append({
            "key": key,
            "title": resource_display_name(meta, resource),
            "url": resource["url"],
            "description": meta["description"] or meta["web_desc"],
            "kind": resource_kind,
            "topics": topics,
            "facets": facets,
            "mentions": len(resource["mentions"]),
        })
    items.sort(key=lambda item: -item["mentions"])
    con.close()
    return json.dumps(items[: min(limit, 40)], ensure_ascii=False, indent=1)


if __name__ == "__main__":
    mcp.run()
