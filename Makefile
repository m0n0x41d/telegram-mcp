.PHONY: help install dev-install build install-pipx uninstall-pipx run login doctor init check format clean

SHELL := /bin/bash
CMD := uv run
VERSION := $(shell grep '^version' pyproject.toml | head -1 | sed -E 's/version = "(.+)"/\1/')
WHEEL := dist/telegram_mcp-$(VERSION)-py3-none-any.whl

help:
	@echo "Telegram MCP — make targets"
	@echo ""
	@echo "  install         install into current uv-managed venv"
	@echo "  dev-install     install with dev extras"
	@echo "  build           build wheel + sdist into ./dist"
	@echo "  install-pipx    build wheel and install/upgrade via pipx (recommended)"
	@echo "  uninstall-pipx  remove the pipx installation"
	@echo ""
	@echo "  init            run telegram-mcp init"
	@echo "  login           run telegram-mcp login"
	@echo "  doctor          run telegram-mcp doctor"
	@echo "  run             run the MCP stdio server in foreground"
	@echo ""
	@echo "  check           ruff lint --fix"
	@echo "  format          ruff format"
	@echo "  clean           remove dist/ build/ artifacts"

install:
	uv pip install -e .

dev-install:
	uv pip install -e ".[dev]"

build:
	uv build

install-pipx: build
	pipx install $(WHEEL) --force

uninstall-pipx:
	pipx uninstall telegram-mcp

init:
	$(CMD) telegram-mcp init

login:
	$(CMD) telegram-mcp login

doctor:
	$(CMD) telegram-mcp doctor

run:
	$(CMD) telegram-mcp run

check:
	$(CMD) ruff check . --fix

format:
	$(CMD) ruff format .

clean:
	rm -rf dist build *.egg-info src/*.egg-info
