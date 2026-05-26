---
name: service-manual-all
description: Generate user manuals for ALL citizen-facing services of an eRegistrations country instance, plus a catalog index page. Use when the user says "document Lesotho", "generate all manuals", "create manuals for the whole instance", "manual instance [name]", "manual [country]", or names a country/instance without specifying a single service. Do NOT use for a single service (use /service-manual) or for technical analysis (use /eregistrations-docs).
argument-hint: "[mcp-server]"
version: 3.5.0
version-date: 2026-05-22T00:00:00Z
authors:
  - Nelson Perez (nelsonadpa@gmail.com) — original service-manual concept
  - Frank Grozel (gfrankgva) — batch orchestration, subagent architecture, wizard system
changelog: |
  3.5.0 (2026-05-22) - gfrankgva: Part B uses BPA-canvas swimlane (columns = stages, rows = parallel agency lanes) instead of ASCII text diagram. Template extraction adds a bundled-CSS probe fallback for SPA brand sites where Playwright/WebFetch fail.
  3.4.0 (2026-03-23) - gfrankgva: Branch-aware manual structure — detect service branches via service_branches, present each path as a separate track with sticky toggle, per-track TOC/step numbering, print support
  3.3.0 (2026-03-23) - gfrankgva: Form illustrations wizard (generated mockups / real screenshots / both), Playwright screenshot capture instructions, DS URL derivation from connection_status
  3.2.0 (2026-03-23) - gfrankgva: Merged field guidance table, required/conditional field indicators, encouraging tone from single-service skill
  3.1.0 (2026-03-12) - gfrankgva: Identity announcement, Part A/B coverage wizard question, Part B file processing manual generation
  3.0.0 (2026-03-12) - gfrankgva: Merged v2.1 (subagent architecture, template subagent, versioning, parallel batches, TodoWrite) with wizard branch (interactive wizard, DS theming, error handling, explicit read-only whitelist)
  2.1.0 (2026-02-19) - gfrankgva: Intent matching guidance; author credits
  2.0.0 (2026-02-19) - gfrankgva: Configuration wizard, empty service detection, DS template extraction, content depth options, deployment automation
  1.0.0 (2026-02-19) - gfrankgva: Initial skill — parallel subagent batch generation with catalog index (based on /service-manual v1.0 by nelsonadpa)
---

# Generate All Service Manuals for an eRegistrations Instance

> **Based on the original `/service-manual` skill developed by Nelson Perez (nelsonadpa@gmail.com) on 18 Feb 2026.**

## When to Use This Skill
- User says "document Lesotho", "document Cuba", or names a country/instance
- User says "manual instance [name]", "manual [country]", "manual for [instance]"
- User asks to "generate all manuals", "create manuals for the whole instance"
- User wants a full documentation site for a BPA instance

## When NOT to Use This Skill
- User asks about ONE specific service → use `/service-manual`
- User wants a technical Excel analysis → use `/eregistrations-docs`
- User provides a specific service ID or URL → use `/service-manual`

Generate user manuals for every citizen-facing service in a country instance, plus a catalog index page.

## Inputs

- **MCP Server**: `$ARGUMENTS[0]`

If missing, ask the user. Known servers: `BPA-lesotho`, `BPA-cuba-test`, `BPA-jamaica`.

## CRITICAL RULES

- **READ ONLY** — NEVER use create/update/delete MCP operations
- Only use `*_list`, `*_get`, `analyze_service`, `form_get`, `form_component_get`, `field_list`, `determinant_list`, `determinant_get`, `role_list`, `role_get`, `bot_list`, `bot_get`, `registration_list`, `registration_get`, `documentrequirement_list`, `classification_list`, `classification_get`, `notification_list`, `service_export_raw`, `service_to_yaml`, `connection_status`, `debug_scan` operations.
- Do NOT call any tool that creates, updates, deletes, publishes, activates, or modifies data.
- **Use subagents for each manual** — NEVER fetch service detail data in main context
- Main context handles ONLY: wizard, service list, filtering, catalog index, orchestration
- This prevents context saturation which killed previous sessions
- **If a tool call fails 2x, STOP** — report to user, do not retry in a loop

---

## Phase 0: Interactive Wizard (Main Context)

**This step runs BEFORE any MCP calls.**

### Identity Announcement

Before presenting the wizard questions, say:

> **Full Instance Manual Generator** — I'll create user manuals for ALL citizen-facing services of an eRegistrations country instance, plus a catalog index page. If you only need ONE specific service documented, stop me and use `/service-manual` instead.

Then present the wizard using a single `AskUserQuestion` call with all six questions:

### Question 1: UI Style
- **Header**: `UI Style`
- **Question**: `Which visual style should the manuals use?`
- **Options**:
  1. **Label**: `DS Match (Recommended)` — **Description**: `Extract design from the live DS site (e.g., lesotho.eregistrations.dev) to match colors, fonts, logos exactly`
  2. **Label**: `Basic` — **Description**: `Clean built-in styling — fast, no external dependencies`
  3. **Label**: `Custom URL` — **Description**: `Provide any website URL and we'll extract its design system`

### Question 2: Scope
- **Header**: `Scope`
- **Question**: `Which services should be included?`
- **Options**:
  1. **Label**: `All active services (Recommended)` — **Description**: `Generate manuals for all services with real form content. Empty services get 'Coming Soon' badges.`
  2. **Label**: `Selection` — **Description**: `I'll pick which services to include after seeing the list`

