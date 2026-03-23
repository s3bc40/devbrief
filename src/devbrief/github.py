import base64

import httpx


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    parts = url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return parts[-2], parts[-1]


def fetch_repo_data(owner: str, repo: str) -> dict:
    """Fetch repository metadata from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    return {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "stars": data.get("stargazers_count", 0),
        "language": data.get("language", ""),
        "topics": data.get("topics", []),
        "homepage": data.get("homepage", ""),
    }


def fetch_readme(owner: str, repo: str) -> str:
    """Fetch README content from GitHub API (decoded from base64)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/readme"
    response = httpx.get(url, timeout=10)
    if response.status_code == 404:
        return ""
    response.raise_for_status()
    content = response.json().get("content", "")
    return base64.b64decode(content).decode("utf-8", errors="replace")


def fetch_file_tree(owner: str, repo: str) -> list[str]:
    """Fetch top-level file/directory names from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents"
    response = httpx.get(url, timeout=10)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    items = response.json()
    return [item["name"] for item in items if isinstance(item, dict)]


def fetch_latest_commit_sha(owner: str, repo: str) -> str | None:
    """Return the SHA of the most recent commit, or None if unreachable."""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
    try:
        response = httpx.get(url, timeout=5)
        response.raise_for_status()
        commits = response.json()
        if commits and isinstance(commits, list):
            return commits[0].get("sha")
    except Exception:
        return None
    return None
