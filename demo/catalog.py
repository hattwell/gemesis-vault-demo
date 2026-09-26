"""Read-only graph and overview derived from wholly fictional demo messages."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3

from common import collect_resources, resource_display_name, row_get


def _db(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _enrichment(con: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {
        row["key"]: row
        for row in con.execute(
            "SELECT key, description, topics, facets, useless, web_title, web_desc, "
            "kind, display_name FROM resources"
        )
    }


def build_graph(path: Path) -> dict:
    con = _db(path)
    try:
        resources, person_shares, cooccur = collect_resources(con)
        enrichment = _enrichment(con)
    finally:
        con.close()

    nodes: list[dict] = []
    links: list[dict] = []
    kept: set[str] = set()
    for key, resource in resources.items():
        meta = enrichment.get(key)
        if meta is not None and bool(meta["useless"]):
            continue
        kept.add(key)
        topics = json.loads(meta["topics"] or "[]") if meta is not None else []
        facets = json.loads(row_get(meta, "facets") or "[]")
        name = resource_display_name(meta, resource)
        web_title = row_get(meta, "web_title")
        display_name = row_get(meta, "display_name")
        nodes.append({
            "id": key, "name": name,
            "alt": resource["title"] if (display_name or web_title) and resource["title"] != name else None,
            "group": resource["folder"], "kind": row_get(meta, "kind") or resource["folder"],
            "val": len(resource["mentions"]), "url": resource["url"],
            "description": (row_get(meta, "description") or row_get(meta, "web_desc")),
            "topics": topics, "facets": facets, "useless": False,
        })
        links.extend({"source": f"topic:{topic}", "target": key, "kind": "topic"} for topic in topics)

    for topic_id in sorted({link["source"] for link in links if link["kind"] == "topic"}):
        nodes.append({
            "id": topic_id, "name": topic_id.removeprefix("topic:"), "group": "Тема",
            "val": sum(link["source"] == topic_id for link in links), "url": None,
            "description": None, "topics": [], "useless": False,
        })
    for folder in sorted({resource["folder"] for key, resource in resources.items() if key in kept}):
        nodes.append({
            "id": f"cat:{folder}", "name": folder, "group": folder, "val": 60,
            "url": None, "description": None, "topics": [], "useless": False, "cat": True,
        })
    for key, resource in resources.items():
        if key in kept:
            links.append({"source": f"cat:{resource['folder']}", "target": key, "kind": "category"})
    for person, keys in sorted(person_shares.items()):
        visible = sorted(key for key in keys if key in kept)
        if visible:
            pid = f"person:{person}"
            nodes.append({"id": pid, "name": person, "group": "Человек", "val": len(visible),
                          "url": None, "description": None, "topics": [], "useless": False})
            links.extend({"source": pid, "target": key, "kind": "shared"} for key in visible)
    links.extend({"source": left, "target": right, "kind": "cooccur"}
                 for left, right in sorted(cooccur) if left in kept and right in kept)
    return {"nodes": nodes, "links": links}


def build_digest(path: Path) -> dict:
    con = _db(path)
    try:
        latest = con.execute("SELECT MAX(date) FROM messages").fetchone()[0]
        if not latest:
            return {"period": {"start": None, "end": None},
                    "stats": {"messages": 0, "contributors": 0, "new_resources": 0},
                    "topics": [], "new_resources": [], "active_resources": []}
        end = datetime.fromisoformat(latest.replace("Z", "+00:00")).date()
        start_iso = (end - timedelta(days=6)).isoformat()
        end_iso = end.isoformat()
        count, contributors = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT sender_name) FROM messages "
            "WHERE substr(date,1,10) BETWEEN ? AND ?", (start_iso, end_iso)
        ).fetchone()
        resources, _, _ = collect_resources(con)
        enrichment = _enrichment(con)
    finally:
        con.close()

    topics: Counter[str] = Counter()
    active: list[dict] = []
    newly_mentioned: list[dict] = []
    for key, resource in resources.items():
        meta = enrichment.get(key)
        if meta is not None and bool(meta["useless"]):
            continue
        mentions = resource["mentions"]
        recent = [mention for mention in mentions if start_iso <= mention["date"] <= end_iso]
        if not recent:
            continue
        names = json.loads(meta["topics"] or "[]") if meta is not None else []
        for name in names:
            topics[name] += len(recent)
        latest_mention = max(recent, key=lambda mention: mention["msg_id"])
        item = {
            "key": key, "name": resource_display_name(meta, resource),
            "group": resource["folder"], "kind": row_get(meta, "kind") or resource["folder"],
            "description": row_get(meta, "description") or row_get(meta, "web_desc"),
            "topics": names, "mentions": len(recent), "total_mentions": len(mentions),
            "latest_mention": {
                "msg_id": latest_mention["msg_id"], "date": latest_mention["date"],
                "sender": latest_mention["sender"], "telegram_url": None,
            },
        }
        active.append(item)
        if min(mention["date"] for mention in mentions) >= start_iso:
            newly_mentioned.append(item)
    active.sort(key=lambda item: (-item["mentions"], -item["latest_mention"]["msg_id"], item["name"]))
    newly_mentioned.sort(key=lambda item: (-item["latest_mention"]["msg_id"], item["name"]))
    return {
        "period": {"start": start_iso, "end": end_iso},
        "stats": {"messages": count, "contributors": contributors, "new_resources": len(newly_mentioned)},
        "topics": [{"name": name, "mentions": total} for name, total in topics.most_common(6)],
        "new_resources": newly_mentioned[:8], "active_resources": active[:6],
    }
