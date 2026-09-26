"""Build a reproducible, wholly fictional SQLite/FTS knowledge graph."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3

from fts_index import ensure_fts

AUTHORS = ("Ника Искра", "Лев Маяк", "Мира Ветер", "Оля Луч", "Ян Орбит")
TOPICS = ("Навигация", "Заметки", "Поиск", "Мастерская")


def build_demo_database(path: Path) -> None:
    """Create a new fixture DB; refuse existing files rather than risk overwriting data."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    try:
        con = sqlite3.connect(path)
        try:
            con.executescript("""
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY, date TEXT NOT NULL,
                    sender_name TEXT NOT NULL, text TEXT NOT NULL,
                    reply_to INTEGER, topic_id INTEGER, urls TEXT NOT NULL
                );
                CREATE TABLE resources (
                    key TEXT PRIMARY KEY, title TEXT NOT NULL,
                    folder TEXT NOT NULL, url TEXT NOT NULL,
                    description TEXT, web_title TEXT, web_desc TEXT,
                    kind TEXT, topics TEXT, facets TEXT,
                    display_name TEXT, useless INTEGER DEFAULT 0
                );
            """)
            links = [f"https://aerolith-{number:02d}.example/guide" for number in range(1, 21)]
            for index, url in enumerate(links):
                label = f"Аэролит {index + 1:02d}"
                topic = TOPICS[index % len(TOPICS)]
                con.execute(
                    "INSERT INTO resources (key,title,folder,url,description,web_title,web_desc,kind,topics,facets,display_name,useless) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,0)",
                    (
                        "url:" + url.lower(), label, "Веб", url,
                        f"Вымышленный справочник {label} для темы {topic.lower()}.",
                        label, f"Демо-ресурс о теме {topic.lower()}.", "Веб",
                        json.dumps([topic], ensure_ascii=False),
                        json.dumps(["вымышленное", "демо"], ensure_ascii=False), label,
                    ),
                )
            start = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)
            for number in range(1, 101):
                index = (number - 1) % len(links)
                topic = TOPICS[index % len(TOPICS)]
                urls = [links[index]]
                if number % 5 == 0:
                    urls.append(links[(index + 1) % len(links)])
                con.execute(
                    "INSERT INTO messages (id,date,sender_name,text,reply_to,topic_id,urls) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        number, (start + timedelta(days=(number - 1) % 7)).isoformat(),
                        AUTHORS[(number - 1) % len(AUTHORS)],
                        f"Обсуждаем вымышленный аэролит {index + 1:02d}: {topic.lower()}, "
                        "заметки и поиск. Это только демонстрационное сообщение.",
                        None, None, json.dumps(urls, ensure_ascii=False),
                    ),
                )
            report = ensure_fts(con)
            if report.messages != 100 or report.indexed != 100 or report.missing:
                raise RuntimeError("fictional full-text index incomplete")
            con.commit()
        finally:
            con.close()
        path.chmod(0o444)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
