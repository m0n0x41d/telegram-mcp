"""Layer 3: Effect shell — TelegramSession.

A single explicit state object that owns:
  - the live TelegramClient
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
from .telethon_session import ConcurrentSQLiteSession
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
            client = TelegramClient(
                ConcurrentSQLiteSession(str(config.session_path)),
                config.api_id,
                config.api_hash,
            )
            await client.connect()
            return Success(TelegramSession(client=client, config=config, identity=identity))
    return Failure(ConversionError(type_name="unreachable", reason=""))


async def close_session(session: TelegramSession) -> None:
    if session.client.is_connected():
        await session.client.disconnect()
