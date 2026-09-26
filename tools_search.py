"""CLI-инструменты поиска по gemesis.db — для LLM-агента (codex exec).

  python tools_search.py search "запрос"        # полнотекстовый поиск по сообщениям
  python tools_search.py resources ["подстрока"] [--topic ТЕМА] [--kind ТИП] [--facet FACET]
  python tools_search.py resource <key>         # детали ресурса с контекстом
Вывод — JSON в UTF-8.
"""
import argparse
import json
import re
import sqlite3
import sys

from common import DB_PATH, collect_resources, resource_display_name, telegram_message_url

sys.stdout.reconfigure(encoding="utf-8")


def db() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    con.create_function("casefold", 1, lambda value: (value or "").casefold(), deterministic=True)
    return con


def display_name_column(con: sqlite3.Connection) -> str:
    """Фрагмент SELECT для display_name: сама колонка либо NULL-заглушка, если её ещё нет."""
    columns = {row[1] for row in con.execute("PRAGMA table_info(resources)")}
    return "display_name" if "display_name" in columns else "NULL AS display_name"


def cmd_search(query: str) -> list:
    con = db()
    q = query.replace('"', " ")
    columns = {row[1] for row in con.execute("PRAGMA table_info(messages)")}
    topic_col = "m.topic_id" if "topic_id" in columns else "NULL AS topic_id"
    try:
        rows = con.execute(
            f"SELECT m.id, m.date, m.sender_name, m.text, {topic_col} FROM messages_fts f "
            "JOIN messages m ON m.id = f.rowid WHERE messages_fts MATCH ? "
            "ORDER BY rank LIMIT 15", (q,),
        ).fetchall()
    except sqlite3.OperationalError:
        fallback_topic = "topic_id" if "topic_id" in columns else "NULL AS topic_id"
        rows = con.execute(
            f"SELECT id, date, sender_name, text, {fallback_topic} FROM messages "
            "WHERE text LIKE ? LIMIT 15",
            (f"%{query}%",),
        ).fetchall()
    result = [
        {
            "msg_id": row["id"],
            "date": row["date"][:10],
            "from": row["sender_name"],
            "text": row["text"][:400],
            "telegram_url": telegram_message_url(row["id"], "", row["topic_id"]),
        }
        for row in rows
    ]
    con.close()
    return result


