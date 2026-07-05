import json
import sqlite3

DB_PATH = "provenance_guard.db"


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            content_id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            title TEXT,
            text TEXT NOT NULL,
            attribution TEXT NOT NULL,
            confidence REAL NOT NULL,
            transparency_message TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            signals_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            entry_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS appeals (
            appeal_id TEXT PRIMARY KEY,
            content_id TEXT NOT NULL,
            creator_reasoning TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def create_submission(
    content_id,
    creator_id,
    title,
    text,
    attribution,
    confidence,
    transparency_message,
    status,
    created_at,
    signals,
):
    conn = _connect()
    conn.execute(
        """
        INSERT INTO submissions (
            content_id, creator_id, title, text, attribution, confidence,
            transparency_message, status, created_at, signals_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            content_id,
            creator_id,
            title,
            text,
            attribution,
            confidence,
            transparency_message,
            status,
            created_at,
            json.dumps(signals),
        ),
    )
    conn.commit()
    conn.close()


def get_submission(content_id):
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM submissions WHERE content_id = ?", (content_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    result["signals"] = json.loads(result.pop("signals_json"))
    return result


def update_submission_status(content_id, status):
    conn = _connect()
    conn.execute(
        "UPDATE submissions SET status = ? WHERE content_id = ?", (status, content_id)
    )
    conn.commit()
    conn.close()


def create_appeal(appeal_id, content_id, creator_reasoning, submitted_at):
    conn = _connect()
    conn.execute(
        "INSERT INTO appeals (appeal_id, content_id, creator_reasoning, submitted_at) VALUES (?, ?, ?, ?)",
        (appeal_id, content_id, creator_reasoning, submitted_at),
    )
    conn.commit()
    conn.close()


def log_event(event_type, content_id, timestamp, entry):
    entry_with_type = {"event_type": event_type, **entry}
    conn = _connect()
    conn.execute(
        "INSERT INTO audit_log (content_id, event_type, timestamp, entry_json) VALUES (?, ?, ?, ?)",
        (content_id, event_type, timestamp, json.dumps(entry_with_type)),
    )
    conn.commit()
    conn.close()


def get_log(limit=50):
    conn = _connect()
    rows = conn.execute(
        "SELECT entry_json FROM audit_log ORDER BY log_id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [json.loads(row[0]) for row in rows]
