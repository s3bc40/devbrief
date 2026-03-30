---
name: rust-quality
description: Use PROACTIVELY after any edit to rust/src/ — runs cargo clippy (zero warnings) and the full Rust test suite.
tools: Bash, Read
---

# Rust Quality Agent

## Clippy
```
PYO3_BUILD_EXTENSION_MODULE=1 cargo clippy --manifest-path rust/Cargo.toml -- -D warnings
```
Zero warnings allowed. CI enforces `-D warnings`; match that standard.

## Tests
```
PYO3_BUILD_EXTENSION_MODULE=1 cargo test --manifest-path rust/Cargo.toml
```

## Conventions to enforce
- No `unwrap()` in library code (`rust/src/lib.rs`) — use `?` or explicit match.
- `Cargo.toml` must keep `crate-type = ["cdylib", "rlib"]` — do not remove either.
- `PYO3_BUILD_EXTENSION_MODULE=1` is mandatory; never link against libpython in tests.
- Scope is `devbrief env` only — secret scan, gitignore audit, .env drift.
- Published crate name: `devbrief-core`. Do not rename.

## Version sync check
Verify `rust/Cargo.toml` version matches `pyproject.toml` version.
If they diverge, flag it — do not auto-fix.

## Output
Report clippy warnings and test failures with file:line. If all checks pass, output: `rust-quality: OK`.
