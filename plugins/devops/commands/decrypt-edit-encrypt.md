---
description: Walk through decrypt → edit → re-encrypt cycle for `openssl enc -aes-256-cbc -pbkdf2` files (`.env.enc`, `.secrets.enc`).
argument-hint: "[path-to-.enc-file-or-directory]"
allowed-tools: Skill
---

Invoke the decrypt-edit-encrypt skill to safely edit an `openssl`-encrypted `.env.enc` or `.secrets.enc` file: decrypt → read/edit → re-encrypt → cleanup, with gitignore and `-a` flag-consistency pre-checks.

Use the Skill tool with:
- skill: "decrypt-edit-encrypt"
- args: "$ARGUMENTS"
