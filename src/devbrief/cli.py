from dotenv import load_dotenv
import typer

from devbrief.commands.auth import auth_command
from devbrief.commands.repo import repo_command

load_dotenv()

app = typer.Typer(help="Project situational awareness.")

app.command("repo")(repo_command)
app.command("auth")(auth_command)
