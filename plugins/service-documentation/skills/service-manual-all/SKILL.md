---
name: service-manual-all
description: >
  Batch-generates citizen-facing HTML user manuals for ALL services of an eRegistrations
  instance, plus a browsable catalog index page. Use when the user wants to generate all
  service manuals, create a full documentation site, or produce a complete service catalog
  for an eRegistrations country instance.
license: UNCTAD-Internal
compatibility: Requires an authenticated BPA MCP server connection.
allowed-tools: Read, Write, Bash(open *), Bash(mkdir -p *)
metadata:
  version: "1.5.0"
  version-date: "2026-02-19"
  author: "Frank Grozel (gfrankgva)"
  argument-hint: "[instance]"
  disable-model-invocation: "true"
---

# Generate All Service Manuals for an eRegistrations Instance

Generate user manuals for every citizen-facing service in a country instance, plus a catalog index page.

## Inputs

- **Instance**: `$ARGUMENTS[0]`

## Discovering Available BPA Instances

If **Instance** is not provided, discover which instance profiles are registered:

1. Call `mcp__BPA__instance_list()` to get all registered profiles.
2. Present the results to the user:
   > "Found {N} BPA instance(s):
   > 1. **{name}** → {url}
   > Which one would you like to use?"
3. Use the chosen `{name}` as the instance for all subsequent calls (pass `instance="{name}"` to every `mcp__BPA__*` tool).

## CRITICAL RULES

- **READ ONLY** — NEVER use create/update/delete MCP operations
- **Use subagents for each manual** — NEVER fetch service detail data in main context
- Main context handles ONLY: service list, filtering, catalog index, orchestration
- This prevents context saturation which killed previous sessions

## Phase 1: Pre-flight (Main Context)

1. **Check auth**: Call `mcp__BPA__connection_status(instance="{instance}")` → `mcp__BPA__auth_login(instance="{instance}")` if needed
   - If instance not found → run the discovery procedure above
2. **List all services**: Call `mcp__BPA__service_list(instance="{instance}", limit=100)`
3. **Filter citizen-facing services** — exclude:
   - Names containing: "copy", "test", "prueba", "copia" (case-insensitive)
   - Names containing: "Registrar only", "SWR", "BO Registry" (internal admin)
   - Names containing personal names like "darek", "ando" (dev testing)
   - "Basic BPA" (template)
   - Any service with status "inactive" or "draft"
4. **Report to user**: "Found {N} citizen-facing services:"
   - List them numbered with name and ID
   - Ask: "Proceed with all, or exclude any?"

Wait for user confirmation before proceeding.

## Phase 1.5: Visual Identity (Main Context)

Ask the user:
> "Please provide the URL of the website whose visual identity should be reproduced in the manuals
> (logo, header, colors, fonts). Example: https://lesotho.eregistrations.dev
> Press Enter to skip and use neutral defaults."

Store the answer as `brand_url`. Then:

- **If provided** → call WebFetch on `brand_url` with this prompt:
  > "Extract the visual identity of this website as JSON with these exact keys:
  > logo_url (src of the main header logo img, or null),
  > header_bg (hex color of the top navigation bar background),
  > primary_color (hex color used for buttons and primary actions),
  > header_text (hex color of text/icons on the header),
  > font_family (main body font name, e.g. 'Inter' or 'Roboto', or null if not identifiable),
  > accent_color (hex of any secondary highlight color, or same as primary_color if none).
  > Return only the JSON object, no explanation."

  Store the parsed result as `brand`. If WebFetch fails or returns incomplete values, fall back to defaults for missing keys.

- **If skipped** → use defaults:
  `brand = { logo_url: null, header_bg: "#003580", primary_color: "#1a73e8", header_text: "#ffffff", font_family: null, accent_color: "#b8860b" }`

Report: "Visual identity: header={brand.header_bg}, primary={brand.primary_color}, font={brand.font_family || 'default'}"

## Phase 2: Create Output Directory (Main Context)

```bash
mkdir -p {country-slug}
```

Where country-slug is a short identifier for the instance (e.g., derive from the BPA URL or service names — ask the user if ambiguous).

## Phase 3: Track Progress (Main Context)

