from typing import Annotated

import anthropic
import typer

from devbrief.core.config import CONFIG_PATH, clear_api_key, read_config, write_api_key
from devbrief.display import console


def _mask_key(key: str) -> str:
    """Return a masked representation — first 10 chars visible, rest replaced with ***."""
    visible = min(10, max(0, len(key) - 4))
    return key[:visible] + "***"


def _validate_key(api_key: str) -> bool:
    """Return True if the key authenticates successfully against the Anthropic API."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.models.list()
        return True
    except anthropic.AuthenticationError:
        return False
    except Exception:
        return False


def auth_command(
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key", help="Pass the API key directly (non-interactive / CI)."
        ),
    ] = None,
    show: Annotated[
        bool,
        typer.Option(
            "--show", help="Display the masked key currently stored in config."
        ),
    ] = False,
    clear: Annotated[
        bool,
        typer.Option("--clear", help="Remove the stored API key from config."),
    ] = False,
) -> None:
    """Manage API credentials."""
    if show:
        config = read_config()
        stored = config.get("anthropic", {}).get("api_key")
        if not stored:
            console.print(
                "[yellow]No API key configured.[/yellow] Run [bold]devbrief auth[/bold] to set one."
            )
        else:
            console.print(f"[bold]Stored key:[/bold] {_mask_key(stored)}")
        return

    if clear:
        removed = clear_api_key()
        if removed:
            console.print("[green]API key removed from config.[/green]")
        else:
            console.print("[yellow]No API key found in config.[/yellow]")
        return

    # Interactive or flag-based key entry
    if api_key is None:
        api_key = typer.prompt("Anthropic API key", hide_input=True)

    console.print("[bold yellow]Validating key...[/bold yellow]")
    if not _validate_key(api_key):
        console.print(
            "[bold red]Error:[/bold red] Invalid API key (authentication failed). Nothing was saved."
        )
        raise typer.Exit(code=1)

    write_api_key(api_key)
    console.print(
        f"[green]API key saved to[/green] {CONFIG_PATH} [dim](permissions: 600)[/dim]"
    )
