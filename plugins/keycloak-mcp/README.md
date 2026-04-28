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
| `create-theme` | `/keycloak-mcp:create-theme <theme-name> [primary-color-rgb] [locales]` | Scaffold a new country/deployment Keycloak theme inheriting from `unctad-next`. Offers to clone the repo if missing; works on `develop`. After scaffolding, optionally chains into `add-user-attributes`. |
| `propagate-theme` | `/keycloak-mcp:propagate-theme <theme-name> [--from <src-branch>] [--to <target-branches>]` | Propagate an existing theme from one branch (default `develop`) to one or more target branches via `git checkout <src> -- themes/<name>/`. Commits per target; does NOT push. |
| `add-user-attributes` | `/keycloak-mcp:add-user-attributes [instance] [realm] [--spec <file>]` | Configure custom user-profile attributes on a Keycloak realm via `kc_get_user_profile_config` + `kc_update_user_profile_config`. Interactive or spec-file driven. The `unctad-next` theme renders attributes dynamically — no theme-file changes needed. |

**Canonical repo for the theme skills:** https://github.com/UNCTAD-eRegistrations/Keycloak — branch `develop`. Themes are baked into the Keycloak Docker image at build time. The `add-user-attributes` skill is a live Admin-API operation against a running Keycloak; it doesn't touch the repo.

### `create-theme` — full process

**Prerequisites:**

- The eRegistrations Keycloak repo (https://github.com/UNCTAD-eRegistrations/Keycloak) cloned locally. If you invoke the skill outside it, the skill will offer to `git clone` it for you.
- The skill works on the `develop` branch. It will switch to `develop` and `git pull --ff-only` for you, but will stop and ask first if you have uncommitted changes on another branch.

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

### `propagate-theme` — full process

**Prerequisites:** Same as `create-theme` — must be invoked inside a clone of https://github.com/UNCTAD-eRegistrations/Keycloak. The theme being propagated must already exist on the source branch. The working tree must be clean (no uncommitted changes).

**Arguments:**

| Position | Name | Required | Default | Notes |
|---|---|---|---|---|
| 1 | `<theme-name>` | yes | — | Lowercase directory under `themes/` (e.g. `tanzania`). |
| 2 | `--from <src-branch>` | no | `develop` | Branch to copy *from*. |
| 3 | `--to <target-branches>` | yes | — | Comma-separated branch names to copy *to*, e.g. `main,release/2026,cuba-prod`. |

**What the skill does, step by step:**

1. **Verifies the repo + clean tree.** Refuses to run if `themes/unctad-next/` is missing or `git status --porcelain` is non-empty.
2. **Verifies the source.** `git show <src>:themes/<name>/login/theme.properties` — fails fast if the theme isn't on the source branch.
3. **Verifies all target branches exist** (locally or on origin). Fails fast on any missing target rather than partially-applying.
4. **For each target branch:**
   - `git checkout <target>` then `git pull --ff-only origin <target>`. Stops for that target on diverged history (no force).
   - `git checkout <src> -- themes/<name>/` to bring the theme files in.
   - `git add themes/<name>/` then check `git diff --cached --quiet`:
     - **No diff** → target already matches source; skip the commit, move on.
     - **Diff** → `git commit -m "feat(themes): propagate <name> from <src>"`.
5. **Returns to the original branch** and prints a summary table (target → committed `<sha>` / already up-to-date / skipped).
6. **Does NOT push.** The user reviews each branch and pushes manually — important for branches that auto-deploy.

**Examples:**

```
/keycloak-mcp:propagate-theme tanzania --to main
/keycloak-mcp:propagate-theme rwanda --from develop --to release/2026,cuba-prod
/keycloak-mcp:propagate-theme jamaica --to staging,production
```

**Important — one theme per invocation.** If you have several themes to bring across, run the skill once per theme so each lands as its own commit on each target. This keeps the history reverter-friendly.

### `add-user-attributes` — full process

**Prerequisites:**

- Authenticated to the target Keycloak instance (`/keycloak-mcp:login <instance>`). Admin needs `realm-management` roles (`manage-users`, `manage-realm`, `view-realm`) on the realm.
- The realm must already exist (this skill doesn't create realms).
- **No repo / file system requirements** — this skill is purely a Keycloak Admin-API operation.

**Why no theme files are needed:** the parent `unctad-next/login/register.ftl` renders user-profile attributes dynamically. Declaring a new attribute on the realm makes it appear on the registration form automatically — adding a `register.ftl` override in a country theme is **the wrong layer** for this and would diverge from the parent.

**Arguments:**

| Position | Name | Required | Default | Notes |
|---|---|---|---|---|
| 1 | `[instance]` | no (prompted) | — | Instance profile name (e.g. `tanzania`). Listed via `mcp__BPA__instance_list()` if missing. |
| 2 | `[realm]` | no (prompted) | — | Realm name on the chosen instance. Listed via `kc_list_realms` if missing — don't guess based on instance name (naming conventions vary). |
| 3 | `[--spec <file>]` | no | — | Path to a YAML or JSON file with attribute specs. Skips the interactive prompts. |

**What the skill does, step by step:**

1. **Pick the instance.** If not provided, list profiles via `mcp__BPA__instance_list()` and ask.
2. **Pick the realm.** If not provided, list via `kc_list_realms(instance)` and ask.
3. **Fetch the current schema** via `kc_get_user_profile_config(realm, instance)`. Show the user a summary of what's already there so they don't re-add an existing attribute.
4. **Collect attribute definitions** — either:
   - **Spec-file mode:** read the YAML/JSON file, validate every entry, abort on any malformed entry.
   - **Interactive mode:** prompt per attribute for `name`, `displayName` (default `${name}`), `required`, `validation` (none/regex/options/length), `group`, `permissions` (default `view+edit by [admin, user]`). Loop until the user is done.
5. **Show the merged config + counts** ("Adding N attributes; total M → M+N"). Ask **"Apply? (yes/no)"** — only proceed on explicit yes.
6. **Apply** via `kc_update_user_profile_config(realm, instance, config=<merged>)`. Surface any 4xx error verbatim — don't retry.
7. **Verify** by re-fetching the schema and confirming each new attribute is present. Flag loudly if any were silently dropped.
8. **Report** what was added and remind the user about i18n labels (theme `messages_<locale>.properties` or realm-level overrides) and optional follow-ups (required-actions, client protocol mappers).

**The full-replace gotcha (read this):** `kc_update_user_profile_config` replaces the entire schema — it's not a patch. The skill always fetches the current config, merges new attributes into the existing list, and writes the merged result. If you ever call this tool directly with just your new attributes, you will wipe `username`/`email`/`firstName`/`lastName` and break the realm. Don't.

**Examples:**

```
/keycloak-mcp:add-user-attributes tanzania tanzania-eregistrations
/keycloak-mcp:add-user-attributes jamaica
/keycloak-mcp:add-user-attributes --spec ./tanzania-attrs.yaml
```

**Spec-file format (YAML):**

```yaml
- name: nationalIdNumber
  displayName: ${nationalIdNumber}
  required: true
  validations:
    pattern: "^[0-9]{8,12}$"
  group: personalInfo
  permissions:
    view: [admin, user]
    edit: [admin, user]

- name: nationality
  displayName: ${nationality}
  required: false
  validations:
    options: [TZ, KE, UG, RW]
  group: personalInfo
```

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
