# Changelog

## 0.2.0

### Added
- `telegram-mcp` CLI (Typer + Rich) with subcommands:
  - `init` — interactive first-time setup; writes `~/.telegram-mcp/config.env` (mode `0600`)
  - `login` — Telegram authentication, persists session to `~/.telegram-mcp/session.session`
  - `doctor` — validates config, session file, and Telegram authorization
  - `run` — start the MCP stdio server (default when no subcommand given)
  - `config show` / `config path`
- Layered configuration loading: process env → `~/.telegram-mcp/config.env` → `./.env`
- Automatic one-time migration of legacy session from `~/.telegram-scout/telegram_session.session`
- `Makefile` with `install-pipx` / `build` / `dev-install` / `check` / `format` targets
- LICENSE file (MIT) and `[project.urls]` metadata

### Changed
- Internal architecture rewritten as layered FP pipeline:
  - `types.py` (L0) — algebraic domain types including `PeerIdentifier` (sum), `ChatEvent = TextMessage | SystemAction`, typed `TelegramError`
  - `wire.py` (L1a) — pure Telethon ↔ domain converters returning `Result`
  - `operations.py` (L1b) — async ops returning `Result[T, TelegramError]`
  - `formatters.py` (L2) — pure presentation
  - `session.py` (L3) — explicit `TelegramSession` (replaces global singletons)
  - `auth.py` (L4b), `config.py` (L4c) — single-responsibility modules
  - `tools.py` (L4a) — MCP transport boundary
  - `cli.py` (L5) — Typer operator surface, no Telethon imports
- `server.py` now runs everything inside a single `asyncio.run`, fixing
  `event loop must not change after connection` on first tool call
- MCP config in clients reduces to `{"command": "telegram-mcp"}` — no
  absolute paths, no `uv --directory`
- `telethon` floor bumped to `>=1.43.0` (handles 6-column session schema)
- Removed `python-dotenv` dependency in favor of explicit env-file parsing

### Removed
- Legacy `telegram-mcp-login` script alias and `login.py` shim
- Implicit `os.environ` mutation via `load_dotenv()`
