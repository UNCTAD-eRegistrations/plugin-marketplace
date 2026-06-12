---
description: Check and upsert translations directly in the Global Translation Service (works even when the key already exists)
argument-hint: [lang] [key=value ...]
effort: low
allowed-tools: [mcp__Translations__gts_translations, mcp__Translations__gts_update_batch, mcp__Translations__global_reload, mcp__Translations__global_status]
---

# GTS Direct Check & Upsert

Talks straight to the Global Translation Service catalogue (default
https://translations.eregistrations.org, override with `GTS_URL`), bypassing
instance BPAs. Use when keys are stuck: the instance-side sync pipeline only
*inserts* unknown keys — it cannot fix keys that are already registered with
a wrong or key-as-value entry. Access requires your public IP to be on the
GTS haproxy whitelist (`translations-global-whitelist.lst`); a 403 means it
is not.

Arguments: `$ARGUMENTS`

## Instructions

1. Parse the arguments: first token is the language code (e.g. `en`); any
   `key=value` pairs follow. If only keys are known (no values), the operator
   may just want a check — ask which mode they want if ambiguous.

2. **Always check first** — call `gts_translations(target_lang, keys=[...])`
   with the keys in question. Report the classification:
   - `missing` — not in the GTS at all
   - `key_as_value` — registered but never given a real value (renders as the
     raw key in every UI)
   - `present` — already has a real value (show it)
   If `push_needed=false`, report that the catalogue is already up to date
   and stop — no write needed.

3. If a push is needed and the operator supplied values, show exactly what
   would change by calling `gts_update_batch(...)` with its default
   `dry_run=true`. Present the create/update/unchanged breakdown.

4. Ask the operator to confirm: *"Write these N changes to the GLOBAL
   catalogue (affects all instances)? (yes/no)"*

5. On yes, re-run `gts_update_batch` with `dry_run=false`,
   `confirm_affects_global_catalog=true`, and `username` set to the
   operator's name. **Check `verified_failed` in the result** — the GTS has
   historically reported success on writes that did not persist; any key
   listed there must be retried or investigated.

6. Remind the operator that instances do not pick this up automatically:
   offer to run `global_reload(instance=...)` for the instance(s) they care
   about, and verify afterwards with `global_status(instance=...)`.
