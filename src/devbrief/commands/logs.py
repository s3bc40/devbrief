"""devbrief logs — live log dashboard via FastAPI + HTMX polling."""

from __future__ import annotations

import asyncio
import html as _html
import json
import re
import sys
import time as _time
import webbrowser
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from devbrief.display import console

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RING_BUFFER_SIZE = 10_000

_LEVEL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # ISO-ish timestamp prefix: 2024-01-01 12:00:00,123 ERROR msg
    (
        "level",
        re.compile(
            r"(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)"
            r"\s+(?P<level>ERROR|WARN(?:ING)?|INFO|DEBUG)\s+(?P<msg>.+)",
            re.IGNORECASE,
        ),
    ),
    # [LEVEL] msg
    (
        "bracket",
        re.compile(
            r"\[(?P<level>ERROR|WARN(?:ING)?|INFO|DEBUG)\]\s*(?P<msg>.+)",
            re.IGNORECASE,
        ),
    ),
    # LEVEL: msg
    (
        "prefix",
        re.compile(
            r"^(?P<level>ERROR|WARN(?:ING)?|INFO|DEBUG):\s*(?P<msg>.+)",
            re.IGNORECASE,
        ),
    ),
]

_LEVEL_ALIASES = {
    "WARNING": "WARN",
}


# ---------------------------------------------------------------------------
# Log entry model (plain dataclass — no Pydantic needed)
# ---------------------------------------------------------------------------


class LogEntry:
    __slots__ = ("timestamp", "level", "message", "raw")

    def __init__(self, timestamp: str, level: str, message: str, raw: str) -> None:
        self.timestamp = timestamp
        self.level = level
        self.message = message
        self.raw = raw

    def to_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "raw": self.raw,
        }


# ---------------------------------------------------------------------------
# Log parser
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def parse_log_line(line: str) -> LogEntry:
    """Parse a single log line into a LogEntry.

    Resolution order:
    1. Structured JSON (first valid JSON object wins)
    2. Plaintext regex (common log formats)
    3. UNKNOWN — raw line
    """
    stripped = line.strip()
    if not stripped:
        return LogEntry(_now_iso(), "UNKNOWN", stripped, stripped)

    # 1. JSON
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            level = str(
                obj.get("level")
                or obj.get("levelname")
                or obj.get("severity")
                or "UNKNOWN"
            ).upper()
            level = _LEVEL_ALIASES.get(level, level)
            ts = str(
                obj.get("timestamp") or obj.get("time") or obj.get("ts") or _now_iso()
            )
            msg = str(
                obj.get("message") or obj.get("msg") or obj.get("text") or stripped
            )
            return LogEntry(ts, level, msg, stripped)
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. Regex
    for _, pattern in _LEVEL_PATTERNS:
        m = pattern.match(stripped)
        if m:
            gd = m.groupdict()
            level = gd["level"].upper()
            level = _LEVEL_ALIASES.get(level, level)
            ts = gd.get("ts") or _now_iso()
            msg = gd["msg"].strip()
            return LogEntry(ts, level, msg, stripped)

    # 3. Unknown
    return LogEntry(_now_iso(), "UNKNOWN", stripped, stripped)


# ---------------------------------------------------------------------------
# Ring buffer
# ---------------------------------------------------------------------------


class LogBuffer:
    def __init__(self, maxlen: int = RING_BUFFER_SIZE) -> None:
        self._buf: deque[LogEntry] = deque(maxlen=maxlen)
        self._start: float | None = None
        self._total: int = 0  # total ever appended (not capped by maxlen)

    def append(self, entry: LogEntry) -> None:
        if self._start is None:
            self._start = _time.monotonic()
        self._total += 1
        self._buf.append(entry)

    @property
    def entries(self) -> list[LogEntry]:
        return list(self._buf)

    @property
    def total(self) -> int:
        """Absolute count of entries ever appended (monotonically increasing)."""
        return self._total

    def since(self, after: int) -> list[LogEntry]:
        """Return entries with absolute index > after.

        'after' is an absolute insertion count (from .total), not a ring
        position.  Entries already evicted from the ring are silently skipped.
        """
        if after >= self._total:
            return []
        buf = list(self._buf)
        if not buf:
            return []
        buf_start = self._total - len(buf)  # absolute index of buf[0]
        start_pos = max(0, after - buf_start)
        return buf[start_pos:]

    @property
    def rate_per_sec(self) -> float:
        if self._start is None or self._total == 0:
            return 0.0
        elapsed = _time.monotonic() - self._start
        return self._total / elapsed if elapsed > 0 else 0.0

    def __len__(self) -> int:
        return len(self._buf)


# ---------------------------------------------------------------------------
# Shared state (module-level singletons per server process)
# ---------------------------------------------------------------------------

_buffer = LogBuffer()

# Tracks (monotonic_ingest_time, level) for the metrics 5-min window.
# Uses ingest time, NOT log-file timestamps, so old log files work correctly.
_recent: deque[tuple[float, str]] = deque(maxlen=RING_BUFFER_SIZE)


def _append_entry(entry: LogEntry) -> None:
    """Append to the ring buffer and record ingest time for metrics."""
    _buffer.append(entry)
    _recent.append((_time.monotonic(), entry.level))


# ---------------------------------------------------------------------------
# Log ingestion helpers
# ---------------------------------------------------------------------------


async def _ingest_file(path: Path) -> None:
    """Read a log file into the ring buffer, then poll for new lines every 1 s.

    The 1-second sleep loop is a dependency-free replacement for watchfiles:
    after the initial read the file handle is kept open so readline() picks up
    any bytes appended after startup without reopening the file descriptor.
    """
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        while line := fh.readline():
            _append_entry(parse_log_line(line))
        while True:
            await asyncio.sleep(1)
            while line := fh.readline():
                _append_entry(parse_log_line(line))


