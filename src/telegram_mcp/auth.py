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
from .types import (
    ConversionError,
    Identity,
    NotAuthorized,
    Peer,
    PeerKind,
)


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
    """Connect with the existing session; return Identity if authorized."""
    client = TelegramClient(str(config.session_path), config.api_id, config.api_hash)
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
    """Run the interactive sign-in flow. Persists session as a side-effect of Telethon."""
    if config.phone is None:
        return Failure(MissingPhone())

    client = TelegramClient(str(config.session_path), config.api_id, config.api_hash)
    await client.connect()
    try:
        if await client.is_user_authorized():
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
