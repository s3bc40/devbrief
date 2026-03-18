# devbrief

> Project situational awareness.

`devbrief` is a developer CLI for rapid project situational awareness:

- **`devbrief repo`** — takes a GitHub URL, pulls repository metadata, README, and file tree, then asks Claude to produce a structured brief directly in your terminal.
- **`devbrief logs`** — streams a log file (or stdin) into a local browser dashboard with live filtering, level highlighting, and rolling metrics.

---

## Installation

### pip

```bash
pip install devbrief
```

### uvx (run without installing)

```bash
uvx devbrief repo <github-url>
```

### uv (install globally)

```bash
uv tool install devbrief
```

---

## Setup

An [Anthropic API key](https://console.anthropic.com/) is required. Store it securely with:

```bash
devbrief auth
```

This validates your key against the Anthropic API and writes it to `~/.config/devbrief/config.toml` with `600` permissions. You will not be prompted again until the key is cleared or replaced.

**CI / non-interactive environments:**

```bash
devbrief auth --api-key "$ANTHROPIC_API_KEY"
# or just export the env var — devbrief picks it up automatically
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

```
 Usage: devbrief [OPTIONS] COMMAND [ARGS]...

 Project situational awareness.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.      │
│ --show-completion             Show completion for the current shell, to copy │
│                               it or customize the installation.              │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ repo  Analyze a GitHub repository.                                           │
│ auth  Manage API credentials.                                                │
│ logs  Stream logs into a live dashboard.                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### devbrief repo

```bash
devbrief repo <github-url> [--output FILE]
```

**Examples:**

```bash
# Print the brief to the terminal
devbrief repo https://github.com/anthropics/anthropic-sdk-python

# Save the brief as a markdown file
devbrief repo https://github.com/astral-sh/uv --output uv-brief.md
```

| Option | Short | Description |
|---|---|---|
| `--output FILE` | `-o` | Save the brief as a markdown file |
| `--help` | | Show usage and exit |

### devbrief auth

```bash
devbrief auth                        # interactive prompt (hidden input)
devbrief auth --api-key sk-ant-...   # non-interactive
devbrief auth --show                 # display masked stored key
devbrief auth --clear                # remove stored key
```

### devbrief logs

```bash
devbrief logs [FILE] [--port PORT] [--no-browser]
```

Opens a local browser dashboard at `http://127.0.0.1:7890` (default port).

**Examples:**

```bash
# Visualise a log file
devbrief logs /var/log/app.log

# Pipe from a running process
your-app 2>&1 | devbrief logs

# Use a custom port
devbrief logs /var/log/app.log --port 8080
```

| Option | Description |
|---|---|
| `FILE` | Path to a log file. Omit to read from stdin. |
| `--port PORT` | Dashboard port (default: `7890`) |
| `--no-browser` | Do not open the browser automatically |
| `--help` | Show usage and exit |

The dashboard auto-detects common log formats (JSON structured logs, ISO timestamp prefix, `[LEVEL]`, `LEVEL:`) and supports live client-side filtering by level, keyword, and time range. New lines appended to the file appear within ~3 seconds.

---

## Credential resolution order

1. `--api-key` flag
2. `ANTHROPIC_API_KEY` environment variable
3. `~/.config/devbrief/config.toml`
4. Error with instructions to run `devbrief auth`

---

## Output sections

Each generated brief contains:

- **One-line description** — a crisp summary of the project
- **Problem it solves** — the core need being addressed
- **Tech stack** — detected languages, frameworks, and tools
- **Getting started** — steps extracted from the README
- **Who would find it useful** — the target audience
- **Limitations / potential improvements** — honest trade-offs

---

## How it works

```
GitHub URL
    │
    ├── /repos/:owner/:repo        → name, description, stars, language, topics
    ├── /repos/:owner/:repo/readme → decoded README content (first 3000 chars)
    └── /repos/:owner/:repo/contents → top-level file tree
            │
            └── Structured prompt → Claude (model from config) → Rich terminal output
```

---

## Migrating from v0.1.x

| v0.1.x | v0.2.x |
|---|---|
| `devbrief <url>` | `devbrief repo <url>` |
| `export ANTHROPIC_API_KEY=...` | `devbrief auth` (or keep the env var) |

---

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/s3bc40/devbrief
cd devbrief
uv sync --all-groups
```

### Run locally

```bash
uv run devbrief repo https://github.com/s3bc40/devbrief
```

### Run tests

```bash
uv run pytest
```

### Lint

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

### Project structure

```
src/devbrief/
├── cli.py               # Typer app — registers all subcommands
├── commands/
│   ├── repo.py          # devbrief repo
│   ├── auth.py          # devbrief auth
│   └── logs.py          # devbrief logs — FastAPI server, log parser, ring buffer
├── templates/
│   ├── base.html        # Base HTML layout (HTMX)
│   └── logs/
│       └── dashboard.html  # Log dashboard template
├── core/
│   ├── credentials.py   # API key + model resolution chain
│   └── config.py        # Config file read/write (~/.config/devbrief/config.toml)
├── github.py            # GitHub REST API fetchers
├── brief.py             # Prompt construction and Claude API call
└── display.py           # Rich terminal rendering
tests/
├── test_credentials.py  # Credential resolution + auth command tests
├── test_logs.py         # Log parser, ring buffer, polling endpoints
├── test_github.py
└── test_display.py
```

---

## Contributing

1. Fork the repository and create a branch from `main`.
2. Make focused commits with explicit messages (one concern per commit).
3. Add or update tests for any changed behaviour.
4. Open a pull request — describe the problem and your solution.

Please do not open issues to ask for new AI providers or models; the project is intentionally scoped to the Anthropic API.

---

## License

MIT — see [LICENSE](LICENSE) for details.
