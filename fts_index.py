"""Own the SQLite FTS5 schema, synchronization triggers, and coverage checks."""

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class FtsReport:
    messages: int
    indexed: int
    missing: int


TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS messages_fts_ai AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS messages_fts_ad AFTER DELETE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, text)
  VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS messages_fts_au AFTER UPDATE OF text ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, text)
  VALUES ('delete', old.id, old.text);
  INSERT INTO messages_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


def fts_report(con: sqlite3.Connection) -> FtsReport:
    """Return physical FTS document coverage rather than external-content row count."""
    messages = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    indexed = con.execute("SELECT COUNT(*) FROM messages_fts_docsize").fetchone()[0]
    missing = con.execute(
        "SELECT COUNT(*) FROM messages m "
        "LEFT JOIN messages_fts_docsize d ON d.id=m.id WHERE d.id IS NULL"
    ).fetchone()[0]
    return FtsReport(messages, indexed, missing)


def ensure_fts(con: sqlite3.Connection) -> FtsReport:
    """Create, synchronize, integrity-check, and verify the messages FTS index."""
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts "
        "USING fts5(text, content='messages', content_rowid='id')"
    )
    con.executescript(TRIGGERS)
    report = fts_report(con)
    if report.indexed != report.messages or report.missing:
        con.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    con.execute(
        "INSERT INTO messages_fts(messages_fts, rank) "
        "VALUES('integrity-check', 1)"
    )
    con.commit()
    report = fts_report(con)
    if report.indexed != report.messages or report.missing:
        raise RuntimeError(f"FTS incomplete: {report}")
    return report
