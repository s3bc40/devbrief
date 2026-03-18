import os

from devbrief.core.config import read_config

_DEFAULT_MODEL = "claude-sonnet-4-6"

_AUTH_HINT = (
    "No API key found. Run `devbrief auth` to configure your Anthropic API key."
)


def resolve_api_key(flag_value: str | None = None) -> str:
    """Resolve the Anthropic API key using the 4-level chain.

    Priority:
      1. --api-key flag value
      2. ANTHROPIC_API_KEY env var
      3. ~/.config/devbrief/config.toml  [anthropic] api_key
      4. Raise EnvironmentError with hint to run `devbrief auth`
    """
    if flag_value:
        return flag_value

    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key

    config = read_config()
    config_key = config.get("anthropic", {}).get("api_key")
    if config_key:
        return config_key

    raise EnvironmentError(_AUTH_HINT)


def resolve_model(flag_value: str | None = None) -> str:
    """Resolve the model using the 3-level chain.

    Priority:
      1. --model flag value (if the command exposes one)
      2. DEVBRIEF_MODEL env var
      3. ~/.config/devbrief/config.toml  [anthropic] default_model
      4. Hard default: claude-sonnet-4-6
    """
    if flag_value:
        return flag_value

    env_model = os.environ.get("DEVBRIEF_MODEL")
    if env_model:
        return env_model

    config = read_config()
    config_model = config.get("anthropic", {}).get("default_model")
    if config_model:
        return config_model

    return _DEFAULT_MODEL
