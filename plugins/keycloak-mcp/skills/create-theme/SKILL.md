---
name: create-theme
description: >
  Scaffold a new country/deployment Keycloak theme that inherits from `unctad-next` in the
  eRegistrations Keycloak repo (the one with `themes/unctad-next/`). Creates the login + email
  theme directories, `theme.properties`, a `variables.css` keyed off a chosen primary RGB color,
  and `.gitkeep`'d directories for the logo images.
  TRIGGER when: the user asks to create / add / scaffold / bootstrap a new Keycloak theme for a
  country or deployment (e.g. "create a tanzania theme", "add a new theme for rwanda", "bootstrap
  a theme for the new colombia deployment"), AND the working directory contains
  `themes/unctad-next/`.
  DO NOT TRIGGER when: the user wants to edit/customize an EXISTING theme (just edit the files);
  asks to ASSIGN an existing theme to a realm (use `kc_set_realm_theme` directly); or is not
  inside the eRegistrations Keycloak repo.
license: UNCTAD-Internal
compatibility: Pure file scaffolding — does not require an active Keycloak MCP connection.
allowed-tools: Read, Write, Bash(mkdir -p *), Bash(test *), Bash(ls *)
metadata:
  version: "1.0.1"
  version-date: "2026-04-28"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<theme-name> [primary-color-rgb] [locales]"
  disable-model-invocation: "false"
  changelog:
    - "1.0.1 (2026-04-28): Clarified that `css/styles.css` and `js/conditional-fields.js` referenced by `login/theme.properties` are inherited from `unctad-next` and must NOT be scaffolded — surfaced by pressure-testing where two subagents independently flagged it as ambiguous."
    - "1.0.0 (2026-04-28): Initial port from `Keycloak/.claude/skills/create-theme.md`. Scaffolds login + email theme inheriting from `unctad-next` with parameterized primary color (RGB) and locales. Adds explicit working-directory verification, RGB→hex conversion guidance, and a post-deployment hand-off to `mcp__Keycloak__kc_set_realm_theme`."
---

# Create Keycloak Theme

Scaffold a new country/deployment theme that inherits from `unctad-next` in the eRegistrations Keycloak repo (the one whose Docker image bakes `/opt/keycloak/themes/`).

## When to Use

- The user wants a new theme for a country deployment (e.g. *"create a tanzania theme with primary color 51,102,204"*).
- They have a primary color (or accept the `unctad-next` default) and possibly a set of locales.
- They are working in the eRegistrations Keycloak repo — verifiable by the presence of `themes/unctad-next/`.

**Don't use this for:**

- Modifying an existing theme — just edit the files.
- Deploying a theme to a running Keycloak server — themes are baked into the Docker image at build time. After deployment, assign the theme to a realm with `mcp__Keycloak__kc_set_realm_theme`.

## Arguments

Parsed from the user's invocation (or asked for if missing):

| Position | Name | Required | Default | Example |
|---|---|---|---|---|
| 1 | `theme-name` | yes | — | `tanzania` |
| 2 | `primary-color-rgb` | no | `74,98,136` (unctad-next blue) | `51,102,204` |
| 3 | `locales` | no | `en` | `en,fr,ar` |

If no theme name is given, ask the user — don't guess.

`theme-name` must be lowercase (it becomes the directory name AND the value users see in Keycloak's theme picker).

## Verify the working directory

Before touching anything, confirm we're in the right repo and the target name is free:

```bash
test -d themes/unctad-next && echo OK || echo "NOT_IN_KEYCLOAK_REPO"
test ! -d themes/<theme-name> && echo OK || echo "ALREADY_EXISTS"
```

- If `themes/unctad-next/` is missing → stop. Tell the user this skill must be run from the Keycloak repo root.
- If `themes/<theme-name>/` already exists → stop. Don't overwrite. Ask whether they want to delete it first or pick a different name.

## Steps

### 1. Create directory structure

```bash
mkdir -p themes/<name>/login/resources/css
mkdir -p themes/<name>/login/resources/images
mkdir -p themes/<name>/email/resources/images
```

### 2. Write `themes/<name>/login/theme.properties`

```properties
parent=unctad-next
locales=<locales>
styles=css/variables.css css/styles.css
scripts=js/conditional-fields.js
```

`css/styles.css` and `js/conditional-fields.js` are inherited from the `unctad-next` parent — do **not** scaffold them under the new theme. The new theme only ships `css/variables.css` (and optionally `css/custom.css`, see step 6).

### 3. Write `themes/<name>/login/resources/css/variables.css`

Substitute `<R>`, `<G>`, `<B>` with the parsed RGB triple:

```css
:root {
    --main-primary: <R>, <G>, <B>;
    --main-primary-color: rgb(var(--main-primary));
    --main-primary-40-color: rgba(var(--main-primary), 0.4);
    --main-info-bg-color: rgba(var(--main-primary), 0.08);

    --main-bg-color: #EFF1F5;
    --main-text-color: #374151;
    --main-card-color: #fff;
    --main-border-color: #CBD5E1;
    --main-border-hover: #94A3B8;
    --main-btn-light-bg: #E8EBF0;
    --main-btn-light-bg-hover: #DCE0E7;

    --main-error-color: #FEF2F2;
    --main-error-text-color: #DC2626;
}
```

### 4. Write `themes/<name>/email/theme.properties`

Convert the RGB triple to a 6-digit lowercase hex string for `mainColor`:

```properties
parent=unctad-next
locales=<locales>
styles=css/styles.css
mainColor=<hex-color>
```

### 5. `.gitkeep` placeholders for logo directories

Create empty `.gitkeep` files in each images dir so git tracks them until logos are added:

- `themes/<name>/login/resources/images/.gitkeep`
- `themes/<name>/email/resources/images/.gitkeep`

### 6. Report to the user

List every file created. Then remind them to:

- **Add logo images** (the skill cannot generate these):
  - `themes/<name>/login/resources/images/logo.png` — login page logo
  - `themes/<name>/email/resources/images/logo.png` — email template logo
- **Optional further customization:**
  - Add `css/custom.css` and update `styles=` in `login/theme.properties` to `css/variables.css css/styles.css css/custom.css`.
  - Override messages: `login/messages/messages_<locale>.properties`.
  - Override FTL templates (e.g. `register.ftl`) for custom form fields.
- **After Docker image rebuild + deploy**, assign the theme to a realm via the Keycloak MCP server:

  ```
  mcp__Keycloak__kc_set_realm_theme(
      realm="<realm-name>",
      login_theme="<name>",
      email_theme="<name>",
      instance="<instance>"
  )
  ```

  (See `/keycloak-mcp:login <instance>` if not yet authenticated. The authenticated user must have `realm-management` roles.)

## RGB → Hex Conversion

For the email `mainColor`:

```
hex = '#' + format(R, '02x') + format(G, '02x') + format(B, '02x')
```

Examples:

| RGB | Hex |
|---|---|
| `74, 98, 136` | `#4a6288` |
| `255, 204, 0` | `#ffcc00` |
| `51, 102, 204` | `#3366cc` |
| `220, 38, 38` | `#dc2626` |

Always lowercase, always 6 digits (zero-pad each component).

## Connecting to Keycloak

This skill **does not** call any `mcp__Keycloak__*` tool — it only writes files into the local repo. The hand-off to `kc_set_realm_theme` is informational, for the user to run *after* the Docker image is rebuilt and deployed.

If the user asks the skill to also assign the theme to a realm right now: redirect them. The theme must be inside the running Keycloak server's themes directory before `kc_set_realm_theme` can reference it, and that happens at image build / pod restart time — not when the files are written locally.

## Common Mistakes

- **Running outside the Keycloak repo** (no `themes/unctad-next/` parent) → files end up in the wrong place. Always run the working-directory check first.
- **Overwriting an existing theme** → check `test ! -d themes/<name>` first; if it exists, ask the user whether to abort or remove it.
- **Uppercase or mixed-case theme names** → keep lowercase. This becomes the directory name *and* the value users see in Keycloak's theme picker.
- **Forgetting the RGB → hex conversion** for the email theme. The login CSS uses an `R, G, B` triple (a CSS custom property fed into `rgb()`); the email properties file uses a hex string.
- **Skipping the logo files** — the theme will render with broken/missing images until `logo.png` is dropped in. Always remind the user.
- **Calling `kc_set_realm_theme` immediately after scaffolding** — the theme isn't on the server yet. It only appears after the Docker image is rebuilt and the Keycloak pod restarts.

## Reference

Existing country themes in the repo serve as good examples — e.g. `themes/jamaica/` (yellow `255, 204, 0` / `#ffcc00`), `themes/kenya/`, `themes/lesotho/`. Read one of those alongside `themes/unctad-next/` to understand what the parent provides versus what each child overrides.
