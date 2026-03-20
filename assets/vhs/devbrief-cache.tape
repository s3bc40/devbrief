# devbrief cache demo — Post 2 builder story
# Pattern: Hide + Sleep to mask API wait time
# Requires: rm -rf ~/.cache/devbrief/ before running

Output devbrief-cache.gif

Set FontSize 16
Set Width 1200
Set Height 600
Set Theme "Ayu Mirage"
Set FontFamily "Noto Sans Mono"
Set Padding 20
Set CursorBlink false
Set TypingSpeed 40ms
Set WindowBar Colorful

# ── Setup: clear cache ──────────────────────────────────────
Hide
Type "rm -rf ~/.cache/devbrief/"
Enter
Sleep 500ms
Type "clear"
Enter
Show

# ── Scene 1: cold run (cache miss) ─────────────────────────
Type "devbrief repo https://github.com/fastapi/typer"
Sleep 400ms
Enter
Hide
Sleep 25s
Show
Sleep 2500ms

# ── Scene 2: cache hit ──────────────────────────────────────
Hide
Type "clear"
Enter
Show

Type "devbrief repo https://github.com/fastapi/typer"
Sleep 400ms
Enter
Hide
Sleep 2s
Show
Sleep 2500ms

# ── Scene 3: --refresh then cache hit ───────────────────────
Hide
Type "clear"
Enter
Show

Type "devbrief repo https://github.com/fastapi/typer --refresh"
Sleep 400ms
Enter
Hide
Sleep 25s
Show
Sleep 800ms

Type "devbrief repo https://github.com/fastapi/typer"
Sleep 300ms
Enter
Hide
Sleep 2s
Show
Sleep 2500ms