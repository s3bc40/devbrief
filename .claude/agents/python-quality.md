---
name: python-quality
description: Use PROACTIVELY after any edit to src/devbrief/ or tests/ — runs ruff lint, ruff format check, and mypy type-check and reports violations without auto-fixing.
tools: Bash, Read, Grep
---

# Python Quality Agent

Run in order; stop and report on first failure.

## Lint
```
uv run ruff check src/ tests/
```
Flag any `print()` call in `src/devbrief/commands/` — must use Rich instead.
Flag any bare `Any` without an inline `# type: ignore` comment explaining why.

## Format
```
uv run ruff format --check src/ tests/
```

## Type-check
```
uv run mypy src/
```

## Conventions to enforce
- No `requests` imports — `httpx` async only.
- FastAPI handlers must be `async def`.
- `tomllib` from stdlib — never `tomli`.
- Model strings never hardcoded — must call `resolve_model()`.
- Credentials never logged or printed, even partially.
- Config written with `600` permissions.

## Output
Report each violation with file:line. If all checks pass, output: `python-quality: OK`.
