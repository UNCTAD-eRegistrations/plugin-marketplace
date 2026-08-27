# GDB quirks — property keys, codes, catalogs, decisions, bulk migration

> Imported 2026-07-07 from the retired wiki (9 - System/memory/wiki), content as of 2026-05-03 — verify dated claims before relying on them. Build mechanics are in `atoms.md` §GDB; the view/`$foreign` state of the art is newer in `ledger.md` (2026-06-21, GDB views ARE bot-consumable).

GDB structural and API quirks. GDB's backend is Django (Python), which shapes its API patterns (`/api/v1/...`), admin interface, and migration system.

## Schema structure

A GDB database (catalog) has:
- **Code** — internal identifier, lowercased on storage (see below)
- **Version** — semantic version string (e.g. `2.2`); each published version is immutable
- **Columns/properties** — JSON Schema `properties` object; keys are display labels
- **Blocks** — visual grouping via `type: "object"` wrappers (flat storage, not nested)
- **Lists** — real nested data via `type: "array"` + `items.type: "object"` (e.g. `Productos[]`)
- **Files/attachments** — `type: "array"` (file fields are arrays even for single uploads)
- **Groups** — organizational folders; catalogs can be grouped or ungrouped

Bots pin to a specific published version via `botServiceId` = `GDB.GDB-{CODE}({VERSION})-{OPERATION}` — mechanics and silent-failure mode in `bots-runtime.md`.

## Property key rules

### Keys accept spaces verbatim

GDB does NOT slugify, camelCase, or transform JSON Schema property keys server-side. Keys like `"Legal entity name"`, `"Field of activity NACE"` are stored and displayed verbatim. There is no separate `title`/`label` field — **the key IS the display label**. Confirmed on the `lu` catalog (id 366, lesotho-training).

Implication for programmatic schema generation: emit labels as property keys with whitespace normalized (collapse runs, trim) but no case change, no separator change. `humanKey`/`pascalKey` transforms are unnecessary damage. Dedupe collisions with trailing ` 2`, ` 3` (space + number).

### Codes are lowercased on storage

`POST /api/v1/database/modify` with `code: "SoleProprietor"` stores `soleproprietor`. The GDB web UI uppercases the stored code for the "Short name" display (renders `SOLEPROPRIETOR`). Do not encode semantics in case — PascalCase intent is lost. `gdb_database_get_by_code` matches what is stored (lowercase).

### Ungrouped catalogs may be invisible

Catalogs with `group_id: null` sometimes appear in a name-filtered `gdb_catalog_list(include_databases=false)` response but NOT with `include_databases=true`, and are missing from the unfiltered default listing. When a newly created ungrouped catalog "can't be found" via MCP, fall back to `fetchAllDatabases` from inside the container — it returns the full payload including ungrouped entries. Root cause unclear (likely a permission or pagination filter on the admin endpoint).

## Flat vs nested schema decisions (Cuba D1-D4, canonical patterns)

Origin: `countries/Cuba/GDB/kb/decisions.md`; they generalize to all GDB implementations.

- **D2 — flat schemas with blocks for visual grouping**: all canonical patterns use flat fields grouped by Blocks (`type: "object"` = visual only, fields stored flat by `$id`, dissolving is schema-only). Lists (`type: "array"` + `items.type: "object"`) are for real nested data. When copying structures between instances, replicate the block layout — it carries semantic meaning for users and for BPA form rendering.
- **D3 — single-product block pattern**: registros use `[Block: Producto]` with flat single-product fields, not a `[List: Productos]`. Exception: `Producto[]` arrays kept where multi-item (permisos only).
- **D1 — separate databases per institution**: agencies keep political autonomy over their own DB; cross-agency visibility via GDB views (reverse-FK joins). A single merged DB was rejected (political resistance + schema conflicts).
- **D4 — unified views across tables**: views on a parent database (e.g. USUARIOS) show records from child databases via reverse-FK joins. Foreign field reference: `$foreign.<catalog_id>.<field_id>`; join type `"left"` or `"inner"`; `is_flatten: true` for one row per child record. Added in GDB v2.18 (migration 0091, Dec 2024, TOBE-15328). Prerequisite: the child DB's join field must have a FK to the parent. **Newer, richer knowledge on views as bot sources: `ledger.md` 2026-06-21** (`GDB.GDB-VIEW-<name>(<version>)-<op>` mule services, live-proven).

## Semantic field matching

When mapping between GDB schemas (migration, service copy, bot remapping), match fields by **meaning**, not by `$id` — internal IDs are instance-specific and frequently differ for the same logical field across environments. Simplest solution first: remap an existing field to the correct target before creating a new one. Duplicate fields for the same concept cause downstream confusion in bots, views, and reports.

## Bulk migration patterns

For migrations over ~50 records, bypass the MCP `gdb_data_create_batch` tool and call the GDB API directly (the tool parameter becomes too large for context):

- **Direct API**: `POST /data/{code_lowercase}/{version}/create-entries` with `{"write": [{"content": {...}}, ...]}`. Returns HTTP 201. Chunk at 20 records with 0.5 s delay.
- **Schema alignment**: table codes and schema structures may differ between instances — always run `gdb_catalog_list` and compare schemas before migrating.
- **Date fields**: empty dates must be omitted entirely; `""` fails GDB validation for `format: "date"` fields.
- **Verify after import**: count + spot-check first/last pages field by field.

Full migration playbook: `data-migration.md` (two-skill chain gdb-schema-compare → gdb-copy).

---

## Full-text search only sees tagged paths (Lesotho, 21-08-2026)

`gdb_data_list(search=...)` searches the paths listed in the database's **`schema_tags`**, not the whole record. A value sitting in an untagged field is unfindable by search even though it is right there in the content.

Proven on `SOLE PROPRIETORS RECONCILED` (catalog 56, database 610): a row carries `RECONCILIATION.ELICENSES ref = "ML107010"`, and `search="ML107010"` returns **count 0**. Its `schema_tags` cover `ID`, `Validity/Status`, `Renewal history/*`, `Status history/*`, `Business details/*` and one document field, and nothing under `RECONCILIATION`. Searching the business number, which does sit in a tagged path, works.

**Why it matters:** the licence number is the one identifier a licence holder has in their hand. A search surface that cannot be searched by it is not a search surface. **Check first:** read `schema_tags` before promising that a database can be searched by a given field, and before designing an exists or read bot around it.

## Repeated import passes duplicate rows and can drop fields between passes

Same database, same date. `SOLE PROPRIETORS RECONCILED` grew from **28,961 rows on 18 August to 104,993 on 20 August**, and one business number returns **six records** written in at least three passes (`Record number` 1, 28962, 79527). Worse, the later passes changed shape: the first pass carried `RECONCILIATION.ELICENSES ref`, the later ones dropped it and added `Source rows merged` instead. So the newest rows, which are the majority, have lost the licence number entirely.

**Rules that follow.** A merge or reconciliation database is rebuilt, not topped up: freeze the sources, write the rules down, run once, count. Before trusting any such database, run three checks: total count against the sum of its sources, one real key searched for duplicates, and one field present in early rows checked in late rows. All three cost one call each and all three failed here.
