---
# Python Conventions

## Runtime
- Python 3.11+ only. `tomllib` is stdlib — import directly (no third-party `tomli`).
- `pyproject.toml` sets `>=3.12` — do not lower this constraint.

## HTTP
- `httpx` async for all HTTP. No `requests`.
- FastAPI handlers must be `async def`.
- Existing `requests` usage is tech debt — migrate if touching those files.

## Typing
- Type hints on every function — no untyped functions.
- No `Any` without an inline comment explaining why.

## Linting & Formatting
- `ruff` only — no black, no flake8, no isort.
- Run: `uv run ruff check src/ tests/` and `uv run ruff format src/ tests/`

## Output
- All terminal output via `Rich` — no raw `print()` in command handlers.

## Model Resolution
- Default: `claude-sonnet-4-6`.
- Always resolved via `resolve_model()` in `devbrief.core.credentials`.
- Chain: `DEVBRIEF_MODEL` env → `config.toml [anthropic] default_model` → `"claude-sonnet-4-6"`.
- Never hardcode a model string in any command file.

## Credentials
- Never log or print credentials (even partially).
- Never commit `.env` or `config.toml` to the repo.
- Config file permissions: `600` on write.

## Rust Extension
- If `devbrief_core` is unavailable at import time, fall back to Python implementation.
- Never hard-crash on a missing native extension.