### Question 3: Content Depth
- **Header**: `Detail level`
- **Question**: `How detailed should each manual be?`
- **Options**:
  1. **Label**: `Standard (Recommended)` — **Description**: `All sections with moderate detail (~1200 lines per manual)`
  2. **Label**: `Quick` — **Description**: `Overview, requirements, basic steps only (~500 lines per manual)`
  3. **Label**: `Detailed` — **Description**: `Full field-level reference, all determinant logic (~1800 lines per manual)`

### Question 4: Coverage
- **Header**: `Coverage`
- **Question**: `What should the manuals cover?`
- **Options**:
  1. **Label**: `Part A only (Recommended)` — **Description**: `Document the applicant form only — what citizens see and fill in`
  2. **Label**: `Part A + Part B` — **Description**: `Also document the processing side — what each government desk sees, reviews, and decides. Generates a separate Part B file per service.`

### Question 5: Form Illustrations
- **Header**: `Form illustrations`
- **Question**: `How should the form be illustrated in the manual?`
- **Options**:
  1. **Label**: `Generated mockups (Recommended)` — **Description**: `CSS-based form mockups generated from the form structure data — fast, no browser needed`
  2. **Label**: `Screenshots` — **Description**: `Real screenshots captured from the live DS portal using Playwright — authentic but slower, requires DS access`
  3. **Label**: `Both` — **Description**: `Generate TWO versions of each manual: one with mockups, one with screenshots`

### Question 6: Output
- **Header**: `Output`
- **Question**: `Where should the manuals be saved?`
- **Options**:
  1. **Label**: `Local files (Recommended)` — **Description**: `Save all HTML files in a country folder locally`
  2. **Label**: `GitHub Pages` — **Description**: `Deploy to UNCTAD-eRegistrations/eregistrations-manual repo`
  3. **Label**: `Both` — **Description**: `Save locally AND deploy to GitHub Pages`

Store results as `WIZARD_UI_STYLE`, `WIZARD_SCOPE`, `WIZARD_DEPTH`, `WIZARD_COVERAGE`, `WIZARD_ILLUSTRATIONS`, `WIZARD_OUTPUT`.

**Follow-up questions (ask in a single follow-up message if needed):**

If `WIZARD_UI_STYLE` is "Custom URL": ask the user for the URL.

If `WIZARD_ILLUSTRATIONS` is "Screenshots" or "Both": ask the user for **DS citizen credentials** — a test account that has existing data (e.g., registered businesses) so screenshots show realistic, populated forms rather than empty fields:
> "For realistic screenshots, I need a citizen account that already has data (e.g., a registered business). Please provide the **username** and **password** for a test citizen account on the DS portal. This account will be used only for Playwright navigation to capture screenshots."

Store as `WIZARD_DS_USERNAME` and `WIZARD_DS_PASSWORD`.

Derive `country_slug` from the MCP server name (e.g., BPA-lesotho -> lesotho, BPA-cuba-test -> cuba).
Derive `ds_url` by calling `connection_status` on the MCP server — it returns `ds_url` in the response. Fall back to `https://{country_slug}.eregistrations.dev` if not available. For Lesotho production, the DS URL is `https://services.businessregistrations.gov.ls`.

---

## Phase 1: Pre-flight & Service Discovery (Main Context)

### 1a. Auth Check

1. Call `connection_status` on the MCP server
2. If not authenticated → run `auth_login`, wait for success

### 1b. List and Filter Services

1. Call `service_list(limit=100)` on the MCP server
2. **Filter OUT non-citizen-facing services** — exclude:
   - Names containing: "copy", "test", "prueba", "copia" (case-insensitive)
   - Names containing: "Registrar only", "SWR", "BO Registry" (internal admin)
   - Names containing personal names like "darek", "ando" (dev testing)
   - "Basic BPA" (template)
   - Any service with status "inactive" or "draft"

### 1c. Empty Service Detection

For each filtered service, run lightweight checks (these calls are small, safe in main context):
- `form_get(service_id)` — get `component_count`
- `role_list(service_id)` — get role `total`

Classify each service:

| component_count | Classification | Action |
|---|---|---|
| `<= 1` | EMPTY | Mark as "Coming Soon" in catalog |
| `2–5` | MINIMAL | Flag for review, generate short manual |
| `> 5` | ACTIVE | Generate full manual |

### 1d. Report to User

Present two lists:

**Active services ({N}):**
1. {name} — {component_count} components, {role_count} roles — ID: {id}
2. ...

**Coming Soon — not yet configured ({M}):**
1. {name} — empty form, no roles — ID: {id}
2. ...

If `WIZARD_SCOPE` is "Selection": ask user to pick which active services to include.
If `WIZARD_SCOPE` is "All": ask "Proceed with all {N} active services? ({M} empty services will show as 'Coming Soon' in the catalog)"

Wait for user confirmation before proceeding.

---

## Phase 2: Template Preparation (Main Context)

### Create Output Directory

```bash
mkdir -p {country_slug}-manuals
```

### Template Handling

**If `WIZARD_UI_STYLE` is "DS Match" or "Custom URL":**
1. Check if `{country_slug}-manuals/TEMPLATE.html` already exists
2. If yes: tell user "Found existing template, will reuse it" — skip extraction
3. If no: spawn a subagent to extract design tokens using a **multi-strategy approach**:

Subagent prompt for template extraction:
~~~
Extract the visual identity of {ds_url or custom URL} for use as a manual design template. Try strategies in order — fall back to the next if the previous yields no usable tokens.

### Strategy 1 — Bundled-CSS probe (works for Vite/React/Angular SPAs)

Most eRegistrations DS sites are SPAs. Playwright works but is slow; WebFetch sees an empty shell. Curl the bundled stylesheet directly:

