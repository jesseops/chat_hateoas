from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import current_app, g


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    conn = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def init_app(app) -> None:  # type: ignore[no-untyped-def]
    app.teardown_appcontext(close_db)


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return get_db().execute(query, params).fetchone()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    return get_db().execute(query, params).fetchall()


def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    conn = get_db()
    cur = conn.execute(query, params)
    conn.commit()
    return int(cur.lastrowid)


def create_conversation(title: str) -> int:
    now = utc_now_iso()
    return execute(
        """
        INSERT INTO conversations (title, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (title, now, now),
    )


def update_conversation_timestamp(conversation_id: int) -> None:
    execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (utc_now_iso(), conversation_id),
    )


def list_conversations() -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        """
    )


def get_conversation(conversation_id: int) -> sqlite3.Row | None:
    return fetch_one(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
        (conversation_id,),
    )


def delete_conversation(conversation_id: int) -> None:
    execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def create_message(
    conversation_id: int,
    role: str,
    raw_text: str,
    rendered_html: str,
    status: str = "complete",
) -> int:
    return execute(
        """
        INSERT INTO messages (conversation_id, role, raw_text, rendered_html, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, role, raw_text, rendered_html, status, utc_now_iso()),
    )


def update_message(
    message_id: int,
    raw_text: str,
    rendered_html: str,
    status: str,
) -> None:
    execute(
        """
        UPDATE messages
        SET raw_text = ?, rendered_html = ?, status = ?
        WHERE id = ?
        """,
        (raw_text, rendered_html, status, message_id),
    )


def get_message(message_id: int) -> sqlite3.Row | None:
    return fetch_one(
        """
        SELECT
          m.id,
          m.conversation_id,
          m.role,
          m.raw_text,
          m.rendered_html,
          m.status,
          m.created_at,
          mf.vote AS feedback_vote
        FROM messages m
        LEFT JOIN message_feedback mf ON mf.message_id = m.id
        WHERE m.id = ?
        """,
        (message_id,),
    )


def list_messages(conversation_id: int) -> list[sqlite3.Row]:
    return fetch_all(
        """
        SELECT
          m.id,
          m.conversation_id,
          m.role,
          m.raw_text,
          m.rendered_html,
          m.status,
          m.created_at,
          mf.vote AS feedback_vote
        FROM messages m
        LEFT JOIN message_feedback mf ON mf.message_id = m.id
        WHERE m.conversation_id = ?
        ORDER BY m.created_at ASC, m.id ASC
        """,
        (conversation_id,),
    )


def list_history_for_conversation(
    conversation_id: int,
    up_to_message_id: int | None = None,
) -> list[dict[str, str]]:
    query = (
        "SELECT id, role, raw_text FROM messages WHERE conversation_id = ?"
        " ORDER BY created_at ASC, id ASC"
    )
    params: tuple[Any, ...] = (conversation_id,)
    if up_to_message_id is not None:
        query = (
            "SELECT id, role, raw_text FROM messages WHERE conversation_id = ? AND id < ?"
            " ORDER BY created_at ASC, id ASC"
        )
        params = (conversation_id, up_to_message_id)

    rows = fetch_all(query, params)
    return [{"role": row["role"], "content": row["raw_text"]} for row in rows]


def save_assistant_metadata(
    message_id: int,
    provider: str,
    model_id: str,
    stop_reason: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    tool_events: list[dict[str, Any]],
    raw_event_count: int,
) -> None:
    execute(
        """
        INSERT INTO assistant_metadata (
          message_id,
          provider,
          model_id,
          stop_reason,
          input_tokens,
          output_tokens,
          latency_ms,
          tool_events_json,
          raw_event_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
          provider = excluded.provider,
          model_id = excluded.model_id,
          stop_reason = excluded.stop_reason,
          input_tokens = excluded.input_tokens,
          output_tokens = excluded.output_tokens,
          latency_ms = excluded.latency_ms,
          tool_events_json = excluded.tool_events_json,
          raw_event_count = excluded.raw_event_count
        """,
        (
            message_id,
            provider,
            model_id,
            stop_reason,
            input_tokens,
            output_tokens,
            latency_ms,
            json.dumps(tool_events),
            raw_event_count,
        ),
    )


def upsert_feedback(message_id: int, vote: str) -> None:
    execute(
        """
        INSERT INTO message_feedback (message_id, vote, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(message_id) DO UPDATE SET
          vote = excluded.vote,
          updated_at = excluded.updated_at
        """,
        (message_id, vote, utc_now_iso()),
    )


def get_feedback(message_id: int) -> str | None:
    row = fetch_one("SELECT vote FROM message_feedback WHERE message_id = ?", (message_id,))
    if row is None:
        return None
    return str(row["vote"])


def conversation_count() -> int:
    row = fetch_one("SELECT COUNT(*) AS count FROM conversations")
    if row is None:
        return 0
    return int(row["count"])
