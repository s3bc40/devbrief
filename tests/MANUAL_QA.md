# Manual QA — devbrief env v0.4.0

Run these from the **devbrief repo root** after `uv run maturin develop`.
Each scenario is one terminal command and one expected result.

---

## Prerequisites

```bash
uv run maturin develop
```

---

## Check 1 — .gitignore audit

### Scenario 1: clean run on devbrief itself

```bash
uv run devbrief env .
```

**Expected:** `.gitignore` shows ✅ present. Any missing advisory entries show ⚠️. No errors on this check since devbrief has a `.gitignore`.

---

### Scenario 2: missing .gitignore

```bash
mkdir /tmp/test-env-empty && uv run devbrief env /tmp/test-env-empty
```

**Expected:** ❌ `.gitignore` not found. Exit code 1.

---

### Scenario 3: .gitignore present but missing entries

```bash
mkdir /tmp/test-env-partial
echo "node_modules" > /tmp/test-env-partial/.gitignore
uv run devbrief env /tmp/test-env-partial
```

**Expected:** ✅ `.gitignore` present, then ⚠️ for each missing advisory entry (`.env`, `*.pem`, etc.).

---

## Check 2 — .env drift

### Scenario 4: clean drift — keys match

```bash
mkdir /tmp/test-env-drift
printf "API_KEY=\nDB_URL=\n" > /tmp/test-env-drift/.env.example
printf "API_KEY=abc\nDB_URL=postgres://...\n" > /tmp/test-env-drift/.env
echo "node_modules" > /tmp/test-env-drift/.gitignore
uv run devbrief env /tmp/test-env-drift
```

**Expected:** ✅ `.env drift` — all `.env.example` keys present.

---

### Scenario 5: key missing from .env

```bash
mkdir /tmp/test-env-missing
printf "API_KEY=\nDB_URL=\nSECRET=\n" > /tmp/test-env-missing/.env.example
printf "API_KEY=abc\n" > /tmp/test-env-missing/.env
echo "node_modules" > /tmp/test-env-missing/.gitignore
uv run devbrief env /tmp/test-env-missing
```

**Expected:** ⚠️ `DB_URL` and `SECRET` missing from `.env`.

---

### Scenario 6: undocumented key in .env

```bash
mkdir /tmp/test-env-undoc
printf "API_KEY=\n" > /tmp/test-env-undoc/.env.example
printf "API_KEY=abc\nMY_SECRET_VAR=xyz\n" > /tmp/test-env-undoc/.env
echo "node_modules" > /tmp/test-env-undoc/.gitignore
uv run devbrief env /tmp/test-env-undoc
```

**Expected:** ⚠️ `MY_SECRET_VAR` undocumented in `.env.example`.

---

### Scenario 7: no .env at all

```bash
mkdir /tmp/test-env-noenv
printf "API_KEY=\n" > /tmp/test-env-noenv/.env.example
echo "node_modules" > /tmp/test-env-noenv/.gitignore
uv run devbrief env /tmp/test-env-noenv
```

**Expected:** INFO — `.env` not found, skipping. Not an error.

---

## Check 3 — Secret detection

### Scenario 8: AWS access key in a Python file

```bash
mkdir /tmp/test-secrets
echo "node_modules" > /tmp/test-secrets/.gitignore
echo 'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"' > /tmp/test-secrets/config.py
uv run devbrief env /tmp/test-secrets
```

**Expected:** ❌ Secret detected — `config.py:1` — `aws_access_key_id` — `AKIA***`. Exit code 1.

---

### Scenario 9: secret in a gitignored file — must NOT be flagged

```bash
mkdir /tmp/test-secrets-ignored
printf ".env\n" > /tmp/test-secrets-ignored/.gitignore
printf 'ANTHROPIC_API_KEY=sk-ant-abc123def456ghi789jkl012mno345pqr678stu\n' \
  > /tmp/test-secrets-ignored/.env
uv run devbrief env /tmp/test-secrets-ignored
```

**Expected:** No secret detection error. `.env` is gitignored so the Rust scanner skips it.

---

### Scenario 10: private key header

```bash
mkdir /tmp/test-privkey
echo "node_modules" > /tmp/test-privkey/.gitignore
echo "-----BEGIN RSA PRIVATE KEY-----" > /tmp/test-privkey/id_rsa.pub
uv run devbrief env /tmp/test-privkey
```

**Expected:** ❌ Secret detected — `id_rsa.pub:1` — `private_key_header`. Exit code 1.

---

## Flags

### Scenario 11: --strict promotes warnings to errors

```bash
uv run devbrief env /tmp/test-env-partial --strict
echo "Exit code: $?"
```

**Expected:** Exit code 1 even when only warnings are present (missing advisory entries).

---

### Scenario 12: --quiet suppresses Rich output

```bash
uv run devbrief env . --quiet
```

**Expected:** Plain text output. No Rich markup, no color codes, no emoji padding.

---

## Cleanup

```bash
rm -rf /tmp/test-env-empty /tmp/test-env-partial /tmp/test-env-drift \
       /tmp/test-env-missing /tmp/test-env-undoc /tmp/test-env-noenv \
       /tmp/test-secrets /tmp/test-secrets-ignored /tmp/test-privkey
```
