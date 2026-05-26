---
name: service-manual
description: Generate a citizen-facing HTML user manual for ONE specific eRegistrations service. Use when the user provides a service ID or BPA URL, asks to "document a service", "create a manual for [service name]", "generate user guide for [service]", "manual for service [name]", or "manual for [service] in [instance]". Do NOT use when the user wants ALL services documented (use /service-manual-all) or wants a technical Excel analysis (use /eregistrations-docs).
argument-hint: "[service-id] [mcp-server]"
version: 3.5.1
version-date: 2026-05-26T00:00:00Z
authors:
  - Nelson Perez (nelsonadpa@gmail.com) — original author
  - Frank Grozel (gfrankgva) — subagent architecture, wizard system, v2–v3 features
changelog: |
  3.5.1 (2026-05-26) - gfrankgva: Back-port from /service-manual-all — (1) Phase 1 split into 1a auth / 1b validate / 1c form complexity & empty-service / 1d report. (2) Brand extraction lifted out of subagent into a new Phase 2 Template Preparation that writes a reusable {country_slug}-TEMPLATE.html; subagent reads template instead of re-extracting. (3) GitHub Pages output now verifies the deployment with curl HTTP 200 + retry, matching Phase 6c in -all.
  3.5.0 (2026-05-22) - gfrankgva: Part B uses BPA-canvas swimlane (columns = stages, rows = parallel agency lanes) instead of ASCII text diagram. Brand token extraction adds a bundled-CSS probe for SPA brand sites (Vite/React/Angular) where WebFetch returns empty.
  3.4.0 (2026-03-23) - gfrankgva: Branch-aware manual structure — detect service branches via service_branches, present each path as a separate track with sticky toggle, per-track TOC/step numbering, print support
  3.3.0 (2026-03-23) - gfrankgva: Form illustrations wizard (generated mockups / real screenshots / both), Playwright screenshot capture instructions, DS URL from connection_status
  3.1.0 (2026-03-12) - gfrankgva: Identity announcement, Part A/B coverage wizard question, Part B file processing manual generation
  3.0.0 (2026-03-12) - gfrankgva: Merged v2.2 (subagent, versioning, templates, recursive tree) with wizard branch (interactive wizard, DS theming, GitHub Pages output, error handling table)
  2.2.0 (2026-02-19) - gfrankgva: Intent matching guidance; author credits
  2.1.0 (2026-02-19) - gfrankgva: Empty service detection; template support; content depth parameter; recursive component tree; per-registration document requirements
  2.0.0 (2026-02-19) - gfrankgva: Subagent architecture to prevent context saturation; pre-flight auth checks; auto-open in browser; manual versioning
  1.0.0 (2026-02-18) - nelsonadpa: Initial skill — single-context fetch + generate
---

# Create a User Manual for an eRegistrations Service

> **Originally developed by Nelson Perez (nelsonadpa@gmail.com) on 18 Feb 2026.**

## When to Use This Skill
- User provides a service ID or pastes a BPA URL
- User asks to "document a service", "create a manual", "generate user guide"
- User says "manual for service [name]", "manual for [service] in [instance]", "manual [service name]"
- User names a specific service (e.g., "make a manual for company registration")

## When NOT to Use This Skill
- User wants ALL services for a country → use `/service-manual-all`
- User wants a technical Excel report → use `/eregistrations-docs`
- User says "document Lesotho" or "all services" → use `/service-manual-all`

---

## Step 0: Interactive Wizard

**This step runs BEFORE any data collection.**

### Identity Announcement

Before presenting the wizard questions, say:

> **Single Service Manual Generator** — I'll create a detailed HTML user manual for one specific eRegistrations service. If you meant to document ALL services in an instance, stop me and use `/service-manual-all` instead.

Then use the `AskUserQuestion` tool to present all five questions in a single call.

### Question 1: UI Style

- **Header**: `UI Style`
- **Question**: `Which visual style should the manual use?`
- **Options**:
  1. **Label**: `DS Match (Recommended)` — **Description**: `Extract design from the live DS site (e.g., lesotho.eregistrations.dev) to match colors, fonts, logos exactly`
  2. **Label**: `Basic` — **Description**: `Clean built-in styling — fast, no external dependencies`
  3. **Label**: `Custom URL` — **Description**: `Provide any website URL and we'll extract its design system`

