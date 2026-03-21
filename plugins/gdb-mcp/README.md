# GDB MCP — Generic Database Builder

MCP tools for managing GDB databases, schemas, and records in eRegistrations.

## Prerequisites

Install the **bpa-mcp** plugin first — it provides authentication and instance management that GDB depends on.

## Tools (27)

### System
- `gdb_status` — Server health and version
- `gdb_instance_list` — List instances with GDB configured
- `gdb_tag_list` — List all database tags

### Catalogs
- `gdb_catalog_list` — List all catalogs (summary, no schemas)
- `gdb_catalog_delete` — Delete a catalog
- `gdb_catalog_move` — Reorder a catalog

### Databases
- `gdb_database_list` — List all databases (flattened, no schemas)
- `gdb_database_get` — Get database with full JSON Schema
- `gdb_database_create` — Create database with schema
- `gdb_database_update` — Update draft database
- `gdb_database_publish` — Publish draft (makes immutable)
- `gdb_database_edit` — Create draft from published
- `gdb_database_delete` — Delete database by UUID
- `gdb_database_duplicate` — Clone database
- `gdb_database_compare` — Compare two database schemas

### Data Records
- `gdb_data_list` — List records (paginated, filterable)
- `gdb_data_get` — Get single record
- `gdb_data_create` — Create record
- `gdb_data_update` — Update record (merge, not replace)
- `gdb_data_delete` — Delete record
- `gdb_data_delete_batch` — Delete multiple records by ID
- `gdb_data_create_batch` — Batch create (registry API)
- `gdb_data_update_batch` — Batch update (registry API)
- `gdb_data_upsert` — Create or update by match
- `gdb_data_upsert_batch` — Batch upsert
- `gdb_data_search_field` — Autocomplete field values
- `gdb_data_filter` — Create filter hash for gdb_data_list

## Quick Start

```
/bpa-mcp:login guatemala-dev    # authenticate (via BPA plugin)
gdb_catalog_list()               # discover databases
gdb_database_get(database_id=4)  # get schema details
gdb_data_list(code="trade names") # list records
```
