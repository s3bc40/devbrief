"""Type stubs for the devbrief Rust extension (_devbrief_core).

These declarations mirror the #[pyclass] / #[pyfunction] definitions in
rust/src/lib.rs and are consumed by IDEs and static type checkers (mypy,
pyright).  The compiled .so provides no inline annotations on its own.
"""

class EnvDiff:
    """Result of comparing .env and .env.example key sets."""

    missing_from_env: list[str]
    """Keys present in .env.example but absent from .env."""

    undocumented_in_example: list[str]
    """Keys present in .env but absent from .env.example."""

class SecretMatch:
    """A line in a committed file that matched a secret pattern."""

    file: str
    """Path to the file containing the match."""

    line: int
    """1-indexed line number of the match."""

    pattern_name: str
    """Name of the pattern that matched (e.g. 'aws_access_key_id')."""

    masked_value: str
    """First 4 characters of the matched value followed by '***'."""

def diff_env_files(env_path: str, example_path: str) -> EnvDiff:
    """Compare key sets between *env_path* and *example_path*.

    Returns an empty :class:`EnvDiff` (no error) if either file is absent.
    Blank lines and comment lines (``#``) are ignored.  Only the left-hand
    side of each ``KEY=value`` pair is considered.
    """
    ...

def scan_secrets(path: str) -> list[SecretMatch]:
    """Walk *path* recursively and return lines matching secret patterns.

    The walk respects ``.gitignore`` rules (via the ``ignore`` crate).
    Binary files and ``rust/target/`` are skipped unconditionally.
    Five patterns are checked: ``anthropic_api_key``, ``openai_api_key``,
    ``aws_access_key_id``, ``github_token``, ``private_key_header``.
    """
    ...
