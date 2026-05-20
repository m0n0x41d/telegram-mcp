"""Layer 0: Domain algebra.

Pure algebraic types — immutable, no I/O, no Telethon/MCP concerns.
Every type here maps 1-to-1 to a domain concept.

Inexpressible at this layer:
  - side effects, network calls, file I/O
  - Telethon wire types, MCP framework types
  - presentation (no __str__ / formatters)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


# --- Peer kinds ---


class PeerKind(Enum):
    USER = "user"
    GROUP = "group"
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"


@dataclass(frozen=True)
class Peer:
    id: int
    kind: PeerKind
    name: str
    username: str | None = None


# --- Peer identifier (sum type — how a peer is referenced from outside) ---


@dataclass(frozen=True)
class Username:
    value: str  # without leading @


@dataclass(frozen=True)
class PhoneNumber:
    value: str  # with leading +


@dataclass(frozen=True)
class NumericId:
    value: int


@dataclass(frozen=True)
class ChatTitle:
    value: str


PeerIdentifier = Username | PhoneNumber | NumericId | ChatTitle


# --- Media ---


class MediaKind(Enum):
    PHOTO = "photo"
    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    VOICE = "voice"
    STICKER = "sticker"
    OTHER = "other"


@dataclass(frozen=True)
class MediaInfo:
    kind: MediaKind
    file_name: str | None = None
    size: int | None = None
    mime_type: str | None = None


# --- Chat events (sum type — what appears in a chat history) ---


@dataclass(frozen=True)
class TextMessage:
    id: int
    text: str
    date: datetime
    sender: Peer | None
    chat: Peer
    reply_to_id: int | None = None
    media: MediaInfo | None = None


@dataclass(frozen=True)
class SystemAction:
    id: int
    date: datetime
    chat: Peer
    description: str  # short human-readable summary (e.g. "user joined")


ChatEvent = TextMessage | SystemAction


# --- Dialog ---


@dataclass(frozen=True)
class Dialog:
    peer: Peer
    unread_count: int
    last_message_date: datetime | None = None
    last_message_preview: str | None = None


# --- Operation results ---


@dataclass(frozen=True)
class SendResult:
    message_id: int
    date: datetime


@dataclass(frozen=True)
class DownloadedMedia:
    data: bytes
    mime_type: str


@dataclass(frozen=True)
class Identity:
    """Authenticated user — a Peer with USER kind plus the fact of authorization."""
    peer: Peer


# --- Error algebra ---


@dataclass(frozen=True)
class ParseError:
    input: str
    reason: str


@dataclass(frozen=True)
class ConversionError:
    type_name: str
    reason: str


@dataclass(frozen=True)
class PeerNotFound:
    identifier: PeerIdentifier


@dataclass(frozen=True)
class NotAuthorized:
    pass


@dataclass(frozen=True)
class RateLimited:
    wait_seconds: int


@dataclass(frozen=True)
class NetworkError:
    detail: str


@dataclass(frozen=True)
class UnknownTelegramError:
    detail: str


TelegramError = (
    PeerNotFound
    | NotAuthorized
    | RateLimited
    | NetworkError
    | UnknownTelegramError
    | ConversionError
)
