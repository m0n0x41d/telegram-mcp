"""Layer 4a entry: build and run the MCP stdio server.

Everything runs inside a single asyncio event loop. Creating the
TelegramClient in one loop and using it from another raises
`asyncio event loop must not change after connection`, so config load,
session open, MCP stdio loop, and teardown all share one `asyncio.run`.
"""

from __future__ import annotations

import asyncio
import sys

from mcp.server.fastmcp import FastMCP
from returns.result import Failure, Success

from . import config as cfg
from . import session as sess
from .tools import register_tools


def _abort(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


async def _serve() -> None:
    match cfg.load():
        case Failure(err):
            _abort(
                f"Missing config: {', '.join(err.missing)}.\n"
                f"Run `telegram-mcp init` to set up."
            )
            return
        case Success(config):
            await _serve_with_config(config)


async def _serve_with_config(config: cfg.Config) -> None:
    match await sess.open_session(config):
        case Failure(_):
            _abort("Not authorized. Run `telegram-mcp login` to authenticate first.")
            return
        case Success(session):
            mcp = FastMCP("telegram-mcp")
            register_tools(mcp, session)
            try:
                await mcp.run_stdio_async()
            finally:
                await sess.close_session(session)


def main() -> None:
    asyncio.run(_serve())
