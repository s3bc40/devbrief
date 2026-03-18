import time
from typing import Annotated

import typer

from devbrief.brief import generate_brief
from devbrief.core.credentials import resolve_api_key, resolve_model
from devbrief.display import (
    show_brief,
    show_error,
    show_fetching,
    show_generating,
    show_saved,
)
from devbrief.github import (
    fetch_file_tree,
    fetch_readme,
    fetch_repo_data,
    parse_repo_url,
)


def repo_command(
    github_url: Annotated[str, typer.Argument(help="GitHub repository URL.")],
    output: Annotated[
        str | None,
        typer.Option(
            "--output", "-o", metavar="FILE", help="Save the brief to a markdown file."
        ),
    ] = None,
) -> None:
    """Analyze a GitHub repository."""
    try:
        api_key = resolve_api_key()
        model = resolve_model()

        show_fetching(github_url)
        owner, repo_name = parse_repo_url(github_url)

        repo = fetch_repo_data(owner, repo_name)
        readme = fetch_readme(owner, repo_name)
        file_tree = fetch_file_tree(owner, repo_name)

        show_generating()
        start = time.monotonic()
        brief = generate_brief(repo, readme, file_tree, api_key=api_key, model=model)
        elapsed = time.monotonic() - start
        show_brief(repo["name"], brief, elapsed)

        if output:
            md = f"# {repo['name']}\n\n> {github_url}\n\n{brief}\n"
            with open(output, "w", encoding="utf-8") as fh:
                fh.write(md)
            show_saved(output)

    except ValueError as exc:
        show_error(str(exc))
        raise typer.Exit(code=1)
    except EnvironmentError as exc:
        show_error(str(exc))
        raise typer.Exit(code=1)
    except Exception as exc:
        show_error(f"Unexpected error: {exc}")
        raise typer.Exit(code=1)