```bash
URL="{ds_url or custom URL}"
HTML=$(curl -sL "$URL" --max-time 15)

# Find the bundled CSS (Vite emits hashed filenames like index-XXXX.css)
CSS_REL=$(echo "$HTML" | grep -oE 'href="[^"]*index[^"]*\.css"' | head -1 | sed 's/href="//;s/"$//')
CSS_URL="${URL%/}/${CSS_REL#/}"
CSS=$(curl -sL "$CSS_URL" --max-time 15)

# Brand tokens (CSS custom properties)
echo "$CSS" | grep -oE -- '--[a-z-]+:\s*[^;]+;' | grep -iE 'brand|primary|accent|bg|background|fg|foreground|header|surface' | sort -u

# Most-used hex colours
echo "$CSS" | grep -oE '#[0-9a-fA-F]{6}' | sort | uniq -c | sort -rn | head -10

# Font imports and families
echo "$CSS" | grep -oE '@import[^;]+'
echo "$CSS" | grep -oE 'font-family:[^;}]+' | sort -u | head -5

# Logo / favicon
echo "$HTML" | grep -oE '(href|src)="[^"]*(logo|favicon)[^"]*"' | head -5
```

Synthesise: `header_bg`, `primary_color` (a usable action color on light backgrounds — if `--brand` is a pale tone like yellow, prefer `--brand-strong`), `accent_color`, `header_text`, `background`, `font_family` (display + body), `logo_url`.

### Strategy 2 — Playwright extraction

If Strategy 1 yields no tokens, navigate to the URL with Playwright. Extract:
- Computed CSS custom properties on `:root`
- Header background and text colour
- Logo `<img>` src in the header
- Heading and body `font-family` values

### Strategy 3 — Known-instance fallback

If both strategies fail and the URL matches a known eR instance, use canned tokens:

- **Lesotho DS** (`*.businessregistrations.gov.ls`): Primary Navy `#2B2A65`, Primary Green `#4CAF74`, Text Dark `#1F2128`, Body `#555866`, Light BG `#F5F5F7`, Heading `Poppins`, Body `Roboto`, pill buttons (`9999px`), card radius `12px`.
- **JSEZA / Jamaica SEZ** (`jseza.eregistrations.dev` or any Jamaica SEZ service): header `#ffd740` brand yellow + text `#1b1b1b`, primary action `#c79500` (brand-strong gold), accent `#009688` (teal-green), background `#fffdf4` (cream), Montserrat (display) + Inter (body). Extracted 2026-05-22.

If no known instance matches, use Basic styling: `#1a56db` primary, `#f9fafb` background, `#111827` text, system font stack.

### Write the template

Write a TEMPLATE.html file to {working_directory}/{country_slug}-manuals/TEMPLATE.html containing:
- A complete CSS stylesheet in a <style> tag with the extracted tokens as CSS variables
- A header template with the logo and country name
- A footer template with branding
- Placeholder markers: {{TITLE}}, {{CONTENT}}, {{TOC}}, {{VERSION}}

The template should NOT be a full manual — just the design shell that manual subagents will use.

Return the file path AND a one-line note saying which strategy (1, 2, or 3-fallback) was used.
~~~

