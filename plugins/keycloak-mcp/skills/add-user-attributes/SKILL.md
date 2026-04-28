---
name: add-user-attributes
description: >
  Add custom user-profile attribute definitions to a Keycloak realm for an eRegistrations
  deployment. Fetches the current schema via `kc_get_user_profile_config`, merges in new
  attribute definitions (preserving existing ones), and writes back via
  `kc_update_user_profile_config`. The unctad-next theme's `register.ftl` renders user
  attributes dynamically — adding an attribute here is sufficient for it to appear on the
  registration form; no theme FTL override is needed.
  TRIGGER when: the user asks to add / configure / declare / register new custom user
  attributes, registration fields, or profile fields on a Keycloak realm (e.g. "add a national
  ID number field for tanzania", "configure user attributes for the new colombia deployment",
  "I need a tax_id attribute on jamaica's realm"). Also use as the chained follow-up when the
  user opts into the optional "configure user attributes?" step at the end of `create-theme`.
  DO NOT TRIGGER when: setting an attribute VALUE on a specific user (use
  `kc_add_user_attribute` / `kc_update_user_attribute` directly); managing realm roles, groups,
  or composites; adding client-level protocol mappers (use `kc_add_client_mapper`); editing the
  registration form layout (the parent theme handles that dynamically).
license: UNCTAD-Internal
compatibility: Live Keycloak Admin API operation — requires an authenticated `Keycloak` MCP connection with realm-management roles on the target realm.
allowed-tools: Read, mcp__BPA__instance_list, mcp__Keycloak__*
metadata:
  version: "1.0.0"
  version-date: "2026-04-28"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[instance] [realm] [--spec <file>]"
  disable-model-invocation: "false"
  changelog:
    - "1.0.0 (2026-04-28): Initial — adds user-profile attribute definitions to a Keycloak realm. Supports interactive collection (prompt-per-attribute) and spec-file mode (`--spec <file>` with YAML/JSON). Fetches current config via `kc_get_user_profile_config`, merges new attributes preserving existing ones, applies via `kc_update_user_profile_config`. Lists realms via `kc_list_realms` if user doesn't specify."
---

# Add Keycloak User Attributes

Configure custom user-profile attributes on a Keycloak realm. Each attribute becomes a registration / account form field.

**Why this is a Keycloak-only operation, not a theme-file operation:** the parent `unctad-next` theme's `register.ftl` reads from the realm's User Profile schema and renders attributes dynamically. As soon as the schema lists a new attribute, the registration form picks it up — no theme override is needed.

## When to Use

- A new country/deployment realm needs registration fields beyond the unctad-next defaults (e.g. `nationalIdNumber`, `nationality`, `taxId`, `companyRegistrationNumber`).
- Chained as the optional follow-up to `/keycloak-mcp:create-theme` for the same deployment.
- Standalone configuration of an existing realm.

**Don't use this for:**

- **Setting attribute values on a specific user** — use `kc_add_user_attribute` / `kc_update_user_attribute` directly. This skill defines the attribute schema; per-user values are a separate operation.
- **Managing realm roles, groups, or composites.**
- **Client-level protocol mappers** — use `kc_add_client_mapper`.
- **Editing the registration form layout** — `unctad-next/login/register.ftl` renders dynamically; layout changes require editing the parent theme, not the user-profile schema.

## Arguments

| Position | Name | Required | Default | Notes |
|---|---|---|---|---|
| 1 | `[instance]` | no (prompted) | — | Instance profile name (e.g. `tanzania`, `jamaica`). Listed via `mcp__BPA__instance_list()` if missing. |
| 2 | `[realm]` | no (prompted) | — | Realm name on the chosen instance. Listed via `kc_list_realms(instance)` if missing. |
| 3 | `[--spec <file>]` | no | — | Path to a YAML or JSON file with a list of attribute specs (skips the interactive prompts). |

## Connecting to Keycloak

Before any tool call:

1. If the instance is unknown, call `mcp__BPA__instance_list()` to see registered profiles. Ask the user which one.
2. Check auth: `mcp__Keycloak__kc_connection_status(instance="{name}")`.
3. If not authenticated → `mcp__Keycloak__kc_auth_login(instance="{name}")`. Wait for success.

The user must have `realm-management` roles (`manage-users`, `manage-realm`, `view-realm`) on the target realm. If not, `kc_update_user_profile_config` will return 403.

Pass `instance="{name}"` to every `mcp__Keycloak__*` tool call.

## Steps

### 1. Pick the instance

If `[instance]` not provided:

```
mcp__BPA__instance_list()
```

Show the user the registered profiles. Ask which one to target.

### 2. Pick the realm

If `[realm]` not provided:

```
mcp__Keycloak__kc_list_realms(instance="<instance>")
```

Show the user the realms (a markdown table with realm name + display name + enabled status). Ask which one. **Don't guess based on instance name** — naming conventions vary across deployments (some realms are `<country>-eregistrations`, some are just `<country>`, some are `master`).

### 3. Fetch the current user-profile config

```
mcp__Keycloak__kc_get_user_profile_config(realm="<realm>", instance="<instance>")
```

Show the user a compact summary of attributes already configured (names + required-status + groups), so they don't accidentally re-add an existing one. Keep the full config around in memory — you'll merge into it in step 5.

