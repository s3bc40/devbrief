import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "devbrief"
CONFIG_PATH = CONFIG_DIR / "config.toml"

_DEFAULT_MODEL = "claude-sonnet-4-6"


def write_api_key(api_key: str, model: str = _DEFAULT_MODEL) -> None:
    """Write api_key to config file and enforce 600 permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    content = f'[anthropic]\napi_key = "{api_key}"\ndefault_model = "{model}"\n'
    CONFIG_PATH.write_text(content, encoding="utf-8")
    os.chmod(CONFIG_PATH, 0o600)


def read_config() -> dict:
    """Return parsed config dict, or empty dict if the file does not exist."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as fh:
        return tomllib.load(fh)


def clear_api_key() -> bool:
    """Remove api_key from config, keeping other fields intact.

    Returns True if a key was removed, False if nothing was found.
    """
    config = read_config()
    if "api_key" not in config.get("anthropic", {}):
        return False

    model = config["anthropic"].get("default_model", _DEFAULT_MODEL)
    content = f'[anthropic]\ndefault_model = "{model}"\n'
    CONFIG_PATH.write_text(content, encoding="utf-8")
    os.chmod(CONFIG_PATH, 0o600)
    return True