def cmd_resources(
    sub: str = "",
    *,
    topic: str = "",
    kind: str = "",
    facet: str = "",
) -> list:
    """Search resource text and discussion context, with exact taxonomy filters."""
    con = db()
    words = [word for word in re.split(r"\W+", sub) if len(word) >= 3]
    clauses: list[str] = []
    params: list[str] = []
    if words:
        clauses.append(
            "("
            + " OR ".join(
                "(title LIKE ? OR url LIKE ? OR IFNULL(description,'') LIKE ? "
                "OR IFNULL(web_title,'') LIKE ? OR IFNULL(web_desc,'') LIKE ?)"
                for _ in words
            )
            + ")"
        )
        params.extend(value for word in words for value in (f"%{word}%",) * 5)
    if topic:
        clauses.append(
            "EXISTS (SELECT 1 FROM json_each(IFNULL(topics, '[]')) "
            "WHERE casefold(value) = casefold(?))"
        )
        params.append(topic)
    if kind:
        clauses.append("casefold(IFNULL(kind, folder)) = casefold(?)")
        params.append(kind)
    if facet:
        clauses.append(
            "EXISTS (SELECT 1 FROM json_each(IFNULL(facets, '[]')) "
            "WHERE casefold(value) = casefold(?))"
        )
        params.append(facet)

    where = " AND ".join(clauses) or "1=1"
    where = f"COALESCE(useless, 0)=0 AND ({where})"
    name_col = display_name_column(con)
    found: dict[str, dict] = {}
    for row in con.execute(
        "SELECT key, title, folder, url, description, web_title, web_desc, kind, topics, facets, "
        f"{name_col} FROM resources WHERE {where} LIMIT 40",
        params,
    ).fetchall():
        topics = json.loads(row["topics"] or "[]")
        facets = json.loads(row["facets"] or "[]")
        found[row["key"]] = {
            "key": row["key"],
            "title": resource_display_name(row, row),
            "type": row["kind"] or row["folder"],
            "kind": row["kind"] or row["folder"],
            "url": row["url"],
            "description": row["description"] or row["web_desc"],
            "topics": topics,
            "facets": facets,
            "matched": "название/описание",
        }

    if words:
        try:
            fts_query = " OR ".join(words)
            message_ids = {
                row[0]
                for row in con.execute(
                    "SELECT rowid FROM messages_fts WHERE messages_fts MATCH ? LIMIT 200",
                    (fts_query,),
                ).fetchall()
            }
        except sqlite3.OperationalError:
            message_ids = set()
        if message_ids:
            resources, _, _ = collect_resources(con)
            metadata = {
                row["key"]: row
                for row in con.execute(
                    "SELECT key, description, web_title, web_desc, kind, folder, topics, facets, "
                    f"{name_col} FROM resources WHERE COALESCE(useless, 0)=0"
                ).fetchall()
            }
            for key, resource in resources.items():
                if key in found or not any(
                    mention["msg_id"] in message_ids for mention in resource["mentions"]
                ):
                    continue
                meta = metadata.get(key)
                if not meta:
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
                found[key] = {
                    "key": key,
                    "title": resource_display_name(meta, resource),
                    "type": resource_kind,
                    "kind": resource_kind,
                    "url": resource["url"],
                    "description": meta["description"] or meta["web_desc"],
                    "topics": topics,
                    "facets": facets,
                    "matched": "контекст обсуждения",
                }
                if len(found) >= 40:
                    break
    con.close()
    return list(found.values())[:40]


def cmd_resource(key: str) -> dict:
    con = db()
    resources, _, _ = collect_resources(con)
    resource = resources.get(key)
    if not resource:
        con.close()
        return {"error": "нет такого key"}
    meta = con.execute(
        "SELECT folder, description, web_title, web_desc, kind, topics, facets, "
        f"{display_name_column(con)} FROM resources "
        "WHERE key=? AND COALESCE(useless, 0)=0",
        (key,),
    ).fetchone()
    if meta is None:
        con.close()
        return {"error": "нет такого key"}
    result = {
        "key": key,
        "title": resource_display_name(meta, resource),
        "type": meta["kind"] or meta["folder"],
        "url": resource["url"],
        "description": meta["description"] or meta["web_desc"],
        "topics": json.loads(meta["topics"] or "[]"),
        "facets": json.loads(meta["facets"] or "[]"),
        "mentions": [
            {
                "msg_id": mention["msg_id"],
                "date": mention["date"],
                "from": mention["sender"],
                "text": mention["text"][:400],
                "telegram_url": telegram_message_url(
                    mention["msg_id"], "", mention.get("topic_id")
                ),
            }
            for mention in resource["mentions"][:10]
        ],
    }
    con.close()
    return result


def dispatch(argv: list[str]) -> object:
    if not argv:
        raise ValueError("Не указана команда")
    command, *args = argv
    if command == "resources":
        parser = argparse.ArgumentParser(prog="tools_search.py resources", add_help=False)
        parser.add_argument("--topic", default="")
        parser.add_argument("--kind", default="")
        parser.add_argument("--facet", default="")
        parser.add_argument("query", nargs="*")
        parsed = parser.parse_args(args)
        return cmd_resources(
            " ".join(parsed.query),
            topic=parsed.topic,
            kind=parsed.kind,
            facet=parsed.facet,
        )
    if command == "search":
        return cmd_search(" ".join(args))
    if command == "resource":
        return cmd_resource(" ".join(args))
    raise ValueError(f"Неизвестная команда: {command}")


def main(argv: list[str] | None = None) -> None:
    result = dispatch(sys.argv[1:] if argv is None else argv)
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
