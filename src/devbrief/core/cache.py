import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def cache_dir() -> Path:
    d = Path.home() / ".cache" / "devbrief"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_key(repo_url: str, commit_sha: str) -> str:
    return hashlib.sha256(f"{repo_url}{commit_sha}".encode()).hexdigest()


def cache_path(key: str) -> Path:
    return cache_dir() / f"{key}.json"


def read_cache(key: str) -> dict | None:
    path = cache_path(key)
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def write_cache(key: str, repo_url: str, commit_sha: str, brief: str) -> None:
    entry = {
        "url": repo_url,
        "commit_sha": commit_sha,
        "brief": brief,
        "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = cache_path(key)
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(entry, fh, indent=2)
    except OSError:
        pass  # never fail on cache write errors


def find_latest_cache_by_url(repo_url: str) -> dict | None:
    """Scan cache dir for the most recent entry matching repo_url.

    Used as fallback when the GitHub API is unreachable and we cannot
    compute a commit-SHA-keyed cache key.
    """
    best: dict | None = None
    best_time: str = ""
    try:
        for path in cache_dir().glob("*.json"):
            try:
                with path.open(encoding="utf-8") as fh:
                    entry = json.load(fh)
                if (
                    entry.get("url") == repo_url
                    and entry.get("cached_at", "") > best_time
                ):
                    best = entry
                    best_time = entry["cached_at"]
            except (json.JSONDecodeError, OSError):
                continue
    except OSError:
        pass
    return best


def cache_age_str(cached_at: str) -> str:
    try:
        then = datetime.fromisoformat(cached_at)
        delta = datetime.now(timezone.utc) - then
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 0:
            return f"{hours}h ago"
        if minutes > 0:
            return f"{minutes}m ago"
        return "just now"
    except Exception:
        return "unknown"
