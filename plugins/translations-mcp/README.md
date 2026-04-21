# Translations MCP — eRegistrations Translation Tools

Governance-grade MCP for managing translations across eRegistrations services. Combines context-aware authoring with portfolio-level visibility, rollback, and cross-instance safety.

Covers four concerns:

1. **Authoring** — context-aware translation of BPA service definitions (field labels, tooltips, grid columns, form structure, DS system strings) with glossary enforcement, GDB catalog enrichment, and audited batch writes.
2. **Portfolio governance** — instance-wide coverage, cross-service diff, audit history, and rollback of prior writes.
3. **Global Translation Service (GTS) sync** — one-command recovery when a country instance is out of sync with the central catalog (shell keys showing as raw identifiers like `nav.services` in the admin UI).
4. **Safety gates** — explicit confirmation for writes that affect all instances or flip display-wide behavior.

## Prerequisites

Install the **bpa-mcp** plugin first — it provides authentication and instance management that Translations depends on.

## Tools (22)

### Authoring & Context
- `translation_status` — Per-language translation coverage for a service
- `translation_instance_status` — **Portfolio view**: rank services by missing translations across the instance
- `language_list` — Active languages for an instance
- `translation_glossary` — Glossary terms for a language (from GDB, cached)
- `translation_context` — Compiled translation brief: field context, glossary, GDB enrichment
- `translation_categories` — List filter taxonomy (location → category)

### Write Operations (Audited)
- `translate_batch` — Batch-write service translations. Dry-run, snapshot, audit
- `translation_rollback` — Undo a prior translate_batch from its snapshot
- `translation_replace_or_create` — Rename a fieldId across translations, or create fresh rows
- `translation_delete` — Delete translation entries by ID
- `translation_settings_set` — Update `localAuthorized` / `localSupersedesGlobal` flags. Gated by `confirm_affects_display`
- `ds_system_translate_batch` — Batch-write DS system strings. **Gated by `confirm_affects_global_catalog`** (affects all instances)
- `ds_system_sync` — Register new DS keys after a DS deployment

### Search & Audit
- `translation_search` — Search translations by text; per-service or instance-wide when `service_id` is omitted
- `translation_audit_check` — 4 quality signals: inconsistencies, length warnings, duplicate sources, missing counts
- `translation_audit_detail` — Inspect a prior audit entry + its rollback snapshot
- `translation_history` — Browse recent audit entries; filter by operation_type, user, date
- `translation_diff` — Compare translated keys between two services (only_in_a / only_in_b / different, with 4 reason discriminators)

### DS System Strings
- `ds_system_translations` — List DS system strings (globalName labels, messages)

### Global Translation Service (GTS) Sync
- `translation_global_status` — Probe whether an instance is in sync with GTS (read-only)
- `translation_global_reload` — Pull from GTS. Audited write. Mirrors the "Global Translation" button

### Settings
- `translation_settings_get` — Read instance-wide translation flag state (with plain-English interpretation)

## Commands

| Command | Description |
|---------|-------------|
| `/translations-mcp:status [instance]` | Check whether this instance needs a translation sync |
| `/translations-mcp:fix [instance]` | Diagnose + auto-reload if the instance is out of sync |
| `/translations-mcp:issue [description]` | Report a Translations MCP tool issue |

## Quick Start — Portfolio Coverage

```
# Where should I focus French translations across all active services?
translation_instance_status(instance="guatemala-dev", target_lang="fr")
# → {service_count, total_strings, by_language, services, focus_by_absolute_missing, ...}

# Who's edited translations this week?
translation_history(instance="guatemala-dev", since="2026-04-14")

# Undo yesterday's bad batch
translation_rollback(audit_id="<uuid>", instance="guatemala-dev")
```

## Quick Start — Global Translation Sync

```
# Check whether an instance is out of sync with GTS
translation_global_status(instance="lesotho2")

# If reload_recommended=true, pull from Global Translation Service
translation_global_reload(instance="lesotho2")
```

The `reload` call takes 10–30s — backend iterates every active language and reconciles BPA, DS, and STATISTICS domains in one sweep. The cache is refreshed automatically.

## Quick Start — Service Translation Workflow

```
# 1. Check coverage for a service
translation_status(service_id="<uuid>", instance="jamaica")

# 2. Fetch a compiled brief for a target language
translation_context(service_id="<uuid>", target_lang="fr", instance="jamaica")

# 3. Batch-write translations (dry-run first)
translate_batch(
    service_id="<uuid>",
    target_lang="fr",
    translations=[{"key": "<fieldId>|label|form", "value": "Nom"}, ...],
    dry_run=True,
    instance="jamaica",
)

# 4. Audit recent writes
translation_audit_check(service_id="<uuid>", instance="jamaica")

# 5. If needed, roll back
translation_rollback(audit_id="<audit-id-from-step-3>", instance="jamaica")
```

## Auth

Authentication is shared with bpa-mcp via the OS keyring — login once via BPA and Translations tools work automatically.

```
/bpa-mcp:login jamaica
```

Or authenticate directly via the shared token refresh chain. The operator must have the `translation admin` role in the country realm to use `translate_batch`, `ds_system_translate_batch`, `translation_global_reload`, or `translation_settings_set`.

## Safety

Two writes require explicit confirmation because of their blast radius:

| Tool | Gate | Why |
|------|------|-----|
| `ds_system_translate_batch` | `confirm_affects_global_catalog=True` (for `dry_run=False`) | Writes to the Global Translation Service — affects all eRegistrations instances |
| `translation_settings_set` | `confirm_affects_display=True` (for `local_supersedes_global=True`) | Flipping the override flag ON changes what users see across every service in the instance |

`dry_run=True` is the default on both. Turning flags OFF (`local_supersedes_global=False`) does not require confirmation.

## Compatible Instances

All eRegistrations instances with a BPA backend (`bparest/bpa/v2016/06/`) and the Global Translation Service URL configured (`TRANSLATION_SERVICE_URL`).
