"""Tests for devbrief logs — parser, buffer, and command behaviour."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from devbrief.commands.logs import LogBuffer, LogEntry, parse_log_line, _build_app


# ---------------------------------------------------------------------------
# parse_log_line — JSON
# ---------------------------------------------------------------------------


class TestParseLogLineJSON:
    def test_json_extracts_level(self):
        line = json.dumps(
            {"level": "ERROR", "message": "boom", "timestamp": "2024-01-01T00:00:00"}
        )
        entry = parse_log_line(line)
        assert entry.level == "ERROR"

    def test_json_extracts_message(self):
        line = json.dumps(
            {"level": "INFO", "message": "started", "timestamp": "2024-01-01T00:00:00"}
        )
        entry = parse_log_line(line)
        assert entry.message == "started"

    def test_json_extracts_timestamp(self):
        line = json.dumps(
            {"level": "INFO", "message": "ok", "timestamp": "2024-06-15T12:34:56"}
        )
        entry = parse_log_line(line)
        assert entry.timestamp == "2024-06-15T12:34:56"

    def test_json_levelname_alias(self):
        line = json.dumps(
            {"levelname": "WARNING", "msg": "low disk", "ts": "2024-01-01T00:00:00"}
        )
        entry = parse_log_line(line)
        assert entry.level == "WARN"

    def test_json_severity_field(self):
        line = json.dumps(
            {"severity": "DEBUG", "text": "trace", "time": "2024-01-01T00:00:00"}
        )
        entry = parse_log_line(line)
        assert entry.level == "DEBUG"

    def test_json_preserves_raw(self):
        raw = json.dumps({"level": "INFO", "message": "hello"})
        entry = parse_log_line(raw)
        assert entry.raw == raw


# ---------------------------------------------------------------------------
# parse_log_line — Plaintext regex
# ---------------------------------------------------------------------------


class TestParseLogLinePlaintext:
    def test_iso_timestamp_prefix(self):
        line = "2024-03-01 10:20:30 ERROR database connection failed"
        entry = parse_log_line(line)
        assert entry.level == "ERROR"
        assert "database connection failed" in entry.message

    def test_iso_t_separator(self):
        line = "2024-03-01T10:20:30 WARN high memory usage"
        entry = parse_log_line(line)
        assert entry.level == "WARN"

    def test_bracket_format(self):
        entry = parse_log_line("[INFO] server started on port 8080")
        assert entry.level == "INFO"
        assert "server started" in entry.message

    def test_bracket_error(self):
        entry = parse_log_line("[ERROR] null pointer exception")
        assert entry.level == "ERROR"

    def test_prefix_colon_format(self):
        entry = parse_log_line("DEBUG: entering request handler")
        assert entry.level == "DEBUG"
        assert "entering request handler" in entry.message

    def test_case_insensitive(self):
        entry = parse_log_line("[warn] disk almost full")
        assert entry.level == "WARN"

    def test_warning_normalized_to_warn(self):
        entry = parse_log_line("[WARNING] deprecated function called")
        assert entry.level == "WARN"


# ---------------------------------------------------------------------------
# parse_log_line — Unknown / malformed
# ---------------------------------------------------------------------------


class TestParseLogLineMalformed:
    def test_arbitrary_text_is_unknown(self):
        entry = parse_log_line("random unstructured text here")
        assert entry.level == "UNKNOWN"

    def test_malformed_json_is_unknown(self):
        entry = parse_log_line('{"level": "INFO", "message":')
        assert entry.level == "UNKNOWN"

    def test_raw_preserved_for_unknown(self):
        raw = "some garbage line 42"
        entry = parse_log_line(raw)
        assert entry.raw == raw

    def test_empty_line_is_unknown(self):
        entry = parse_log_line("   ")
        assert entry.level == "UNKNOWN"

    def test_log_entry_is_correct_type(self):
        entry = parse_log_line("garbage")
        assert isinstance(entry, LogEntry)


# ---------------------------------------------------------------------------
# LogBuffer — ring buffer
# ---------------------------------------------------------------------------


class TestLogBuffer:
    def test_appends_entries(self):
        buf = LogBuffer(maxlen=100)
        buf.append(parse_log_line("[INFO] hello"))
        assert len(buf) == 1

    def test_ring_caps_at_maxlen(self):
        buf = LogBuffer(maxlen=10_000)
        for i in range(10_001):
            buf.append(parse_log_line(f"[INFO] line {i}"))
        assert len(buf) == 10_000

    def test_oldest_entry_evicted(self):
        buf = LogBuffer(maxlen=3)
        for msg in ["first", "second", "third", "fourth"]:
            buf.append(parse_log_line(f"[INFO] {msg}"))
        messages = [e.message for e in buf.entries]
        assert "first" not in messages
        assert "fourth" in messages

    def test_entries_returns_list(self):
        buf = LogBuffer()
        buf.append(parse_log_line("[DEBUG] x"))
        assert isinstance(buf.entries, list)

    def test_total_counts_all_appends(self):
        buf = LogBuffer(maxlen=3)
        for i in range(5):
            buf.append(parse_log_line(f"[INFO] {i}"))
        assert buf.total == 5
        assert len(buf) == 3  # ring capped

    def test_since_returns_entries_after_cursor(self):
        buf = LogBuffer()
        for msg in ["a", "b", "c"]:
            buf.append(parse_log_line(f"[INFO] {msg}"))
        result = buf.since(1)
        assert len(result) == 2
        assert result[0].message == "b"
        assert result[1].message == "c"

    def test_since_returns_empty_when_cursor_at_total(self):
        buf = LogBuffer()
        buf.append(parse_log_line("[INFO] x"))
        assert buf.since(1) == []

    def test_since_returns_empty_when_buffer_empty(self):
        buf = LogBuffer()
        assert buf.since(0) == []

    def test_since_handles_ring_wrap(self):
        buf = LogBuffer(maxlen=3)
        for i in range(5):  # evicts 0 and 1
            buf.append(parse_log_line(f"[INFO] {i}"))
        # total=5, buf holds indices 2,3,4; asking after=0 returns all 3
        result = buf.since(0)
        assert len(result) == 3
        assert result[0].message == "2"


# ---------------------------------------------------------------------------
# logs_command — --no-browser suppresses webbrowser.open
# ---------------------------------------------------------------------------


class TestLogsCommand:
    def test_no_browser_suppresses_open(self, tmp_path: Path):
        log_file = tmp_path / "app.log"
        log_file.write_text("[INFO] started\n")

        opened: list[str] = []

        async def _fake_serve(path, *, port, open_browser):
            if open_browser:
                opened.append(f"http://127.0.0.1:{port}")

        with patch("devbrief.commands.logs._serve", side_effect=_fake_serve):
            from typer.testing import CliRunner
            from devbrief.cli import app

            runner = CliRunner()
            runner.invoke(app, ["logs", str(log_file), "--no-browser"])

        assert opened == [], "browser should not be opened with --no-browser"

    def test_browser_opens_without_flag(self, tmp_path: Path):
        log_file = tmp_path / "app.log"
        log_file.write_text("[INFO] started\n")

        opened: list[str] = []

        async def _fake_serve(path, *, port, open_browser):
            if open_browser:
                opened.append(f"http://127.0.0.1:{port}")

        with patch("devbrief.commands.logs._serve", side_effect=_fake_serve):
            from typer.testing import CliRunner
            from devbrief.cli import app

            runner = CliRunner()
            runner.invoke(app, ["logs", str(log_file)])

        assert opened == ["http://127.0.0.1:7890"]

    def test_missing_file_exits_with_error(self, tmp_path: Path):
        from typer.testing import CliRunner
        from devbrief.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["logs", str(tmp_path / "nope.log")])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Polling endpoints — /rows and /metrics
# ---------------------------------------------------------------------------


class TestPollingEndpoints:
    def setup_method(self) -> None:
        """Reset module-level singletons before each test."""
        import devbrief.commands.logs as logs_mod

        logs_mod._buffer = logs_mod.LogBuffer()
        logs_mod._recent.clear()

    def test_rows_content_type_is_html(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        logs_mod._append_entry(parse_log_line("[INFO] hello"))
        client = TestClient(_build_app())
        response = client.get("/rows?after=0")
        assert response.headers["content-type"].startswith("text/html")

    def test_rows_after_0_returns_all_entries(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        for msg in ["first", "second", "third"]:
            logs_mod._append_entry(parse_log_line(f"[INFO] {msg}"))
        client = TestClient(_build_app())
        response = client.get("/rows?after=0")
        assert "first" in response.text
        assert "second" in response.text
        assert "third" in response.text

    def test_rows_after_n_returns_only_new_entries(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        logs_mod._append_entry(parse_log_line("[INFO] old"))
        logs_mod._append_entry(parse_log_line("[INFO] new"))
        client = TestClient(_build_app())
        response = client.get("/rows?after=1")
        assert "old" not in response.text
        assert "new" in response.text

    def test_rows_empty_when_no_new_entries(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        logs_mod._append_entry(parse_log_line("[INFO] entry"))
        client = TestClient(_build_app())
        # after=1 means cursor is at total; no new entries
        response = client.get("/rows?after=1")
        assert response.status_code == 200
        assert "<tr" not in response.text

    def test_rows_response_contains_updated_cursor(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        for i in range(3):
            logs_mod._append_entry(parse_log_line(f"[INFO] {i}"))
        client = TestClient(_build_app())
        response = client.get("/rows?after=0")
        # OOB hidden input must carry the new cursor value (3)
        assert 'id="poll-cursor"' in response.text
        assert 'value="3"' in response.text

    def test_metrics_returns_html(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        logs_mod._append_entry(parse_log_line("[INFO] test"))
        client = TestClient(_build_app())
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    def test_metrics_reflects_buffer_count(self) -> None:
        import devbrief.commands.logs as logs_mod
        from fastapi.testclient import TestClient

        for i in range(5):
            logs_mod._append_entry(parse_log_line(f"[INFO] {i}"))
        client = TestClient(_build_app())
        response = client.get("/metrics")
        assert "5" in response.text
