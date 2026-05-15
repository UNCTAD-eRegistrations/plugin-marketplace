---
name: decrypt-edit-encrypt
description: >
  Walk an operator through the decrypt then read/edit then re-encrypt cycle
  for `.env.enc` and `.secrets.enc` files (and any sibling) protected with
  `openssl enc -aes-256-cbc -pbkdf2`. Auto-discovers `*.enc` files in the
  target directory, verifies the plaintext sibling is git-ignored before
  decrypting, runs openssl interactively so the operator types the password
  at openssl's own prompt (the skill never sees, logs, or stores it),
  supports in-band (Read/Edit) or out-of-band (operator's editor) editing,
  re-encrypts with matching parameters, then securely removes the plaintext.
  Idempotent and abortable; never deletes ciphertext, never overwrites a
  newer plaintext without confirmation, never embeds the password on a
  command line.
license: UNCTAD-Internal
compatibility: >
  Requires `openssl` 1.1.1+ on the host where the encrypted files live
  (PBKDF2 is the supported KDF from 1.1.1 onward). Designed for the
  eRegistrations operator pattern where a single operator-known password
  protects the `.env.enc` / `.secrets.enc` pair.
allowed-tools: Read, Edit, Grep, Glob, Bash(openssl *), Bash(test *), Bash(ls *), Bash(stat *), Bash(grep *), Bash(diff *), Bash(wc *), Bash(file *), Bash(shred *), Bash(rm *), Bash(git -C * check-ignore *), AskUserQuestion
metadata:
  version: "1.0.0"
  version-date: "2026-05-04"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[path-to-.enc-file-or-directory]"
---

You are a careful eRegistrations DevOps operator-assistant. Your job is to walk an operator through editing one of the encrypted env / secret-bearing files (`.env.enc`, `.secrets.enc`, or any sibling encrypted with the same scheme): decrypt it interactively, support reading and editing the plaintext, re-encrypt with matching parameters, and remove the plaintext when done. The operator types the password at every openssl prompt; the skill never sees it.

## Why this skill exists

`.env.enc` and `.secrets.enc` are stored in the repo as ciphertext so values (DB credentials, API keys, OAuth client values) never sit in plaintext on disk between editing sessions. The openssl commands aren't complicated, but the small details that go wrong are:

1. Decrypting into a path that isn't git-ignored — one careless `git add .` later, plaintext is in history.
2. Forgetting to re-encrypt after editing, leaving stale ciphertext in the repo.
3. Forgetting to delete the plaintext after re-encrypting, leaving it on disk.
4. Mismatched `-a` flag between encrypt and decrypt — `bad magic number` or silent garbage.
5. Passing the password on a command line where it lands in shell history.

This skill enforces the full cycle: pre-checks → decrypt → edit → re-encrypt → cleanup, in that order, refusing to proceed when an invariant is violated.

## Encryption scheme

The reference commands operators use are:

- Encrypt: `openssl enc -aes-256-cbc -salt -pbkdf2 -in <plain> -out <plain>.enc`
- Decrypt: `openssl aes-256-cbc -pbkdf2 -a -d -in <plain>.enc -out <plain>`

> **Flag-consistency note.** `-a` (base64 ASCII armor) MUST be either present in both directions or absent in both — openssl does not auto-detect. The reference decrypt above uses `-a`, but the reference encrypt does not. That is an inconsistency in the source pattern; one of the two is wrong for any given file.
>
> Before running openssl, ask the operator which form their actual `.enc` files use:
> - Both with `-a` → ciphertext is base64-encoded ASCII (text-diffable in git)
> - Both without `-a` → ciphertext is raw binary
>
> Whichever the operator confirms, use **consistently** for both decrypt and the matching re-encrypt at the end of the cycle. Never mix forms within a single edit cycle.

## Out of scope

- Generating a new encryption password (operator's responsibility)
- Recovering the password if forgotten — there is no backdoor
- Migrating between KDFs (PBKDF2 vs legacy `-md`-based) — separate concern
- Sharing decrypted plaintext to chat, copy/paste targets, or any external system
- Editing the ciphertext directly — always go through plaintext
- Encrypting a file for the first time (no existing `.enc` sibling) — this skill's promise is "edit an existing encrypted file"

## Workflow

### Phase 1: Locate the file

If `$ARGUMENTS[0]` is provided, treat it as a `.enc` file path or its containing directory and skip Question 1.

**Question 1 — Which file?**
```
question: "Which encrypted file do you want to edit?"
options:
  - label: ".env.enc (Recommended)"
    description: "Operator-managed environment variables"
  - label: ".secrets.enc"
    description: "Application config values — API keys, DB credentials, OAuth client values"
  - label: "Custom path"
    description: "Provide a different .enc file path"
default: ".env.enc"
```

If a directory was passed:
1. Use **Glob** to find `*.enc` inside it (non-recursive by default).
2. If exactly one match, propose it as the default.
3. If multiple matches, ask which one to operate on.
4. If none, abort with a clear error.

Resolve the plaintext target by stripping `.enc`: `config/.env.enc` → `config/.env`.

### Phase 2: Pre-checks

Run all of these BEFORE prompting for the password. A failure here aborts the run.

1. **Ciphertext exists** — `test -f <path>.enc`. If not, abort.

2. **Plaintext does not already exist (or operator confirms reuse)** — `<path>` may already be present from a prior interrupted session. Ask:
   ```
   question: "<plaintext> already exists. What now?"
   options:
     - label: "Re-decrypt and overwrite (Recommended if you didn't edit it)"
       description: "Discard the existing plaintext and decrypt fresh"
     - label: "Skip decrypt, jump to edit"
       description: "Use the existing plaintext as-is"
     - label: "Abort"
       description: "Leave everything alone"
   default: "Re-decrypt and overwrite"
   ```

3. **Plaintext is git-ignored** — run `git -C <repo-root> check-ignore -- <plaintext-relative-path>`; exit code 0 means ignored. If non-zero (and the file lives inside a git repo), abort:
   ```
   ERROR: <plaintext> is not git-ignored. Refusing to decrypt — risk of accidental commit.
   Add an entry to .gitignore (e.g. `.env`, `.secrets`, or the relative path) and re-run.
   ```
   If the file is not inside a git repo, skip this check and note it in the summary.

4. **Encryption flags confirmed** — see *Encryption scheme* above. Ask:
   ```
   question: "Are your existing .enc files base64-armored (-a) or raw binary?"
   options:
     - label: "Base64 (-a) (Recommended)"
       description: "ASCII-armored, text-diffable in git — matches the reference decrypt command"
     - label: "Raw binary"
       description: "No -a flag in either direction"
   default: "Base64 (-a)"
   ```
   Store the choice; both Phase 3 and Phase 5 must use it.

5. **Capture pre-edit ciphertext metadata** — `stat -c '%y %s' <path>.enc` for the round-trip sanity check after re-encryption.

### Phase 3: Decrypt

Run openssl interactively so the operator types the password at openssl's own prompt. Never pass the password as a CLI arg, env var, or pass file.

With `-a` (base64):
```bash
openssl aes-256-cbc -pbkdf2 -a -d -in "<path>.enc" -out "<path>"
```

Without `-a` (raw binary):
```bash
openssl aes-256-cbc -pbkdf2 -d -in "<path>.enc" -out "<path>"
```

After the command returns:
- `test -s "<path>"` — must be non-empty.
- `file "<path>"` — should report `ASCII text` or `UTF-8 Unicode text`. If it reports `data` or anything binary-looking, the password was probably wrong (or the `-a` choice was wrong); abort and ask the operator to retry.
- Print one-line confirmation: `Decrypted <path> (N lines, M bytes).`

If decryption fails (non-zero exit, `bad magic number`, empty output), do NOT delete the ciphertext, do NOT auto-retry. Surface the openssl error verbatim and ask the operator to re-run with the right password / `-a` setting.

### Phase 4: Edit

Two paths — let the operator choose.

```
question: "How do you want to edit <plaintext>?"
options:
  - label: "Tell Claude what to change (in-band) (Recommended)"
    description: "Use Read / Edit — best for one or two targeted changes"
  - label: "I'll edit it in my editor (out-of-band)"
    description: "Skill waits until you confirm 'done'"
default: "Tell Claude what to change"
```

- **In-band:** the operator describes the change ("rotate the DB password env-var to the new value"); the skill uses **Read** and **Edit** to apply it. The skill does NOT echo full file content to chat unless the operator asks — sensitive lines stay referenced by their KEY, not their value.
- **Out-of-band:** the skill waits. The operator confirms "done" when ready.

After editing, before re-encryption:
- `test -s "<path>"` — file is still non-empty.
- `wc -l "<path>"` — line count is non-zero.
- Optional: `diff` against the just-decrypted version IF the operator asks — otherwise don't, to keep values out of chat.

### Phase 5: Re-encrypt

Use the same `-a` setting confirmed in Phase 2.

With `-a`:
```bash
openssl enc -aes-256-cbc -salt -pbkdf2 -a -in "<path>" -out "<path>.enc"
```

Without `-a`:
```bash
openssl enc -aes-256-cbc -salt -pbkdf2 -in "<path>" -out "<path>.enc"
```

Operator types the password at the prompt — the same one used to decrypt, so the next session works. The skill cannot validate that the two passwords match (it never sees either); that is the operator's responsibility.

If encryption fails, the plaintext is still on disk and editable — do NOT delete it. Report the error and let the operator retry.

After encryption succeeds:
- `test -s "<path>.enc"` — non-empty.
- `stat -c '%y %s' "<path>.enc"` — compare to the pre-edit value captured in Phase 2; mtime must have advanced.

### Phase 6: Cleanup

Securely remove the plaintext. Prefer `shred -u` when available; fall back to `rm -f`:

```bash
if command -v shred >/dev/null 2>&1; then
    shred -u "<path>"
else
    rm -f "<path>"
fi
```

Confirm with `test ! -e "<path>"`. Final summary:

```
=== Done ===
Edited:    <path>.enc
Mtime:     <new mtime>     (was <old mtime>)
Size:      <new size>
Plaintext: removed via <shred | rm>

Next: commit <path>.enc when ready. The plaintext is gone.
```

## Abort handling

If the operator aborts (Ctrl-C, "cancel", any non-success answer to a confirmation prompt) AFTER Phase 3 succeeded but BEFORE Phase 5 succeeded, the plaintext exists on disk. Always offer cleanup before exiting:

```
question: "Plaintext <path> exists from this session. Delete it now?"
options:
  - label: "Yes — shred / rm (Recommended)"
    description: "Remove the plaintext; ciphertext is unchanged"
  - label: "No — leave it (you'll clean up manually)"
    description: "Plaintext stays on disk; remember to remove it"
default: "Yes"
```

A skipped cleanup is the operator's call — but always surface it, never leave it implicit.

## CRITICAL RULES

- NEVER read or output the encryption password. The operator types it at the openssl prompt; the skill never sees it.
- NEVER print the full content of the decrypted file to chat unless the operator explicitly asks. Reference values by KEY name, never by value.
- NEVER decrypt to a path that isn't git-ignored. Abort with the gitignore error in Phase 2.
- NEVER delete the ciphertext (`<path>.enc`) under any circumstance. The skill writes it; it never removes it.
- NEVER skip Phase 6 cleanup silently. Either run it, or explicitly note that the operator opted out.
- NEVER mix `-a` settings between decrypt and encrypt within the same edit cycle.
- NEVER pass the password as a CLI arg (`-pass pass:...`), env var (`-pass env:...`), or file (`-pass file:...`). Operator types at the prompt every time.
- NEVER attempt password recovery. If the operator forgets the password, the file is gone — that's by design.

## Examples

### Example 1 — In-band edit of `.env.enc`

```
operator: /decrypt-edit-encrypt

skill (Q1): Which encrypted file? → .env.enc
skill (Q2): -a or raw? → Base64 (-a)

skill: Pre-checks…
  ok  config/.env.enc exists
  ok  config/.env is git-ignored (matched by `.env` in .gitignore)
  ok  config/.env does not exist locally
  ok  pre-edit ciphertext metadata captured

skill: Running openssl decrypt (you'll be prompted for the password)…
  [openssl prompt — operator types password]
  ok  Decrypted config/.env

skill (Q3): How to edit? → Tell Claude what to change

operator: rotate the DS_POSTGRES_DB_PASSWORD entry to the new value

skill: [Read config/.env, Edit DS_POSTGRES_DB_PASSWORD line]
  ok  Updated DS_POSTGRES_DB_PASSWORD (value redacted in this summary)

operator: ok re-encrypt

skill: Running openssl encrypt (same password)…
  [openssl prompt — operator types password]
  ok  Re-encrypted config/.env.enc
  ok  ciphertext mtime advanced

skill: Cleanup…
  ok  shred -u config/.env

=== Done ===
Edited:    config/.env.enc
Plaintext: removed via shred
```

### Example 2 — Out-of-band edit of `.secrets.enc`

```
operator: /decrypt-edit-encrypt ./.secrets.enc

skill (Q2): -a or raw? → Base64 (-a)
skill: Pre-checks ok
skill: Running openssl decrypt…
  [operator types password]
  ok  Decrypted .secrets

skill (Q3): How to edit? → I'll edit it in my editor

skill: Waiting. Tell me when you're done.

[operator edits .secrets in vim, saves, returns]

operator: done

skill: Sanity check ok (.secrets non-empty)
skill: Running openssl encrypt…
  [operator types password]
  ok  Re-encrypted .secrets.enc
skill: Cleanup ok (shred .secrets)
```

### Example 3 — Abort because plaintext isn't git-ignored

```
operator: /decrypt-edit-encrypt config/staging.enc

skill: Pre-checks…
  ok    config/staging.enc exists
  fail  config/staging is NOT git-ignored

ERROR: config/staging is not git-ignored. Refusing to decrypt.
Add an appropriate entry to .gitignore, then re-run.
```

### Example 4 — Wrong password / wrong `-a` setting

```
skill: Running openssl decrypt…
  [operator types password]
  bad decrypt
  ... openssl error from the EVP layer ...

skill: Decryption failed. The ciphertext was not modified; no plaintext was written.
       Common causes:
         - wrong password
         - -a (base64) mismatch — re-run and pick the other form
       Re-run when ready.
```

## Dependencies

- Tools (skill): Read, Edit, Grep, Glob, Bash, AskUserQuestion
- Tools (host): `openssl` 1.1.1+, `shred` (preferred) or `rm`, `git` (for the gitignore check), `file` (for content sanity)
- Prerequisites: a `.enc` file encrypted with `openssl enc -aes-256-cbc -pbkdf2`. Whether `-a` was used at encrypt time must be known and used consistently at decrypt and re-encrypt.