async def _ingest_stdin() -> None:
    """Read stdin line-by-line in a thread executor to avoid blocking."""
    loop = asyncio.get_running_loop()

    def _read_all() -> list[str]:
        return sys.stdin.read().splitlines()

    lines = await loop.run_in_executor(None, _read_all)
    for line in lines:
        _append_entry(parse_log_line(line))


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _build_app() -> FastAPI:
    app = FastAPI(title="devbrief logs")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request) -> HTMLResponse:
        entries = _buffer.entries
        return templates.TemplateResponse(
            "logs/dashboard.html",
            {
                "request": request,
                "entries": entries,
                "metrics": _compute_metrics(),
                "total": _buffer.total,
            },
        )

    @app.get("/rows", response_class=HTMLResponse)
    async def get_rows(after: int = 0) -> HTMLResponse:
        entries = _buffer.since(after)
        new_after = _buffer.total
        rows_html = "".join(_render_row(e) for e in entries)
        # OOB-swap only the cursor input (a plain data element — no triggers).
        # The polling div (#row-poll) is never replaced, so its every-2s timer
        # runs stably and always picks up the current value of #poll-cursor via
        # hx-include.  Replacing the polling element itself via OOB can leave
        # the old setTimeout running on the detached node, preventing the new
        # element's timer from starting and freezing the after= cursor at 0.
        cursor = (
            f'<input type="hidden" id="poll-cursor" name="after"'
            f' value="{new_after}" hx-swap-oob="true">'
        )
        return HTMLResponse(rows_html + cursor)

    @app.get("/metrics", response_class=HTMLResponse)
    async def get_metrics() -> HTMLResponse:
        return HTMLResponse(_render_metrics())

    @app.get("/entries")
    async def get_entries() -> list[dict[str, str]]:
        return [e.to_dict() for e in _buffer.entries]

    return app


def _render_row(entry: LogEntry) -> str:
    """Render a single log entry as a one-line HTML <tr> fragment."""
    ts = _html.escape(entry.timestamp)
    level = _html.escape(entry.level)
    msg = _html.escape(entry.message)
    return (
        f'<tr class="log-row" data-level="{level}" data-ts="{ts}" data-msg="{msg.lower()}">'
        f'<td class="ts">{ts}</td>'
        f'<td class="level-cell level-{level}">{level}</td>'
        f"<td>{msg}</td>"
        f"</tr>"
    )


def _compute_metrics() -> dict[str, str]:
    """Compute current metric values.

    The 5-min window uses monotonic INGEST time from _recent, not the log-file
    timestamps stored in LogEntry.  Log files typically have old timestamps so
    comparing them to datetime.now() would always return zero errors/warnings.
    """
    total = len(_buffer)
    cutoff = _time.monotonic() - 5 * 60
    errors5 = sum(1 for t, lvl in _recent if t >= cutoff and lvl == "ERROR")
    warns5 = sum(1 for t, lvl in _recent if t >= cutoff and lvl == "WARN")
    return {
        "total": str(total),
        "errors5": str(errors5),
        "warns5": str(warns5),
        "rate": f"{_buffer.rate_per_sec:.1f}",
    }


def _render_metrics() -> str:
    """Render the inner HTML of the metrics bar as a single-line string."""
    m = _compute_metrics()
    return (
        f'<div class="metric"><span class="label">Total entries</span>'
        f'<span class="value">{m["total"]}</span></div>'
        f'<div class="metric"><span class="label">Errors / 5 min</span>'
        f'<span class="value error">{m["errors5"]}</span></div>'
        f'<div class="metric"><span class="label">Warnings / 5 min</span>'
        f'<span class="value warn">{m["warns5"]}</span></div>'
        f'<div class="metric"><span class="label">Entries / sec</span>'
        f'<span class="value info">{m["rate"]}</span></div>'
    )


# ---------------------------------------------------------------------------
# Typer command
# ---------------------------------------------------------------------------


def logs_command(
    log_file: Annotated[
        Path | None,
        typer.Argument(
            help="Path to a local log file. Omit to read from stdin.",
            exists=False,
            show_default=False,
        ),
    ] = None,
    port: Annotated[
        int,
        typer.Option("--port", help="Dashboard port.", show_default=True),
    ] = 7890,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Suppress automatic browser open."),
    ] = False,
) -> None:
    """Stream logs into a live dashboard."""
    stdin_mode = log_file is None
    if not stdin_mode and not log_file.exists():  # type: ignore[union-attr]
        console.print(f"[bold red]Error:[/bold red] File not found: {log_file}")
        raise typer.Exit(code=1)

    asyncio.run(_serve(log_file, port=port, open_browser=not no_browser))


async def _serve(
    log_file: Path | None,
    *,
    port: int,
    open_browser: bool,
) -> None:
    app = _build_app()

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    if log_file is not None:
        ingest_task = asyncio.create_task(_ingest_file(log_file))
    else:
        ingest_task = asyncio.create_task(_ingest_stdin())

    url = f"http://127.0.0.1:{port}"
    console.print(
        f"[bold green]devbrief logs[/bold green] dashboard at [link={url}]{url}[/link]"
    )
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    if open_browser:
        # Slight delay so the server is ready before the browser hits it
        async def _open() -> None:
            await asyncio.sleep(0.8)
            webbrowser.open(url)

        asyncio.create_task(_open())

    try:
        await server.serve()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        ingest_task.cancel()
        console.print("\n[dim]Server stopped.[/dim]")
