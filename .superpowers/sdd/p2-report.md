# P2 — ereg-issue test-theater → real guards (2026-06-26)

Branch: feature/ereg-issue (PR #33). Worktree: .claude/worktrees/ereg-issue.

## Fix 1 — real symptom-routing test

**Files changed:** `tests/corpus.json`, `tests/test_routing_table.py`

Each of the 15 corpus entries received a `symptom` field — a realistic
free-text incident report authored so its domain-specific keywords
score highest on the intended routing rule. Example (entry 1):

> "On comores after the 2.18 upgrade a file finalizes immediately and
> never reaches the review desk — the token appears locked and the task
> list for agents stays empty."

This symptom scores 6 on `bpmn-routing-2.18` (`file`, `reach`, `desk`,
`locked`, `finalize`, `finalizes`) vs. ≤1 on any other rule.

New test `test_symptom_routes_to_expected_rule` in `test_routing_table.py`:
- Lowercase-substring matcher scores every routing rule against each symptom.
- Asserts unique winner AND that the winner matches `memory_ref`.
- `_main()` updated to include the new test (standalone `python3 test_routing_table.py`
  also covers it).

**Disambiguation note:** no tie found across all 15 entries. The `file`
keyword in `bpmn-routing-2.18` is the most common false-positive source
(substring of "filepending", "profile", "exported file") but always
loses to the intended rule by ≥4 keyword-score margin.

## Fix 2 — live autopilot enum drift guard

**File created:** `tests/test_autopilot_conformance.py`

`test_enums_match_live_autopilot` inserts
`~/PROJECTS/software-factory/autopilot/src` onto `sys.path` and
imports from `autopilot.triage.{rubric,isc,constraints}`. It asserts
set-equality for all five validator enums:

| Validator constant | Autopilot source | Line(s) |
|---|---|---|
| `_SEVERITY` | `rubric._VALID_SEVERITY` (frozenset) | rubric.py:37 |
| `_SCALE` | `rubric._VALID_SCALE` (frozenset) | rubric.py:40 |
| `_KIND` | `rubric._VALID_KIND` (frozenset) | rubric.py:41-43 |
| `_CLAIM_TYPE` | `isc._VALID_CLAIM_TYPES` (frozenset) | isc.py:54-62 |
| `_CONSTRAINT_KIND` | `get_args(constraints.ConstraintKind)` (Literal) | constraints.py:34 |

Import failure → `pytest.skip(...)` so an offline CI run is never broken.

**Drift guard executed (NOT skipped)** — autopilot is importable on this
machine. All five assertions PASSED: the current validator enums are
exact matches for autopilot's live collections.

## run_all.sh

Added a pytest probe step: tries `python3`, `python3.12`, `python3.11` in
order for the first that has pytest installed (login-shell alias
`python3=python3.12` does not apply in non-interactive bash).

## Test results

```
pytest -v → 4 passed in 0.03s
  test_autopilot_conformance.py::test_enums_match_live_autopilot  PASSED  (LIVE, not skipped)
  test_routing_table.py::test_every_rule_well_formed              PASSED
  test_routing_table.py::test_corpus_coverage                     PASSED
  test_routing_table.py::test_symptom_routes_to_expected_rule     PASSED

run_all.sh → ALL GATES PASSED
```

## Concerns

None. No disambiguation failure, no enum mismatch. The drift guard is
live and will fail the day autopilot adds or removes an enum member.
