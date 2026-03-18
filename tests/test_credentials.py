import stat
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from devbrief.cli import app
from devbrief.core.config import clear_api_key, read_config, write_api_key
from devbrief.core.credentials import resolve_api_key, resolve_model

runner = CliRunner()

# ---------------------------------------------------------------------------
# resolve_api_key — resolution chain
# ---------------------------------------------------------------------------


class TestResolveApiKey:
    def test_flag_takes_priority_over_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        assert resolve_api_key(flag_value="flag-key") == "flag-key"

    def test_env_takes_priority_over_config(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        fake_config = tmp_path / "config.toml"
        fake_config.write_text('[anthropic]\napi_key = "config-key"\n')
        with patch(
            "devbrief.core.credentials.read_config",
            return_value={"anthropic": {"api_key": "config-key"}},
        ):
            assert resolve_api_key() == "env-key"

    def test_config_used_when_no_env(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch(
            "devbrief.core.credentials.read_config",
            return_value={"anthropic": {"api_key": "config-key"}},
        ):
            assert resolve_api_key() == "config-key"

    def test_missing_key_raises_with_auth_hint(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("devbrief.core.credentials.read_config", return_value={}):
            with pytest.raises(EnvironmentError, match="devbrief auth"):
                resolve_api_key()


# ---------------------------------------------------------------------------
# resolve_model — resolution chain
# ---------------------------------------------------------------------------


class TestResolveModel:
    def test_flag_takes_priority(self, monkeypatch):
        monkeypatch.setenv("DEVBRIEF_MODEL", "env-model")
        assert resolve_model(flag_value="flag-model") == "flag-model"

    def test_env_takes_priority_over_config(self, monkeypatch):
        monkeypatch.setenv("DEVBRIEF_MODEL", "env-model")
        with patch(
            "devbrief.core.credentials.read_config",
            return_value={"anthropic": {"default_model": "config-model"}},
        ):
            assert resolve_model() == "env-model"

    def test_config_used_when_no_env(self, monkeypatch):
        monkeypatch.delenv("DEVBRIEF_MODEL", raising=False)
        with patch(
            "devbrief.core.credentials.read_config",
            return_value={"anthropic": {"default_model": "config-model"}},
        ):
            assert resolve_model() == "config-model"

    def test_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("DEVBRIEF_MODEL", raising=False)
        with patch("devbrief.core.credentials.read_config", return_value={}):
            assert resolve_model() == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# config helpers
# ---------------------------------------------------------------------------


class TestWriteApiKey:
    def test_writes_file_and_enforces_600(self, tmp_path, monkeypatch):
        monkeypatch.setattr("devbrief.core.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr(
            "devbrief.core.config.CONFIG_PATH", tmp_path / "config.toml"
        )

        write_api_key("sk-ant-test123")

        cfg_path = tmp_path / "config.toml"
        assert cfg_path.exists()
        perms = stat.S_IMODE(cfg_path.stat().st_mode)
        assert perms == 0o600

    def test_written_content_is_parseable(self, tmp_path, monkeypatch):
        monkeypatch.setattr("devbrief.core.config.CONFIG_DIR", tmp_path)
        cfg_path = tmp_path / "config.toml"
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        write_api_key("sk-ant-test123")

        config = (
            read_config.__wrapped__(cfg_path)
            if hasattr(read_config, "__wrapped__")
            else _read_toml(cfg_path)
        )
        assert config["anthropic"]["api_key"] == "sk-ant-test123"
        assert config["anthropic"]["default_model"] == "claude-sonnet-4-6"

    def test_key_not_in_stdout(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr("devbrief.core.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr(
            "devbrief.core.config.CONFIG_PATH", tmp_path / "config.toml"
        )
        write_api_key("sk-ant-supersecret")
        captured = capsys.readouterr()
        assert "sk-ant-supersecret" not in captured.out
        assert "sk-ant-supersecret" not in captured.err


class TestClearApiKey:
    def test_removes_api_key_preserves_model(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            '[anthropic]\napi_key = "sk-ant-x"\ndefault_model = "claude-sonnet-4-6"\n'
        )
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        result = clear_api_key()

        assert result is True
        content = cfg_path.read_text()
        assert "api_key" not in content
        assert "claude-sonnet-4-6" in content

    def test_returns_false_when_no_key(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text('[anthropic]\ndefault_model = "claude-sonnet-4-6"\n')
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        assert clear_api_key() is False


# ---------------------------------------------------------------------------
# devbrief auth — CLI integration
# ---------------------------------------------------------------------------


class TestAuthCommand:
    def test_valid_key_saved_to_config(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "config.toml"
        monkeypatch.setattr("devbrief.commands.auth.CONFIG_PATH", cfg_path)
        monkeypatch.setattr("devbrief.core.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        with (
            patch("devbrief.commands.auth.write_api_key") as mock_write,
            patch("devbrief.commands.auth._validate_key", return_value=True),
        ):
            result = runner.invoke(app, ["auth", "--api-key", "sk-ant-valid"])

        assert result.exit_code == 0
        mock_write.assert_called_once_with("sk-ant-valid")

    def test_invalid_key_writes_nothing(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "config.toml"
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        with patch("devbrief.commands.auth._validate_key", return_value=False):
            result = runner.invoke(app, ["auth", "--api-key", "sk-ant-bad"])

        assert result.exit_code == 1
        assert not cfg_path.exists()

    def test_invalid_key_does_not_print_key(self):
        with patch("devbrief.commands.auth._validate_key", return_value=False):
            result = runner.invoke(app, ["auth", "--api-key", "sk-ant-supersecret"])

        assert "sk-ant-supersecret" not in result.output

    def test_show_displays_masked_key(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            '[anthropic]\napi_key = "sk-ant-abcdefghij1234"\ndefault_model = "claude-sonnet-4-6"\n'
        )
        monkeypatch.setattr("devbrief.commands.auth.CONFIG_PATH", cfg_path)
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        result = runner.invoke(app, ["auth", "--show"])

        assert result.exit_code == 0
        assert "sk-ant-abc" in result.output  # first 10 chars visible
        assert "***" in result.output  # suffix masked
        assert "sk-ant-abcdefghij1234" not in result.output  # full key never shown

    def test_show_no_key_configured(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "devbrief.core.config.CONFIG_PATH", tmp_path / "config.toml"
        )

        result = runner.invoke(app, ["auth", "--show"])

        assert result.exit_code == 0
        assert "No API key configured" in result.output

    def test_clear_removes_key(self, tmp_path, monkeypatch):
        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            '[anthropic]\napi_key = "sk-ant-x"\ndefault_model = "claude-sonnet-4-6"\n'
        )
        monkeypatch.setattr("devbrief.commands.auth.CONFIG_PATH", cfg_path)
        monkeypatch.setattr("devbrief.core.config.CONFIG_PATH", cfg_path)

        result = runner.invoke(app, ["auth", "--clear"])

        assert result.exit_code == 0
        assert "removed" in result.output.lower()
        assert "api_key" not in cfg_path.read_text()

    def test_clear_idempotent_when_no_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "devbrief.core.config.CONFIG_PATH", tmp_path / "config.toml"
        )

        result = runner.invoke(app, ["auth", "--clear"])

        assert result.exit_code == 0
        assert "No API key" in result.output


# ---------------------------------------------------------------------------
# Missing key on repo command → error points to devbrief auth
# ---------------------------------------------------------------------------


class TestMissingKeyOnRepo:
    def test_repo_error_mentions_devbrief_auth(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with patch("devbrief.core.credentials.read_config", return_value={}):
            result = runner.invoke(app, ["repo", "https://github.com/owner/repo"])

        assert result.exit_code == 1
        assert "devbrief auth" in result.output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_toml(path: Path) -> dict:
    import tomllib

    with open(path, "rb") as fh:
        return tomllib.load(fh)
