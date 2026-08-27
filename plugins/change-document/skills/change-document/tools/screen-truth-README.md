# Screen truth

**What it is.** One script that reads a BPA container's raw JSON and prints what the citizen's screen shows. Born 21-08-2026, after eight fidelity errors in one contract drawing of the Lesotho dashboard, every one of them caused by drawing from the form definition instead of from what renders.

**How to use it.**

1. `form_component_get(service_id=..., component_key=<the outermost container>, summary=False)`. The harness saves the large response to a file; note the path.
2. `python3 screen_truth.py <that file>`
3. Draw from the report. Then read `componentbehaviour_get_by_component` for every effect it names, because the report cannot see determinants.

**The rule that makes it worth running.** Anything absent from the report does not go in the drawing. Anything in the report that the drawing leaves out is justified in one line of commentary.

## What it catches, and what each one cost

| Trap | What it looks like | What it cost on 21-08 |
|---|---|---|
| `headerComponents` | A button on a block's title line. No tree walk reports it: `form_get` returned 202 components without it and `form_component_get` answered FORM_003. | Drew the wrong button, then told Frank the real one could not be found. Two corrections. |
| `hidden:true` inside a grid | Renew, Update and the status pill all carry it and all render. | Declared a visible button hidden, published a review finding on it, retracted the finding. |
| `hidden:true` outside a grid | `applicantType3` really is hidden. | Drew a Type column that does not exist. |
| `fieldsShownInGrid` | The authority on what a row shows. | Would have prevented the Type column on its own. |
| `collapsedDS` with no `collapsed:false` in the effect | The block renders shut. Two sibling blocks on one dashboard differ. | Drew an open grid where the citizen meets a closed strip. |
| `hide-if-empty` | Per grid, not a platform default. | Drew headers over nothing where the grid hides itself, and nothing where it does not. |
| Ancestor switched off | A child cannot render inside a block that is off. | Placed an empty-state invitation inside a block that only appears when the list is not empty, so it could never reach its audience. |
| Drawing classes | `datagrid-hide-column-label`, `remove-vertical-lines`. | Drew a column header that does not exist, and a grey rule that does not exist. |

## What it deliberately does not do

It does not read determinants: the raw carries effect ids, not their conditions. Every `renders IF its effect fires` line is a prompt to run `componentbehaviour_get_by_component` and then `determinant_get`. **A badge tooltip is written from that read, never from the effect's existence.** Writing a rule you have not read is how an invented Companies determinant reached a drawing on 21-08 and had to be corrected one minute later.

## Its own bug, kept as a lesson

The first version of this script repeated the very mistake it exists to prevent: it reported every `hidden:true` component inside a grid as not rendered. It was corrected the same hour. A tool written from the same wrong belief carries the belief; test it against a case you already know the answer to before trusting it.