**If `WIZARD_UI_STYLE` is "Basic":** No template needed. Subagents use built-in styling:
- Colors: `#1a56db` primary, `#f9fafb` background, `#111827` text
- Fonts: system font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`)
- Buttons: rounded (`border-radius: 6px`)

**If `WIZARD_UI_STYLE` is "Custom URL":** Same as "DS Match" but use the user-provided URL instead of `ds_url`.

Store `template_path` variable (path to TEMPLATE.html, or empty string if "Basic").

---

## Phase 3: Generate Manuals (Subagents — PARALLEL batches)

For EACH active (non-empty) citizen-facing service, spawn a Task subagent.

**Launch 3-4 subagents in parallel** (multiple Agent tool calls in one message). When a batch completes, launch the next batch.

**Progress tracking:** Use TodoWrite to mark each service as pending/in_progress/completed. Update after each batch completes.

Each subagent receives this prompt (fill in actual values):

~~~
You are generating an HTML user manual for an eRegistrations service.

**Service ID**: {service_id}
**MCP Server**: {mcp_server} (use MCP tools prefixed with mcp__{mcp_server}__)
**Service Name**: {service_name}
**Output file**: {working_directory}/{country_slug}-manuals/{service_slug}/index.html
**Template file**: {template_path} (read this first if non-empty, use its CSS/header/footer)
**Content Depth**: {wizard_depth}
**Coverage**: {wizard_coverage}
**Form Illustrations**: {wizard_illustrations} (either "Generated mockups", "Screenshots", or "Both")
**DS URL**: {ds_url} (e.g., https://services.businessregistrations.gov.ls — only needed if illustrations include screenshots)
**Part B output file**: {working_directory}/{country_slug}-manuals/{service_slug}/part-b.html (only if coverage includes Part B)
**Screenshots output file**: {working_directory}/{country_slug}-manuals/{service_slug}/index-screenshots.html (only if illustrations is "Both")

### Step 1: Fetch ALL Data

Call these MCP tools in parallel:
1. `mcp__{mcp_server}__form_get(service_id="{service_id}")` — full form structure
2. `mcp__{mcp_server}__field_list(service_id="{service_id}", limit=500)` — all fields
3. `mcp__{mcp_server}__determinant_list(service_id="{service_id}")` — conditional logic
4. `mcp__{mcp_server}__role_list(service_id="{service_id}")` — workflow roles
5. `mcp__{mcp_server}__bot_list(service_id="{service_id}")` — automations
6. `mcp__{mcp_server}__analyze_service(service_id="{service_id}")` — overview with costs/requirements
7. `mcp__{mcp_server}__registration_list(service_id="{service_id}")` — registrations
8. `mcp__{mcp_server}__service_branches(service_id="{service_id}")` — branching logic (which guide choices create different form paths)

If field_list has `has_more=true`, fetch additional pages with offset.

**If Coverage is "Part A + Part B"**, also fetch detailed role data:
8. For EACH role from role_list: `mcp__{mcp_server}__role_get(role_id="{role_id}")` — gets formSchema, statuses, description
9. For each role status found in role details: note destination_id and transition names
10. `mcp__{mcp_server}__componentbehaviour_list(service_id="{service_id}")` — component behaviours for role form logic

**Document requirements per registration**: After fetching registration_list, for EACH registration that has an ID, also call:
`mcp__{mcp_server}__documentrequirement_list(registration_id="{registration_id}")`
This gives the actual required documents per registration type. Include these in the Prerequisites section organized by registration type.

### Step 2: Map the Form Structure

From form_get, identify:
- **Top-level panels** = tabs (e.g., "Company", "Shareholders", "Documents")
- **Components within each panel** = fields, grids, uploads, radio buttons
- **Conditional visibility** from determinants (which fields/panels depend on other answers)

**Recursive component tree traversal** — for nested forms (tabs containing panels containing datagrids), traverse the component tree recursively:
- Level 1: Top panels = tabs/steps
- Level 2: Sub-panels, fieldsets, columns within each tab
- Level 3: Individual fields, grids, uploads within sub-panels
- For each datagrid: document what each column means and how to add rows
- For conditional fields: note which fields appear/disappear based on other selections (use determinant data)

### Step 2b: Detect and Handle Branches

Analyze the `service_branches` response. Classify each branching field into one of two categories:

**Branches vs. disclosures — the critical distinction:**
- **Application-type branches** (→ separate tracks): A field where different values lead to fundamentally different form paths — different tabs appear, different fields are required, different fees apply. Typically a guide-level radio/select with 2-3 values that each show/hide 3+ tabs or panels. Example: "Business is: Sole Proprietorship / Company".
- **Conditional disclosures** (→ inline notes): A yes/no or boolean field that expands or collapses a section within a tab. These do NOT create separate tracks. Handle them inline: "This section only appears if you selected X." Example: "Do you want a branch office? Yes/No" → shows address fields.

**How to tell:** Look at the `shows` arrays in service_branches. If a field's different values show/hide entire tabs (top-level form panels), it's an application-type branch. If it only toggles a sub-panel or a few fields within a single tab, it's a disclosure.

**Value grouping:** Multiple option values may map to the same form behavior. E.g., 5 company types might all show the same "local company" tabs while 1 type shows "external company" tabs — that's 2 tracks, not 5. Group values by their `shows` arrays: values that show the same set of components belong to the same track.

**When a major branch exists:**

1. **Identify the branch field** — e.g., `guideTypeOfBusiness2` with values `soleProprietor` and `company`
2. **Group values into tracks** — values with identical or near-identical `shows` arrays form one track. Name each track using representative option labels.
3. **Map each track's tabs** — cross-reference the `shows` arrays with the form tabs from form_get. Determine which tabs appear for each track.
4. **Identify shared vs. track-specific tabs** — tabs visible regardless of the branch choice are shared; tabs that only appear for one track are track-specific.
5. **Nested branches stay inline** — if a branching field exists *inside* a track-specific tab (e.g., "Type of shares" within the Company track), handle it as an inline conditional within that track's step, not as a sub-track. The manual uses only ONE level of track splitting.

**Branch-aware manual structure:**

When a major branch is detected, the manual MUST use a **track-based layout** instead of a single linear flow:

```
Shared sections: Header, Introduction, Prerequisites, Guide (explains the branch choice)

BRANCH SELECTOR — sticky toggle bar with pill buttons for each branch
  Active = filled button, Inactive = outlined. JavaScript toggles visibility.
  Default: first branch option selected.

Track A (e.g., Sole Proprietorship):
  Steps 1..N: only the tabs that appear for this branch
  Each step header has a colored badge identifying the track
  Left border accent color (e.g., green)

Track B (e.g., Company):
  Steps 1..M: only the tabs that appear for this branch
  Each step header has a colored badge identifying the track
  Left border accent color (e.g., navy)