### Question 2: Content Depth

- **Header**: `Detail level`
- **Question**: `How detailed should the manual be?`
- **Options**:
  1. **Label**: `Standard (Recommended)` — **Description**: `All sections with moderate detail — good for most users (~1200 lines)`
  2. **Label**: `Quick` — **Description**: `Overview, requirements, and basic steps only (~500 lines)`
  3. **Label**: `Detailed` — **Description**: `Full field-level reference tables, all determinant logic explained (~1800 lines)`

### Question 3: Coverage

- **Header**: `Coverage`
- **Question**: `What should the manual cover?`
- **Options**:
  1. **Label**: `Part A only (Recommended)` — **Description**: `Document the applicant form only — what citizens see and fill in`
  2. **Label**: `Part A + Part B` — **Description**: `Also document the processing side — what each government desk sees, reviews, and decides. Generates a separate Part B file.`

### Question 4: Form Illustrations

- **Header**: `Form illustrations`
- **Question**: `How should the form be illustrated in the manual?`
- **Options**:
  1. **Label**: `Generated mockups (Recommended)` — **Description**: `CSS-based form mockups generated from the form structure data — fast, no browser needed`
  2. **Label**: `Screenshots` — **Description**: `Real screenshots captured from the live DS portal using Playwright — authentic but slower, requires DS access`
  3. **Label**: `Both` — **Description**: `Generate TWO versions of the manual: one with mockups, one with screenshots`

### Question 5: Output

- **Header**: `Output`
- **Question**: `Where should the manual be saved?`
- **Options**:
  1. **Label**: `Local file (Recommended)` — **Description**: `Save HTML file in the current working directory`
  2. **Label**: `GitHub Pages` — **Description**: `Deploy to UNCTAD-eRegistrations/eregistrations-manual repo`
  3. **Label**: `Both` — **Description**: `Save locally AND deploy to GitHub Pages`

After the user answers, store results as `WIZARD_UI_STYLE`, `WIZARD_DEPTH`, `WIZARD_COVERAGE`, `WIZARD_ILLUSTRATIONS`, and `WIZARD_OUTPUT`.

**Follow-up questions (ask in a single follow-up message if needed):**

If `WIZARD_UI_STYLE` is "Custom URL": ask the user for the URL.

If `WIZARD_ILLUSTRATIONS` is "Screenshots" or "Both": ask the user for **DS citizen credentials** — a test account that has existing data (e.g., registered businesses) so screenshots show realistic, populated forms rather than empty fields:
> "For realistic screenshots, I need a citizen account that already has data (e.g., a registered business). Please provide the **username** and **password** for a test citizen account on the DS portal. This account will be used only for Playwright navigation to capture screenshots."

Store as `WIZARD_DS_USERNAME` and `WIZARD_DS_PASSWORD`.

Then proceed to Phase 1.

---

## Inputs

- **Service ID**: `$ARGUMENTS[0]` — if missing, ask the user for it.
- **MCP Server**: `$ARGUMENTS[1]` — if missing, list available servers (`BPA-lesotho`, `BPA-cuba-test`, `BPA-jamaica`) and ask the user which one to use.

## CRITICAL: Read-Only MCP Access

The MCP server is **READ ONLY**. You must:

- **ONLY** use read/list/get/analyze/export operations.
- **NEVER** use create, update, delete, publish, activate, deactivate, or any write operation.
- **NEVER** modify anything in the BPA system.

If you are unsure whether an operation is read-only, do NOT call it.

---

## Phase 1: Pre-flight (Main Context)

Run these checks BEFORE any heavy data fetching.

### 1a. Auth Check

- Call `connection_status` on the MCP server.
- If not authenticated → run `auth_login`, wait for success.
- If server name not found → suggest corrections (common: "BPA-lesotho2" should be "BPA-lesotho"). List available servers.

### 1b. Validate Service

- Call `service_get(service_id)` to confirm it exists.
- Get the service name, description, and status.
- If not found → tell user and stop.

### 1c. Form Complexity & Empty-Service Detection

