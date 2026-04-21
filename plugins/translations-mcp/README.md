# Translations MCP — eRegistrations Translation Tools

MCP tools for translating eRegistrations services and keeping country instances in sync with the central Global Translation Service.

Covers two distinct concerns:

1. **Authoring** — context-aware translation of BPA service definitions (field labels, tooltips, grid columns, form structure, DS system strings) with glossary enforcement, GDB catalog enrichment, and audited batch writes.
2. **Global sync** — one-command recovery when a country instance is out of sync with the Global Translation Service (shell keys showing as raw identifiers like `nav.services` in the admin UI).

## Prerequisites

Install the **bpa-mcp** plugin first — it provides authentication and instance management that Translations depends on.

## Tools (12)

### Status & Context
- `translation_status` — Per-language translation coverage for a service
- `language_list` — Active languages for an instance
- `translation_glossary` — Glossary terms for a language (from GDB, cached)
- `translation_context` — Compiled translation brief: field context, glossary, GDB enrichment

### Authoring (Audited Writes)
- `translate_batch` — Batch-write service translations. Atomic dry-run, snapshot, audit
- `ds_system_translations` — List DS system strings (globalName labels, messages)
- `ds_system_translate_batch` — Batch-write DS system string translations
- `ds_system_sync` — Sync DS system strings from the live DS instance

### Search & Audit
- `translation_search` — Search translations by text, field, or category
- `translation_audit_check` — Check recent translation writes and flag issues

### Global Translation Service (GTS) Sync
- `translation_global_status` — Probe whether an instance is in sync with GTS (read-only)
- `translation_global_reload` — Pull from GTS. Audited write. Mirrors the "Global Translation" button

## Commands

| Command | Description |
|---------|-------------|
| `/translations-mcp:status [instance]` | Check whether this instance needs a translation sync |
| `/translations-mcp:fix [instance]` | Diagnose + auto-reload if the instance is out of sync |
| `/translations-mcp:issue [description]` | Report a Translations MCP tool issue |

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
    instance="jamaica"
)

# 4. Audit recent writes
translation_audit_check(instance="jamaica")
```

## Auth

Authentication is shared with bpa-mcp via the OS keyring — login once via BPA and Translations tools work automatically.

```
/bpa-mcp:login jamaica
```

Or authenticate directly via the shared token refresh chain. The operator must have the `translation admin` role in the country realm to use `translate_batch`, `ds_system_translate_batch`, or `translation_global_reload`.

## Compatible Instances

All eRegistrations instances with a BPA backend (`bparest/bpa/v2016/06/`) and the Global Translation Service URL configured (`TRANSLATION_SERVICE_URL`).
