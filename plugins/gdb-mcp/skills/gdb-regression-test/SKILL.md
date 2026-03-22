---
name: gdb-regression-test
description: >
  Run pre-release regression tests for the GDB MCP server against a live GDB instance.
  Exercises all 27 GDB tools across 6 phases: discovery mirror, database lifecycle,
  batch operations, error handling, duplicate/compare, and cleanup. Use when:
  (1) preparing a release, (2) user says "run GDB regression", "test GDB",
  (3) verifying GDB changes haven't broken tool functionality,
  (4) validating against a specific GDB instance.
---

# GDB MCP Regression Test Runner

Execute comprehensive regression tests against a live GDB instance using MCP tools directly.

**CRITICAL**: All MCP tool calls MUST execute in the main conversation context. Do NOT delegate
to subagents — subagents cannot access MCP connections. Every tool invocation must be a direct
MCP call from this session.

## Workflow

### 1. Instance Selection

Ask the user which GDB instance to test against. Default: `guatemala-dev`.

The selected server name becomes the tool prefix: `mcp__{server_name}__{tool_name}`.
Example: `mcp__GDB-local-dev__gdb_status`.

### 2. Load Tools

Use `ToolSearch` to load required MCP tools before each phase:

```
ToolSearch(query="+GDB-local-dev gdb_status")
ToolSearch(query="+GDB-local-dev gdb_catalog")
ToolSearch(query="+GDB-local-dev gdb_database")
ToolSearch(query="+GDB-local-dev gdb_data")
```

### 3. Authentication

GDB uses BPA's authentication. Load and call `auth_login` from the BPA server:

```
ToolSearch(query="+BPA-local-dev auth_login")
mcp__BPA-local-dev__auth_login(instance="guatemala-dev", username=..., password=...)
```

Ask the user for credentials if not known.

### 4. Execute Phases

Run each phase sequentially. Report results as a table after each phase.
Track: phase name, test count, pass/fail, any errors.

If a phase fails, report the failure and ask if the user wants to continue or stop.

#### Phase 1 — Discovery Mirror (read-only)

Compare MCP read tools against known GDB state on the target instance.

**Ground truth for Guatemala dev "Trade names" database:**
- catalog_code: `trade names`, catalog_id: `3`, db_id: `4`
- Schema fields: ID, Trade name, date 1, Activity, City, Request date, Expiration date, Used, Owner ID, eR User ID, Applicant
- Record count: `7`, first record ID: `51`

| # | Test | Tool | Check |
|---|------|------|-------|
| 1 | Server health | `gdb_status(instance)` | status == "ok" |
| 2 | Instance list | `gdb_instance_list()` | count >= 1, instance present |
| 3 | Catalog count | `gdb_catalog_list(instance)` | count >= 10 |
| 4 | Trade names exists | (from catalog_list) | code "trade names" in catalogs |
| 5 | Database list | `gdb_database_list(instance)` | count >= 10 |
| 6 | Schema fields | `gdb_database_get(database_id=4, instance)` | 11 expected fields present |
| 7 | Record count | `gdb_data_list(code="trade names", instance)` | count == 7 |
| 8 | Record content | `gdb_data_get(data_id=51, instance)` | ID == "TRADE NAMES1", City == "Ben Ghazi" |
| 9 | Search field | `gdb_data_search_field(code="trade names", q="Ben", field="City", instance)` | results >= 1 |
| 10 | Tag list | `gdb_tag_list(instance)` | has count and tags keys |

#### Phase 2 — Database Lifecycle (write, then cleanup)

Full round-trip: create → verify → publish → CRUD records → cleanup.

| # | Test | Action | Check |
|---|------|--------|-------|
| 1 | Create database | `gdb_database_create(catalog_name="GDB Regression", code="gdbregtest", schema=..., is_draft=True, schema_tags=[{name:"",path:"/Name",is_fulltext:true}], instance)` | id > 0, catalog_code == "gdbregtest" |
| 2 | Verify exists | `gdb_database_get(database_id=<id>, instance)` | is_draft == True, Name in schema |
| 3 | Schema tags | (from database_get) | schema_tags has /Name entry |
| 4 | Publish | `gdb_database_publish(database_id=<id>, instance)` | returns id |
| 5 | Verify published | `gdb_database_get(database_id=<id>, instance)` | is_draft == False |
| 6 | Create record | `gdb_data_create(database_id=<id>, content={Name:"Alice",Email:"alice@test.com",Age:30}, instance)` | id > 0 |
| 7 | List records | `gdb_data_list(code="gdbregtest", instance)` | count == 1, Name == "Alice" |
| 8 | Get record | `gdb_data_get(data_id=<record_id>, instance)` | content matches |
| 9 | Update + merge | `gdb_data_update(data_id=<record_id>, content={Name:"Alice Updated"}, instance)` then `gdb_data_get` | Name updated, Email preserved (merge!) |
| 10 | Search field | `gdb_data_search_field(code="gdbregtest", q="Alice", field="Name", instance)` | results >= 1 |
| 11 | Delete record | `gdb_data_delete(data_id=<record_id>, instance)` then `gdb_data_list` | count == 0 |

