# telegram-mcp

MCP server that gives AI agents full access to your Telegram account — read messages, send replies, search chats, download media.

Built on [Telethon](https://github.com/LonamiWebs/Telethon) + [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

## Tools

| Tool | Description |
|------|-------------|
| `list_dialogs` | List chats, groups, and channels |
| `read_messages` | Read recent messages from any chat |
| `send_message` | Send a message or reply |
| `search_messages` | Search messages within a chat |
| `get_chat_info` | Get info about a user, group, or channel |
| `download_media` | Download photos, documents, etc. from a message |

## Prerequisites

- Python **3.12+**
- [`pipx`](https://pipx.pypa.io/) (or [`uv`](https://docs.astral.sh/uv/) for the `uvx` flow)
- Telegram API credentials — see [Get API credentials](#get-api-credentials) below

---

## Get API credentials

This MCP is a **userbot** (acts on your personal Telegram account through MTProto/Telethon), not a `@BotFather` bot. Telegram requires every userbot to register an "app" and use its `api_id` + `api_hash`. **No way around this** — leaving them empty makes Telethon fail with `ValueError: Your API ID or Hash cannot be empty or None`.

The good news: registering an app is free and takes ~2 minutes.

1. Open **[https://my.telegram.org/auth](https://my.telegram.org/auth)** and log in with your phone (Telegram sends a code to your authorized device).
2. Click **API development tools**.
3. Fill in:
   - **App title** — anything, e.g. `telegram-mcp`
   - **Short name** — anything, e.g. `tg_mcp`
   - **Platform** — pick whatever (Desktop is fine)
   - **URL / Description** — leave blank
4. Submit. The next page shows your **`api_id`** (number) and **`api_hash`** (32-char hex). Copy both.

Keep them secret — anyone with these can impersonate your app (not your account, but Telegram may rate-limit/ban the app key if abused). `telegram-mcp init` stores them in `~/.telegram-mcp/config.env` with mode `0600`.

---

## Quick start (≈ 2 minutes after creds)

### 1. Install

**pipx from GitHub — recommended:**

```bash
pipx install git+https://github.com/m0n0x41d/telegram-mcp.git
pipx ensurepath   # first pipx install only
```

Pin a specific version (once tags exist):

```bash
pipx install git+https://github.com/m0n0x41d/telegram-mcp.git@v0.2.0
```

Upgrade later:

```bash
pipx upgrade telegram-mcp
# or, for git installs:
pipx reinstall telegram-mcp
```

### 2. Configure

```bash
telegram-mcp init
```

Walks you through `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE`. Saved to `~/.telegram-mcp/config.env` with `0600` permissions.

### 3. Authenticate

```bash
telegram-mcp login
```

Telegram sends you a verification code in-app; the session is persisted to `~/.telegram-mcp/session.session`.

### 4. Verify

```bash
telegram-mcp doctor
```

If everything is green you're done. Otherwise it tells you exactly what is missing.

### 5. Wire it into your MCP client

**Claude Code** — `.mcp.json`:

```json
{
  "mcpServers": {
    "telegram": { "command": "telegram-mcp" }
  }
}
```

**Claude Desktop** — `claude_desktop_config.json`: identical block. If `telegram-mcp` isn't on the PATH the GUI app sees, replace `"telegram-mcp"` with the full path printed by `which telegram-mcp` (usually `~/.local/bin/telegram-mcp`).

---

## Zero-install via `uvx`

If you don't want a global install, your MCP client can run the server straight from GitHub on each invocation:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/m0n0x41d/telegram-mcp.git",
        "telegram-mcp"
      ]
    }
  }
}
```

You still need a config and an authenticated session. Bootstrap them once with the same `uvx` form:

```bash
uvx --from git+https://github.com/m0n0x41d/telegram-mcp.git telegram-mcp init
uvx --from git+https://github.com/m0n0x41d/telegram-mcp.git telegram-mcp login
```

`uvx` caches the build, so subsequent runs are fast.

---

## CLI reference

| Command | Description |
|---------|-------------|
| `telegram-mcp init` | Interactive setup — writes `~/.telegram-mcp/config.env` |
| `telegram-mcp login` | Authenticate and persist the Telegram session |
| `telegram-mcp doctor` | Validate config, session, and authorization |
| `telegram-mcp run` | Start the MCP stdio server (default if no subcommand) |
| `telegram-mcp config path` | Print the config file path |
| `telegram-mcp config show` | Print resolved configuration (API_HASH redacted) |

---

## Configuration

Values are resolved in this order, first hit wins:

1. **Process environment variables** (set by the MCP client, your shell, etc.)
2. **`~/.telegram-mcp/config.env`** (written by `telegram-mcp init`)

The current working directory is never consulted — `telegram-mcp` is a user-global CLI, not a per-project tool, so it never reads `./.env`.

| Variable | Required | Default |
|----------|----------|---------|
| `TELEGRAM_API_ID` | yes | — |
| `TELEGRAM_API_HASH` | yes | — |
| `TELEGRAM_PHONE` | login only | — |
| `TELEGRAM_SESSION_PATH` | no | `~/.telegram-mcp/session` (falls back to `~/.telegram-scout/telegram_session` if only the legacy one exists) |

Run `telegram-mcp config show` to see which sources are currently active.

---

## Development

Clone-flow is for contributors, not end users:

```bash
git clone https://github.com/m0n0x41d/telegram-mcp.git
cd telegram-mcp
make dev-install    # uv pip install -e ".[dev]"
make run            # foreground stdio server
make check          # ruff lint --fix
make format         # ruff format
make build          # build wheel + sdist
make install-pipx   # build wheel and pipx-install it locally
```

See [CHANGELOG.md](CHANGELOG.md) for release history.

## License

[MIT](LICENSE)
