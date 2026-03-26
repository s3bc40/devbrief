from importlib.metadata import version as _pkg_version

from dotenv import load_dotenv
import typer

from devbrief.commands.auth import auth_command
from devbrief.commands.env import env_command
from devbrief.commands.logs import logs_command
from devbrief.commands.repo import repo_command

load_dotenv()

app = typer.Typer(help="Project situational awareness.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"devbrief {_pkg_version('devbrief')}")
        raise typer.Exit()


@app.callback()
def _cli(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


app.command("repo")(repo_command)
app.command("auth")(auth_command)
app.command("logs")(logs_command)
app.command("env")(env_command)