- Call `form_get(service_id)` to get component count.
  - This tells us the complexity (small: <50 components, medium: 50-150, large: 150+).
- Also call `role_list(service_id)` and `registration_list(service_id)`.
- A service is **empty** if `component_count <= 1` (form has no real fields).
  - If empty: warn "Service '{name}' appears to be empty. Marking as Coming Soon." **STOP**.
  - If `component_count` is 2–5: stub or minimal — warn and ask whether to proceed.
  - If `component_count > 5`: proceed normally.

### 1d. Report to User

"Found service: {name}. {component_count} form components, {role_count} roles. Generating manual ({WIZARD_DEPTH} depth)..."

---

## Phase 2: Template Preparation (Main Context)

Extract the brand tokens **once** in main context and write them to a reusable `TEMPLATE.html` file. The subagent in Phase 3 reads this file instead of re-extracting on every run. This mirrors `service-manual-all` Phase 2 so the two skills share the same recipe.

**DS URL:** Before extraction, call `connection_status` on the MCP server to get the `ds_url`. Fall back to `https://{country_slug}.eregistrations.dev`.

**Template path:** `{working_directory}/{country_slug}-TEMPLATE.html` where `country_slug` is derived from the MCP server name (e.g., `BPA-lesotho` → `lesotho`, `BPA-jamaica` → `jamaica`).

### Skip if cached

If `{country_slug}-TEMPLATE.html` already exists in the working directory, tell the user "Found existing template, will reuse it" and skip extraction. Otherwise run the strategies below in order — fall back to the next if the previous yields no usable tokens.

### Strategy 1 — Bundled-CSS probe (works for Vite/React/Angular SPAs)

Most eRegistrations DS sites are SPAs. WebFetch sees an empty shell and returns nulls. Curl the bundled stylesheet directly:

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
- **JSEZA / Jamaica SEZ** (`jseza.eregistrations.dev`): header `#ffd740` brand yellow + text `#1b1b1b`, primary `#c79500`, accent `#009688`, background `#fffdf4`, Montserrat (display) + Inter (body). Extracted 2026-05-22.

If no known instance matches, use Basic styling: `#1a56db` primary, `#f9fafb` background, `#111827` text, system font stack.

### Write TEMPLATE.html

Write the template to `{working_directory}/{country_slug}-TEMPLATE.html` containing:
- A complete `<style>` block with the extracted tokens as CSS custom properties
- A header template (logo + country name + brand bar)
- A footer template
- Placeholders: `{{TITLE}}`, `{{CONTENT}}`, `{{TOC}}`, `{{VERSION}}`

The template is the design shell only — the subagent fills in the manual content.

Report: "Brand extraction via {Strategy 1/2/3}: header={header_bg}, primary={primary_color}, font={font_family}. Template at {template_path}." If using fallback tokens, say so explicitly.

Store `template_path` for the subagent.

---

## Phase 3: Generate Manual (DELEGATE TO SUBAGENT)

**CRITICAL: Do NOT fetch detailed service data (field_list, determinant_list, etc.) in the main context.** This is what causes context saturation. Instead, spawn a Task subagent.

Use the Agent tool with:
- `subagent_type`: `"general-purpose"`
- `description`: `"Generate service manual HTML"`

Pass this prompt to the subagent (fill in actual values for service_id, mcp_server, service_name, working_directory, wizard_ui_style, wizard_depth, wizard_illustrations, ds_url, template_path, and wizard_output):

~~~
You are generating an HTML user manual for an eRegistrations service.

