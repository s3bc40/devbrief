# devbrief

> Generate a human-readable project brief for any GitHub repository using Claude AI.

`devbrief` takes a GitHub URL, pulls the repository metadata, README, and file tree, then asks Claude to produce a structured brief — covering what the project does, its tech stack, how to get started, and its limitations — directly in your terminal.

---

## Installation

### pip

```bash
pip install devbrief
```

### uvx (run without installing)

```bash
uvx devbrief <github-url>
```

### uv (install globally)

```bash
uv tool install devbrief
```

---

## Prerequisites

An [Anthropic API key](https://console.anthropic.com/) is required.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or place it in a `.env` file at your working directory:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Usage

```bash
devbrief <github-url> [--output FILE]
```

### Examples

```bash
# Print the brief to the terminal
devbrief https://github.com/anthropics/anthropic-sdk-python

# Save the brief as a markdown file
devbrief https://github.com/astral-sh/uv --output uv-brief.md
```

### Options

| Option | Short | Description |
|---|---|---|
| `--output FILE` | `-o` | Save the brief as a markdown file |
| `--help` | | Show usage and exit |

### Output sections

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
            └── Structured prompt → Claude claude-opus-4-6 → Rich terminal output
```

---

## Development

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/s3bc40/devbrief
cd devbrief
uv sync
```

### Run locally

```bash
uv run devbrief https://github.com/s3bc40/devbrief
```

### Run tests

```bash
uv run pytest
```

Tests cover URL parsing, GitHub API response mapping, edge cases (missing README, empty file tree), and Rich display output. No real API calls are made — all HTTP responses are mocked.

### Project structure

```
src/devbrief/
├── main.py       # Click CLI entry point
├── github.py     # GitHub REST API fetchers
├── brief.py      # Prompt construction and Claude API call
└── display.py    # Rich terminal rendering
tests/
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
