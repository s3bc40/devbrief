---
# Testing Conventions

## Python — pytest

- **Required:** tests for every new command and every credential resolution path.
- Current count: ~122 Python tests across 5 test files.
- Test files mirror `src/devbrief/` structure:
  - `test_cache.py` — cache module + repo cache integration
  - `test_credentials.py` — credential resolution + auth command
  - `test_logs.py` — log parser, ring buffer, polling endpoints
  - `test_github.py` — GitHub fetchers
  - `test_display.py` — Rich display functions

## Credential Mocking
- **Always** mock credential reads in tests — never use real API keys.
- Mock at the `devbrief.core.credentials` boundary, not deeper.

## Running Python Tests

```
uv run pytest
```

## Rust — cargo test

- Current count: 12 `#[cfg(test)]` tests in `rust/`.
- `dev-dependencies` must include `tempfile` for filesystem tests.

## Running Rust Tests

```
PYO3_BUILD_EXTENSION_MODULE=1 cargo test --manifest-path rust/Cargo.toml
```

See `rust.md` for why this env var is required.

## CI
- `ci.yml` runs lint + type-check + Python tests on every PR and push to `main`.
- `rust-check` CI job runs Rust tests with `PYO3_BUILD_EXTENSION_MODULE=1` set automatically.
