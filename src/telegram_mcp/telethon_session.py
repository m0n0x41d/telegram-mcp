"""SQLite session tuned for multi-process use.

Telethon's stock `SQLiteSession` opens the session DB with default SQLite
settings: rollback journal mode and `busy_timeout=0`. The consequence is
that two Telethon processes sharing the same session file race each other
on every `auth_key` update — the second one crashes with
`OperationalError: database is locked`.

This wrapper does two things on first connection:
  - Switches the DB to WAL journal mode (readers and writers no longer
    block each other; only writer-vs-writer briefly serialises).
  - Sets `busy_timeout` so the rare writer-vs-writer contention waits
    instead of erroring out.

Telegram itself allows many concurrent MTProto connections sharing one
`auth_key` (that's how Desktop, mobile, and web coexist), so the only
shared-state hazard is the local SQLite file — which WAL fixes.
"""

from __future__ import annotations

from telethon.sessions import SQLiteSession

_BUSY_TIMEOUT_MS = 30_000


class ConcurrentSQLiteSession(SQLiteSession):
    """SQLiteSession with WAL + busy_timeout applied lazily on first cursor."""

    def _cursor(self):  # type: ignore[override]
        first_open = self._conn is None
        cursor = super()._cursor()
        if first_open:
            # WAL switch needs an exclusive lock; if another process holds it,
            # we silently stay in rollback mode for this connection.
            # busy_timeout is per-connection and always safe to set.
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
            try:
                cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            except Exception:
                pass
        return cursor


__all__ = ["ConcurrentSQLiteSession"]
