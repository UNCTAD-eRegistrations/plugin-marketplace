---
name: create-theme
description: >
  Scaffold a new country/deployment Keycloak theme that inherits from `unctad-next` in the
  eRegistrations Keycloak repo (https://github.com/UNCTAD-eRegistrations/Keycloak, branch `develop`).
  Creates the login + email theme directories, `theme.properties`, a `variables.css` keyed off a
  chosen primary RGB color, and `.gitkeep`'d directories for the logo images. Offers to clone the
  repo if missing, and ensures we're working on `develop`.
  TRIGGER when: the user asks to create / add / scaffold / bootstrap a new Keycloak theme for a
  country or deployment (e.g. "create a tanzania theme", "add a new theme for rwanda", "bootstrap
  a theme for the new colombia deployment").
  DO NOT TRIGGER when: the user wants to edit/customize an EXISTING theme (just edit the files);
  asks to ASSIGN an existing theme to a realm (use `kc_set_realm_theme` directly); or wants to
  PORT/PROPAGATE an existing theme to other branches (use `propagate-theme`).
license: UNCTAD-Internal
compatibility: File scaffolding + git ops — does not require an active Keycloak MCP connection.
allowed-tools: Read, Write, Bash(mkdir -p *), Bash(test *), Bash(ls *), Bash(git *)
metadata:
  version: "1.2.0"
  version-date: "2026-04-28"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<theme-name> [primary-color-rgb] [locales]"
  disable-model-invocation: "false"
  changelog:
    - "1.2.0 (2026-04-28): Added optional step 7 — after file scaffolding, ask the user whether they want to configure custom user-profile attributes for the deployment via the new `add-user-attributes` skill. Clarified in step 6 that overriding `register.ftl` is NOT the right way to add registration fields — the parent unctad-next theme renders user-profile attributes dynamically, so attribute work belongs on the realm, not in the theme."
    - "1.1.0 (2026-04-28): Added handling for the canonical repo location (https://github.com/UNCTAD-eRegistrations/Keycloak) — the skill now offers to clone the repo when invoked outside it, and ensures work happens on the `develop` branch (with a safety check for uncommitted changes)."
    - "1.0.1 (2026-04-28): Clarified that `css/styles.css` and `js/conditional-fields.js` referenced by `login/theme.properties` are inherited from `unctad-next` and must NOT be scaffolded — surfaced by pressure-testing where two subagents independently flagged it as ambiguous."
    - "1.0.0 (2026-04-28): Initial port from `Keycloak/.claude/skills/create-theme.md`. Scaffolds login + email theme inheriting from `unctad-next` with parameterized primary color (RGB) and locales. Adds explicit working-directory verification, RGB→hex conversion guidance, and a post-deployment hand-off to `mcp__Keycloak__kc_set_realm_theme`."
---

# Create Keycloak Theme

Scaffold a new country/deployment theme that inherits from `unctad-next` in the eRegistrations Keycloak repo (the one whose Docker image bakes `/opt/keycloak/themes/`).

**Canonical repo:** https://github.com/UNCTAD-eRegistrations/Keycloak
**Working branch:** `develop`

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

### 1. Are we in the Keycloak repo?

```bash
test -d themes/unctad-next && echo IN_REPO || echo "NOT_IN_KEYCLOAK_REPO"
```

**If not in the repo**, the canonical home is https://github.com/UNCTAD-eRegistrations/Keycloak. Offer to clone:

> "I don't see `themes/unctad-next/` here. The Keycloak repo lives at https://github.com/UNCTAD-eRegistrations/Keycloak. Want me to clone it into `./Keycloak/` and `cd` in? (yes/no)"

If yes:

```bash
git clone https://github.com/UNCTAD-eRegistrations/Keycloak.git
cd Keycloak
git checkout develop
```

If no, stop — the user can clone it themselves and re-invoke from the repo root.

### 2. Are we on `develop`?

Theme work happens on `develop`, not `main`:

```bash
git rev-parse --abbrev-ref HEAD     # current branch
git status --porcelain               # uncommitted changes?
```

- If **already on `develop`**: `git pull --ff-only origin develop` to sync. (If the pull fails because of diverged history, stop and ask the user how to proceed — don't force.)
- If on another branch with **no uncommitted changes**: `git checkout develop && git pull --ff-only origin develop`.
- If on another branch **WITH uncommitted changes**: stop. Show the user `git status` and ask whether to commit/stash first or invoke from `develop` directly. Don't risk their work.

If the user prefers to scaffold on a feature branch off `develop` (recommended for a PR-based flow), ask whether to `git checkout -b feature/<theme-name>-theme` first.

### 3. Is the target name free?

```bash
test ! -d themes/<theme-name> && echo OK || echo "ALREADY_EXISTS"
```

- If `themes/<theme-name>/` already exists → stop. Don't overwrite. Ask whether to abort, pick a different name, or delete first.

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
  - Override messages: `login/messages/messages_<locale>.properties` (e.g. for new attribute labels — see step 7 below).
  - **Don't** override `register.ftl` — the parent `unctad-next` template renders user-profile attributes dynamically, so new registration fields are configured at the realm level (step 7), not in theme files.
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

### 7. (Optional) Configure custom user attributes for this deployment

After the file scaffolding, ask the user:

> "The theme files are scaffolded. Want to also configure custom user-profile attributes on the Keycloak realm for this deployment? (yes/no)
> — yes if this country needs registration fields beyond the unctad-next defaults (e.g. national ID number, nationality, tax ID).
> — no if you'll use the standard fields, or want to do it later (`/keycloak-mcp:add-user-attributes`)."

If **yes** → hand off to `/keycloak-mcp:add-user-attributes`. That skill will prompt for the instance + realm and walk through attribute definitions interactively (or accept a `--spec <file>`). Because the unctad-next parent theme's `register.ftl` renders user-profile attributes dynamically, simply declaring them on the realm is enough for the new fields to appear on the registration page — no further file changes in this theme.

If **no** → done. The user can run the attribute setup later, independently.

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
