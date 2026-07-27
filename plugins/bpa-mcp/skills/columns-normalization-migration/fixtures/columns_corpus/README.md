# Columns normalization fixture corpus

Language-neutral pure-JSON `{input, expected}` reference pairs for the
column-layout normalize-to-12 rules (TOBE-18003 / DS-Frontend#172). Each file
covers one live-found edge case: textarea `rows:3` int round-trip,
already-normalized rows, keyless / duplicate paths, width 1–12 bounds,
editgrid-inner, `adjust-columns` customClass, over-12, and the malformed /
null-width fail-loud path.

## Conventions (so ports can assert against the same reference)

- Pure JSON only: explicit numeric types (`rows` stays integer `3`, never
  `3.0`), no `NaN` / `Infinity`, no Python reprs.
- Comparisons must be order-independent — do not rely on dict insertion order.
- Every normalized `expected` set of column widths sums to exactly 12.
- Malformed fixtures declare a fail-loud expectation (`error` / `raises`) so
  ports assert the walker raises rather than emitting a corrupt plan.

## ⚠ Placement / relocation note (still a cross-language contract)

The corpus used to live inside the `mcp_eregistrations_bpa` package — a
**consumer** of the rules, not their owner. That inverted the dependency
direction: the ports would have had to depend on an MCP server package to get
their reference data.

That inversion is now fixed. The corpus lives next to the
`columns-normalization-migration` skill, which owns the normalize-to-12 logic
(`scripts/columns_logic.py` and friends). Reference data and reference
implementation ship together.

**The warning is reduced, not gone.** This corpus is still a **cross-language
contract**, and it is still housed with exactly one implementation — the
Python one. If the planned ports ever ship:

- SQL detector **TOBE-18007** (BPA-backend)
- Builder TypeScript **TOBE-18006** (BPA-frontend)

…then two more codebases depend on fixtures that live in a third repo's plugin
directory. At that point the honest move is to promote the corpus to a neutral
shared home — the **NOVA** knowledge base or a dedicated shared fixtures
package — and have all three implementations vendor it. Until a second port
exists, promoting it early would be ceremony; treat this directory as the
source of truth, and keep any vendored copy in sync with it.
