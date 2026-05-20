"""Layer 2: Presentation.

Pure functions: domain values → human-readable strings.

Inexpressible:
  - I/O of any kind
  - MCP framework concerns
  - business logic / filtering decisions

Composition: format_events = "\n".join(format_event(e) for e in events).
"""

from __future__ import annotations

from .types import (
    ChatEvent,
    ChatTitle,
    Dialog,
    NetworkError,
    NotAuthorized,
    NumericId,
    Peer,
    PeerIdentifier,
    PeerNotFound,
    PhoneNumber,
    RateLimited,
    SendResult,
    SystemAction,
    TelegramError,
    TextMessage,
    UnknownTelegramError,
    Username,
)
from .types import ConversionError as _ConversionError


def format_peer(p: Peer) -> str:
    lines = [
        f"Name: {p.name}",
        f"Type: {p.kind.value}",
        f"ID: {p.id}",
    ]
    if p.username:
        lines.append(f"Username: @{p.username}")
    return "\n".join(lines)


def format_dialog(d: Dialog) -> str:
    unread = f" ({d.unread_count} unread)" if d.unread_count else ""
    kind = d.peer.kind.value
    username = f" @{d.peer.username}" if d.peer.username else ""
    peer_id = f" id:{d.peer.id}"
    preview = f"\n  > {d.last_message_preview}" if d.last_message_preview else ""
    return f"[{kind}] {d.peer.name}{username}{peer_id}{unread}{preview}"


def format_event(ev: ChatEvent) -> str:
    match ev:
        case TextMessage():
            return _format_text_message(ev)
        case SystemAction():
            return _format_system_action(ev)


def _format_text_message(m: TextMessage) -> str:
    sender = m.sender.name if m.sender else "Unknown"
    username = f" (@{m.sender.username})" if m.sender and m.sender.username else ""
    media_tag = f" [{m.media.kind.value}]" if m.media else ""
    reply_tag = f" (reply to #{m.reply_to_id})" if m.reply_to_id else ""
    return (
        f"[{m.date:%Y-%m-%d %H:%M}] #{m.id} "
        f"{sender}{username}{reply_tag}: {m.text}{media_tag}"
    )


def _format_system_action(s: SystemAction) -> str:
    return f"[{s.date:%Y-%m-%d %H:%M}] #{s.id} <system: {s.description}>"


def format_send_result(r: SendResult) -> str:
    return f"Message sent (id: {r.message_id}, date: {r.date:%Y-%m-%d %H:%M})"


def format_peer_identifier(pid: PeerIdentifier) -> str:
    match pid:
        case Username(value=u):
            return f"@{u}"
        case PhoneNumber(value=p):
            return p
        case NumericId(value=n):
            return str(n)
        case ChatTitle(value=t):
            return t


def format_telegram_error(err: TelegramError) -> str:
    match err:
        case PeerNotFound(identifier=pid):
            return f"Peer not found: {format_peer_identifier(pid)}"
        case NotAuthorized():
            return "Not authorized. Run `telegram-mcp login` to authenticate."
        case RateLimited(wait_seconds=secs):
            return f"Rate limited by Telegram. Retry after {secs}s."
        case NetworkError(detail=d):
            return f"Network error: {d}"
        case _ConversionError(type_name=t, reason=r):
            return f"Conversion error ({t}): {r}"
        case UnknownTelegramError(detail=d):
            return f"Telegram error: {d}"
