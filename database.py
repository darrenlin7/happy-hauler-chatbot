"""
database.py — SQLite read/write operations for chat session persistence.

Uses Python's built-in sqlite3 so no external DB dependency is needed.
The DB file (chatbot.db) is created next to this script on first run.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "chatbot.db"


# ─── Connection helper ────────────────────────────────────────────────────────

def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Rows behave like dicts
    return conn


# ─── Schema setup ─────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create the sessions table if it doesn't already exist."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                created_at  TIMESTAMP NOT NULL,
                ended_at    TIMESTAMP,
                messages    TEXT      NOT NULL DEFAULT '[]',
                summary     TEXT,
                passed      INTEGER
            )
            """
        )
        conn.commit()


# ─── Write operations ─────────────────────────────────────────────────────────

def create_session() -> str:
    """Insert a blank session row and return its UUID."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at, messages) VALUES (?, ?, ?)",
            (session_id, now, "[]"),
        )
        conn.commit()
    return session_id


def save_session(
    session_id: str,
    messages: list[dict],
    summary: str | None,
    passed: bool | None,
) -> None:
    """
    Finalize a session when the conversation ends.

    Args:
        session_id: UUID of the session to update.
        messages:   Full message history as a list of {role, content} dicts.
        summary:    LLM-generated summary text (may be None if generation failed).
        passed:     True = pass, False = fail, None = incomplete.
    """
    passed_int = None if passed is None else (1 if passed else 0)
    ended_at = datetime.utcnow().isoformat()
    with _get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
               SET messages  = ?,
                   summary   = ?,
                   passed    = ?,
                   ended_at  = ?
             WHERE id = ?
            """,
            (json.dumps(messages), summary, passed_int, ended_at, session_id),
        )
        conn.commit()


# ─── Read operations ──────────────────────────────────────────────────────────

def get_all_sessions() -> list[dict]:
    """Return all completed sessions ordered by most recent first."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE ended_at IS NOT NULL ORDER BY created_at DESC"
        ).fetchall()

    result = []
    for row in rows:
        session = dict(row)
        session["messages"] = json.loads(session.get("messages") or "[]")
        result.append(session)
    return result


def get_session(session_id: str) -> dict | None:
    """Fetch a single session by ID, or None if not found."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

    if row is None:
        return None

    session = dict(row)
    session["messages"] = json.loads(session.get("messages") or "[]")
    return session
