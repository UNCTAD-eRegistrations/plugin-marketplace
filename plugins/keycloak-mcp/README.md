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

## Skills

| Skill | Slash invocation | Description |
|-------|------------------|-------------|
| `create-theme` | `/keycloak-mcp:create-theme <theme-name> [primary-color-rgb] [locales]` | Scaffold a new country/deployment Keycloak theme inheriting from `unctad-next`. Run from the eRegistrations Keycloak repo (the directory containing `themes/unctad-next/`). |

### `create-theme` — full process

**Prerequisites:** Run from the eRegistrations Keycloak repo root — the directory whose Docker image bakes `/opt/keycloak/themes/`. The repo must contain `themes/unctad-next/` (the parent theme all country themes inherit from).

**Arguments:**

| Position | Name | Required | Default | Notes |
|---|---|---|---|---|
| 1 | `<theme-name>` | yes | — | Lowercase, e.g. `tanzania`. Becomes the directory name **and** the value users see in Keycloak's theme picker. |
| 2 | `[primary-color-rgb]` | no | `74,98,136` (unctad-next blue) | Comma-separated 0–255 triple, e.g. `51,102,204`. |
| 3 | `[locales]` | no | `en` | Comma-separated locale codes, e.g. `en,fr,ar`. |

**What the skill does, step by step:**

1. **Verifies the working directory.** Runs `test -d themes/unctad-next` — stops if missing. Refuses to scaffold outside the Keycloak repo.
2. **Checks for collisions.** Runs `test ! -d themes/<theme-name>` — stops if the theme already exists. Won't overwrite. Offers the user three options: abort, pick a different name, or delete-and-recreate.
3. **Creates the directory tree:**
   ```
   themes/<name>/
   ├── login/
   │   ├── theme.properties
   │   └── resources/
   │       ├── css/variables.css
   │       └── images/.gitkeep
   └── email/
       ├── theme.properties
       └── resources/
           └── images/.gitkeep
   ```
4. **Writes `themes/<name>/login/theme.properties`:**
   ```properties
   parent=unctad-next
   locales=<locales>
   styles=css/variables.css css/styles.css
   scripts=js/conditional-fields.js
   ```
   `css/styles.css` and `js/conditional-fields.js` are **inherited from `unctad-next`** — the skill does not scaffold them under the new theme.
5. **Writes `themes/<name>/login/resources/css/variables.css`** — sets `--main-primary` to the chosen RGB triple, plus the standard unctad-next palette (background, text, borders, error colors). The login CSS uses an `R, G, B` triple fed into `rgb()`/`rgba()`.
6. **Writes `themes/<name>/email/theme.properties`** — converts the RGB triple to a 6-digit lowercase hex (`#rrggbb`) for the email `mainColor`:

   | RGB | Hex |
   |---|---|
   | `74, 98, 136` | `#4a6288` |
   | `255, 204, 0` | `#ffcc00` |
   | `51, 102, 204` | `#3366cc` |
7. **Adds `.gitkeep` placeholders** in both `images/` directories so git tracks them until logos are dropped in.
8. **Reports back to the user** with the file list and three reminders:
   - **Add logo PNGs** (the skill cannot generate these): `themes/<name>/login/resources/images/logo.png` and `themes/<name>/email/resources/images/logo.png`.
   - **Optional further customization:** add `css/custom.css` (and update the `styles=` line in `login/theme.properties`); override messages at `login/messages/messages_<locale>.properties`; override FTL templates (e.g. `register.ftl`) for custom form fields.
   - **After Docker image rebuild + deploy**, assign the theme to a realm via the Keycloak MCP server:
     ```
     mcp__Keycloak__kc_set_realm_theme(
         realm="<realm-name>",
         login_theme="<name>",
         email_theme="<name>",
         instance="<instance>"
     )
     ```

**Examples:**

```
/keycloak-mcp:create-theme tanzania 51,102,204 en,fr,sw
/keycloak-mcp:create-theme rwanda
/keycloak-mcp:create-theme jamaica 255,204,0 en
```

**Important — scaffolding is not deployment.** Themes are baked into the Keycloak Docker image at build time. After running this skill you still need to commit the new files, build the image, push, and redeploy. Only then can `kc_set_realm_theme` reference the new theme name; calling it earlier will fail because the server doesn't have the theme on disk yet.

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