### 4. Collect attribute definitions

#### 4a. Spec-file mode (`--spec <file>`)

Read the file with the `Read` tool. Expected YAML form:

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

JSON form is the same shape but as a JSON array. Validate each entry — if any are malformed (missing `name`, name conflicts with an existing attribute, malformed regex, etc.), stop and report all problems at once. Don't apply a partial spec.

#### 4b. Interactive mode

For each attribute, prompt:

| Field | Prompt | Notes |
|---|---|---|
| `name` | "Attribute name (lowercase, no spaces, e.g. `nationalIdNumber`)?" | Required. Reject if it conflicts with an existing attribute name in the current config. |
| `displayName` | "Display name / i18n key (default `${<name>}`)?" | Optional. The `${...}` form looks up a localized message. Plain text is also accepted. |
| `required` | "Required? (yes/no)" | Defaults `no`. |
| `validation` | "Validation? (none / regex / options / length)" | Branch into the appropriate sub-prompt. |
| `group` | "Group? (e.g. `personalInfo`, blank for none)" | Optional — groups visually cluster fields on the form. |
| `permissions` | "Use default permissions (view+edit by admin+user)? (yes/no)" | If `no`, prompt explicitly for each of `view: roles` and `edit: roles`. |

Validation sub-prompts:

- **regex:** "Pattern (anchored, e.g. `^[0-9]{8,12}$`)?"
- **options:** "Allowed values (comma-separated, e.g. `TZ,KE,UG,RW`)?"
- **length:** "Min length?" / "Max length?"

After each attribute, ask "Add another? (yes/no)" — loop until the user is done.

### 5. Show the merged config + ask before applying

Construct the merged config:

```python
new_config = dict(current_config)
new_config["attributes"] = list(current_config["attributes"]) + new_attrs
# preserve groups, unmanagedAttributePolicy, etc. — only the attributes list grows
```

Show the user:

- **Existing attribute names** (untouched) — `username`, `email`, `firstName`, `lastName`, etc.
- **New attribute names + their full configuration** — formatted as readable YAML.
- **Counts:** "Adding N attributes (current total M → new total M+N)."

Ask explicitly: "Apply? (yes/no)". Only proceed on `yes`. **No silent application** — the user must confirm.

### 6. Apply

```
mcp__Keycloak__kc_update_user_profile_config(
    realm="<realm>",
    instance="<instance>",
    config=<merged-config>,
)
```

If the call fails (403 = missing roles, 400 = validation rejected the schema, etc.), surface the error verbatim to the user. Don't retry — let the user fix the input or auth.

### 7. Verify

Re-fetch and confirm the new attributes are present:

```
mcp__Keycloak__kc_get_user_profile_config(realm="<realm>", instance="<instance>")
```

For each attribute the user added, check it's in the returned `attributes` list. If any are missing → flag it loudly (something was silently dropped server-side, e.g. a validator was rejected).

### 8. Report

Tell the user:

- The list of attributes added (names + key properties).
- **Where to test:** the registration page for the realm — the unctad-next parent theme's `register.ftl` will pick up the new fields automatically on next load.
- **Optional follow-ups:**
  - Add i18n labels for each `${attrName}` displayName key. Either in the theme's `login/messages/messages_<locale>.properties`, or via Keycloak's realm-level message overrides in the admin UI (Realm settings → Localization).
  - If any attribute should be required at registration but optional later, configure required-actions on the realm.
  - If the new fields need to flow into ID/access tokens, add a corresponding client protocol mapper via `kc_add_client_mapper`.

## Connecting to BPA

Only used in step 1 (`mcp__BPA__instance_list()`) to discover registered instance profiles. The skill does not call any other BPA tool.

## Common Mistakes

- **Replacing the whole config instead of merging.** `kc_update_user_profile_config` is a full-replace operation. If you submit just the new attributes without merging in the existing ones, you'll wipe `username`/`email`/`firstName`/`lastName` and break login. **Always fetch → merge → write.**
- **Re-adding an attribute that already exists.** Step 4 must reject duplicate names. If the user wants to *modify* an existing attribute, that's a different operation outside this skill's scope (it would replace the attribute's config, not append).
- **Skipping permissions.** A missing or empty `permissions` block makes the attribute invisible to all roles — the field silently doesn't render. Always default to `view: [admin, user], edit: [admin, user]` unless the user specifies otherwise.
- **Assuming the registration form will auto-update.** It does — but only because the unctad-next parent theme's `register.ftl` renders dynamically. If a country theme has overridden `register.ftl` (which it shouldn't, per the project convention), the new attribute won't appear until the override is deleted or updated.
- **Applying without showing a diff first.** Step 5 is non-skippable — confirmation before `kc_update_user_profile_config` is essential. A wrong write to the user-profile schema can lock users out at next login.
- **Treating per-user attribute calls as schema changes.** `kc_add_user_attribute` is for setting a value on ONE user; this skill is for declaring the attribute exists at all on the realm. Different operation.

## Examples

```
/keycloak-mcp:add-user-attributes tanzania tanzania-eregistrations
/keycloak-mcp:add-user-attributes jamaica
/keycloak-mcp:add-user-attributes --spec ./tanzania-attrs.yaml
```
