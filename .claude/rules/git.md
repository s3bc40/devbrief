---
# Git & PR Discipline

## Branch Naming
- `feat/<subcommand-or-description>`
- `fix/<short-description>`
- `chore/<short-description>`
- `docs/<short-description>`
- `test/<short-description>`

Never work directly on `main`.

## Commit Format — Conventional Commits

```
type(scope): description
```

Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`

- Atomic commits — one intention per commit.
- Never squash unless explicitly instructed.
- Never amend a commit that has already been pushed.

## PR Workflow
1. Create feature branch.
2. Work and commit atomically.
3. Push: `git push -u origin <branch>`
4. Open PR: `gh pr create` — title follows conventional commits.
5. **Stop. Do not merge. Sebastien reviews.**

## Versioning
- Semver. Python and Rust share the same version number.
- Update `pyproject.toml` and `rust/Cargo.toml` version + git tag simultaneously.
- Tag format: `v<major>.<minor>.<patch>`

## Hard Stops — Create BLOCKED.md and Halt
- Ambiguous spec on anything touching architecture.
- Test suite failing without an understood cause.
- Non-trivial merge conflict.
- Any operation touching credentials or `.env` files.
- Uncertainty about which branch to work on.
