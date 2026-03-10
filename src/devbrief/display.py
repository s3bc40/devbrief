from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.rule import Rule
from rich import print as rprint

console = Console()


def show_fetching(url: str) -> None:
    console.print(f"\n[bold cyan]Fetching data for:[/bold cyan] {url}")


def show_generating() -> None:
    console.print("[bold yellow]Generating brief with Claude...[/bold yellow]\n")


def show_brief(repo_name: str, brief_text: str, elapsed: float) -> None:
    console.print(Rule(f"[bold green] DevBrief: {repo_name} [/bold green]"))
    console.print(Panel(Markdown(brief_text), border_style="green", padding=(1, 2)))
    console.print(Rule(style="green"))
    console.print(f"[dim]Brief generated in {elapsed:.1f}s[/dim]\n")


def show_saved(path: str) -> None:
    console.print(f"[dim]Saved to[/dim] [bold]{path}[/bold]\n")


def show_error(message: str) -> None:
    rprint(f"\n[bold red]Error:[/bold red] {message}\n")
