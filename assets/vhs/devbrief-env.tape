# devbrief env demo — Social post
# Three checks: gitignore audit · .env drift · secret scan
# Requires: uv run maturin develop (Rust extension must be compiled)

Output ../devbrief-env.gif

Set FontSize 16
Set Width 1200
Set Height 600
Set Theme "Ayu Mirage"
Set FontFamily "Noto Sans Mono"
Set Padding 20
Set CursorBlink false
Set TypingSpeed 40ms
Set WindowBar Colorful
Set PlaybackSpeed 1.5

# ── Setup: prepare temp demo dirs ──────────────────────
Hide
Type "rm -rf /tmp/demo-env-drift /tmp/demo-env-secrets"
Enter
Sleep 200ms
Type "mkdir /tmp/demo-env-drift"
Enter
Type "echo API_KEY= > /tmp/demo-env-drift/.env.example"
Enter
Type "echo DB_URL= >> /tmp/demo-env-drift/.env.example"
Enter
Type "echo SECRET= >> /tmp/demo-env-drift/.env.example"
Enter
Type "echo API_KEY=abc > /tmp/demo-env-drift/.env"
Enter
Type "echo node_modules > /tmp/demo-env-drift/.gitignore"
Enter
Type "mkdir /tmp/demo-env-secrets"
Enter
Type "echo node_modules > /tmp/demo-env-secrets/.gitignore"
Enter
Type "echo AWS_ACCESS_KEY_ID = AKIAIOSFODNN7EXAMPLE > /tmp/demo-env-secrets/config.py"
Enter
Sleep 300ms
Type "clear"
Enter
Show

# ── Scene 1: all-green run on devbrief itself ──────────
Type "devbrief env ."
Sleep 400ms
Enter
Sleep 3s
Sleep 2000ms

# ── Scene 2: .env drift — keys missing from .env ───────
Hide
Type "clear"
Enter
Show

Type "devbrief env /tmp/demo-env-drift"
Sleep 400ms
Enter
Sleep 3s
Sleep 2000ms

# ── Scene 3: secret scan — AWS key caught ──────────────
Hide
Type "clear"
Enter
Show

Type "devbrief env /tmp/demo-env-secrets"
Sleep 400ms
Enter
Sleep 3s
Sleep 2000ms

# ── Cleanup ────────────────────────────────────────────
Hide
Type "rm -rf /tmp/demo-env-drift /tmp/demo-env-secrets"
Enter
Show
