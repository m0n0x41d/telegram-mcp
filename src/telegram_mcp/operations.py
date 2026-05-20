"""Layer 1b: Effectful Telegram operations.

Async functions that talk to Telethon. Each takes a TelegramClient and
typed inputs (PeerIdentifier), returns a Result wrapping domain types.

Inexpressible:
  - presentation / formatting (string output belongs to L2)
  - MCP transport, tool schemas
  - session lifecycle (the client is passed in)

Side effects: network I/O via Telethon. Confined to this layer.
"""

from __future__ import annotations

from typing import Any

from returns.result import Failure, Result, Success
from telethon import TelegramClient
from telethon.errors import (
    AuthKeyError,
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
)

from . import wire
from .types import (
    ChatEvent,
    ChatTitle,
    Dialog,
    DownloadedMedia,
    NetworkError,
    NotAuthorized,
    NumericId,
    Peer,
    PeerIdentifier,
    PeerNotFound,
    PhoneNumber,
    RateLimited,
    SendResult,
    TelegramError,
    UnknownTelegramError,
    Username,
)


# --- Identifier -> Telethon-acceptable value ---


def _identifier_to_telethon(pid: PeerIdentifier) -> int | str:
    match pid:
        case NumericId(value=n):
            return n
        case Username(value=u):
            return u
        case PhoneNumber(value=p):
            return p
        case ChatTitle(value=t):
            return t


# --- Telethon exception -> typed TelegramError ---


def _map_exception(exc: BaseException, pid: PeerIdentifier | None = None) -> TelegramError:
    if isinstance(exc, FloodWaitError):
        return RateLimited(wait_seconds=int(exc.seconds))
    if isinstance(exc, (UsernameInvalidError, UsernameNotOccupiedError)):
        if pid is not None:
            return PeerNotFound(identifier=pid)
        return UnknownTelegramError(detail=str(exc))
    if isinstance(exc, AuthKeyError):
        return NotAuthorized()
    if isinstance(exc, (ConnectionError, OSError)):
        return NetworkError(detail=str(exc))
    if isinstance(exc, ValueError) and pid is not None:
        return PeerNotFound(identifier=pid)
    return UnknownTelegramError(detail=f"{type(exc).__name__}: {exc}")


# --- Resolve identifier to Telethon entity, then to domain Peer ---


async def _resolve_peer(
    client: TelegramClient, pid: PeerIdentifier
) -> Result[tuple[Any, Peer], TelegramError]:
    try:
        entity = await client.get_entity(_identifier_to_telethon(pid))
    except BaseException as exc:  # noqa: BLE001 — boundary with untyped library
        return Failure(_map_exception(exc, pid))

    match wire.to_peer(entity):
        case Failure(conv_err):
            return Failure(conv_err)
        case Success(peer):
            return Success((entity, peer))
    return Failure(UnknownTelegramError(detail="unreachable"))


# --- Public operations ---


async def list_dialogs(client: TelegramClient, limit: int) -> Result[list[Dialog], TelegramError]:
    try:
        raw = await client.get_dialogs(limit=limit)
    except BaseException as exc:  # noqa: BLE001
        return Failure(_map_exception(exc))

    dialogs: list[Dialog] = []
    for r in raw:
        match wire.to_dialog(r):
            case Success(d):
                dialogs.append(d)
            case Failure(_):
                continue
    return Success(dialogs)


async def get_messages(
    client: TelegramClient, pid: PeerIdentifier, limit: int
) -> Result[list[ChatEvent], TelegramError]:
    resolved = await _resolve_peer(client, pid)
    match resolved:
        case Failure(err):
            return Failure(err)
        case Success(pair):
            entity, chat_peer = pair
            return await _fetch_events(client, entity, chat_peer, limit, search=None, pid=pid)
    return Failure(UnknownTelegramError(detail="unreachable"))


async def search_messages(
    client: TelegramClient, pid: PeerIdentifier, query: str, limit: int
) -> Result[list[ChatEvent], TelegramError]:
    resolved = await _resolve_peer(client, pid)
    match resolved:
        case Failure(err):
            return Failure(err)
        case Success(pair):
            entity, chat_peer = pair
            return await _fetch_events(client, entity, chat_peer, limit, search=query, pid=pid)
    return Failure(UnknownTelegramError(detail="unreachable"))


async def _fetch_events(
    client: TelegramClient,
    entity: Any,
    chat_peer: Peer,
    limit: int,
    *,
    search: str | None,
    pid: PeerIdentifier,
) -> Result[list[ChatEvent], TelegramError]:
    try:
        raw = (
            await client.get_messages(entity, limit=limit, search=search)
            if search is not None
            else await client.get_messages(entity, limit=limit)
        )
    except BaseException as exc:  # noqa: BLE001
        return Failure(_map_exception(exc, pid))

    events: list[ChatEvent] = []
    for r in raw:
        match wire.to_chat_event(r, chat_peer):
            case Success(ev):
                events.append(ev)
            case Failure(_):
                continue
    return Success(events)


async def send_message(
    client: TelegramClient,
    pid: PeerIdentifier,
    text: str,
    reply_to: int | None = None,
) -> Result[SendResult, TelegramError]:
    resolved = await _resolve_peer(client, pid)
    match resolved:
        case Failure(err):
            return Failure(err)
        case Success(pair):
            entity, _ = pair
            try:
                msg = await client.send_message(entity, text, reply_to=reply_to)
            except BaseException as exc:  # noqa: BLE001
                return Failure(_map_exception(exc, pid))
            return Success(SendResult(message_id=msg.id, date=msg.date))
    return Failure(UnknownTelegramError(detail="unreachable"))


async def get_chat_info(
    client: TelegramClient, pid: PeerIdentifier
) -> Result[Peer, TelegramError]:
    resolved = await _resolve_peer(client, pid)
    match resolved:
        case Failure(err):
            return Failure(err)
        case Success(pair):
            _, peer = pair
            return Success(peer)
    return Failure(UnknownTelegramError(detail="unreachable"))


async def download_media(
    client: TelegramClient, pid: PeerIdentifier, message_id: int
) -> Result[DownloadedMedia | None, TelegramError]:
    resolved = await _resolve_peer(client, pid)
    match resolved:
        case Failure(err):
            return Failure(err)
        case Success(pair):
            entity, _ = pair
            return await _download_media_for_entity(client, entity, message_id, pid)
    return Failure(UnknownTelegramError(detail="unreachable"))


async def _download_media_for_entity(
    client: TelegramClient, entity: Any, message_id: int, pid: PeerIdentifier
) -> Result[DownloadedMedia | None, TelegramError]:
    try:
        messages = await client.get_messages(entity, ids=message_id)
    except BaseException as exc:  # noqa: BLE001
        return Failure(_map_exception(exc, pid))

    if not messages or not messages[0] or not messages[0].media:
        return Success(None)

    msg = messages[0]
    try:
        data = await client.download_media(msg, bytes)
    except BaseException as exc:  # noqa: BLE001
        return Failure(_map_exception(exc, pid))

    if data is None:
        return Success(None)

    media_info = wire.to_media_info(msg.media)
    mime = (media_info.mime_type if media_info else None) or "application/octet-stream"
    return Success(DownloadedMedia(data=data, mime_type=mime))
