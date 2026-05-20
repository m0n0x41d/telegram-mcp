"""Layer 5: Operator surface (Typer + Rich).

Pure orchestration over L4 (config, auth, server). No Telethon imports here —
the auth module is the only authority that talks to Telethon for identity.

Inexpressible:
  - Telegram protocol details
  - MCP framework details
  - business logic
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import typer
from returns.result import Failure, Success
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import auth
from . import config as cfg

console = Console()
app = typer.Typer(
    help="Telegram MCP server — expose Telegram operations to AI agents.",
    no_args_is_help=False,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@app.command()
def init() -> None:
    """Interactive first-time setup: write ~/.telegram-mcp/config.env."""
    console.print(Panel("Telegram MCP — initial configuration", style="blue"))

    cfg.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    existing: dict[str, str] = {}
    if cfg.CONFIG_FILE.exists():
        console.print(f"[yellow]Existing config found:[/yellow] {cfg.CONFIG_FILE}")
        if not typer.confirm("Overwrite?", default=False):
            console.print("[red]Aborted.[/red]")
            raise typer.Exit(code=1)
        existing = cfg.parse_env_file(cfg.CONFIG_FILE)

    console.print(
        "\n[bold]Telegram API credentials[/bold] are required — this is a userbot\n"
        "(works from your personal account via MTProto), not a @BotFather bot.\n"
        "Get them in ~2 minutes:\n"
        "  1. Open [link=https://my.telegram.org/auth]https://my.telegram.org/auth[/link] and log in with your phone\n"
        "  2. Click [bold]API development tools[/bold]\n"
        "  3. Fill any [bold]App title[/bold] and [bold]Short name[/bold] (e.g. telegram-mcp) — leave the rest blank\n"
        "  4. Copy [bold]api_id[/bold] and [bold]api_hash[/bold] from the result page\n"
    )
    api_id = typer.prompt("TELEGRAM_API_ID", default=existing.get("TELEGRAM_API_ID", ""))
    api_hash = typer.prompt(
        "TELEGRAM_API_HASH",
        default=existing.get("TELEGRAM_API_HASH", ""),
        hide_input=True,
        show_default=False,
    )
    phone = typer.prompt(
        "TELEGRAM_PHONE (with country code, e.g. +12025551234)",
        default=existing.get("TELEGRAM_PHONE", ""),
    )

    _write_env_file(cfg.CONFIG_FILE, {
        "TELEGRAM_API_ID": api_id,
        "TELEGRAM_API_HASH": api_hash,
        "TELEGRAM_PHONE": phone,
    })
    os.chmod(cfg.CONFIG_FILE, 0o600)

    if not api_id or not api_hash:
        console.print(
            "\n[red]Note:[/red] TELEGRAM_API_ID and TELEGRAM_API_HASH are required by Telethon — "
            "without them `telegram-mcp login` will fail with ValueError. Re-run `telegram-mcp init` once you have them."
        )

    if _maybe_migrate_legacy_session():
        console.print(f"[green]Migrated legacy session →[/green] {cfg.DEFAULT_SESSION_PATH}.session")

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold cyan")
    table.add_column(style="white")
    table.add_row("Config:", str(cfg.CONFIG_FILE))
    table.add_row("Session dir:", str(cfg.CONFIG_DIR))
    console.print(Panel(table, title="Saved", style="green"))

    console.print("\nNext step: [code]telegram-mcp login[/code]")


@app.command()
def login() -> None:
    """Authenticate with Telegram and persist a session file."""
    match cfg.load(require_phone=True):
        case Failure(err):
            _report_config_error(err)
            raise typer.Exit(code=1)
        case Success(config):
            config.session_path.parent.mkdir(parents=True, exist_ok=True)
            io = auth.PromptIO(
                code=lambda: typer.prompt("Enter the verification code"),
                password=lambda: typer.prompt("Two-factor password", hide_input=True),
            )
            result = asyncio.run(auth.login(config, io))
            match result:
                case Failure(auth.MissingPhone()):
                    console.print("[red]TELEGRAM_PHONE not set.[/red]")
                    raise typer.Exit(code=1)
                case Failure(auth.TwoFactorFailed()):
                    console.print("[red]Two-factor authentication failed.[/red]")
                    raise typer.Exit(code=1)
                case Failure(other):
                    console.print(f"[red]Login failed:[/red] {other}")
                    raise typer.Exit(code=1)
                case Success(identity):
                    console.print(
                        f"[green]Logged in as[/green] "
                        f"{identity.peer.name} (id: {identity.peer.id})"
                    )
                    console.print(f"Session: {config.session_path}.session")


@app.command()
def doctor() -> None:
    """Check configuration and session health."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Details", style="dim white")

    loaded = cfg.load()
    match loaded:
        case Failure(err):
            table.add_row("Config", "[red]Missing[/red]", ", ".join(err.missing))
            console.print(table)
            console.print("\nRun [code]telegram-mcp init[/code] to set up.")
            raise typer.Exit(code=1)
        case Success(config):
            _run_doctor_checks(table, config)


