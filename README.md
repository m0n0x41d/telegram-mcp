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
- Telegram API credentials — create them at [my.telegram.org](https://my.telegram.org)

---

## Quick start (≈ 2 minutes)

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
3. **`./.env`** in the current working directory (legacy fallback for source checkouts)

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
