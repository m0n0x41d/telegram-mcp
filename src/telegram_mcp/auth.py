"""Layer 4b: Authentication.

Owns the login flow and authorization check. All Telethon contact
related to identity lives here — never in CLI or MCP transport.

Inexpressible:
  - terminal I/O (prompts come from the caller, passed as callables)
  - rich/typer concerns
  - MCP framework
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from returns.result import Failure, Result, Success
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from . import wire
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
    Peer,
    PeerKind,
)


def _make_client(config: Config, session_str: str | None) -> TelegramClient:
    return TelegramClient(make_string_session(session_str), config.api_id, config.api_hash)


@dataclass(frozen=True)
class MissingPhone:
    pass


@dataclass(frozen=True)
class LoginAborted:
    reason: str


@dataclass(frozen=True)
class TwoFactorFailed:
    pass


LoginError = MissingPhone | LoginAborted | TwoFactorFailed | NotAuthorized | ConversionError


@dataclass(frozen=True)
class PromptIO:
    """How auth interacts with the operator. Injected by the caller."""
    code: Callable[[], str]
    password: Callable[[], str]


async def check_authorization(config: Config) -> Result[Identity, NotAuthorized | ConversionError]:
    """Connect with the existing session; return Identity if authorized.

    Auto-migrates a legacy SQLite session on first read (see string_session
    module). Returns NotAuthorized if no session blob exists or contains
    no auth_key.
    """
    session_str = load_session_string(config.session_path)
    if not session_str:
        return Failure(NotAuthorized())
    client = _make_client(config, session_str)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            return Failure(NotAuthorized())
        me = await client.get_me()
        match wire.to_peer(me):
            case Success(peer):
                return Success(Identity(peer=peer))
            case Failure(err):
                return Failure(err)
        return Failure(ConversionError(type_name="unreachable", reason=""))
    finally:
        await client.disconnect()


async def login(config: Config, io: PromptIO) -> Result[Identity, LoginError]:
    """Run the interactive sign-in flow.

    On success the resulting StringSession is persisted to disk. If a
    legacy SQLite session exists and is already authorized, it migrates
    transparently and no code prompt is shown.
    """
    if config.phone is None:
        return Failure(MissingPhone())

    initial = load_session_string(config.session_path)
    client = _make_client(config, initial)
    await client.connect()
    try:
        if await client.is_user_authorized():
            save_session_string(config.session_path, client.session.save())
            me = await client.get_me()
            match wire.to_peer(me):
                case Success(peer):
                    return Success(Identity(peer=peer))
                case Failure(err):
                    return Failure(err)
            return Failure(ConversionError(type_name="unreachable", reason=""))

        await client.send_code_request(config.phone)
        try:
            await client.sign_in(config.phone, io.code())
        except SessionPasswordNeededError:
            try:
                await client.sign_in(password=io.password())
            except BaseException:  # noqa: BLE001
                return Failure(TwoFactorFailed())

        save_session_string(config.session_path, client.session.save())
        me = await client.get_me()
        match wire.to_peer(me):
            case Success(peer):
                return Success(Identity(peer=peer))
            case Failure(err):
                return Failure(err)
        return Failure(ConversionError(type_name="unreachable", reason=""))
    finally:
        await client.disconnect()


__all__ = [
    "Identity",
    "LoginAborted",
    "LoginError",
    "MissingPhone",
    "Peer",
    "PeerKind",
    "PromptIO",
    "TwoFactorFailed",
    "check_authorization",
    "login",
]
