import pytest
from io import StringIO
from rich.console import Console


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capture(fn, *args, **kwargs) -> str:
    """Run a display function with a plain-text Rich console and capture output."""
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=True, no_color=True)

    import devbrief.display as display_module
    original = display_module.console
    display_module.console = console
    try:
        fn(*args, **kwargs)
    finally:
        display_module.console = original

    return buf.getvalue()


# ---------------------------------------------------------------------------
# show_fetching
# ---------------------------------------------------------------------------

class TestShowFetching:
    def test_contains_url(self):
        from devbrief.display import show_fetching
        out = _capture(show_fetching, "https://github.com/owner/repo")
        assert "https://github.com/owner/repo" in out


# ---------------------------------------------------------------------------
# show_generating
# ---------------------------------------------------------------------------

class TestShowGenerating:
    def test_contains_generating_text(self):
        from devbrief.display import show_generating
        out = _capture(show_generating)
        assert "Generating" in out


# ---------------------------------------------------------------------------
# show_brief
# ---------------------------------------------------------------------------

class TestShowBrief:
    def test_contains_repo_name(self):
        from devbrief.display import show_brief
        out = _capture(show_brief, "my-repo", "Some brief text.", 2.5)
        assert "my-repo" in out

    def test_contains_brief_text(self):
        from devbrief.display import show_brief
        out = _capture(show_brief, "repo", "**Problem:** it crashes.", 1.0)
        assert "Problem" in out

    def test_displays_elapsed_time(self):
        from devbrief.display import show_brief
        out = _capture(show_brief, "repo", "brief", 3.7)
        assert "3.7s" in out

    def test_elapsed_time_format(self):
        from devbrief.display import show_brief
        out = _capture(show_brief, "repo", "brief", 10.0)
        assert "10.0s" in out


# ---------------------------------------------------------------------------
# show_saved
# ---------------------------------------------------------------------------

class TestShowSaved:
    def test_contains_file_path(self):
        from devbrief.display import show_saved
        out = _capture(show_saved, "output/brief.md")
        assert "output/brief.md" in out


# ---------------------------------------------------------------------------
# show_error
# ---------------------------------------------------------------------------

class TestShowError:
    def test_contains_error_message(self, capsys):
        from devbrief.display import show_error
        show_error("something went wrong")
        captured = capsys.readouterr()
        assert "something went wrong" in captured.out
