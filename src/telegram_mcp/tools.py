"""Layer 4a: MCP transport.

Maps MCP tool names to L1b operations and L2 formatters.
The transport boundary: typed Results in, strings out.

Inexpressible:
  - business logic (delegated to L1b)
  - formatting (delegated to L2)
  - session/auth lifecycle (received as TelegramSession)
"""

from __future__ import annotations

import os
import tempfile

from mcp.server.fastmcp import FastMCP
from returns.result import Failure, Success

from . import formatters as fmt
from . import operations as ops
from . import wire
from .session import TelegramSession


def register_tools(mcp: FastMCP, session: TelegramSession) -> None:

    @mcp.tool()
    async def list_dialogs(limit: int = 50) -> str:
        """List Telegram chats, groups, and channels.

        Args:
            limit: Maximum number of dialogs to return (default 50)
        """
        match await ops.list_dialogs(session.client, limit):
            case Failure(err):
                return fmt.format_telegram_error(err)
            case Success(dialogs):
                return "\n".join(fmt.format_dialog(d) for d in dialogs) or "No dialogs found."
        return ""

    @mcp.tool()
    async def read_messages(peer: str, limit: int = 20) -> str:
        """Read recent messages from a Telegram chat.

        Args:
            peer: Username (e.g. @username), phone number, chat title, or numeric ID
            limit: Number of messages to fetch (default 20, max 100)
        """
        match wire.parse_peer_identifier(peer):
            case Failure(err):
                return f"Invalid peer: {err.reason} ({err.input!r})"
            case Success(pid):
                match await ops.get_messages(session.client, pid, min(limit, 100)):
                    case Failure(err):
                        return fmt.format_telegram_error(err)
                    case Success(events):
                        rendered = [fmt.format_event(e) for e in reversed(events)]
                        return "\n".join(rendered) or "No messages found."
        return ""

    @mcp.tool()
    async def send_message(peer: str, text: str, reply_to: int | None = None) -> str:
        """Send a message in a Telegram chat.

        Args:
            peer: Username (e.g. @username), phone number, chat title, or numeric ID
            text: Message text to send
            reply_to: Optional message ID to reply to
        """
        match wire.parse_peer_identifier(peer):
            case Failure(err):
                return f"Invalid peer: {err.reason} ({err.input!r})"
            case Success(pid):
                match await ops.send_message(session.client, pid, text, reply_to):
                    case Failure(err):
                        return fmt.format_telegram_error(err)
                    case Success(result):
                        return fmt.format_send_result(result)
        return ""

    @mcp.tool()
    async def search_messages(peer: str, query: str, limit: int = 20) -> str:
        """Search for messages in a Telegram chat.

        Args:
            peer: Username (e.g. @username), phone number, chat title, or numeric ID
            query: Search query string
            limit: Maximum number of results (default 20, max 100)
        """
        match wire.parse_peer_identifier(peer):
            case Failure(err):
                return f"Invalid peer: {err.reason} ({err.input!r})"
            case Success(pid):
                match await ops.search_messages(session.client, pid, query, min(limit, 100)):
                    case Failure(err):
                        return fmt.format_telegram_error(err)
                    case Success(events):
                        rendered = [fmt.format_event(e) for e in reversed(events)]
                        return "\n".join(rendered) or "No messages found."
        return ""

    @mcp.tool()
    async def get_chat_info(peer: str) -> str:
        """Get information about a Telegram user, group, or channel.

        Args:
            peer: Username (e.g. @username), phone number, chat title, or numeric ID
        """
        match wire.parse_peer_identifier(peer):
            case Failure(err):
                return f"Invalid peer: {err.reason} ({err.input!r})"
            case Success(pid):
                match await ops.get_chat_info(session.client, pid):
                    case Failure(err):
                        return fmt.format_telegram_error(err)
                    case Success(p):
                        return fmt.format_peer(p)
        return ""

    @mcp.tool()
    async def download_media(peer: str, message_id: int) -> str:
        """Download media (photo, document, etc.) from a specific message.

        Args:
            peer: Username (e.g. @username), phone number, chat title, or numeric ID
            message_id: The message ID containing the media
        """
        match wire.parse_peer_identifier(peer):
            case Failure(err):
                return f"Invalid peer: {err.reason} ({err.input!r})"
            case Success(pid):
                match await ops.download_media(session.client, pid, message_id):
                    case Failure(err):
                        return fmt.format_telegram_error(err)
                    case Success(None):
                        return "No media found in this message."
                    case Success(media):
                        ext = media.mime_type.split("/")[-1] if "/" in media.mime_type else "bin"
                        fd, path = tempfile.mkstemp(suffix=f".{ext}")
                        os.write(fd, media.data)
                        os.close(fd)
                        return f"Media saved to: {path} ({len(media.data)} bytes, {media.mime_type})"
        return ""
