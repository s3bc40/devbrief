# CLAUDE.md — DevBrief Agent Memory

## 1. Project Identity

DevBrief is a developer CLI tool for **project situational awareness**: given a GitHub repository URL (and later: log streams, API endpoints, infra configs, and PRs), it fetches structured data and generates a human-readable brief via Claude AI. The tool is designed for developers who need rapid context on any project without reading every file manually.

**Tagline:** Project situational awareness
**Distribution:** PyPI (`devbrief`) + crates.io (`devbrief-core`)

---

## 2. Tech Stack

**Python layer:**
- `typer` — CLI framework (migration target from current `click`)
- `fastapi` + `jinja2` + HTMX — web UI for future `devbrief serve`
- SSE (Server-Sent Events) — streaming output in web UI
- `httpx` (async) — HTTP client (migration target from current `requests`)
- `boto3` — AWS integration for `devbrief logs`
- `anthropic` SDK — Claude AI integration
- `tomllib` (stdlib, Python 3.11+) — config file parsing
- `uv` — package manager and virtual env

**Rust layer:**
- `maturin` + `PyO3` — Rust extensions callable from Python
- Enters via `devbrief env` subcommand
- Published as `devbrief-core` on crates.io

**Not used:** React, Node, webpack, Docker (end users install via pip/cargo only)

---

## 3. Project Structure

```
devbrief/
├── src/
│   └── devbrief/
│       ├── __init__.py          # Package init
│       ├── cli.py               # Typer app — registers all subcommands
│       ├── commands/
│       │   ├── repo.py          # devbrief repo (cache-aware)
│       │   ├── auth.py          # devbrief auth
│       │   └── logs.py          # devbrief logs — FastAPI server, log parser, ring buffer
│       ├── core/
│       │   ├── credentials.py   # API key + model resolution chain
│       │   ├── config.py        # Config file read/write (~/.config/devbrief/config.toml)
│       │   └── cache.py         # Brief cache keyed by sha256(url+commit_sha) → ~/.cache/devbrief/
│       ├── github.py            # GitHub REST API fetchers (+ fetch_latest_commit_sha)
│       ├── brief.py             # Claude prompt builder and generate_brief()
│       └── display.py           # Rich terminal display functions
├── tests/
│   ├── __init__.py
│   ├── test_cache.py            # Cache module + repo cache integration tests
│   ├── test_credentials.py      # Credential resolution + auth command tests
│   ├── test_logs.py             # Log parser, ring buffer, polling endpoints
│   ├── test_github.py           # Unit tests for GitHub fetchers
│   └── test_display.py          # Unit tests for Rich display functions
├── dist/                        # Built distributions (gitignored except .gitignore)
├── .github/
│   └── workflows/
│       ├── ci.yml               # CI: lint + test on every PR and push to main
│       └── release.yml          # Release: build + publish to PyPI on git tag v*
├── pyproject.toml               # Project metadata, deps, build config (hatchling)
├── uv.lock                      # Locked dependency tree
├── README.md                    # PyPI-ready README
├── assets/
│   ├── devbrief-cache.gif       # Demo GIF embedded in README (excluded from wheel)
│   └── vhs/
│       └── devbrief-cache.tape  # VHS tape source used to record the demo GIF
├── LICENSE                      # MIT
├── CLAUDE.md                    # This file — agent persistent memory
└── .gitignore
```

**Assets policy:** `assets/` is excluded from the PyPI wheel via `[tool.hatch.build.targets.wheel] exclude`. GIFs and tapes are repo-only. To regenerate the GIF: `vhs assets/vhs/devbrief-cache.tape`.

---

## 4. Subcommand Status

| Subcommand      | Status      | Notes                                          |
|-----------------|-------------|------------------------------------------------|
| devbrief repo   | LIVE        | v0.3.1, cache layer (SHA-keyed, ~/.cache/devbrief/), --no-cache/--refresh |
| devbrief auth   | LIVE        | v0.2.0, key validation, config write/read/clear, 600 perms   |
| devbrief logs   | LIVE        | v0.3.0, FastAPI+HTMX polling dashboard, ring buffer, file (1s tail)/stdin |
| devbrief env    | PLANNED     | Rust entry point via maturin/PyO3              |
| devbrief api    | PLANNED     |                                                |
| devbrief infra  | PLANNED     |                                                |
| devbrief pr     | PLANNED     |                                                |



---

## 5. Credential System

**Layered resolution chain (highest priority first):**
1. Environment variable (e.g. `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`)
2. `.env` file in working directory (loaded via `python-dotenv`)
3. `~/.config/devbrief/config.toml` — user-level config file
4. System keychain (future, not yet implemented)

**Config file:** `~/.config/devbrief/config.toml`
**File permissions:** `600` (user read/write only — enforce on write)
**Rules:**
- Never log credentials
- Never print credentials (even partially) in normal output
- Never commit `.env` files or `config.toml` to the repo
- Tests must mock credential reads — never use real keys in tests

---

## 6. CI/CD Rules

- **`ci.yml`**: Runs on every PR and push to `main`. Steps: lint (ruff), type-check, test (pytest).
- **`release.yml`**: Runs on git tag push matching `v*`. Steps: build wheel + sdist, publish to PyPI via trusted publishing (OIDC).
- **Branch strategy:** `main` is protected. Feature branches: `feat/<subcommand-name>` or `feat/<short-description>`.
- **Conventional commits:** `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`
- **Versioning:** semver. Python and Rust share the same version number. Update `pyproject.toml` version and tag simultaneously.

---

## 7. Coding Rules (Enforce Always)

- **Python 3.11+ only** — `tomllib` is stdlib, import it directly. (`pyproject.toml` currently sets `>=3.12`.)
- **Async-first:** Use `httpx` async for all HTTP. FastAPI handlers must be `async def`. (Current `requests` usage is tech debt to migrate.)
- **Ruff** for linting and formatting — no other linters, no black, no flake8.
- **Type hints everywhere** — no untyped functions, no `Any` without explanation.
- **Rust:** `clippy` clean, zero warnings allowed.
- **Tests required** for every new command and every credential resolution path.
- **Default model:** `claude-sonnet-4-6`. Never hardcode a model string in any command file. Model is always resolved via `resolve_model()` in `devbrief.core.credentials` (env var `DEVBRIEF_MODEL` → `config.toml [anthropic] default_model` → `"claude-sonnet-4-6"`).
- **Graceful degradation:** If Rust extension is unavailable, fall back to Python implementation. Never hard-crash on missing native extension.
- **Rich** for all terminal output — no raw `print()` in command handlers.

---

## 8. Agent Boundaries

- **You implement. You do not decide architecture.**
- If a spec is ambiguous, stop and ask before writing code.
- If a decision would be hard to reverse (schema changes, public API shape, breaking changes), flag it before proceeding.
- When a task is complete, summarize: what was built, what files changed, what tests cover it.
- Read this file at the start of every session. If a subcommand ships or status changes, update the table in section 4.

---

## 9. Current Task Queue

1. [x] Create CLAUDE.md
2. [x] Set up CI/CD pipeline (`ci.yml` + `release.yml`) — Rust steps present as commented stubs
3. [x] v0.2.0: CLI restructure (`devbrief repo`), `devbrief auth`, credential + model resolution
4. [x] v0.3.0: `devbrief logs` — FastAPI+HTMX polling dashboard, ring buffer, file/stdin
5. [x] v0.3.1: `devbrief repo` cache layer — SHA-keyed local cache, --no-cache/--refresh flags
6. [ ] Await spec card before touching any subcommand
