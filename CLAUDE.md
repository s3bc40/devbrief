# CLAUDE.md — DevBrief

## Project

DevBrief: developer CLI for **project situational awareness** — fetches structured data from a GitHub repo and generates a human-readable brief via Claude AI.

**Distribution:** PyPI (`devbrief`) + crates.io (`devbrief-core`)
**Stack:** Python (uv) + Rust (maturin/PyO3). No React, no Docker, no webpack.

---

## Commands

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check src/ tests/` |
| Format | `uv run ruff format src/ tests/` |
| Type check | `uv run mypy src/` |
| Rust tests | `PYO3_BUILD_EXTENSION_MODULE=1 cargo test --manifest-path rust/Cargo.toml` |
| Build wheel | `maturin develop` |

---

## Architecture — Do Not Change Without a Spec Card

- **Credential resolution:** env var → `.env` file → `~/.config/devbrief/config.toml` → keychain (future). Implemented in `devbrief.core.credentials`.
- **Cache key:** `sha256(url + commit_sha)` → `~/.cache/devbrief/`
- **Config file:** `~/.config/devbrief/config.toml`, permissions `600` on write.
- **Model:** always resolved via `resolve_model()` — never hardcoded in command files.
- **Rust extension:** `devbrief env` only. If unavailable at runtime, fall back to Python.
- **Assets:** `assets/` excluded from PyPI wheel via `[tool.maturin] exclude`.

---

## Subcommand Status

| Subcommand      | Status   | Notes                                                          |
|-----------------|----------|----------------------------------------------------------------|
| devbrief repo   | LIVE     | v0.3.2, SHA-keyed cache, --no-cache/--refresh                  |
| devbrief auth   | LIVE     | v0.2.0, key validation, config write/read/clear, 600 perms     |
| devbrief logs   | LIVE     | v0.3.0, FastAPI+HTMX polling dashboard, ring buffer, file/stdin|
| devbrief env    | LIVE     | v0.4.2, gitignore audit + .env drift + secret scan (Rust)      |
| devbrief api    | PLANNED  |                                                                |
| devbrief infra  | PLANNED  |                                                                |
| devbrief pr     | PLANNED  |                                                                |

---

## Current Sprint

All subcommands through v0.4.2 are LIVE. **Next action:** await spec card before touching any subcommand.

- **CI:** `ci.yml` runs lint + type-check + test on every PR and push to `main`.
- **Release:** `release.yml` on git tag `v*` — wheels only (no sdist), PyPI OIDC.
- **Versioning:** semver. Python and Rust share version. Update `pyproject.toml` + tag simultaneously.

---

## What NOT to Touch

- Do not push to `main` or merge PRs — Sebastien reviews.
- Do not hardcode model strings — always use `resolve_model()`.
- Do not use `print()` in command handlers — use Rich.
- Do not commit `.env` or `config.toml`.
- Do not build `sdist` — Rust extension requires Rust toolchain; wheels only.
- Do not implement new subcommands without a spec card.

---

## Conventions

See `.claude/rules/` for enforced coding conventions:
- `python.md` — Python conventions, async, typing, Rich, model resolution
- `rust.md` — PyO3/maturin, clippy, cargo test setup
- `testing.md` — pytest structure, cargo test, credential mocking
- `git.md` — branch naming, conventional commits, PR discipline, hard stops