Shared sections: After Submission, Costs & Fees, FAQ
```

**Key rules for branch-aware manuals:**
- **Step numbering restarts per track** — Track A has Steps 1-4, Track B has Steps 1-7 (not continuing from Track A)
- **TOC adapts** — show separate sub-sections per track in the table of contents, toggle visibility with JS
- **Do NOT duplicate shared content** — tabs that appear in both tracks (if any) should reference the same content via CSS, not be written twice
- **Costs & Fees section** should show fee tables per branch if fees differ
- **FAQ** should include branch-specific questions (e.g., "What's the difference between SP and Company?")
- **Print support** — both tracks print fully with `@media print { .track-a, .track-b { display: block !important; } }` and colored left borders to distinguish them

**When NO major branch exists** (service has no guide-level branching, or branching only affects a few fields within a tab): use the standard linear structure — no track selector needed. Minor conditional fields are handled inline with "This field only appears if you selected X" notes.

### Step 3: Generate HTML Manual

Create a single self-contained HTML file.

**If template_path is provided:** Read TEMPLATE.html, use its CSS and header/footer, replace placeholders.
**If no template:** Use built-in clean styling with light theme.

**Content Depth Controls:**

| Section | Quick (~500 lines) | Standard (~1200 lines) | Detailed (~1800 lines) |
|---|---|---|---|
| Introduction | 2-3 sentences | Full paragraph | Full paragraph + legal basis |
| Prerequisites | Bullet list | Bullet list + tips | Bullet list + tips + where to get each doc |
| Form mockups | Skip | Include | Include with annotations |
| Field explanations | 1 line each | 2-3 lines each | 3-5 lines each + validation rules |
| Conditional logic | Skip | Major conditions only | All determinant logic documented |
| Workflow | 1 sentence | Role-by-role summary | Full workflow with timelines |
| FAQ | Skip | 5-8 questions | 10+ questions |
| Field reference tables | Skip | Skip | Include per-tab tables |
| Conditional Logic Reference | Skip | Skip | Full appendix |

**Structure (linear — when no major branch detected):**
1. Header — service name, country name, logo (if template)
2. Table of Contents — linked anchors to all sections
3. Introduction — what is this service, who needs it
4. Prerequisites — documents/information to gather before starting (organized by registration type)
5. Step-by-step sections — one per form tab:
   a. Step number + tab name
   b. CSS form mockup mimicking the real interface (skip for `quick` depth)
   c. Plain-language explanation of every field (summary only for `quick` depth)
   d. Tips, examples, common mistakes
6. Review & Submit section
7. What happens after submission (workflow roles)
8. Costs/fees breakdown (full formula detail for `detailed` depth)
9. FAQ (skip for `quick` depth)
10. Field Reference Table (only for `detailed` depth)
11. Conditional Logic Reference (only for `detailed` depth)

**Structure (branch-aware — when major branch detected via Step 2b):**
1. Header — service name, country name
2. Table of Contents — with sub-sections per track (toggle with JS)
3. Introduction — what is this service, who needs it
4. Prerequisites — organized by branch if different
5. Guide section — explains the branch choice, mockup of guide form
6. **Sticky branch selector** — pill toggle bar (JS show/hide)
7. **Track A** — steps for first branch only (own step numbering, colored badge + left border)
8. **Track B** — steps for second branch only (own step numbering, different color)
9. After Submission (shared)
10. Costs & Fees — per-branch fee tables if fees differ
11. FAQ — includes branch-specific questions

**Writing Style:**
- Write for **CITIZENS**, not administrators or developers
- Simple, clear language — no jargon
- Explain **WHY** each field is needed
- Give realistic examples using locally appropriate names/context
- Use "you" and "your" — speak directly to the reader
- Mention common mistakes and how to avoid them
- For conditional fields: "This section only appears if you selected X."
- Be encouraging: "Don't worry if you're not sure — you can save your progress and come back later."

For each field or section, provide:

| Aspect | What to write |
|---|---|
| **What it is** | Plain language description of the field |
| **Why it's needed** | Legal or practical reason for collecting this data |
| **How to fill it** | Specific guidance with concrete examples |
| **Common errors** | What people frequently get wrong |
| **Conditional fields** | "This only appears if you selected X" |

### Form Illustrations

The approach depends on the `Form Illustrations` setting:

**If "Generated mockups":** Use CSS mockups (skip for `quick` depth):
```html
<div class="form-mockup">
    <div class="form-mockup-bar">
        <span class="bar-title">{Service Name}</span>
    </div>
    <div class="form-mockup-tabs">
        <span class="mtab">Tab 1</span>
        <span class="mtab active">Current Tab</span>
        <span class="mtab">Tab 3</span>
    </div>
    <div class="form-mockup-body">
        <!-- mock-field, mock-input, mock-select, mock-radio, mock-upload, mock-grid -->
        <!-- mock-checkbox, mock-date, mock-signature -->
    </div>
</div>
```

Component Type Mapping:

| Form.io Type | Mockup Class | Manual Description |
|---|---|---|
| `textfield` | `mock-input` | "Type your answer in the text box" |
| `textarea` | `mock-input` (taller) | "Enter a detailed description in the large text box" |
| `select` | `mock-select` | "Select from the dropdown list" |
| `radio` | `mock-radio` | "Choose one option from the list" |
| `checkbox` | `mock-checkbox` | "Tick the box if this applies to you" |
| `datagrid` | `mock-grid` | "Click 'Add Row' to add each entry. You can add as many as needed." |
| `file` | `mock-upload` | "Click the upload area or drag your document here (PDF, JPG accepted)" |
| `datetime` | `mock-date` | "Select the date from the calendar picker" |
| `number` | `mock-input` | "Enter the number (digits only)" |
| `currency` | `mock-input` | "Enter the amount in the local currency" |
| `signature` | `mock-signature` | "Sign using your mouse, trackpad, or finger on a touchscreen" |
| `content` | *(informational)* | Explain what the static text tells the user |
| `panel` | *(section/tab)* | Becomes a section heading in the manual |
| `columns` | *(layout)* | Fields displayed side by side — describe each column's fields |
| `table` | `mock-grid` | "Fill in each row of the table" |
| `htmlelement` | *(informational)* | Explain the displayed content |
| `hidden` | *(skip)* | Do not show in the manual |

Include styles for:
- Required field indicator (red asterisk next to label)
- Conditional field indicator (dashed border or icon to signal "this field may not appear for everyone")

**If "Screenshots":** Capture real screenshots from the live DS portal using Playwright (skip for `quick` depth):

1. **Navigate to DS**: Use `mcp__playwright__browser_navigate` to go to `{ds_url}/services/{service_id}`
2. **Handle login**: If redirected to a login page, use `mcp__playwright__browser_fill_form` with username=`{wizard_ds_username}` and password=`{wizard_ds_password}`, then click Login
3. **For each form tab** (Guide, Form sub-tabs, Documents, Payment, Send):
   a. Click the tab using `mcp__playwright__browser_click`
   b. Wait for content to load using `mcp__playwright__browser_wait_for`
   c. Take a viewport screenshot with `mcp__playwright__browser_take_screenshot`
   d. If the form content extends below the viewport, scroll down and take additional screenshots — find clean cut points between form sections (never cut mid-field or mid-component)
   e. Save each screenshot to `{working_directory}/{country_slug}-manuals/{service_slug}/screenshots/` as `{tab-slug}-{n}.png`
4. **For the Guide tab specifically**: Select each guide option to reveal conditional questions, take screenshots of each state
5. **Embed screenshots** in the HTML using relative `<img>` tags:
```html
<div class="form-screenshot">
    <img src="screenshots/{tab-slug}-1.png" alt="Screenshot of {tab name} showing {brief description}">
    <div class="screenshot-caption">The {tab name} tab as it appears on the portal</div>