**Schema to use:**
```json
{
  "type": "object",
  "properties": {
    "ID": {"type": "string", "primaryKey": true, "$id": 1, "readOnly": true,
      "triggers": [{"conditions": [{"logic": "==", "value": "", "gate": "&&"}],
        "actions": [{"type": "set-value", "value": "{code}{indexNoByCode}", "field_id": 1}]}]},
    "Name": {"type": "string", "$id": 2},
    "Email": {"type": "string", "$id": 3},
    "Age": {"type": "number", "$id": 4}
  },
  "$incrementIndex": 4,
  "required": ["ID"]
}
```

Save `database_id`, `catalog_code`, `db_uuid`, `db_version` for subsequent phases.

#### Phase 3 — Batch Operations

Uses the database from Phase 2 (must be published).

| # | Test | Action | Check |
|---|------|--------|-------|
| 1 | Batch create | `gdb_data_create_batch(code="gdbregtest", version=<db_version>, records=[{Name:"Bob"},{Name:"Carol"},{Name:"Dave"}], instance)` | created_count == 3 |
| 2 | Verify count | `gdb_data_list(code="gdbregtest", instance)` | count == 3 |
| 3 | Auto-ID | (from data_list) | All IDs start with "gdbregtest" |
| 4 | Upsert new | `gdb_data_upsert(code="gdbregtest", version=<db_version>, content={Name:"Eve"}, instance)` | has "receive" key |
| 5 | Verify count | `gdb_data_list(code="gdbregtest", instance)` | count == 4 |

**IMPORTANT**: Batch tools require numeric version (e.g., "1.0"), NOT "any".

#### Phase 4 — Error Handling

| # | Test | Action | Check |
|---|------|--------|-------|
| 1 | Update published DB | `gdb_database_update(database_id=<id>, schema={...}, instance)` | ToolError raised (406) |
| 2 | Nonexistent DB | `gdb_database_get(database_id=999999, instance)` | ToolError with "not found" |
| 3 | Empty create | `gdb_database_create(catalog_name="", code="", schema={}, instance)` | ToolError raised |
| 4 | Batch size limit | `gdb_data_create_batch(code="gdbregtest", version=<db_version>, records=[501 items], instance)` | ToolError with "exceeds maximum" |

#### Phase 5 — Duplicate & Compare

| # | Test | Action | Check |
|---|------|--------|-------|
| 1 | Duplicate | `gdb_database_duplicate(database_id=<id>, instance)` | dup_id != original_id |
| 2 | Compare schemas | `gdb_database_compare(first_database_id=<id>, second_database_id=<dup_id>, instance)` | is_equals == True |
| 3 | Dup has no data | (best effort) | May have separate catalog code |

Save `dup_id` for cleanup.

#### Phase 6 — Cleanup

| # | Test | Action | Check |
|---|------|--------|-------|
| 1 | Delete duplicate | Get UUID via `gdb_database_get`, then `gdb_database_delete(database_uuid=<uuid>, instance)` | deleted |
| 2 | Delete main DB | `gdb_database_delete(database_uuid=<db_uuid>, instance)` | deleted |
| 3 | Delete catalogs | `gdb_catalog_list(instance)`, find "gdbregtest*", `gdb_catalog_delete` each | deleted |
| 4 | Verify clean | `gdb_catalog_list(instance)` | no "gdbregtest" catalogs remain |

### 5. Final Report

Present a summary table:

```
| Phase | Tests | Passed | Failed |
|-------|-------|--------|--------|
| 1. Discovery Mirror | 10 | ? | ? |
| 2. Database Lifecycle | 11 | ? | ? |
| 3. Batch Operations | 5 | ? | ? |
| 4. Error Handling | 4 | ? | ? |
| 5. Duplicate & Compare | 3 | ? | ? |
| 6. Cleanup | 4 | ? | ? |
| **TOTAL** | **37** | **?** | **?** |
```

If all pass: "GDB MCP regression passed. Safe to release."
If any fail: list failures with details and suggest fixes.
