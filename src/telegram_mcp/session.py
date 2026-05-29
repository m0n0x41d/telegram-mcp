"""Layer 3: Effect shell — TelegramSession.

A single explicit state object that owns:
  - the live TelegramClient (built over a StringSession)
  - the Config it was built from
  - the authenticated Identity

Replaces the global `_client`/`_config` singletons. Built once at startup,
passed by reference to L4a (MCP transport).

Inexpressible:
  - FastMCP / stdio transport concerns
  - tool schemas
  - operator UX
"""

from __future__ import annotations

from dataclasses import dataclass

from returns.result import Failure, Result, Success
from telethon import TelegramClient

from . import auth
from .config import Config
from .string_session import (
    load_session_string,
    make_string_session,
    save_session_string,
)
from .types import (
    ConversionError,
    Identity,
    NotAuthorized,
)


@dataclass(frozen=True)
class TelegramSession:
    client: TelegramClient
    config: Config
    identity: Identity


OpenError = NotAuthorized | ConversionError


async def open_session(config: Config) -> Result[TelegramSession, OpenError]:
    match await auth.check_authorization(config):
        case Failure(err):
            return Failure(err)
        case Success(identity):
            session_str = load_session_string(config.session_path)
            client = TelegramClient(
                make_string_session(session_str),
                config.api_id,
                config.api_hash,
            )
            await client.connect()
            return Success(TelegramSession(client=client, config=config, identity=identity))
    return Failure(ConversionError(type_name="unreachable", reason=""))


async def close_session(session: TelegramSession) -> None:
    """Persist any in-memory session updates (e.g. auth_key rotation) to
    disk before disconnecting. Atomic rename keeps concurrent shutdowns
    from interleaving a half-written blob."""
    if session.client.is_connected():
        try:
            save_session_string(session.config.session_path, session.client.session.save())
        except Exception:
            # Disk write failures must not block clean disconnect; the
            # in-memory state is fine to drop — next process resumes from
            # the prior on-disk snapshot.
            pass
        await session.client.disconnect()
