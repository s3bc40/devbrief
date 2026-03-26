"""Tests for devbrief env subcommand — Python orchestration layer only.

Rust functions (_diff_env_files, _scan_secrets) are mocked; Rust internals
are not tested here.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from devbrief.cli import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _make_env_diff(
    missing_from_env: list[str] | None = None,
    undocumented_in_example: list[str] | None = None,
) -> MagicMock:
    diff = MagicMock()
    diff.missing_from_env = missing_from_env or []
    diff.undocumented_in_example = undocumented_in_example or []
    return diff


def _make_secret_match(
    file: str = "src/config.py",
    line: int = 12,
    pattern_name: str = "aws_access_key_id",
    masked_value: str = "AKIA***",
) -> MagicMock:
    m = MagicMock()
    m.file = file
    m.line = line
    m.pattern_name = pattern_name
    m.masked_value = masked_value
    return m


def _invoke(tmp_path: Path, extra_args: list[str] | None = None) -> object:
    runner = CliRunner()
    args = ["env", str(tmp_path)] + (extra_args or [])
    return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# Check 1: .gitignore presence and entry audit (Python-only)
# ---------------------------------------------------------------------------


class TestGitignoreCheck:
    def test_missing_gitignore_is_error(self, tmp_path: Path) -> None:
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_present_gitignore_shows_ok(self, tmp_path: Path) -> None:
        full_ignore = "\n".join(
            [
                ".env",
                ".env.local",
                ".env.*.local",
                "*.pem",
                "*.key",
                "id_rsa",
                "id_rsa.*",
                ".aws/credentials",
            ]
        )
        _write(tmp_path / ".gitignore", full_ignore)
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert result.exit_code == 0
        assert "present" in result.output

    def test_missing_entries_produce_warnings(self, tmp_path: Path) -> None:
        # .gitignore exists but is empty — all entries missing
        _write(tmp_path / ".gitignore", "")
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        # Warnings only → exit 0 without --strict
        assert result.exit_code == 0
        assert "missing entry" in result.output

    def test_missing_entries_with_strict_exits_1(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path, ["--strict"])
        assert result.exit_code == 1

    def test_specific_missing_entry_named_in_output(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", ".env\n.env.local\n")
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert "*.pem" in result.output

    def test_quiet_mode_plain_text(self, tmp_path: Path) -> None:
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path, ["--quiet"])
        assert result.exit_code == 1
        # No Rich markup brackets in quiet output
        assert "[red]" not in result.output
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# Check 2: .env vs .env.example drift
# ---------------------------------------------------------------------------


class TestEnvDriftCheck:
    def test_missing_key_from_env_is_warning(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        _write(tmp_path / ".env", "")
        _write(tmp_path / ".env.example", "")
        diff = _make_env_diff(missing_from_env=["DATABASE_URL"])
        with patch("devbrief.commands.env._diff_env_files", return_value=diff):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert result.exit_code == 0
        assert "DATABASE_URL" in result.output
        assert "missing from .env" in result.output

    def test_undocumented_key_is_warning(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        _write(tmp_path / ".env", "")
        _write(tmp_path / ".env.example", "")
        diff = _make_env_diff(undocumented_in_example=["SECRET_KEY"])
        with patch("devbrief.commands.env._diff_env_files", return_value=diff):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert result.exit_code == 0
        assert "SECRET_KEY" in result.output
        assert "undocumented in .env.example" in result.output

    def test_clean_state_shows_ok(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        _write(tmp_path / ".env", "")
        _write(tmp_path / ".env.example", "")
        diff = _make_env_diff()
        with patch("devbrief.commands.env._diff_env_files", return_value=diff):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert "all .env.example keys present" in result.output

    def test_missing_env_file_shows_info(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        # No .env file created
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert ".env not found, skipping" in result.output

    def test_missing_env_example_file_shows_info(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        _write(tmp_path / ".env", "FOO=bar\n")
        # No .env.example created
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert ".env.example not found, skipping" in result.output

    def test_rust_unavailable_shows_info(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        _write(tmp_path / ".env", "FOO=bar\n")
        _write(tmp_path / ".env.example", "FOO=\n")
        with patch("devbrief.commands.env._diff_env_files", None):
            with patch("devbrief.commands.env._scan_secrets", None):
                result = _invoke(tmp_path)
        assert "unavailable" in result.output
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Check 3: Secret pattern detection
# ---------------------------------------------------------------------------


class TestScanSecretsCheck:
    def test_match_found_is_error(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        match = _make_secret_match(
            file="src/config.py",
            line=12,
            pattern_name="aws_access_key_id",
            masked_value="AKIA***",
        )
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[match]):
                result = _invoke(tmp_path)
        assert result.exit_code == 1
        assert "Secret detected" in result.output
        assert "src/config.py:12" in result.output
        assert "aws_access_key_id" in result.output
        assert "AKIA***" in result.output

    def test_no_match_no_error(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        # Warnings only from empty gitignore, but no errors from secrets
        assert "Secret detected" not in result.output

    def test_skips_gitignored_path_no_error(self, tmp_path: Path) -> None:
        """When scan_secrets returns empty (gitignored file skipped), no errors reported."""
        _write(tmp_path / ".gitignore", "")
        # Rust layer would skip the gitignored file; simulate with empty result
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert "Secret detected" not in result.output

    def test_skips_binary_no_error(self, tmp_path: Path) -> None:
        """When scan_secrets returns empty (binary file skipped), no errors reported."""
        _write(tmp_path / ".gitignore", "")
        # Rust layer would skip the binary file; simulate with empty result
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert "Secret detected" not in result.output

    def test_multiple_matches_all_reported(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        matches = [
            _make_secret_match(file="a.py", line=1, pattern_name="aws_access_key_id"),
            _make_secret_match(
                file="b.py", line=5, pattern_name="github_token", masked_value="ghp_***"
            ),
        ]
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=matches):
                result = _invoke(tmp_path)
        assert result.exit_code == 1
        assert "a.py:1" in result.output
        assert "b.py:5" in result.output

    def test_rust_unavailable_shows_info(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")
        with patch("devbrief.commands.env._diff_env_files", None):
            with patch("devbrief.commands.env._scan_secrets", None):
                result = _invoke(tmp_path)
        assert "unavailable" in result.output
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Summary line
# ---------------------------------------------------------------------------


class TestSummaryLine:
    def test_all_pass_message(self, tmp_path: Path) -> None:
        full_ignore = "\n".join(
            [
                ".env",
                ".env.local",
                ".env.*.local",
                "*.pem",
                "*.key",
                "id_rsa",
                "id_rsa.*",
                ".aws/credentials",
            ]
        )
        _write(tmp_path / ".gitignore", full_ignore)
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path)
        assert "all checks passed" in result.output
        assert result.exit_code == 0

    def test_summary_counts_errors_and_warnings(self, tmp_path: Path) -> None:
        _write(tmp_path / ".gitignore", "")  # 8 missing entries → 8 warnings
        match = _make_secret_match()  # 1 secret → 1 error
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[match]):
                result = _invoke(tmp_path)
        assert "1 error" in result.output
        assert "warning" in result.output
        assert result.exit_code == 1

    def test_quiet_summary_plain(self, tmp_path: Path) -> None:
        full_ignore = "\n".join(
            [
                ".env",
                ".env.local",
                ".env.*.local",
                "*.pem",
                "*.key",
                "id_rsa",
                "id_rsa.*",
                ".aws/credentials",
            ]
        )
        _write(tmp_path / ".gitignore", full_ignore)
        with patch(
            "devbrief.commands.env._diff_env_files", return_value=_make_env_diff()
        ):
            with patch("devbrief.commands.env._scan_secrets", return_value=[]):
                result = _invoke(tmp_path, ["--quiet"])
        assert "all checks passed" in result.output
        assert "[green]" not in result.output
