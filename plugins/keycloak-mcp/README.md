# keycloak-mcp

Keycloak Admin API tools for eRegistrations IAM management.

**Requires the `bpa-mcp` plugin** — instance profiles are shared. Install `bpa-mcp` first if you haven't already.

## What this installs

A single `Keycloak` MCP server (51 tools). It reuses the instance profiles registered by `/bpa-mcp:install` — the same Keycloak URLs and realms apply.

## Commands

| Command | Description |
|---------|-------------|
| `/keycloak-mcp:install` | Verify the Keycloak MCP server is loaded and ready |
| `/keycloak-mcp:status [instance]` | Check connection status for all or one instance |
| `/keycloak-mcp:login <instance>` | Authenticate to a Keycloak instance (admin credentials) |
| `/keycloak-mcp:doctor` | Diagnose and fix common issues |

## Prerequisites

### 1. Install `bpa-mcp` first

Instance profiles are shared across all eRegistrations MCP servers. Run `/bpa-mcp:install` to register them.

### 2. Install `uv` (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

The MCP server is auto-downloaded via `uvx` when the plugin starts — no manual install needed.

### 3. Authenticate with admin credentials

Keycloak Admin API requires admin-level credentials (not the regular BPA user):

```
/keycloak-mcp:login jamaica
```

The authenticated user must have Keycloak `realm-management` roles (manage-users, manage-realm, view-realm).

## Tool categories (51 tools)

| Category | Tools | Description |
|----------|-------|-------------|
| System | `kc_auth_login`, `kc_connection_status`, `kc_audit_log`, `kc_rollback`, `kc_rollback_list`, `kc_rollback_cleanup` | Auth, audit, rollback |
| Realms | `kc_list_realms`, `kc_get_realm`, `kc_create_realm`, `kc_update_realm`, `kc_delete_realm` | Realm CRUD |
| Users | `kc_list_users`, `kc_get_user`, `kc_create_user`, `kc_update_user`, `kc_delete_user`, `kc_reset_user_password`, `kc_get_user_sessions` | User management |
| User Profile | `kc_get_user_profile_config`, `kc_update_user_profile_config`, `kc_add_user_attribute`, `kc_update_user_attribute`, `kc_remove_user_attribute` | User profile schema |
| Roles | `kc_list_realm_roles`, `kc_get_realm_role`, `kc_create_realm_role`, `kc_update_realm_role`, `kc_delete_realm_role`, `kc_list_client_roles`, `kc_list_role_users`, `kc_get_composite_roles`, `kc_add_composite_roles`, `kc_remove_composite_roles`, `kc_get_user_role_mappings`, `kc_get_effective_realm_roles`, `kc_get_available_realm_roles`, `kc_assign_realm_roles`, `kc_remove_user_realm_roles` | Role management |
| Mappers | `kc_list_client_mappers`, `kc_add_client_mapper`, `kc_delete_client_mapper` | Client protocol mappers |
| Themes | `kc_list_themes`, `kc_get_realm_theme`, `kc_set_realm_theme` | Theme management |
| JWT | `kc_get_token_info`, `kc_decode_token`, `kc_validate_token`, `kc_introspect_token` | Token inspection |
| Diagnostics | `kc_debug_scan_realm`, `kc_connection_status` | Health checks |
| Export | `kc_export_realm_yaml`, `kc_compare_realms` | Realm export & diff |