**Service ID**: {service_id}
**MCP Server**: {mcp_server} (use MCP tools prefixed with mcp__{mcp_server}__)
**Service Name**: {service_name}
**Output file (Part A)**: {working_directory}/{service-slug}.html
**Output file (Part B)**: {working_directory}/{service-slug}-part-b.html (only if WIZARD_COVERAGE includes Part B)
**Screenshots version**: {working_directory}/{service-slug}-screenshots.html (only if WIZARD_ILLUSTRATIONS is "Both")
**Content Depth**: {wizard_depth}
**UI Style**: {wizard_ui_style}
**Coverage**: {wizard_coverage} (either "Part A only" or "Part A + Part B")
**Form Illustrations**: {wizard_illustrations} (either "Generated mockups", "Screenshots", or "Both")
**DS URL**: {ds_url} (e.g., https://services.businessregistrations.gov.ls — only needed if illustrations include screenshots)

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

**Document requirements per registration**: After fetching registration_list, for EACH registration that has an ID, also call:
`mcp__{mcp_server}__documentrequirement_list(registration_id="{registration_id}")`
This gives the actual required documents per registration type. Include these in the Prerequisites section organized by registration type.

**If Coverage is "Part A + Part B"**, also fetch detailed role data:
8. For EACH role from role_list: `mcp__{mcp_server}__role_get(role_id="{role_id}")` — gets formSchema, statuses, description
9. For each role status found in role details: note destination_id and transition names
10. `mcp__{mcp_server}__componentbehaviour_list(service_id="{service_id}")` — component behaviours for role form logic

### Step 2: Map the Form Structure

From form_get, identify:
- **Top-level panels** = tabs (e.g., "Company Information", "Shareholders", "Documents")
- **Components within each panel** = fields, grids, uploads, etc.
- **Conditional visibility** = which determinants control which panels/fields

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

Build a mental map of the service flow:

```
Guide answers → determine which tabs appear
  → Tab 1: [list of fields with types]
  → Tab 2: [list of fields with types]
  → ...
  → Submit → Workflow roles process the application
```

### Step 3: Apply Design System

The brand tokens were extracted once in Phase 2 (Template Preparation) and written to `{template_path}`. Read that file first and use its CSS / header / footer / placeholders verbatim.

- **If `template_path` is provided and the file exists:** Read `TEMPLATE.html` and use its `<style>` block, header, and footer. Fill the `{{TITLE}}`, `{{TOC}}`, `{{CONTENT}}`, `{{VERSION}}` placeholders with the manual content you generate in Step 4.
- **If `WIZARD_UI_STYLE` is "Basic"** (no template was created): use built-in clean styling — light theme, system font stack, `#2563EB` accent on white, subtle gray borders, no external font dependencies.

Do NOT re-extract brand tokens in the subagent. If the template is missing or unreadable, fall back to Basic styling and report it.

### Step 4: Generate HTML Manual

Create a **single self-contained HTML file**. All CSS inline in a `<style>` block, no external stylesheets except Google Fonts if the DS uses them.

**Content Depth Controls:**
- **quick**: Overview, prerequisites, basic steps list. No form mockups. No field-level detail. No FAQ. Target ~500 lines of HTML.
- **standard**: All sections below, form mockups, field explanations, FAQ. Target ~1200 lines of HTML.
- **detailed**: Everything in standard PLUS: complete field reference table with every field's type/validation/options, all determinant conditions explained as a reference appendix, full cost formula breakdowns. Target ~1800 lines of HTML.

| Section | Quick | Standard | Detailed |
|---|---|---|---|
| CSS form mockups | Skip | Include | Include with all fields |
| Field explanations | 1 line each | 2–3 lines each | 3–5 lines per field |
| FAQ | Skip | Include (5–8 questions) | Include (10+ questions) |
| Determinant logic | Skip | Explain major conditions | Full condition breakdown |
| Validation rules | Skip | Mention key ones | Complete reference table |
| Field reference tables | Skip | Skip | Include per-tab tables |
| Conditional Logic Reference | Skip | Skip | Full appendix |

**Document Structure (linear — when no major branch detected):**
1. Header — service name, country name, logo (if DS Match)
2. Table of Contents — linked anchors to all sections
3. Introduction — what is this service, who needs it, what you'll get
4. Prerequisites — documents/information to gather before starting (organized by registration type using document requirements data)
5. Step-by-step sections — one per form tab:
   a. Step number + tab name as heading
   b. CSS form mockup mimicking the real interface (skip for `quick` depth)
   c. Plain-language explanation of every field (summary only for `quick` depth)
   d. Tips, examples, common mistakes
6. Review & Submit — what happens when you click submit
7. After Submission — workflow roles, what each reviewer does, expected timeline
8. Costs & Fees — fee breakdown (if any; full formula detail for `detailed` depth)
9. FAQ — common questions and answers (skip for `quick` depth)
10. Field Reference Table (only for `detailed` depth — every field with type, validation rules, options)
11. Conditional Logic Reference (only for `detailed` depth — all determinant conditions explained)

**Document Structure (branch-aware — when major branch detected via Step 2b):**
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
- Give **realistic examples** using locally appropriate names/context
- Use **"you" and "your"** — speak directly to the reader
- Mention **common mistakes** and how to avoid them
- Be encouraging: "Don't worry if you're not sure — you can save your progress and come back later."

For each field or section, provide:

| Aspect | What to write |
|---|---|
| **What it is** | Plain language description of the field |
| **Why it's needed** | Legal or practical reason for collecting this data |
| **How to fill it** | Specific guidance with concrete examples |
| **Common errors** | What people frequently get wrong |
| **Conditional fields** | "This only appears if you selected X" |

Use determinant data to explain conditional logic in human terms:
- "If you selected 'Company' as your business type, you'll see additional tabs for Shareholders and Directors."
- "If you are a foreign national, a Business Permit section will appear after the Personal Information tab."

### Form Illustrations

The approach depends on the `Form Illustrations` setting:

**If "Generated mockups":** Use CSS mockups (skip for `quick` depth) — create styled mockups resembling the real form:
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

All CSS must be in the `<style>` block. Include styles for:
- `.form-mockup` container with border and border-radius
- `.form-mockup-bar` header bar with background color
- `.form-mockup-tabs` tab strip
- `.mtab` and `.mtab.active` tab styling
- `.form-mockup-body` content area
- `.mock-field` with label and input representation
- `.mock-input`, `.mock-select`, `.mock-radio`, `.mock-upload`, `.mock-grid`, `.mock-checkbox`, `.mock-date`, `.mock-signature`
- Required field indicator (red asterisk)
- Conditional field indicator (dashed border or icon)

**Component Type Mapping:**

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

**If "Screenshots":** Capture real screenshots from the live DS portal using Playwright (skip for `quick` depth):

1. **Navigate to DS**: Use `mcp__playwright__browser_navigate` to go to `{ds_url}/services/{service_id}`
2. **Handle login**: If redirected to a login page, use `mcp__playwright__browser_fill_form` with username=`{wizard_ds_username}` and password=`{wizard_ds_password}`, then click Login
3. **For each form tab** (Guide, Form sub-tabs, Documents, Payment, Send):
   a. Click the tab using `mcp__playwright__browser_click`
   b. Wait for content to load using `mcp__playwright__browser_wait_for`
   c. Take a viewport screenshot with `mcp__playwright__browser_take_screenshot`
   d. If the form content extends below the viewport, scroll down and take additional screenshots — find clean cut points between form sections (never cut mid-field or mid-component)
   e. Save each screenshot to `{working_directory}/screenshots/` as `{tab-slug}-{n}.png`
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
- `{service-slug}.html` — uses CSS generated mockups (follow "Generated mockups" instructions above)
- `{service-slug}-screenshots.html` — uses real screenshots (follow "Screenshots" instructions above)
Both files share the same field explanations, text content, structure, and styling — only the form illustration method differs. Generate the mockup version first, then duplicate it and replace the mockup `<div>` elements with `<img>` screenshot elements.

**HTML Requirements:**
- Self-contained — all CSS inline in style tag
- Responsive — desktop and mobile
- Professional styling
- Print-friendly
- Country-appropriate branding colors (from design system step)

**Manual Versioning (REQUIRED):**
Every generated manual MUST include a version block in the HTML footer:
```html
<footer class="manual-version">
  <p>Manual v1.0 — Generated {YYYY-MM-DD HH:MM UTC} — Source: {mcp_server}/{service_id}</p>
  <p>Generated by /service-manual skill v3.5.1</p>
</footer>
```
Use the current date/time when generating. First generation is always v1.0. If a manual already exists at the output path, read its version number and increment (v1.0 → v1.1).

### Step 5: Write File

Write the HTML file using the Write tool to: {working_directory}/{service-slug}.html

Return ONLY this summary (do NOT return HTML content):
- file_path: the path written
- service_name: name of the service
- tabs_count: number of form tabs documented
- fields_count: number of fields documented
- file_size_kb: approximate file size
- content_depth: the depth used
- ui_style: the style used
- part_b_generated: true/false
- part_b_file_path: path to Part B file (if generated)
- part_b_desks_count: number of desks documented (if generated)

### Step 6: Generate Part B HTML (Only if Coverage is "Part A + Part B")

**Skip this step entirely if coverage is "Part A only".**

Create a SEPARATE HTML file: {working_directory}/{service-slug}-part-b.html

Use the same CSS/design system as the Part A manual for visual consistency.

**Part B Document Structure:**

1. **Header** — "{Service Name} — File Processing Manual (Part B)", with link back to Part A manual
2. **Table of Contents**
3. **Workflow Overview — BPA-canvas swimlane (REQUIRED)**

   Render the role graph as a column-grid swimlane that **mirrors the BPA designer canvas**: columns = workflow stages, cards stacked inside a column = roles that run **in parallel**. This is the format SEZ / agency managers recognise.

   **Source data:** `role_list(include_details=true)` gives every role's `sort_order`, `start_role`, `role_type`, and the `destinations[]` on each status (the `FileValidatedStatus` destination is the happy-path next role). The full BPA canvas is reconstructible from this.

   **Build the columns:**
   - Sort roles by `sort_order`. Roles sharing the same `sort_order` form one column. Trace `FileValidatedStatus.destination_id` chains to verify the column ordering matches the actual transitions.
   - Post-decision chains often share a single high `sort_order` (e.g., 299) and are linear, not parallel — render those as a SECONDARY swimlane below the main one (titled e.g., "After pre-approval — license issuance") OR omit if not requested. Do NOT pad the main swimlane with a long linear tail.
   - The Applicant role and dangling/amendment roles (e.g., "Documents check (Type revision)", "NOC appeal") are NOT part of the main happy path — surface them in a separate "Side branches" section, not the main columns.

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

   **CSS (paste into the page's `<style>` block):**
   ```css
   .flowchart-wrap {
     background: var(--card-bg, #fff);
     border: 1px solid var(--border, #e7e3d4);
     border-radius: 8px;
     padding: 28px 24px;
     overflow-x: auto;
     /* break out of the article width so all stages fit */
     width: calc(100vw - 48px);
     max-width: 1640px;
     margin-left: 50%;
     transform: translateX(-50%);
     position: relative;
   }
   .swimlane {
     display: grid;
     grid-template-columns: repeat({N}, minmax(155px, 1fr));   /* {N} = number of stages */
     gap: 18px;
     align-items: start;
     min-width: 1400px;
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

   **Actor badge palette** — assign one class per distinct institution. Use soft tinted backgrounds compatible with the page's brand. Defaults:
   ```css
   .actor-jseza    { background: #fff3b8; color: #6b4a00; }   /* internal authority — gold */
   .actor-jca      { background: #d8ece1; color: #167b5b; }   /* customs — green */
   .actor-taj      { background: #fde0c2; color: #8a4a0d; }   /* tax — amber */
   .actor-mofps    { background: #e3dcef; color: #4d3678; }   /* finance — purple */
   .actor-mic      { background: #f0dadc; color: #7a2e3c; }   /* ministry — brick */
   .actor-applicant{ background: #ece8db; color: #5a5240; }   /* applicant — neutral */
   .actor-system   { background: #cfe7e3; color: #195854; }   /* bot — teal */
   ```
   Rename the classes to match the actual institutions in the service. Keep the visual palette (one institution = one consistent colour across the whole document).

   **What to write under the swimlane:** one paragraph stating "Columns are stages; cards stacked in a column run in parallel; per-agency lanes (e.g., Legal, Business, Technical, Compliance) each carry their own evaluation → approval — evaluations and approvals are not sequential phases."

   **Anti-patterns:**
   - Do NOT use Mermaid for this overview — Mermaid auto-layout does not produce the column-grid SEZ managers recognise.
   - Do NOT collapse parallel evaluations into a single "Parallel evaluations" abstract node. Show each lane.
   - Do NOT include the Applicant role as a column — it's the citizen side, not Part B.
4. **Per-Desk Sections** — one section per role, in workflow order (use sort_order_number):
   a. **Desk name** and description
   b. **What arrives at this desk** — from which previous role/status
   c. **Role Form** — CSS mockup of the role's formSchema showing what the reviewer sees:
      - Parse the role's `formSchema` to identify visible fields, panels, sections
      - Distinguish read-only fields (applicant data shown for reference) from editable fields (reviewer inputs)
      - Note any fields unique to this desk that don't appear in the applicant form
      - Use the same `.form-mockup` CSS classes as Part A for consistency
   d. **Available Actions** — list each role status:
      - Status name (e.g., "FILE VALIDATED", "SEND BACK", "REJECT")
      - Destination: which role/desk receives the file next
      - Any determinant conditions on the status (when is this action available?)
   e. **Automations** — bots attached to this role:
      - Bot name, type (data/document/internal/message), category
      - What it does (read/create/update data, generate documents, send notifications)
      - When it triggers
   f. **Reviewer Tips** — practical guidance for officers at this desk
5. **Bot Reference Table** — summary of all bots across all desks:

   | Bot Name | Type | Desk | Trigger | What It Does |
   |---|---|---|---|---|

6. **Footer** — version, generation timestamp, link to Part A

**Writing Style for Part B:**
- Write for **GOVERNMENT OFFICERS**, not citizens
- Professional, procedural language
- Explain what to check and verify at each step
- Use "you" addressing the reviewer/officer
- Reference applicant data: "The applicant's company name appears in the header"
- Include processing expectations: "Typical review time: 2-3 business days"

**CSS Form Mockups for Role Forms:**
Use the same `.form-mockup` classes as Part A. Additionally:
- `.readonly-field` — gray background, label says "(Read-only)" for applicant data shown to reviewer
- `.reviewer-field` — highlighted border for fields the reviewer must fill in
- `.action-buttons` — styled buttons showing available status transitions

Write the Part B file using the Write tool. Update the return summary above to include Part B info.
~~~

---

## Phase 4: Deliver (Main Context)

After the subagent completes:

1. Report the summary to the user (service name, tabs, fields, depth, style, file path).
2. If Part B was generated, also report: Part B file path, number of desks documented.

3. **Output based on `WIZARD_OUTPUT`:**

   **If "Local file":**
   - Open the Part A file in the browser: `open {filename}.html` (via Bash tool).
   - If Part B was generated, also open it: `open {filename}-part-b.html`.
   - Tell the user next steps: "To publish, push to the eregistrations-manual GitHub Pages repo."

   **If "GitHub Pages":**
   1. Clone or pull `UNCTAD-eRegistrations/eregistrations-manual` (use `gh-pages` branch).
   2. Create the country directory if it doesn't exist (e.g., `lesotho/`).
   3. Copy the Part A HTML file into the country directory. If Part B was generated, copy it too.
   4. Commit with message: `Add manual: {service-name} ({country})`.
   5. Push to `gh-pages` branch.
   6. **Verify deployment** — wait 15s for CDN propagation, then check the URL:
      ```bash
      sleep 15
      curl -s -o /dev/null -w "%{http_code}" https://unctad-eregistrations.github.io/eregistrations-manual/{country}/{slug}.html
      ```
      Expected: HTTP 200. If not 200, wait another 15s and retry once. Report status (live / not yet propagated / failed).
   7. Report the live URL: `https://unctad-eregistrations.github.io/eregistrations-manual/{country}/{slug}.html`. If Part B was generated, also report its URL.

   **If "Both":**
   Do both of the above in sequence.

---

## Error Handling

| Situation | Action |
|---|---|
| MCP server unreachable | Report error, suggest checking server name. List available servers. |
| Service ID not found | Report error, suggest listing services with `service_list()`. |
| Empty service (component_count <= 1) | Report "Coming Soon" status. Do NOT generate a manual. |
| GitHub push fails | Save locally. Report the push error. Suggest manual push. |
| File write fails | Report the error with the file path. Suggest alternative directory. |

---

## Example Invocations

```
/service-manual abc-123-uuid BPA-lesotho
/service-manual def-456-uuid BPA-cuba-test
/service-manual                              ← will prompt for service ID and server
```
