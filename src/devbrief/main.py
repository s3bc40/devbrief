import time
import click
from dotenv import load_dotenv

from devbrief.github import parse_repo_url, fetch_repo_data, fetch_readme, fetch_file_tree
from devbrief.brief import generate_brief
from devbrief.display import show_fetching, show_generating, show_brief, show_error, show_saved

load_dotenv()


@click.command()
@click.argument("github_url")
@click.option("--output", "-o", default=None, metavar="FILE", help="Save the brief to a markdown file.")
def cli(github_url: str, output: str | None) -> None:
    """Generate a human-readable brief for a GitHub repository."""
    try:
        show_fetching(github_url)
        owner, repo_name = parse_repo_url(github_url)

        repo = fetch_repo_data(owner, repo_name)
        readme = fetch_readme(owner, repo_name)
        file_tree = fetch_file_tree(owner, repo_name)

        show_generating()
        start = time.monotonic()
        brief = generate_brief(repo, readme, file_tree)
        elapsed = time.monotonic() - start
        show_brief(repo["name"], brief, elapsed)

        if output:
            md = f"# {repo['name']}\n\n> {github_url}\n\n{brief}\n"
            with open(output, "w", encoding="utf-8") as f:
                f.write(md)
            show_saved(output)

    except ValueError as e:
        show_error(str(e))
        raise SystemExit(1)
    except EnvironmentError as e:
        show_error(str(e))
        raise SystemExit(1)
    except Exception as e:
        show_error(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
