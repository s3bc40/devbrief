---
name: subcommand-impl
description: Use PROACTIVELY when asked to implement a new devbrief subcommand — scaffolds the command file, registers it in cli.py, and creates a corresponding test skeleton.
tools: Read, Write, Edit, Bash, Glob, Grep
---

# Subcommand Implementation Agent

## Pre-flight check
1. Confirm a spec card exists for this subcommand. If not, write `BLOCKED.md` and halt.
2. Verify the subcommand is listed as PLANNED in `CLAUDE.md`. If absent, write `BLOCKED.md` and halt.

## Scaffold steps
1. Create `src/devbrief/commands/<name>.py` — model from `commands/repo.py`.
2. Register the command in `src/devbrief/cli.py` with `app.add_typer(...)` or `@app.command`.
3. Create `tests/test_<name>.py` with at least one happy-path and one error-path test.

## Conventions
- Handler function must be `async def`.
- All output via Rich — no `print()`.
- HTTP via `httpx` async — no `requests`.
- Type hints on every function; no untyped signatures.
- Model via `resolve_model()` from `devbrief.core.credentials` — never hardcoded.
- Credential mocks in tests target `devbrief.core.credentials` boundary.

## After scaffold
Spawn `python-quality` and `test-runner` agents to validate the new files before committing.

## Output
List files created/modified. Flag any convention violation found during scaffold.
