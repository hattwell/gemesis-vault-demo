"""Общая логика: классификация ссылок и сборка ресурсов из gemesis.db."""
import json
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from demo.url import normalize_url

BASE = Path(__file__).parent
_demo_path = os.environ.get("DEMO_DB_PATH")
if not _demo_path or not Path(_demo_path).is_file():
    raise RuntimeError("an existing fictional DEMO_DB_PATH is required")
DB_PATH = Path(_demo_path)

SKIP_DOMAINS = {"tglink.io"}
BAD_FS_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]\n\r\t]')


def safe_name(s: str, maxlen: int = 80) -> str:
    s = BAD_FS_CHARS.sub("-", s).strip(" .-")
    return s[:maxlen] or "untitled"


def clean_url(u: str) -> str:
    return normalize_url(u)


def _classify_normalized(url: str):
    p = urlparse(url)
    dom = p.netloc.lower().removeprefix("www.")
    path = p.path.strip("/")
    parts = path.split("/") if path else []

    if dom in SKIP_DOMAINS:
        return None
    if dom == "github.com":
        if len(parts) >= 2 and parts[0] not in ("topics", "search", "orgs", "features", "settings", "sponsors"):
            repo = f"{parts[0]}/{parts[1]}"
            return ("GitHub", repo, f"gh:{repo.lower()}")
        return None
    if dom in ("youtu.be", "youtube.com", "m.youtube.com"):
        vid = parts[0] if dom == "youtu.be" else parse_qs(p.query).get("v", [""])[0]
        if not vid and parts[:1] == ["shorts"] and len(parts) > 1:
            vid = parts[1]
        if vid:
            return ("Видео", f"youtube {vid}", f"yt:{vid}")
        return None
    if dom in ("x.com", "twitter.com"):
        if len(parts) >= 3 and parts[1] == "status":
            return ("Twitter", f"@{parts[0]} {parts[2]}", f"x:{parts[0].lower()}/{parts[2]}")
        if len(parts) == 1 and parts[0] not in ("home", "search", "i"):
            return ("Twitter", f"@{parts[0]}", f"x:@{parts[0].lower()}")
        return None
    if dom in ("t.me", "telegram.me"):
        if parts and parts[0] not in ("c", "+", "joinchat") and not parts[0].startswith("+"):
            return ("Telegram", f"tg @{parts[0]}", f"tg:{parts[0].lower()}")
        return None
    slug = safe_name(path.replace("/", " ")) if path else ""
    title = f"{dom} {slug}".strip()
    return ("Веб", title, f"url:{url.lower()}")


def classify(url: str):
    """Возвращает (folder, title, key) для ресурса или None, если ресурс не интересен."""
    normalized_url = normalize_url(url)
    return _classify_normalized(normalized_url) if normalized_url else None


def collect_resources(con: sqlite3.Connection):
    """Собирает ресурсы и их упоминания из messages.

    Возвращает (resources, person_shares, cooccur):
      resources: key -> {folder, title, url, mentions: [{msg_id, date, sender, text}]}
      person_shares: sender -> set(keys)
      cooccur: set((key1, key2)) — ссылки из одного сообщения
    """
    columns = {row[1] for row in con.execute("PRAGMA table_info(messages)")}
    topic_col = "topic_id" if "topic_id" in columns else "NULL AS topic_id"
    select_cols = f"id, date, sender_name, text, reply_to, {topic_col}, urls"
    rows = con.execute(
        f"SELECT {select_cols} FROM messages WHERE urls IS NOT NULL ORDER BY id"
    ).fetchall()
    by_id = {r[0]: r for r in con.execute(f"SELECT {select_cols} FROM messages").fetchall()}

    resources = {}
    person_shares = defaultdict(set)
    cooccur = set()

    for msg_id, date, sender, text, reply_to, topic_id, urls_json in rows:
        keys_in_msg = []
        for url in json.loads(urls_json):
            normalized_url = normalize_url(url)
            if not normalized_url:
                continue
            info = _classify_normalized(normalized_url)
            if not info:
                continue
            folder, title, key = info
            res = resources.setdefault(
                key, {"folder": folder, "title": title, "url": normalized_url, "mentions": []}
            )
            if key in keys_in_msg:  # та же ссылка дважды в одном сообщении — не дублируем
                continue
            keys_in_msg.append(key)
            context = text
            if reply_to and reply_to in by_id:
                q = by_id[reply_to]
                context = f"[в ответ на {q[2]}: {(q[3] or '')[:200]}]\n{text}"
            res["mentions"].append(
                {
                    "msg_id": msg_id,
                    "date": date[:10],
                    "sender": sender or "неизвестно",
                    "text": context,
                    "topic_id": topic_id,
                }
            )
            if sender:
                person_shares[sender].add(key)
        for i, a in enumerate(keys_in_msg):
            for b in keys_in_msg[i + 1:]:
                cooccur.add(tuple(sorted((a, b))))

    return resources, person_shares, cooccur


# --- общие ссылки и канонические имена ресурсов ---


def telegram_message_url(msg_id: int, group: str, topic_id: int | None = None) -> None:
    """The public fictional demo never links to Telegram, regardless of input."""
    return None


def row_get(row, col):
    return row[col] if row is not None and col in row.keys() else None


def resource_display_name(meta, resource) -> str:
    """Единое имя ресурса для всех выдач: display_name → web_title → сырое title.

    meta — строка обогащения (может не знать про display_name на старой схеме),
    resource — любой mapping/Row с полем title (не только запись collect_resources).
    """
    return (
        row_get(meta, "display_name")
        or row_get(meta, "web_title")
        or resource["title"]
    )[:90]