Before spawning subagents, print a numbered list of all services to be processed:
```
Processing {N} services:
1. {service_name} (id={service_id}) → {country-slug}/{service-slug}/index.html
2. ...
```
Track results in a local list as subagents complete. Print a running tally after each batch.

## Phase 4: Generate Manuals (Subagents — PARALLEL batches)

For EACH citizen-facing service, spawn a Task subagent with this COMPLETE prompt (fill in {service_id}, {instance}, {service_name}, {working_directory}, {service-slug} with actual values before spawning):

~~~
You are generating an HTML user manual for an eRegistrations service.

**Service ID**: {service_id}
**Instance**: {instance} (pass `instance="{instance}"` to all `mcp__BPA__*` tools)
**Service Name**: {service_name}
**Output file**: {working_directory}/{service-slug}/index.html
**Visual Identity**:
- Logo URL: {brand.logo_url}
- Header background: {brand.header_bg}
- Primary/button color: {brand.primary_color}
- Header text color: {brand.header_text}
- Font family: {brand.font_family}
- Accent color: {brand.accent_color}

## CRITICAL: No Hallucination

Only document what actually exists in the data returned by the MCP tools.
- Do NOT invent fields, steps, roles, procedures, costs, or requirements
- Do NOT fill in "typical" content based on what a service like this might have
- If a section has no data (e.g. no roles, no costs), write: "No information available for this section."
- If the total form component count is ≤ 5, include a prominent warning banner in the manual:
  "⚠️ This service has very limited form data. This manual may be incomplete or inaccurate."

### Step 1: Fetch ALL Data

Call these MCP tools in parallel:
1. `mcp__BPA__form_get(service_id="{service_id}", instance="{instance}")` — full form structure
2. `mcp__BPA__field_list(service_id="{service_id}", instance="{instance}", limit=500)` — all fields
3. `mcp__BPA__determinant_list(service_id="{service_id}", instance="{instance}")` — conditional logic
4. `mcp__BPA__role_list(service_id="{service_id}", instance="{instance}")` — workflow roles
5. `mcp__BPA__bot_list(service_id="{service_id}", instance="{instance}")` — automations
6. `mcp__BPA__analyze_service(service_id="{service_id}", instance="{instance}")` — overview with costs/requirements
7. `mcp__BPA__registration_list(service_id="{service_id}", instance="{instance}")` — registrations

If field_list has `has_more=true`, fetch additional pages with offset.

### Step 2: Map the Form Structure

From form_get, identify:
- **Top-level panels** = tabs (e.g., "Company", "Shareholders", "Documents")
- **Components within each panel** = fields, grids, uploads, radio buttons
- **Conditional visibility** from determinants (which fields/panels depend on other answers)

### Step 3: Generate HTML Manual

Create a single self-contained HTML file with:

**Structure:**
1. Header with service name and country branding
2. Table of Contents with anchor links
3. Introduction — what this service is, who needs it
4. Prerequisites — documents/information to gather before starting
5. Step-by-step sections — one per form tab:
   - Step number + tab name
   - CSS form mockup mimicking the real interface
   - Plain-language explanation of every field
   - Tips, examples, common mistakes
6. Review & Submit section
7. What happens after submission (workflow roles)
8. Costs/fees breakdown
9. FAQ (8-10 questions)

**Writing Style:**
- Write for citizens, NOT administrators
- Simple, clear language — no jargon
- Explain WHY each field is needed
- Give realistic examples using local names/context
- Use "you" and "your"
- Mention common mistakes

**CSS Form Mockups** — create styled mockups resembling the real form:
```html
<div class="form-mockup">
  <div class="form-mockup-bar"><span class="bar-title">{Service Name}</span></div>
  <div class="form-mockup-tabs">
    <span class="mtab">Tab 1</span>
    <span class="mtab active">Current Tab</span>
  </div>
  <div class="form-mockup-body">
    <!-- mock-field, mock-input, mock-select, mock-radio, mock-upload, mock-grid -->
  </div>
</div>
```

**Component Type Mapping:**
| Form.io Type | Manual Description |
|---|---|
| textfield | "Type your answer in the text box" |
| textarea | "Enter a detailed description" |
| select | "Select from the dropdown list" |
| radio | "Choose one option" |
| checkbox | "Tick the box if applicable" |
| datagrid | "Click 'Add' to add each entry" |
| file | "Click to upload your document (PDF, JPG)" |
| datetime | "Select the date from the calendar" |
| number | "Enter the number" |
| currency | "Enter the amount" |
| signature | "Sign using your mouse or finger" |
| content | (informational — explain what it tells the user) |
| panel | (becomes a section in the manual) |

