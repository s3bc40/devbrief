"""Tests for the local file cache layer (devbrief repo --cache)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from devbrief.core.cache import (
    cache_age_str,
    cache_key,
    find_latest_cache_by_url,
    read_cache,
    write_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_URL = "https://github.com/owner/repo"
COMMIT_SHA = "abc123def456"
BRIEF_TEXT = "## Summary\n\nA cool project."


def _make_entry(
    tmp_cache: Path,
    url: str = REPO_URL,
    sha: str = COMMIT_SHA,
    brief: str = BRIEF_TEXT,
    cached_at: str | None = None,
) -> dict:
    """Write a cache entry directly and return it."""
    if cached_at is None:
        cached_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    key = cache_key(url, sha)
    entry = {"url": url, "commit_sha": sha, "brief": brief, "cached_at": cached_at}
    (tmp_cache / f"{key}.json").write_text(json.dumps(entry))
    return entry


@pytest.fixture()
def tmp_cache(tmp_path: Path, monkeypatch):
    """Redirect cache_dir() to a temp directory for isolation."""
    monkeypatch.setattr("devbrief.core.cache.cache_dir", lambda: tmp_path / "devbrief")
    (tmp_path / "devbrief").mkdir()
    return tmp_path / "devbrief"


# ---------------------------------------------------------------------------
# cache_key
# ---------------------------------------------------------------------------


class TestCacheKey:
    def test_deterministic(self):
        k1 = cache_key(REPO_URL, COMMIT_SHA)
        k2 = cache_key(REPO_URL, COMMIT_SHA)
        assert k1 == k2

    def test_different_sha_gives_different_key(self):
        assert cache_key(REPO_URL, "sha1") != cache_key(REPO_URL, "sha2")

    def test_different_url_gives_different_key(self):
        assert cache_key("https://github.com/a/b", COMMIT_SHA) != cache_key(
            "https://github.com/c/d", COMMIT_SHA
        )

    def test_returns_hex_string(self):
        key = cache_key(REPO_URL, COMMIT_SHA)
        assert all(c in "0123456789abcdef" for c in key)
        assert len(key) == 64  # sha256 → 32 bytes → 64 hex chars


# ---------------------------------------------------------------------------
# read_cache / write_cache
# ---------------------------------------------------------------------------


class TestReadWriteCache:
    def test_cache_miss_returns_none(self, tmp_cache):
        assert read_cache("nonexistent-key") is None

    def test_write_then_read_roundtrip(self, tmp_cache):
        key = cache_key(REPO_URL, COMMIT_SHA)
        write_cache(key, REPO_URL, COMMIT_SHA, BRIEF_TEXT)
        entry = read_cache(key)
        assert entry is not None
        assert entry["url"] == REPO_URL
        assert entry["commit_sha"] == COMMIT_SHA
        assert entry["brief"] == BRIEF_TEXT
        assert "cached_at" in entry

    def test_cache_file_written_to_correct_path(self, tmp_cache):
        key = cache_key(REPO_URL, COMMIT_SHA)
        write_cache(key, REPO_URL, COMMIT_SHA, BRIEF_TEXT)
        expected = tmp_cache / f"{key}.json"
        assert expected.exists()

    def test_cache_file_has_correct_structure(self, tmp_cache):
        key = cache_key(REPO_URL, COMMIT_SHA)
        write_cache(key, REPO_URL, COMMIT_SHA, BRIEF_TEXT)
        raw = json.loads((tmp_cache / f"{key}.json").read_text())
        assert set(raw.keys()) == {"url", "commit_sha", "brief", "cached_at"}

    def test_corrupted_json_returns_none(self, tmp_cache):
        key = cache_key(REPO_URL, COMMIT_SHA)
        (tmp_cache / f"{key}.json").write_text("not-valid-json{{")
        assert read_cache(key) is None

    def test_write_silently_ignores_os_error(self, tmp_cache, monkeypatch):
        """write_cache must not raise even if the filesystem is read-only."""
        monkeypatch.setattr(
            "builtins.open",
            lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")),
        )
        key = cache_key(REPO_URL, COMMIT_SHA)
        # Should not raise
        write_cache(key, REPO_URL, COMMIT_SHA, BRIEF_TEXT)


# ---------------------------------------------------------------------------
# find_latest_cache_by_url
# ---------------------------------------------------------------------------


class TestFindLatestCacheByUrl:
    def test_returns_none_when_no_entries(self, tmp_cache):
        assert find_latest_cache_by_url(REPO_URL) is None

    def test_returns_entry_matching_url(self, tmp_cache):
        _make_entry(tmp_cache)
        result = find_latest_cache_by_url(REPO_URL)
        assert result is not None
        assert result["url"] == REPO_URL

    def test_returns_most_recent_entry(self, tmp_cache):
        older_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(
            timespec="seconds"
        )
        newer_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _make_entry(tmp_cache, sha="sha-old", brief="old brief", cached_at=older_time)
        _make_entry(tmp_cache, sha="sha-new", brief="new brief", cached_at=newer_time)
        result = find_latest_cache_by_url(REPO_URL)
        assert result is not None
        assert result["brief"] == "new brief"

    def test_ignores_entries_for_other_urls(self, tmp_cache):
        _make_entry(tmp_cache, url="https://github.com/other/repo")
        assert find_latest_cache_by_url(REPO_URL) is None


# ---------------------------------------------------------------------------
# cache_age_str
# ---------------------------------------------------------------------------


class TestCacheAgeStr:
    def test_hours(self):
        t = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(
            timespec="seconds"
        )
        assert cache_age_str(t) == "3h ago"

    def test_minutes(self):
        t = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat(
            timespec="seconds"
        )
        assert cache_age_str(t) == "45m ago"

    def test_just_now(self):
        t = datetime.now(timezone.utc).isoformat(timespec="seconds")
        assert cache_age_str(t) == "just now"

    def test_bad_value_returns_unknown(self):
        assert cache_age_str("not-a-date") == "unknown"


# ---------------------------------------------------------------------------
# Integration: repo command cache behaviour
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_env(monkeypatch):
    """Provide required credentials without touching the real filesystem."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GITHUB_TOKEN", "")


