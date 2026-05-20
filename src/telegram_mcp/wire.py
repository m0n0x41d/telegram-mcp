"""Layer 1a: Wire → Domain converters.

Pure functions. No network, no client, no I/O.
Telethon wire types come in; domain types come out wrapped in Result.

No silent fallbacks: an unrecognized entity becomes Failure(ConversionError),
not a bogus Peer with id=0.

Inexpressible:
  - async / await (no I/O here)
  - MCP framework concerns
  - presentation
"""

from __future__ import annotations

from typing import Any

from returns.result import Failure, Result, Success
from telethon.tl.types import (
    Channel as TlChannel,
    Chat as TlChat,
    MessageMediaDocument,
    MessageMediaPhoto,
    User as TlUser,
)

from .types import (
    ChatEvent,
    ChatTitle,
    ConversionError,
    Dialog,
    MediaInfo,
    MediaKind,
    NumericId,
    ParseError,
    Peer,
    PeerIdentifier,
    PeerKind,
    PhoneNumber,
    SystemAction,
    TextMessage,
    Username,
)


# --- Parse peer identifier from raw string ---


def parse_peer_identifier(raw: str) -> Result[PeerIdentifier, ParseError]:
    s = raw.strip()
    if not s:
        return Failure(ParseError(input=raw, reason="empty"))

    if s.startswith("@"):
        rest = s[1:]
        if not rest:
            return Failure(ParseError(input=raw, reason="empty username after @"))
        if not _is_username_chars(rest):
            return Failure(ParseError(input=raw, reason="invalid username characters"))
        return Success(Username(value=rest))

    if s.startswith("+"):
        digits = s[1:]
        if not digits or not digits.isdigit():
            return Failure(ParseError(input=raw, reason="invalid phone number"))
        return Success(PhoneNumber(value=s))

    if _is_int_literal(s):
        return Success(NumericId(value=int(s)))

    return Success(ChatTitle(value=s))


def _is_username_chars(s: str) -> bool:
    return all(c.isalnum() or c == "_" for c in s)


def _is_int_literal(s: str) -> bool:
    stripped = s[1:] if s.startswith("-") else s
    return bool(stripped) and stripped.isdigit()


# --- Telethon entity → Peer ---


def to_peer(entity: Any) -> Result[Peer, ConversionError]:
    if isinstance(entity, TlUser):
        name = " ".join(filter(None, [entity.first_name, entity.last_name]))
        return Success(Peer(
            id=entity.id,
            kind=PeerKind.USER,
            name=name or "Deleted Account",
            username=entity.username,
        ))

    if isinstance(entity, TlChannel):
        kind = PeerKind.CHANNEL if entity.broadcast else PeerKind.SUPERGROUP
        return Success(Peer(
            id=entity.id,
            kind=kind,
            name=entity.title or "",
            username=entity.username,
        ))

    if isinstance(entity, TlChat):
        return Success(Peer(
            id=entity.id,
            kind=PeerKind.GROUP,
            name=entity.title or "",
        ))

    return Failure(ConversionError(
        type_name=type(entity).__name__,
        reason="unknown telethon entity type",
    ))


# --- Telethon media → MediaInfo (None when no media) ---


def to_media_info(media: Any) -> MediaInfo | None:
    if media is None:
        return None

    if isinstance(media, MessageMediaPhoto):
        return MediaInfo(kind=MediaKind.PHOTO)

    if isinstance(media, MessageMediaDocument):
        doc = media.document
        if doc is None:
            return None
        mime = getattr(doc, "mime_type", None)
        file_name = _extract_file_name(doc)
        return MediaInfo(
            kind=_classify_document(mime),
            file_name=file_name,
            size=doc.size,
            mime_type=mime,
        )

    return MediaInfo(kind=MediaKind.OTHER)


def _extract_file_name(doc: Any) -> str | None:
    for attr in getattr(doc, "attributes", []):
        if hasattr(attr, "file_name"):
            return attr.file_name
    return None


def _classify_document(mime: str | None) -> MediaKind:
    if not mime:
        return MediaKind.DOCUMENT
    if mime.startswith("video/"):
        return MediaKind.VIDEO
    if mime.startswith("audio/"):
        return MediaKind.AUDIO
    if "ogg" in mime:
        return MediaKind.VOICE
    if mime == "image/webp":
        return MediaKind.STICKER
    return MediaKind.DOCUMENT


# --- Telethon message → ChatEvent ---


def to_chat_event(msg: Any, chat: Peer) -> Result[ChatEvent, ConversionError]:
    if msg is None:
        return Failure(ConversionError(type_name="NoneType", reason="message is None"))

    if getattr(msg, "action", None) is not None:
        return Success(SystemAction(
            id=msg.id,
            date=msg.date,
            chat=chat,
            description=type(msg.action).__name__,
        ))

    sender: Peer | None = None
    if hasattr(msg, "sender") and msg.sender is not None:
        match to_peer(msg.sender):
            case Success(p):
                sender = p
            case Failure(_):
                sender = None

    reply_to_id = None
    if getattr(msg, "reply_to", None) is not None:
        reply_to_id = getattr(msg.reply_to, "reply_to_msg_id", None)

    return Success(TextMessage(
        id=msg.id,
        text=msg.text or "",
        date=msg.date,
        sender=sender,
        chat=chat,
        reply_to_id=reply_to_id,
        media=to_media_info(msg.media),
    ))


# --- Telethon dialog → Dialog ---


def to_dialog(raw: Any) -> Result[Dialog, ConversionError]:
    peer_result = to_peer(raw.entity)
    match peer_result:
        case Failure(err):
            return Failure(err)
        case Success(peer):
            preview = None
            last_date = None
            if raw.message is not None:
                preview = raw.message.text[:100] if raw.message.text else None
                last_date = raw.message.date
            return Success(Dialog(
                peer=peer,
                unread_count=raw.unread_count,
                last_message_date=last_date,
                last_message_preview=preview,
            ))
