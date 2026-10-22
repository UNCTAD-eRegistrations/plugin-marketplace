<!-- Journey map template. One file per service. Every line ends with its source:
     `LAW §<section>` OR FORM <component key> OR FLOW <role/registration>.
     Organise by the citizen JOURNEY — not by the form's field order. -->

# Journey map — {{SERVICE}}

**Sources.** `LAW` = {{regulation}} · FORM/FLOW = live BPA service `{{service_id}}` @ `{{instance}}`.
Every claim below traces to a `LAW §…`, a `FORM <component key>`, or a `FLOW <desk>`. Unknowns are marked **confirm**, never invented.

## What it's for (purpose)

- {{one or two plain sentences: what this service does for the citizen}} — `LAW §…` / FORM `…`

## Who it's for (eligibility)

| Condition | Who qualifies / who doesn't | Source |
|---|---|---|
| … | … | `LAW §…` / FORM `…` (determinant) |

## What you provide

| Item | Detail | Source |
|---|---|---|
| {{field / data}} | … | FORM `…` |
| {{document}} | … | FORM `…` (document requirement) / `LAW §…` |

## The journey (steps in order)

1. **{{step / role}}** — {{what happens, who acts}} — FLOW `{{desk/registration}}` / FORM `{{tab}}`
2. **{{step}}** — … — FLOW `…`
   *(the ordered flow from `workflow_graph` — applicant submission → each Part B role → issuance)*

## What you receive

- {{document / record}} — FORM template `{{id}}` (read the actual template, not bot mappings)

## After (obligations)

- {{renewal / display / reporting duty}} — `LAW §…`

## The act vs the system (reconciliation notes)

- **Difference:** {{the law requires X; the service does Y}} — `LAW §…` vs FORM `…`
- **Presentation, not legal text:** {{a design choice stated as such}} — source
- **Over-claim softened:** {{original → gentler wording, same substance}} — `LAW §…`

## Excluded (deliberately, unsourced — do not add without a source)

- {{plausible-but-unsourced claim left out}}