def _make_mock_response(json_data, status_code: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


class TestRepoCacheIntegration:
    """End-to-end tests for cache interaction in repo_command."""

    def _run(self, mocker, tmp_cache, url=REPO_URL, extra_args=None):
        """Invoke repo_command with common mocks and return call counts."""
        import base64
        from typer.testing import CliRunner
        from devbrief.cli import app

        # Patch cache_dir used by the cache module functions
        mocker.patch("devbrief.core.cache.cache_dir", return_value=tmp_cache)

        # GitHub API mocks
        commit_resp = _make_mock_response([{"sha": COMMIT_SHA}])
        repo_resp = _make_mock_response(
            {
                "name": "repo",
                "description": "",
                "stargazers_count": 0,
                "language": "Python",
                "topics": [],
                "homepage": "",
            }
        )
        readme_resp = _make_mock_response(
            {"content": base64.b64encode(b"# Readme").decode()}, 200
        )
        tree_resp = _make_mock_response([{"name": "src"}], 200)

        get_mock = mocker.patch(
            "devbrief.github.requests.get",
            side_effect=[commit_resp, repo_resp, readme_resp, tree_resp],
        )
        brief_mock = mocker.patch(
            "devbrief.commands.repo.generate_brief",
            return_value=BRIEF_TEXT,
        )

        runner = CliRunner()
        args = ["repo", url] + (extra_args or [])
        result = runner.invoke(app, args)
        return result, get_mock, brief_mock

    def test_cache_miss_calls_api_and_writes_cache(self, mocker, tmp_path, mock_env):
        tmp_cache = tmp_path / "devbrief"
        tmp_cache.mkdir()
        result, get_mock, brief_mock = self._run(mocker, tmp_cache)
        assert result.exit_code == 0
        brief_mock.assert_called_once()
        # Cache file should exist
        assert any(tmp_cache.glob("*.json"))

    def test_cache_hit_same_sha_skips_api(self, mocker, tmp_path, mock_env):
        from typer.testing import CliRunner
        from devbrief.cli import app

        tmp_cache = tmp_path / "devbrief"
        tmp_cache.mkdir()

        # Pre-populate cache
        key = cache_key(REPO_URL, COMMIT_SHA)
        cached_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = {
            "url": REPO_URL,
            "commit_sha": COMMIT_SHA,
            "brief": BRIEF_TEXT,
            "cached_at": cached_at,
        }
        (tmp_cache / f"{key}.json").write_text(json.dumps(entry))

        mocker.patch("devbrief.core.cache.cache_dir", return_value=tmp_cache)

        # Only commit SHA fetch should happen — no repo/readme/tree/brief calls
        commit_resp = _make_mock_response([{"sha": COMMIT_SHA}])
        get_mock = mocker.patch(
            "devbrief.github.requests.get", return_value=commit_resp
        )
        brief_mock = mocker.patch("devbrief.commands.repo.generate_brief")

        runner = CliRunner()
        result = runner.invoke(app, ["repo", REPO_URL])

        assert result.exit_code == 0
        brief_mock.assert_not_called()
        # Only 1 request: the commit SHA fetch
        assert get_mock.call_count == 1

    def test_sha_changed_invalidates_cache(self, mocker, tmp_path, mock_env):
        import base64
        from typer.testing import CliRunner
        from devbrief.cli import app

        tmp_cache = tmp_path / "devbrief"
        tmp_cache.mkdir()

        # Cache entry with OLD sha
        old_key = cache_key(REPO_URL, "old-sha")
        entry = {
            "url": REPO_URL,
            "commit_sha": "old-sha",
            "brief": "old brief",
            "cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        (tmp_cache / f"{old_key}.json").write_text(json.dumps(entry))

        mocker.patch("devbrief.core.cache.cache_dir", return_value=tmp_cache)

        commit_resp = _make_mock_response([{"sha": "new-sha"}])
        repo_resp = _make_mock_response(
            {
                "name": "repo",
                "description": "",
                "stargazers_count": 0,
                "language": "Python",
                "topics": [],
                "homepage": "",
            }
        )
        readme_resp = _make_mock_response(
            {"content": base64.b64encode(b"# Readme").decode()}, 200
        )
        tree_resp = _make_mock_response([{"name": "src"}], 200)
        commit_resp2 = _make_mock_response([{"sha": "new-sha"}])

        mocker.patch(
            "devbrief.github.requests.get",
            side_effect=[commit_resp, repo_resp, readme_resp, tree_resp, commit_resp2],
        )
        brief_mock = mocker.patch(
            "devbrief.commands.repo.generate_brief", return_value="new brief"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["repo", REPO_URL])

        assert result.exit_code == 0
        brief_mock.assert_called_once()

    def test_github_api_unreachable_serves_cached(self, mocker, tmp_path, mock_env):
        import requests as req_lib
        from typer.testing import CliRunner
        from devbrief.cli import app

        tmp_cache = tmp_path / "devbrief"
        tmp_cache.mkdir()

        # Pre-populate cache for URL
        _make_entry(tmp_cache)

        mocker.patch("devbrief.core.cache.cache_dir", return_value=tmp_cache)

        # Commit SHA fetch raises (network error)
        mocker.patch(
            "devbrief.github.requests.get",
            side_effect=req_lib.exceptions.ConnectionError("unreachable"),
        )
        brief_mock = mocker.patch("devbrief.commands.repo.generate_brief")

        runner = CliRunner()
        result = runner.invoke(app, ["repo", REPO_URL])

        assert result.exit_code == 0
        brief_mock.assert_not_called()
        assert "cached" in result.output

    def test_no_cache_flag_bypasses_cache(self, mocker, tmp_path, mock_env):
        import base64
        from typer.testing import CliRunner
        from devbrief.cli import app

        tmp_cache = tmp_path / "devbrief"
        tmp_cache.mkdir()

        # Pre-populate cache
        _make_entry(tmp_cache)

        mocker.patch("devbrief.core.cache.cache_dir", return_value=tmp_cache)

        repo_resp = _make_mock_response(
            {
                "name": "repo",
                "description": "",
                "stargazers_count": 0,
                "language": "Python",
                "topics": [],
                "homepage": "",
            }
        )
        readme_resp = _make_mock_response(
            {"content": base64.b64encode(b"# Readme").decode()}, 200
        )
        tree_resp = _make_mock_response([{"name": "src"}], 200)
        mocker.patch(
            "devbrief.github.requests.get",
            side_effect=[repo_resp, readme_resp, tree_resp],
        )
        brief_mock = mocker.patch(
            "devbrief.commands.repo.generate_brief", return_value="fresh brief"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["repo", REPO_URL, "--no-cache"])

        assert result.exit_code == 0
        brief_mock.assert_called_once()

    def test_refresh_flag_is_alias_for_no_cache(self, mocker, tmp_path, mock_env):
        import base64
        from typer.testing import CliRunner
        from devbrief.cli import app

        tmp_cache = tmp_path / "devbrief"
        tmp_cache.mkdir()

        _make_entry(tmp_cache)

        mocker.patch("devbrief.core.cache.cache_dir", return_value=tmp_cache)

        repo_resp = _make_mock_response(
            {
                "name": "repo",
                "description": "",
                "stargazers_count": 0,
                "language": "Python",
                "topics": [],
                "homepage": "",
            }
        )
        readme_resp = _make_mock_response(
            {"content": base64.b64encode(b"# Readme").decode()}, 200
        )
        tree_resp = _make_mock_response([{"name": "src"}], 200)
        mocker.patch(
            "devbrief.github.requests.get",
            side_effect=[repo_resp, readme_resp, tree_resp],
        )
        brief_mock = mocker.patch(
            "devbrief.commands.repo.generate_brief", return_value="fresh brief"
        )

        runner = CliRunner()
        result = runner.invoke(app, ["repo", REPO_URL, "--refresh"])

        assert result.exit_code == 0
        brief_mock.assert_called_once()
