import base64
import pytest
from unittest.mock import MagicMock

from devbrief.github import (
    parse_repo_url,
    fetch_repo_data,
    fetch_readme,
    fetch_file_tree,
)


# ---------------------------------------------------------------------------
# parse_repo_url
# ---------------------------------------------------------------------------


class TestParseRepoUrl:
    def test_standard_url(self):
        assert parse_repo_url("https://github.com/anthropics/anthropic-sdk-python") == (
            "anthropics",
            "anthropic-sdk-python",
        )

    def test_trailing_slash(self):
        assert parse_repo_url("https://github.com/owner/repo/") == ("owner", "repo")

    def test_short_path_raises(self):
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_repo_url("not-a-url")


# ---------------------------------------------------------------------------
# fetch_repo_data
# ---------------------------------------------------------------------------


class TestFetchRepoData:
    def test_maps_api_fields(self, mocker):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "my-repo",
            "description": "A cool project",
            "stargazers_count": 42,
            "language": "Python",
            "topics": ["cli", "ai"],
            "homepage": "https://example.com",
        }
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        result = fetch_repo_data("owner", "my-repo")

        assert result == {
            "name": "my-repo",
            "description": "A cool project",
            "stars": 42,
            "language": "Python",
            "topics": ["cli", "ai"],
            "homepage": "https://example.com",
        }

    def test_missing_fields_use_defaults(self, mocker):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        result = fetch_repo_data("owner", "repo")

        assert result["name"] == ""
        assert result["stars"] == 0
        assert result["topics"] == []


# ---------------------------------------------------------------------------
# fetch_readme
# ---------------------------------------------------------------------------


class TestFetchReadme:
    def test_decodes_base64_content(self, mocker):
        encoded = base64.b64encode(b"# Hello World\n").decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": encoded}
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        assert fetch_readme("owner", "repo") == "# Hello World\n"

    def test_returns_empty_string_on_404(self, mocker):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        assert fetch_readme("owner", "repo") == ""

    def test_returns_empty_string_when_content_missing(self, mocker):
        encoded = base64.b64encode(b"").decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": encoded}
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        assert fetch_readme("owner", "repo") == ""


# ---------------------------------------------------------------------------
# fetch_file_tree
# ---------------------------------------------------------------------------


class TestFetchFileTree:
    def test_returns_names_list(self, mocker):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"name": "src", "type": "dir"},
            {"name": "README.md", "type": "file"},
            {"name": "pyproject.toml", "type": "file"},
        ]
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        assert fetch_file_tree("owner", "repo") == [
            "src",
            "README.md",
            "pyproject.toml",
        ]

    def test_returns_empty_list_on_404(self, mocker):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        assert fetch_file_tree("owner", "repo") == []

    def test_skips_non_dict_items(self, mocker):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"name": "src"}, "unexpected-string"]
        mocker.patch("devbrief.github.httpx.get", return_value=mock_response)

        assert fetch_file_tree("owner", "repo") == ["src"]
