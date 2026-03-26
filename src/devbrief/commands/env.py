"""devbrief env — Project environment health checks."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

if TYPE_CHECKING:
    from devbrief._devbrief_core import EnvDiff, SecretMatch

# ---------------------------------------------------------------------------
# Rust extension — imported at module level for easy mocking in tests.
# Falls back gracefully if the extension is not compiled.
#
# Variables are declared with explicit Optional[Callable] types so that:
#   • the IDE resolves EnvDiff / SecretMatch via the .pyi stub, and
#   • no `type: ignore` is needed on the None fallback.
# ---------------------------------------------------------------------------

_diff_env_files: Callable[[str, str], "EnvDiff"] | None = None
_scan_secrets: Callable[[str], "list[SecretMatch]"] | None = None

try:
    from devbrief._devbrief_core import diff_env_files as _diff_env_files
    from devbrief._devbrief_core import scan_secrets as _scan_secrets
except ImportError:
    pass  # already None — Rust extension not compiled

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_GITIGNORE_ENTRIES: list[str] = [
    ".env",
    ".env.local",
    ".env.*.local",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_rsa.*",
    ".aws/credentials",
]

_console = Console()


# ---------------------------------------------------------------------------
# Check helpers — each returns (errors, warnings)
# ---------------------------------------------------------------------------


def _check_gitignore(root: Path, quiet: bool) -> tuple[int, int]:
    """Check .gitignore presence and required entries."""
    errors = 0
    warnings = 0
    gitignore = root / ".gitignore"

    if not gitignore.exists():
        errors += 1
        if quiet:
            print("ERROR  .gitignore            not found")
        else:
            _console.print(
                "  [red]\u274c[/red]  [bold].gitignore[/bold]           [red]not found[/red]"
            )
        return errors, warnings

    if quiet:
        print("OK     .gitignore            present")
    else:
        _console.print(
            "  [green]\u2705[/green]  [bold].gitignore[/bold]           present"
        )

    lines = {
        line.strip()
        for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    }
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        if entry not in lines:
            warnings += 1
            if quiet:
                print(f"WARN   .gitignore            missing entry: {entry}")
            else:
                _console.print(
                    f"  [yellow]\u26a0\ufe0f[/yellow]   [bold].gitignore[/bold]"
                    f"           missing entry: {entry}"
                )

    return errors, warnings


def _check_env_drift(root: Path, quiet: bool) -> tuple[int, int]:
    """Check .env vs .env.example key drift via Rust extension."""
    errors = 0
    warnings = 0

    if _diff_env_files is None:
        if quiet:
            print("INFO   .env drift            Rust extension unavailable, skipping")
        else:
            _console.print(
                "  [dim]\u2139\ufe0f   .env drift           Rust extension unavailable, skipping[/dim]"
            )
        return errors, warnings

    env_path = root / ".env"
    example_path = root / ".env.example"

    if not env_path.exists():
        if quiet:
            print("INFO   .env drift            .env not found, skipping")
        else:
            _console.print(
                "  [dim]\u2139\ufe0f   .env drift           .env not found, skipping[/dim]"
            )
        return errors, warnings

    if not example_path.exists():
        if quiet:
            print("INFO   .env drift            .env.example not found, skipping")
        else:
            _console.print(
                "  [dim]\u2139\ufe0f   .env drift           .env.example not found, skipping[/dim]"
            )
        return errors, warnings

    diff = _diff_env_files(str(env_path), str(example_path))

    for key in diff.missing_from_env:
        warnings += 1
        if quiet:
            print(f"WARN   .env drift            {key} missing from .env")
        else:
            _console.print(
                f"  [yellow]\u26a0\ufe0f[/yellow]   [bold].env drift[/bold]"
                f"           {key} missing from .env"
            )

    for key in diff.undocumented_in_example:
        warnings += 1
        if quiet:
            print(f"WARN   .env drift            {key} undocumented in .env.example")
        else:
            _console.print(
                f"  [yellow]\u26a0\ufe0f[/yellow]   [bold].env drift[/bold]"
                f"           {key} undocumented in .env.example"
            )

    if not diff.missing_from_env and not diff.undocumented_in_example:
        if quiet:
            print("OK     .env drift            all .env.example keys present")
        else:
            _console.print(
                "  [green]\u2705[/green]  [bold].env drift[/bold]           all .env.example keys present"
            )

    return errors, warnings


def _check_secrets(root: Path, quiet: bool) -> tuple[int, int]:
    """Scan committed files for secret patterns via Rust extension."""
    errors = 0
    warnings = 0

    if _scan_secrets is None:
        if quiet:
            print("INFO   Secret scan           Rust extension unavailable, skipping")
        else:
            _console.print(
                "  [dim]\u2139\ufe0f   Secret scan          Rust extension unavailable, skipping[/dim]"
            )
        return errors, warnings

    matches = _scan_secrets(str(root))

    for match in matches:
        errors += 1
        loc = f"{match.file}:{match.line}"
        if quiet:
            print(
                f"ERROR  Secret detected       {loc} \u2014"
                f" {match.pattern_name} ({match.masked_value})"
            )
        else:
            _console.print(
                f"  [red]\u274c[/red]  [bold]Secret detected[/bold]      "
                f"[cyan]{loc}[/cyan] \u2014 {match.pattern_name}"
                f" ([yellow]{match.masked_value}[/yellow])"
            )

    return errors, warnings


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def env_command(
    path: Annotated[
        Path,
        typer.Argument(
            help="Project root to scan. Default: current working directory."
        ),
    ] = Path("."),
    strict: Annotated[
        bool,
        typer.Option(
            "--strict", help="Treat warnings as errors. Exit 1 if any warnings."
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet", help="Suppress Rich formatting. Plain text output only."
        ),
    ] = False,
) -> None:
    """Check project environment health: .gitignore, .env drift, and secret scanning."""
    root = path.resolve()

    if not quiet:
        _console.print()

    total_errors = 0
    total_warnings = 0

    e, w = _check_gitignore(root, quiet)
    total_errors += e
    total_warnings += w

    if not quiet:
        _console.print()

    e, w = _check_env_drift(root, quiet)
    total_errors += e
    total_warnings += w

    if not quiet:
        _console.print()

    e, w = _check_secrets(root, quiet)
    total_errors += e
    total_warnings += w

    if not quiet:
        _console.print()

    # Summary line
    parts: list[str] = []
    if total_errors:
        parts.append(f"{total_errors} error{'s' if total_errors != 1 else ''}")
    if total_warnings:
        parts.append(f"{total_warnings} warning{'s' if total_warnings != 1 else ''}")
    summary = " \u00b7 ".join(parts) if parts else "all checks passed"

    if quiet:
        print(summary)
    elif total_errors:
        _console.print(f"  [bold red]{summary}[/bold red]")
    elif total_warnings:
        _console.print(f"  [bold yellow]{summary}[/bold yellow]")
    else:
        _console.print(f"  [bold green]{summary}[/bold green]")

    if total_errors or (strict and total_warnings):
        raise typer.Exit(code=1)