**HTML Requirements:**
- Self-contained — all CSS inline in style tag
- Responsive — desktop and mobile
- Professional styling, light theme
- Print-friendly
- Reproduce the visual identity faithfully:
  - Header: background={brand.header_bg}, text/icons={brand.header_text}
  - If logo_url is not null: display the logo in the header using an `<img>` tag
  - Buttons, links, step counters: {brand.primary_color}
  - Callout borders, highlights, badges: {brand.accent_color}
  - Body font: load {brand.font_family} from Google Fonts if not null, else use system sans-serif

**Manual Versioning (REQUIRED):**
Every generated manual MUST include a version block in the HTML footer:
```html
<footer class="manual-version">
  <p>Manual v1.0 — Generated {YYYY-MM-DD HH:MM UTC} — Source: BPA/{instance}/{service_id}</p>
  <p>Generated by /service-manual-all skill v1.5.0</p>
</footer>
```
Use the current date/time when generating. First generation is always v1.0. If a manual already exists at the output path, read its version number and increment (v1.0 → v1.1).

### Step 4: Write File

Create the output directory and write the file:
```bash
mkdir -p {working_directory}/{service-slug}
```
Write the HTML using the Write tool to: {working_directory}/{service-slug}/index.html

Return ONLY this summary (do NOT return HTML content):
- file_path: the path written
- service_name: name of the service
- tabs_count: number of form tabs documented
- fields_count: number of fields documented
- file_size_kb: approximate file size
- status: "success" or "failed"
- error: error message if failed
~~~

**Launch 3-4 subagents in parallel** (multiple Task tool calls in one message). When a batch completes, update your running tally and launch the next batch.

After each subagent completes, record the result (success/failure, tabs_count, fields_count) in your local tracking list.

## Phase 5: Generate Catalog Index (Main Context)

After all manuals are done, generate `{country-slug}/index.html` — a catalog page.

The catalog should include:
- Country header with branding (use brand.header_bg, brand.header_text, logo if brand.logo_url is not null)
- Grid of service cards, each with:
  - Service name
  - Brief description
  - Number of steps/fields
  - Link to the manual (`{service-slug}/index.html`)
  - Status badge: green "Available" if manual exists, gray "Coming soon" if failed
- Professional responsive styling matching individual manuals
- Same visual identity as the individual manuals (brand.primary_color, brand.accent_color, brand.font_family)

This is the ONLY HTML generated in main context (small file, ~100-150 lines).

## Phase 6: Deliver (Main Context)

1. Open catalog in browser: `open {country-slug}/index.html` (Bash)
2. Report summary table:
   | Service | Status | Tabs | Fields | File |
   |---------|--------|------|--------|------|
   | ... | ... | ... | ... | ... |
3. Totals: {success}/{total} services documented

## Phase 7: Publish to GitHub Pages (Optional)

If user says "publish":
1. Clone/pull `eregistrations-manual` repo
2. Copy `{country-slug}/` folder into the repo
3. Commit and push to gh-pages branch
4. Report live URL: `https://unctad-eregistrations.github.io/eregistrations-manual/{country-slug}/`

## Changelog

- 1.5.0 (2026-02-19) gfrankgva — Multi-instance migration: instance_list discovery, mcp__BPA__ prefix with instance= param; replace TaskCreate/TaskUpdate with local tally
- 1.4.0 (2026-02-19) gfrankgva — Phase 1.5: ask user for brand URL, fetch visual identity (logo, colors, font), pass to subagents and catalog
- 1.3.0 (2026-02-19) gfrankgva — Discovery via server_info tool; dropped ! injection and config file parsing
- 1.2.0 (2026-02-19) gfrankgva — Generic BPA MCP discovery via ! injection; removed hardcoded server names
- 1.1.0 (2026-02-19) gfrankgva — disable-model-invocation true; allowed-tools; inline subagent prompt; replace TodoWrite with TaskCreate/TaskUpdate; no-hallucination rule
- 1.0.0 (2026-02-19) gfrankgva — Initial skill — parallel subagent batch generation with catalog index
