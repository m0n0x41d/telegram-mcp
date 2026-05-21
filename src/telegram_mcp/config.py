"""Layer 4c: Configuration loading.

Pure read of two sources, merged with documented precedence.
No mutation of `os.environ` — the previous load_dotenv approach was a
hidden global side-effect; here we read each source explicitly into our
own Mapping and pick the first hit.

Resolution order (first hit wins):
1. Process environment variables
2. ~/.telegram-mcp/config.env

The CWD is never consulted — telegram-mcp is a user-global CLI, not a
per-project tool. Reading `./.env` from arbitrary working directories
leaks unrelated project secrets into telegram-mcp's process and breaks
when `.env` is a directory.

Inexpressible:
  - Telegram, Telethon, MCP concerns
  - mutation of process environment
  - per-project / per-CWD configuration
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from returns.result import Failure, Result, Success

CONFIG_DIR = Path.home() / ".telegram-mcp"
CONFIG_FILE = CONFIG_DIR / "config.env"
DEFAULT_SESSION_PATH = CONFIG_DIR / "session"
LEGACY_SESSION_PATH = Path.home() / ".telegram-scout" / "telegram_session"


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    phone: str | None
    session_path: Path
    sources: tuple[Path, ...]


@dataclass(frozen=True)
class ConfigError:
    missing: tuple[str, ...]
    sources: tuple[Path, ...]


def parse_env_file(path: Path) -> dict[str, str]:
    """Read a `.env`-style file into a plain dict. No interpolation, no quoting magic
    beyond stripping outer single/double quotes."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _lookup(name: str, layers: tuple[Mapping[str, str], ...]) -> str | None:
    for layer in layers:
        if name in layer and layer[name]:
            return layer[name]
    return None


def _resolve_session_path(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()
    if (
        not Path(f"{DEFAULT_SESSION_PATH}.session").exists()
        and Path(f"{LEGACY_SESSION_PATH}.session").exists()
    ):
        return LEGACY_SESSION_PATH
    return DEFAULT_SESSION_PATH


def load(*, require_phone: bool = False) -> Result[Config, ConfigError]:
    process_env: Mapping[str, str] = os.environ
    home_env = parse_env_file(CONFIG_FILE)
    layers = (process_env, home_env)

    sources: list[Path] = []
    if home_env:
        sources.append(CONFIG_FILE)

    api_id_raw = _lookup("TELEGRAM_API_ID", layers)
    api_hash = _lookup("TELEGRAM_API_HASH", layers)
    phone = _lookup("TELEGRAM_PHONE", layers)
    session_override = _lookup("TELEGRAM_SESSION_PATH", layers)

    missing: list[str] = []
    if not api_id_raw:
        missing.append("TELEGRAM_API_ID")
    if not api_hash:
        missing.append("TELEGRAM_API_HASH")
    if require_phone and not phone:
        missing.append("TELEGRAM_PHONE")
    if missing:
        return Failure(ConfigError(missing=tuple(missing), sources=tuple(sources)))

    assert api_id_raw is not None and api_hash is not None
    return Success(Config(
        api_id=int(api_id_raw),
        api_hash=api_hash,
        phone=phone,
        session_path=_resolve_session_path(session_override),
        sources=tuple(sources),
    ))
