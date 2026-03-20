import time
from typing import Annotated

import typer

from devbrief.brief import generate_brief
from devbrief.core.cache import (
    cache_age_str,
    cache_key,
    find_latest_cache_by_url,
    read_cache,
    write_cache,
)
from devbrief.core.credentials import resolve_api_key, resolve_model
from devbrief.display import (
    show_brief,
    show_cached,
    show_error,
    show_fetching,
    show_generating,
    show_saved,
)
from devbrief.github import (
    fetch_file_tree,
    fetch_latest_commit_sha,
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
    no_cache: Annotated[
        bool,
        typer.Option(
            "--no-cache",
            "--refresh",
            help="Skip cache and force a fresh API call.",
        ),
    ] = False,
) -> None:
    """Analyze a GitHub repository."""
    try:
        api_key = resolve_api_key()
        model = resolve_model()

        show_fetching(github_url)
        owner, repo_name = parse_repo_url(github_url)

        commit_sha: str | None = None
        cached_entry: dict | None = None

        if not no_cache:
            commit_sha = fetch_latest_commit_sha(owner, repo_name)
            if commit_sha:
                key = cache_key(github_url, commit_sha)
                cached_entry = read_cache(key)
            else:
                # GitHub API unreachable — fall back to any cached entry for this URL
                cached_entry = find_latest_cache_by_url(github_url)

        if cached_entry:
            brief = cached_entry["brief"]
            display_name = cached_entry.get("url", github_url).rstrip("/").split("/")[-1]
            show_brief(display_name, brief, 0.0)
            show_cached(cache_age_str(cached_entry["cached_at"]))
        else:
            repo = fetch_repo_data(owner, repo_name)
            readme = fetch_readme(owner, repo_name)
            file_tree = fetch_file_tree(owner, repo_name)

            show_generating()
            start = time.monotonic()
            brief = generate_brief(repo, readme, file_tree, api_key=api_key, model=model)
            elapsed = time.monotonic() - start
            show_brief(repo["name"], brief, elapsed)

            if not no_cache and commit_sha:
                key = cache_key(github_url, commit_sha)
                write_cache(key, github_url, commit_sha, brief)

        if output:
            md = f"# {repo_name}\n\n> {github_url}\n\n{brief}\n"
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
