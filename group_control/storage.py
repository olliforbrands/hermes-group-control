"""SQLite storage for group-control archive."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Optional

_SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS groups (
    jid TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    mode TEXT NOT NULL DEFAULT 'observe',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL UNIQUE,
    group_jid TEXT NOT NULL,
    sender_jid TEXT NOT NULL DEFAULT '',
    sender_name TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    ts TEXT NOT NULL,
    msg_type TEXT NOT NULL DEFAULT 'text',
    has_media INTEGER NOT NULL DEFAULT 0,
    media_path TEXT,
    mime_type TEXT,
    media_size INTEGER
);

CREATE INDEX IF NOT EXISTS idx_messages_group_ts ON messages (group_jid, ts);
"""


class Storage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.executescript(_DDL)
            row = cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                cur.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (_SCHEMA_VERSION,),
                )
            elif int(row[0]) < _SCHEMA_VERSION:
                cur.execute(
                    "UPDATE schema_version SET version = ?",
                    (_SCHEMA_VERSION,),
                )
            self._conn.commit()

    def message_exists(self, message_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM messages WHERE message_id = ? LIMIT 1",
                (message_id,),
            ).fetchone()
            return row is not None

    def upsert_group(self, jid: str, name: str, default_mode: str, now: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT mode FROM groups WHERE jid = ?",
                (jid,),
            ).fetchone()
            if row is None:
                mode = default_mode if default_mode in {"observe", "mention"} else "observe"
                self._conn.execute(
                    """
                    INSERT INTO groups (jid, name, mode, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (jid, name, mode, now, now),
                )
            else:
                mode = str(row["mode"])
                self._conn.execute(
                    "UPDATE groups SET name = ?, last_seen = ? WHERE jid = ?",
                    (name, now, jid),
                )
            self._conn.commit()
            return mode

    def insert_message(self, fields: Dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO messages (
                    message_id, group_jid, sender_jid, sender_name, body, ts,
                    msg_type, has_media, media_path, mime_type, media_size
                ) VALUES (
                    :message_id, :group_jid, :sender_jid, :sender_name, :body, :ts,
                    :msg_type, :has_media, :media_path, :mime_type, :media_size
                )
                """,
                fields,
            )
            self._conn.commit()

    def touch_group(self, jid: str, now: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE groups SET last_seen = ? WHERE jid = ?",
                (now, jid),
            )
            self._conn.commit()

    def set_group_mode(self, jid: str, mode: str, now: str) -> bool:
        if mode not in {"observe", "mention"}:
            return False
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM groups WHERE jid = ?",
                (jid,),
            ).fetchone()
            if row is None:
                return False
            self._conn.execute(
                "UPDATE groups SET mode = ?, last_seen = ? WHERE jid = ?",
                (mode, now, jid),
            )
            self._conn.commit()
            return True
