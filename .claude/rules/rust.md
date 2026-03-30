---
# Rust Conventions

## Quality
- `clippy` clean — zero warnings allowed. CI enforces this.
- No `unwrap()` in library code — use `?` or explicit error handling.

## Build Setup (PyO3 / maturin)
- `Cargo.toml` must declare `crate-type = ["cdylib", "rlib"]`:
  - `cdylib` — produces the Python extension module.
  - `rlib` — lets the linker produce a test binary.
- `maturin develop` to build and install locally.

## Running Tests

```
PYO3_BUILD_EXTENSION_MODULE=1 cargo test --manifest-path rust/Cargo.toml
```

- `PYO3_BUILD_EXTENSION_MODULE=1` tells PyO3 not to link against libpython
  (may not be available as a shared lib on the host).
- Tests only call pure Rust functions — no live Python interpreter needed.
- The `rust-check` CI job sets this env var automatically.

## Versioning
- Python and Rust share the same version number (semver).
- Update both `pyproject.toml` and `rust/Cargo.toml` versions simultaneously.
- Tag format: `v<major>.<minor>.<patch>`

## Scope
- Rust is used only for `devbrief env` (gitignore audit, .env drift, secret scan).
- Published as `devbrief-core` on crates.io.
- If unavailable at runtime, Python falls back gracefully — never hard-crash.
