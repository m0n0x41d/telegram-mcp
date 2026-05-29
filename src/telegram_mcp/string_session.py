"""In-memory session backend with per-process isolation.

Replaces the previous shared-SQLite approach. Each MCP process loads the
session as a string blob at startup and keeps state in memory; the file
is read once on start and written once on graceful shutdown. There is
no shared SQLite contention because there is no shared SQLite file at
runtime — telethon never opens a database when given a StringSession.

Trade-offs vs SQLiteSession:
  - No persistent entity cache (id↔hash for chats/users). First lookup
    after a process restart re-resolves via API.
  - No update_state (pts/qts). Not needed for MCP request-response use.
  - Auth_key drift: if Telegram rotates auth_key for one running process,
    siblings hold a stale key in memory until they next hit the API and
    get AUTH_KEY_UNREGISTERED. Recovery is a loud, well-defined error —
    the operator re-runs `telegram-mcp login`.

File layout:
  <session_path>.string   — current source of truth (text, telethon
                            StringSession encoding)
  <session_path>.session  — legacy SQLite from V1; left untouched after
                            migration as a manual rollback option.

Inexpressible:
  - Telegram protocol concerns
  - MCP framework
  - cross-process coordination (intentionally absent — see Storage
    section above)
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from telethon.crypto import AuthKey
from telethon.sessions import StringSession


def string_path(session_path: Path) -> Path:
    """Resolve the .string file path that mirrors telethon's .session naming."""
    return Path(f"{session_path}.string")


def sqlite_path(session_path: Path) -> Path:
    return Path(f"{session_path}.session")


def load_session_string(session_path: Path) -> str | None:
    """Return the persisted session blob, or None if absent.

    Auto-migrates from a legacy SQLiteSession file the first time it's
    called, so V1 users transition transparently on next start.
    """
    p = string_path(session_path)
    if p.exists():
        return p.read_text(encoding="utf-8").strip() or None

    legacy = sqlite_path(session_path)
    if legacy.exists():
        encoded = _migrate_from_sqlite(legacy)
        if encoded:
            save_session_string(session_path, encoded)
            return encoded
    return None


def save_session_string(session_path: Path, content: str) -> None:
    """Atomic write — tmp file + rename — so concurrent shutdowns can't
    leave a half-written blob. Last writer wins; conflicting auth_keys
    are extraordinarily rare and surface loudly on the loser side."""
    p = string_path(session_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, p)


def make_string_session(content: str | None) -> StringSession:
    """Build a StringSession from persisted content, or empty if absent."""
    return StringSession(content) if content else StringSession()


def _migrate_from_sqlite(legacy: Path) -> str | None:
    """One-shot read of the legacy SQLiteSession DB. Read-only via URI mode
    so we don't take any write locks against a sibling process that may
    still be using the V1 backend mid-migration."""
    try:
        con = sqlite3.connect(f"file:{legacy}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return None
    try:
        row = con.execute(
            "SELECT dc_id, server_address, port, auth_key FROM sessions"
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        con.close()

    if not row:
        return None
    dc_id, server, port, key = row
    if not key:
        return None

    s = StringSession()
    s.set_dc(dc_id, server, port)
    s.auth_key = AuthKey(data=key)
    return s.save()


__all__ = [
    "load_session_string",
    "make_string_session",
    "save_session_string",
    "string_path",
]
