# BPA mockup rendering: canvas-true from a service's JSON

How to render a service's own JSON as a mockup indistinguishable from the live BPA canvas, so the drawing can serve as a change document's contract. Canonized 2026-07-22 from the Lesotho capital-and-shares proposal.

**Use this when** a "where we stand" or "end situation" screen is needed for a change proposal or implementation plan (the `er-implementation-plan` skill), or any time a service's real screen must be drawn faithfully rather than described in prose. Not for a citizen-facing leaflet or a teaching page; those follow their own skills.

**Doctrine:** skill [`er-implementation-plan`](/Users/unctad/.claude/skills/er-implementation-plan/SKILL.md) (the document this method feeds) and memory [`feedback-er-implementation-plan-style.md`](/Users/unctad/.claude/projects/-Users-unctad-Claude/memory/feedback-er-implementation-plan-style.md) (Frank's settled rules; read fully before a first pass). Pattern: [`patterns.md`](/Users/unctad/Claude/2%20-%20eR%20services/knowledge/patterns.md) §"The faithful mockup is the build contract".
**Exemplar:** [`capital-shares-proposal.html`](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/register-a-business/capital-shares-proposal.html), section `<details id="why">`. Precursors: [`specs/rendering-a-canvas-true.html`](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/register-a-business/specs/rendering-a-canvas-true.html), [`specs/capital-shares-real-look.html`](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/register-a-business/specs/capital-shares-real-look.html).
**Kit:** [`tools/bpa-mockup-kit.css`](../tools/bpa-mockup-kit.css); every class named below lives there.

## 0. Two modes: proposal vs contract (decide before drawing)

Two ways to draw, chosen by one question: **does the thing being drawn exist in the live product?**

- **Contract mode (exact-BPA)** — the screen exists, or is the end-state of an approved change to an existing screen. Render canvas-true from a live pull with the kit (steps 1–6 below). This is the mode for implementation plans: the drawing is the build contract. Default for `er-implementation-plan`.
- **Proposal mode (simulated)** — the thing drawn does not exist yet anywhere (a new platform feature, a new option, a product idea). Draw a clean simulated panel that borrows the product's basic look (its header, its panel shapes) but does not claim pixel-truth; its job is to make **what's new** unmissable, typically today-vs-proposed side by side with the new part highlighted. Exemplar: [`internal-bot-switch-mockup.html`](/Users/unctad/Claude/2%20-%20eR%20services/countries/Lesotho/services/register-a-business/internal-bot-switch-mockup.html) (the internal-bot write-mode switch, Frank: "very good", 2026-07-22).

**Who decides:** the session, by the rule above — it announces its pick in one line ("drawing in proposal mode: the switch doesn't exist yet — say 'exact' to override") and asks only when genuinely ambiguous. Frank is not quizzed each time. When a proposal is approved and becomes an implementation plan, the same screen is redrawn in contract mode.

Simulated never means invented style: when proposing a feature inside an existing product, wear that product's chrome (memory `feedback-proposal-mockups-in-real-chrome.md`).

## 1. Pull the section live

`form_component_get` (read-only) on the panel/section, saved to a new dated folder: `exports/<section>-fetch-YYYY-MM-DD/`. Re-pull right before building, not just before drawing; services drift under a shared design (verified 2026-07-22: the Lesotho team added a content block and two validations between a 19 July and a 22 July pull on the same tab). Never describe a component from memory or from an older export.

## 2. Parse the raw tree

Properties that decide the drawing, per component:

- `label` / `workingLabel`: the visible text (workingLabel resolves a mustache label for the canvas; Critical Rule 4 in `VISUAL-DICTIONARY.md`).
- `hideLabel`: draws the label anyway, struck through, with the eye-slash (never omit it, "hidden fields are rendered too", Frank 2026-07-22).
- `hidden`: striped fill on the component's outline.
- `customClasses`: selects a content-box look (`background-blue`, `background-red`) or a component state.
- `validate.required`: the red asterisk.
- `suffix`, `defaultValue`, `disabled`: the unit text, the pre-filled value, and whether the box is the form's own computed grey.
- `columns[].width`: the 12-grid track width (`c3`, `c6`, and so on).
- `html` (on a `content` component): the paragraph or heading text, verbatim.
- The logic ids: `effectsIds` / `behaviourId`, `componentValidationId` + `validationRowIds`, `componentFormulaId` + `formulaRowIds`, `componentActionId`.

## 3. Map JSON to kit classes

| Property | Kit class | What the eye sees |
|---|---|---|
| `label` / `workingLabel` | `.control-label` | Bold label above the field |
| `hideLabel:true` | `.ghost-label` + `.eye-slash` | Same label, struck through, eye-slash icon |
| `hidden:true` | `.bpa-hidden-stripes` | Striped background on the outline |
| `customClasses:["background-blue"]` | `.bpa-info` | Flat blue-tinted box, no left bar |
| `customClasses:["background-red"]` | `.bpa-alert` | Flat red-tinted box, no left bar |
| `validate.required:true` | `.req` | Red asterisk after the label |
| `suffix` | `.bpa-suffix` | Grey unit text beside the input |
| `disabled:true` plus a formula | `.bpa-input.computed` | Grey-filled box, bold value |
| `columns[].width` | `.c3` / `.c6` | Field width on the row (12-grid) |
| `html` (content) | `.bpa-content-text` (+ `.heading`) | Plain paragraph, no box |
| every component | `.bpa-outline` | Dashed outline (the canvas draws this around all components, general rule) |
| `effectsIds` / `behaviourId` | `.bpa-badge.e` | Blue E badge, corner of its own component |
| `componentValidationId` + rows | `.bpa-badge.v` | Pink V badge |
| `componentFormulaId` + rows | `.bpa-badge.f` | Light-blue F badge |
| `componentActionId` | `.bpa-badge.a` | Green A badge |
| `type:"editgrid"`/`"datagrid"` | `.bpa-editgrid` + `.bpa-dg-header` | Salmon dashed wrapper, grey header band |

## 4. The logic overlay

Every logic id becomes a badge (`.bpa-badges` > `.bpa-badge.e/v/f/a`), stacked at its own component's top-right corner, never inline after the label. Each badge carries two things at once: a plain-English `title=` tooltip for a human hovering, and a `data-logic="..."` attribute holding the actual ids for an AI reading the markup. Both facts live on the same element, never one without the other.

The logic's content is reviewable, not just badged: under each drawing, a collapsed "The logic, spelled out" annex lists one line per badge, component, type, plain English, ids, pulled live via `componentformula_get`, `componentbehaviour_get_by_component`, and `determinant_get`. One line reads, for example: "Total shares (F): value per share times number of shares; `componentFormulaId f3f74d80-9a56-313d-9043-cef28e10577a`." For an end-situation screen this annex is agreed like the pixels: the logic is contract too.

## 5. The change overlay (end-situation screens)

Only on the "contract" screen, apply `.chip.new` (blue) or `.chip.modified` (grey) to every changed element, content texts included. A modified field's `.help-text` opens with "Was ..." naming what it replaces. Draw one screen per path (for example ordinary-only vs ordinary-and-preferred); chips mark only what changes in that path. The author never comments inside the screen, no "this draws path X" asides; the paths are shown, not narrated.

## 6. What stays out

Editor chrome (toolbars, trash/gear icons), author comments, and any trace of a design negotiation (an abandoned idea, a "not a field" note, a previous draft's ghost) never appear in the drawing. The one exception: a dashed struck-through ghost is honest only for a component that exists in the live service today and that the change removes.

## Evidence tags used in this guide

"Verified live YYYY-MM-DD" means confirmed via the MCP tool named. "Frank, YYYY-MM-DD" means his explicit correction or ruling. A claim without one of these tags does not belong in a mockup or in this guide.

## Related reading

- [`VISUAL-DICTIONARY.md`](./VISUAL-DICTIONARY.md) §"Component states" and §"Critical Rules": the base rendering rules this kit builds on (fieldset/columns/info-box/alert-box left-bar rules, indicator anchoring).
- [`rosetta-stone.md`](./rosetta-stone.md) Section J: the same visual rules in the designer-vocabulary bridge.
- [`dynamic-logic.md`](./dynamic-logic.md): the three-axis effect reasoning (Activate/Deactivate, Show/Hide, Enable/Disable) behind every E badge.


---

## Take the kit, never copy a plan (21-08-2026)

**The rule.** The CSS for a canvas-true drawing comes from `tools/bpa-mockup-kit.css`. It never comes from the `<style data-specimen>` block of an existing implementation plan, however good that plan is.

**Why.** A delivered plan freezes. It keeps whatever the kit said on the day it shipped, and the kit moves on. Copying it copies its corrections back out.

**What it cost.** On 21-08-2026 the Lesotho recovery change document was built by copying the capital-shares plan's style block. That block still carries `border-left:4px solid rgb(191,197,206)` on `.bpa-fieldset`, an invented left bar the kit dropped on 22-07-2026 with the comment *"canvas-true correction, no invented left bar"*. The drawing therefore showed grey rules down the left of every field group, which BPA does not draw. Frank saw it on the screen and asked what the lines were. Four weeks after the fix, reintroduced in one copy.

**What BPA draws around a fieldset:** nothing but the dashed outline, `.bpa-outline`, `1px dashed rgba(107,114,128,0.5)`, radius 6, padding 10.

**The check before delivering any drawing.** Diff your page's specimen block against the kit. Every difference is either a deliberate, commented addition for this page, or a bug you inherited.