def _run_doctor_checks(table: Table, config: cfg.Config) -> None:
    sources_str = ", ".join(str(s) for s in config.sources) or "process env only"
    table.add_row("Config", "[green]Loaded[/green]", sources_str)
    table.add_row("API_ID", "[green]OK[/green]", str(config.api_id))
    table.add_row("Session path", "[blue]—[/blue]", f"{config.session_path}.session")

    session_file = Path(f"{config.session_path}.session")
    if not session_file.exists():
        table.add_row("Session file", "[red]Missing[/red]", "run `telegram-mcp login`")
        console.print(table)
        raise typer.Exit(code=1)
    table.add_row("Session file", "[green]Present[/green]", f"{session_file.stat().st_size} bytes")

    match asyncio.run(auth.check_authorization(config)):
        case Success(identity):
            table.add_row(
                "Authorization", "[green]Active[/green]",
                f"{identity.peer.name} (id: {identity.peer.id})",
            )
            console.print(table)
        case Failure(_):
            table.add_row(
                "Authorization", "[red]Not authorized[/red]",
                "run `telegram-mcp login`",
            )
            console.print(table)
            raise typer.Exit(code=1)


@app.command()
def run() -> None:
    """Run the MCP stdio server (default when no subcommand given)."""
    from .server import main as server_main
    server_main()


config_app = typer.Typer(help="Inspect configuration.", no_args_is_help=True)
app.add_typer(config_app, name="config")


@config_app.command("path")
def config_path() -> None:
    """Print the config file path."""
    console.print(str(cfg.CONFIG_FILE))


@config_app.command("show")
def config_show() -> None:
    """Print resolved configuration (api_hash redacted)."""
    match cfg.load():
        case Failure(err):
            _report_config_error(err)
            raise typer.Exit(code=1)
        case Success(c):
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column(style="bold cyan")
            table.add_column(style="white")
            table.add_row("API_ID", str(c.api_id))
            table.add_row("API_HASH", c.api_hash[:4] + "…" + c.api_hash[-4:])
            table.add_row("PHONE", c.phone or "—")
            table.add_row("SESSION_PATH", str(c.session_path))
            table.add_row("SOURCES", ", ".join(str(s) for s in c.sources) or "process env only")
            console.print(table)


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in values.items() if v]
    path.write_text("\n".join(lines) + "\n")


def _maybe_migrate_legacy_session() -> bool:
    legacy = Path(f"{cfg.LEGACY_SESSION_PATH}.session")
    target = Path(f"{cfg.DEFAULT_SESSION_PATH}.session")
    if legacy.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
        return True
    return False


def _report_config_error(e: cfg.ConfigError) -> None:
    console.print(f"[red]Missing config:[/red] {', '.join(e.missing)}")
    if e.sources:
        console.print(f"Sources checked: {', '.join(str(s) for s in e.sources)}")
    console.print("\nRun [code]telegram-mcp init[/code] to set up.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