</div>
```
6. Add CSS for `.form-screenshot` (border, border-radius, box-shadow) and `.screenshot-caption` (italic, smaller text, gray background)

**If "Both":** Generate TWO separate HTML files:
- `index.html` — uses CSS generated mockups (follow "Generated mockups" instructions above)
- `index-screenshots.html` — uses real screenshots (follow "Screenshots" instructions above)
Both files share the same field explanations, text content, structure, and styling — only the form illustration method differs. Generate the mockup version first, then duplicate it and replace the mockup `<div>` elements with `<img>` screenshot elements.

**HTML Requirements:**
- Self-contained — all CSS inline in style tag (unless using template)
- Responsive — desktop and mobile
- Print-friendly
- Country-appropriate branding colors

**Manual Versioning (REQUIRED):**
```html
<footer class="manual-version">
  <p>Manual v1.0 — Generated {YYYY-MM-DD HH:MM UTC} — Source: {mcp_server}/{service_id}</p>
  <p>Generated by /service-manual-all skill v3.5.0</p>
</footer>
```
Use the current date/time when generating. First generation is always v1.0. If a manual already exists at the output path, read its version number and increment (v1.0 → v1.1).

### Step 4: Write File

Create the directory and write the file:
```bash
mkdir -p {working_directory}/{country_slug}-manuals/{service_slug}
```
Write the HTML file using the Write tool.

### Step 5: Generate Part B HTML (Only if Coverage is "Part A + Part B")

Create a SEPARATE HTML file at the Part B output path (`part-b.html` in the same service folder).

**Part B Document Structure:**
1. **Header** — "{Service Name} — File Processing Manual (Part B)", with link back to Part A: `<a href="index.html">Back to Part A (Applicant Manual)</a>`
2. **Table of Contents** — linked anchors to each desk section
3. **Workflow Overview — BPA-canvas swimlane (REQUIRED)**

   Render the role graph as a column-grid swimlane that **mirrors the BPA designer canvas**: columns = workflow stages, cards stacked inside a column = roles that run **in parallel**. This is the format SEZ / agency managers recognise.

   **Source data:** `role_list(include_details=true)` gives every role's `sort_order`, `start_role`, `role_type`, and the `destinations[]` on each status (the `FileValidatedStatus` destination is the happy-path next role). The full BPA canvas is reconstructible from this.

   **Build the columns:**
   - Sort roles by `sort_order`. Roles sharing the same `sort_order` form one column. Trace `FileValidatedStatus.destination_id` chains to verify the ordering matches the actual transitions.
   - Post-decision chains often share a single high `sort_order` (e.g., 299) and are linear, not parallel — render those as a SECONDARY swimlane below the main one (e.g., "After pre-approval — license issuance") OR omit if not requested.
   - The Applicant role and dangling/amendment roles are NOT part of the main happy path — surface them in a separate "Side branches" section, not the main columns.

   **HTML structure:**
   ```html
   <div class="flowchart-wrap">
     <div class="swimlane">
       <div class="swimlane-col">
         <div class="swimlane-stage"><span>1</span>Intake</div>
         <div class="swimlane-card">
           <div class="name">Fact check</div>
           <div class="swimlane-actor actor-jseza">JSEZA</div>
         </div>
       </div>
       <!-- one .swimlane-col per stage; multiple .swimlane-card inside if parallel -->
     </div>
     <div class="swimlane-legend">
       <span>Actors:</span>
       <span class="swimlane-actor actor-jseza">JSEZA</span>
       <!-- one chip per distinct institution -->
     </div>
   </div>
   ```

   **CSS (paste into the page's `<style>` block — adapt `{N}` to the number of stages):**
   ```css
   .flowchart-wrap {
     background: var(--card-bg, #fff);
     border: 1px solid var(--border, #e7e3d4);
     border-radius: 8px; padding: 28px 24px; overflow-x: auto;
     /* break out of the article width so all stages fit */
     width: calc(100vw - 48px); max-width: 1640px;
     margin-left: 50%; transform: translateX(-50%); position: relative;
   }
   .swimlane {
     display: grid; grid-template-columns: repeat({N}, minmax(155px, 1fr));
     gap: 18px; align-items: start; min-width: 1400px;
   }
   .swimlane-col { display: flex; flex-direction: column; gap: 10px; position: relative; }
   .swimlane-col::after {
     content: ""; position: absolute; right: -12px; top: 38px;
     width: 10px; height: 10px;
     border-top: 1.5px solid #c4cbd6; border-right: 1.5px solid #c4cbd6;
     transform: rotate(45deg); opacity: 0.8;
   }
   .swimlane-col:last-child::after { display: none; }
   .swimlane-stage {
     font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
     color: var(--muted, #5b6b7c); font-weight: 600; margin-bottom: 4px;
   }
   .swimlane-stage span {
     display: inline-flex; align-items: center; justify-content: center;
     width: 20px; height: 20px; border-radius: 50%;
     background: var(--primary); color: #fff;
     font-weight: 600; margin-right: 8px; font-size: 11px;
   }
   .swimlane-card {
     background: #fff; border: 1px solid #d8dee6; border-radius: 6px;
     padding: 10px 12px 12px; font-size: 13.5px;
     box-shadow: 0 1px 2px rgba(20, 33, 60, 0.04);
   }
   .swimlane-card .name { font-weight: 600; color: #1a2733; line-height: 1.3; margin-bottom: 8px; }
   .swimlane-actor {
     display: inline-flex; align-items: center; gap: 5px;
     font-size: 11.5px; padding: 2px 8px; border-radius: 10px;
     font-weight: 500; line-height: 1.4;
   }
   .swimlane-actor::before {
     content: ""; display: inline-block; width: 8px; height: 8px;
     border-radius: 50%; background: currentColor; opacity: 0.45;
   }
   .swimlane-legend { display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 18px; font-size: 12.5px; }
   ```

   **Actor badge palette** — assign one class per distinct institution. Default palette (rename classes to match the actual institutions in the service):
   ```css
   .actor-jseza    { background: #fff3b8; color: #6b4a00; }   /* internal authority — gold */
   .actor-jca      { background: #d8ece1; color: #167b5b; }   /* customs — green */
   .actor-taj      { background: #fde0c2; color: #8a4a0d; }   /* tax — amber */
   .actor-mofps    { background: #e3dcef; color: #4d3678; }   /* finance — purple */
   .actor-mic      { background: #f0dadc; color: #7a2e3c; }   /* ministry — brick */
   .actor-applicant{ background: #ece8db; color: #5a5240; }   /* applicant — neutral */
   .actor-system   { background: #cfe7e3; color: #195854; }   /* bot — teal */
   ```

   **One-paragraph caption under the swimlane:** "Columns are stages; cards stacked in a column run in parallel; per-agency lanes (e.g., Legal, Business, Technical, Compliance) each carry their own evaluation → approval — evaluations and approvals are not sequential phases."

   **Anti-patterns:**
   - Do NOT use Mermaid for this overview — auto-layout doesn't produce the column-grid managers recognise.
   - Do NOT collapse parallel evaluations into a single abstract "Parallel evaluations" node. Show each lane.
   - Do NOT include the Applicant role as a column.
4. **Per-Desk Sections** — one section per role, each containing:
   a. Desk name, description, assigned institution (if available)
   b. **Reviewer Form Mockup** — CSS mockup of the role's formSchema, distinguishing:
      - Read-only fields (applicant data shown for reference) — use `.readonly-field` class
      - Editable fields (reviewer inputs) — use `.reviewer-field` class
   c. **Available Actions** — each role status as a button with its destination:
      ```html
      <div class="action-buttons">
        <button class="action-btn approve">FILE VALIDATED → Next Desk</button>
        <button class="action-btn reject">REJECT → Applicant</button>
        <button class="action-btn sendback">SEND BACK → Applicant</button>
      </div>
      ```
   d. **Automations** — any bots triggered at this desk (from bot_list)
   e. **Reviewer Tips** — practical guidance for the reviewer
5. **Bot Reference Table** — summary of all bots: name, type, category, what they do
6. **Footer** — same versioning pattern as Part A, with `Generated by /service-manual-all skill v3.5.0`

**Writing Style for Part B:**
- Write for **government officers**, not citizens
- Professional, procedural language
- Use "you" to address the reviewer directly
- Explain what each field means and what to check
- For read-only fields: "This field shows the applicant's [X]. You cannot edit this."
- For editable fields: "Enter your [assessment/decision/comment] here."

**CSS Form Mockup additions for Part B:**
```css
.readonly-field { background: #f0f0f0; border-left: 3px solid #999; opacity: 0.8; }
.reviewer-field { background: #fff; border-left: 3px solid #2196F3; }
.action-btn { padding: 8px 16px; border-radius: 4px; margin: 4px; cursor: pointer; font-weight: bold; }
.action-btn.approve { background: #4CAF50; color: white; }
.action-btn.reject { background: #f44336; color: white; }
.action-btn.sendback { background: #FF9800; color: white; }
```

Return ONLY this summary (do NOT return HTML content):
- file_path: the path written (Part A index.html)
- service_name: name of the service
- tabs_count: number of form tabs documented
- fields_count: number of fields documented
- file_size_kb: approximate file size
- content_depth: the depth used
- illustrations: which mode was used (mockups/screenshots/both)
- screenshots_file_path: path to screenshots version (if "Both" mode)
- screenshots_count: number of screenshots captured (if screenshots mode)
- part_b_generated: true/false
- part_b_file_path: path to Part B file (if generated)
- part_b_desks_count: number of desks documented (if generated)
~~~

Collect from each subagent:
- service_name, file_path, tabs_count, fields_count, status (success/failed), error message if failed
- part_b_generated, part_b_file_path, part_b_desks_count (if Part B was requested)

---

## Phase 4: Generate Catalog Index (Main Context)

After all manuals complete, generate `{country_slug}-manuals/index.html` — a catalog page.

This is the ONLY HTML generated in main context (small file, ~150-200 lines).

The catalog must include:

1. **Sticky header** — instance logo (from template extraction or DS), country/institution name, optional nav links ("About", "Help"). If template has a logo URL, use it; otherwise use a text-only header. Adapt colors to the instance's branding (from template or DS Match).

2. **Hero section** — gradient background using the instance's primary color. Contains:
   - Title: "Service Manuals"
   - Subtitle: "Step-by-step guides for {institution_name} services" (adapt to instance)
   - Service count: "Showing all {N} manuals" (updates dynamically with search)

3. **Search/filter bar** — centered search input with dynamic results counter and keyboard shortcuts:
   ```javascript
   const search = document.getElementById('search');
   const counter = document.getElementById('counter');
   search.addEventListener('input', function(e) {
     const query = e.target.value.toLowerCase();
     let visible = 0;
     document.querySelectorAll('.service-card').forEach(card => {
       const match = card.textContent.toLowerCase().includes(query);
       card.style.display = match ? '' : 'none';
       if (match) visible++;
     });
     counter.textContent = query ? `Showing ${visible} of ${total} manuals` : `Showing all ${total} manuals`;
   });
   document.addEventListener('keydown', e => {
     if (e.key === '/' && document.activeElement !== search) { e.preventDefault(); search.focus(); }
     if (e.key === 'Escape') { search.value = ''; search.dispatchEvent(new Event('input')); search.blur(); }
   });
   ```

4. **Service cards grid** — responsive CSS grid (3 columns desktop, 2 tablet, 1 mobile) with gap. Each card includes:
   - **Contextual emoji icon** in a rounded square (choose an emoji that fits the service name — e.g., building for registration, renewal for renew, document for filing)
   - Service name as heading
   - Brief description (from `service_get` or `analyze_service`)
   - **Action link**: green pill button "View Manual →" linked to `{service_slug}/index.html`
   - If Part B was generated: secondary link "Part B: File Processing →" to `{service_slug}/part-b.html`
   - **Status badge**:
     - Green "Available" if manual was generated
     - Gray "Coming Soon" if service was empty — card gets **grayscale filter, reduced opacity (0.7), disabled hover**
     - Red "Error" if subagent failed (with error tooltip)
   - **Hover effect**: subtle shadow elevation + slight upward translate (`transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.12)`)

5. **Category grouping** — if services have natural groupings (e.g., Business Registration, Licensing, Filings), group under subheadings. Otherwise, alphabetical order.

6. **Footer** — instance-adaptive:
   - Institution name and address (if available from DS or template)
   - Implementation partners (if known — e.g., UNCTAD, World Bank)
   - "Last updated: {YYYY-MM-DD}" timestamp
   - Total service count
   - "Generated by /service-manual-all"

7. **Print support** — `@media print` hides search bar and nav, shows all cards without hover effects

8. **Responsive styling** — works on desktop, tablet, and mobile. All colors, logos, and institution names adapt to the instance — nothing hardcoded to a specific country.

---

## Phase 5: Deliver (Main Context)

1. **Summary table** — report to user:
   | # | Service | Status | Tabs | Fields | Part B | File |
   |---|---------|--------|------|--------|--------|------|
   | 1 | ... | Success | ... | ... | 3 desks | ... |
   | 2 | ... | Coming Soon | - | - | - | - |

   (Part B column only shown if coverage included Part B)

2. **Totals**: "{success}/{total_active} services documented. {empty_count} services marked as Coming Soon." If Part B: "+ {part_b_count} Part B processing manuals generated."

3. **Output based on `WIZARD_OUTPUT`:**

   **If "Local files":**
   - Verify `index.html` is present
   - Open in browser: `open {country_slug}-manuals/index.html`
   - Tell user: "To publish later, run `/service-manual-all` again and select the GitHub Pages output option."

   **If "GitHub Pages":**
   - Proceed to Phase 6.

   **If "Both":**
   - Open locally AND proceed to Phase 6.

---

## Phase 6: Deploy to GitHub Pages (Conditional)

Only run if `WIZARD_OUTPUT` includes "GitHub Pages" or "Both".

### 6a. Prepare Repository

```bash
# Check if repo exists locally
if [ -d /tmp/eregistrations-manual ]; then
  cd /tmp/eregistrations-manual && git pull origin gh-pages
else
  gh repo clone UNCTAD-eRegistrations/eregistrations-manual /tmp/eregistrations-manual -- -b gh-pages
fi
```

### 6b. Copy and Deploy

```bash
# Copy generated manuals into the repo
cp -r {working_directory}/{country_slug}-manuals/ /tmp/eregistrations-manual/{country_slug}/

# Commit and push
cd /tmp/eregistrations-manual
git add {country_slug}/
git commit -m "Update {country_slug} service manuals — {success}/{total_active} services — $(date +%Y-%m-%d)"
git push origin gh-pages
```

### 6c. Verify Deployment

Wait up to 30 seconds for CDN propagation, then verify:
```bash
sleep 15
curl -s -o /dev/null -w "%{http_code}" https://unctad-eregistrations.github.io/eregistrations-manual/{country_slug}/
```

Expected: HTTP 200. If not 200, wait another 15 seconds and retry once.

Report live URLs to user:
- **Catalog**: `https://unctad-eregistrations.github.io/eregistrations-manual/{country_slug}/`
- **Individual manuals**: `https://unctad-eregistrations.github.io/eregistrations-manual/{country_slug}/{service_slug}/`
- **Part B manuals** (if generated): `https://unctad-eregistrations.github.io/eregistrations-manual/{country_slug}/{service_slug}/part-b.html`

---

## Error Handling

| Situation | Action |
|---|---|
| MCP connection fails | Report error, ask user to verify server name and connection status. |
| Service fetch fails | Skip that service, log it, continue with others. Report skipped services in summary. |
| Playwright extraction fails | Fall back to known DS tokens (if Lesotho) or Basic styling. Warn user. |
| GitHub push fails | Save locally, report the push error, suggest manual push. |
| Subagent fails | Report which service failed, offer to retry individually with `/service-manual {service-id} {mcp-server}`. |
| File write fails | Report the error with the file path. Suggest alternative directory. |
