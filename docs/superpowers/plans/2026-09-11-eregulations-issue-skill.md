# `eregulations-issue` Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `eregulations-issue` skill in the `eregulations` plugin: it turns a human report about a **7.x** eRegulations instance (bug or feature) into a validated `qualified-ticket` 1.1, filed as a GitHub issue on the right `UNCTAD-eRegistrations/eRegulations-*` repo, after the router's gates have passed. An instance that is not on 7.x is refused, never ticketed (spec D-1).

**Architecture:** A thin `SKILL.md` orchestrates five stdlib Python scripts (`probe_surface.py`, `route.py`, `rules.py`, `redact.py`, `validate_ticket.py`) plus one context builder (`gate_context.py`) that encodes the line rule (spec D-2), and reuses the router's `fleet_resolve.py` and `gates.py` untouched. Order is load-bearing: resolve → gate → probe → ground → qualify → emit → validate → disprove → file. No host contact before `host_posture` passes; nothing but anonymous GET ever reaches a host; the defect rules are fetched at runtime from the private repository, never committed.

**Tech Stack:** Python 3.9+ stdlib only (`json`, `re`, `argparse`, `urllib`, `subprocess`, `base64`), pytest for tests, `gh` CLI for the overlay fetch and for filing, Claude Code plugin conventions of this repository.

**Spec:** `docs/superpowers/specs/2026-09-11-eregulations-issue-skill-design.md` — read it first; the plan argues from it. One plan-level addition to the spec's layout: `scripts/gate_context.py` (Task 6), because the spec's line rule must be code, not prose (router Rule 1). Task 9 amends the spec accordingly.

## Global Constraints

- The repository is **public**: no host address, credential, VPN name, real instance slug, security posture, **or description of an open defect** (keywords, evidence paths, disprove text, security flags) in any committed file — this plan included. Defect rules and their corpus live in the private knowledge base `UNCTAD-eRegistrations/eregulations-knowledge-base` (`defects.json`), which `rules.py` fetches at runtime with the operator's `gh` credential; a local `~/.ereg/defects.local.json` is only a manual fallback. The plan carries only the three gotcha rules. Samples use the router fixture slugs only (`alpha`, `bravo`, `charlie`, `delta`); the fixture overlay uses synthetic `fx-*` rules.
- **7.x only (spec D-1).** The skill serves 7.x instances and nothing else: a probe that answers `not-7.x` is a refusal (what the probe saw, the migration policy, nothing filed, a local `NOTES.md` at most), with no override, no `audit.py` entry and no Jira comment. Surface A (ERegWebApi) has no 7.x and is refused at intake. The ticket's `line` enum is `7.x, unknown`.
- Scripts are **stdlib-only**, run under plain `python3`, no requirements file (`CLAUDE.md` "Bundled skill tests").
- Every test module lives in `skills/eregulations-issue/tests/`, named `test_issue_*.py`; `tests/conftest.py` puts this skill's `scripts/` **and** `../ereg-router/scripts` on `sys.path`.
- `SKILL.md` frontmatter must carry `name`, `description`, `allowed-tools`, `metadata.version`, `metadata.version-date` (checked by `scripts/validate-plugins.py`); `commands/*.md` must carry `description`, `allowed-tools`.
- Skill version `0.1.0`, version-date `2026-09-11`; plugin `0.2.1` → `0.3.0`; router `ereg-router` `0.1.1` → `0.2.0` with a changelog entry.
- Ticket enums are the autopilot's exact enums (see Task 1); `instance.name` is required on **every** ticket; `fleet` keys are the allowlist `line`, `overlay_version`, `platform`, `source_silent`, `drift`.
- Commit after every task. Conventional subject; the body says what and why. **No attribution trailer, no tool name, no session link** in any commit or PR body (operator rule).
- Work on branch `feature/eregulations-issue-skill`, created fresh from `origin/main` with no history from the earlier branch (whose commits carried the defect descriptions and are not reused). Run tests from the repo root:
  `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests -q`.
- **Baseline facts (2026-09-11):** `api-surfaces.md` lives whole in the private knowledge base (spec D-9), and PR #81, which replaces PR 79, wires router Step 1 to it (Task 0 checks both): read at the 7.4.2 tips, every 7.x branch is `main`, roxana is retired, no default credential; the router suite has **107** tests on `main` today and **110** once PR #76 (`fix/branch-pair-case-diagnosis`, three router tests) is merged — Task 0 Step 3 records the actual number and every later total derives from it; the langadmin suite has **19**; `scripts/validate-plugins.py` crashes on Python 3.9 (`dict | None` at import) so it must run under 3.13 (`uv run --python 3.13 python scripts/validate-plugins.py`); `generate-kimi-manifests.py --check` is already red for six other plugins and the two root catalogs.
- **Execution estimate:** about 3 h of agent time — 24 files (18 created, 6 modified), 9 commits, ~15 test runs, 3 verification gates, corpus tuning against the fetched overlay (Task 9). Most script code already exists from the scratch-tree execution (64/66 green before the 7.x restriction) and is trimmed rather than designed. Task 0 must land first: Tasks 3, 7 and 8 read files that only PR 79's branch carries.

## File map

| Path (under `plugins/eregulations/`) | Responsibility | Task |
| --- | --- | --- |
| (PR #81 merged into `main`; replaces PR 79) | router `SKILL.md` 0.1.1 whose Step 1 fetches `api-surfaces.md` from the private knowledge base, `versions.md`, plugin 0.2.1 — the baseline the plan reads | 0 |
| `skills/eregulations-issue/tests/conftest.py` | sys.path for both scripts dirs; points CI at the fixture overlay | 1 |
| `skills/eregulations-issue/scripts/validate_ticket.py` | 1.0/1.1 conformance validator + CLI | 1 |
| `skills/eregulations-issue/qualified-ticket.schema.json` | documents the 1.1 contract | 1 |
| `skills/eregulations-issue/samples/*.json` | two 1.1 samples (bug, feature) | 1 |
| `skills/eregulations-issue/scripts/redact.py` | evidence and URL redaction, `strip_query` | 2 |
| `skills/eregulations-issue/routing-table.json` | the three gotcha rules only; the 27 defect rules are fetched from the private repository | 3 |
| `skills/eregulations-issue/surface-defaults.json` | surface → candidate repos (branch is always `main`), the answer when no rule matches | 3 |
| `skills/eregulations-issue/fixtures/defects.sample.json` | synthetic overlay (four `fx-*` rules + corpus) that CI loads | 3 |
| `skills/eregulations-issue/scripts/rules.py` | public table ∪ overlay: flag → env → `gh api` fetch → cache → local file → not loaded with the reason | 3 |
| `skills/eregulations-issue/scripts/route.py` | filter by surface + score + confidence; `overlay_ref` passthrough | 4 |
| `skills/eregulations-issue/scripts/probe_surface.py` | read-only HTTP probe: surface, `7.x` / `not-7.x` / `unknown`, release | 5 |
| `skills/eregulations-issue/scripts/gate_context.py` | line rule (D-2) + context builders | 6 |
| `skills/eregulations-issue/SKILL.md` | orchestration | 7 |
| `commands/issue.md` | explicit entry | 7 |
| `README.md`, `.claude-plugin/plugin.json` | plugin surface | 7 |
| `skills/ereg-router/SKILL.md` | Step 5 clause + version | 8 |
| `.kimi-plugin/plugin.json`, spec amendment, full verification | 9 |

---

### Task 0: Confirm the router baseline (PR #81) and the private reference

PR #81 (`feature/ereg-router-api-reference`, which replaces the closed PR 79) carries the router changes this plan builds on: router `SKILL.md` 0.1.1, whose Step 1 fetches `api-surfaces.md` from the private knowledge base; corrected `references/versions.md`; `plugin.json` 0.2.1 and its Kimi manifest. The reference itself is not in this repository and never will be (spec D-9): every routing rule's `memory_ref` and `read_via` cite `api-surfaces.md` in `UNCTAD-eRegistrations/eregulations-knowledge-base`. This branch never merges a pull-request branch; it rebases on `main` once #81 is merged. Until then this task stops, and nothing else in the plan starts.

**Files:**
- None created; a rebase only.

- [ ] **Step 1: Confirm PR #81 is merged into `main`**

```bash
git fetch -q origin
git show origin/main:plugins/eregulations/skills/ereg-router/SKILL.md | grep -c eregulations-knowledge-base   # expect >= 1: Step 1 fetches the private reference
git show origin/main:plugins/eregulations/.claude-plugin/plugin.json | grep -c '"version": "0.2.1"'   # expect 1
git ls-tree --name-only origin/main plugins/eregulations/skills/ereg-router/references/ | grep -c api-surfaces   # expect 0: the reference is never public
```

If the first count is 0 or the version is not 0.2.1, #81 is not merged: **stop and report**. If the last count is not 0, the reference was published again: stop and report it as a disclosure. Otherwise bring the branch onto that baseline:

```bash
git rebase origin/main
```

(The branch starts from `origin/main` with only the two `docs/superpowers/` files, so the rebase is a fast-forward or a trivial replay.)

- [ ] **Step 2: Confirm the knowledge base is readable**

```bash
gh api repos/UNCTAD-eRegistrations/eregulations-knowledge-base/contents/api-surfaces.md -H 'Accept: application/vnd.github.raw' | head -1   # expect: # eRegulations HTTP API surfaces, by version line
gh api repos/UNCTAD-eRegistrations/eregulations-knowledge-base/contents/defects.json -H 'Accept: application/vnd.github.raw' | python3 -c "import json,sys; print(len(json.load(sys.stdin)['rules']))"   # expect > 0 (27 on 2026-09-11)
```

Either command failing means no access to the knowledge base: stop and ask the operator for repository access. Never copy either file into this repository; read them into a scratch directory only.

- [ ] **Step 3: Record the baselines the later tasks derive from**

```bash
python3 -m pytest plugins/eregulations/skills/ereg-router/tests -q | tail -1     # 107 passed on main today; 110 once PR #76 (fix/branch-pair-case-diagnosis) is merged
python3 -m pytest plugins/eregulations/skills/merged-eregulations-translations-into-langadmin/tests -q | tail -1   # expect: 19 passed
git status --short   # expect only the untracked .claude/ directory
```

Write the router number down — call it **R** (107 or 110, depending on whether PR #76 is in `main`). Tasks 8 and 9 state their expected totals as `R + 19 + 82`; if R is anything else, say so in that task's commit message.

---

### Task 1: Scaffold, validator, schema, samples

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/tests/conftest.py`
- Create: `plugins/eregulations/skills/eregulations-issue/scripts/validate_ticket.py`
- Create: `plugins/eregulations/skills/eregulations-issue/qualified-ticket.schema.json`
- Create: `plugins/eregulations/skills/eregulations-issue/samples/qualified-ticket.bug.example.json`
- Create: `plugins/eregulations/skills/eregulations-issue/samples/qualified-ticket.feature.example.json`
- Test: `plugins/eregulations/skills/eregulations-issue/tests/test_issue_validate_ticket.py`

**Interfaces:**
- Produces: `validate_ticket.validate_ticket(ticket: dict) -> list[str]` (empty list = valid); CLI `python3 validate_ticket.py <file>` prints `VALID` (exit 0) or `INVALID:` + reasons (exit 1). Constants `FLEET_ALLOWED`, `SURFACES`, `LINES` (`{"7.x", "unknown"}`), `LANES`, `DISPROVE` reused by Tasks 3–6.

- [ ] **Step 1: Create the conftest**

```python
# plugins/eregulations/skills/eregulations-issue/tests/conftest.py
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scripts"))
sys.path.insert(0, str(_HERE.parent.parent / "ereg-router" / "scripts"))
# CI has no access to the private knowledge base: load the synthetic one.
# An operator who exports EREG_DEFECTS, or sets EREG_DEFECTS_REAL=1 (rules.py
# then fetches defects.json from the private knowledge base with gh, or falls back
# to its cache), runs the same tests over the real rules.
if "EREG_DEFECTS" not in os.environ and os.environ.get("EREG_DEFECTS_REAL") != "1":
    os.environ["EREG_DEFECTS"] = str(_HERE.parent / "fixtures" / "defects.sample.json")
```

- [ ] **Step 2: Write the failing validator tests**

```python
# plugins/eregulations/skills/eregulations-issue/tests/test_issue_validate_ticket.py
"""The validator is the last gate before filing. It must accept every 1.0
ticket the sibling skill produces (the autopilot reads both) and reject the
1.1 shapes the spec forbids: missing instance.name, missing surface/line/lane,
and any fleet key that could carry a host or a posture out of the machine."""
from __future__ import annotations

import json
from pathlib import Path

import validate_ticket as vt

_SKILL = Path(__file__).resolve().parent.parent
_SAMPLES = _SKILL / "samples"
_SIBLING_10 = _SKILL.parents[2] / "bpa-mcp" / "skills" / "ereg-issue" / "samples" / "qualified-ticket.example.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _minimal_11(**overrides) -> dict:
    t = {
        "schema_version": "1.1", "slug": "2026-09-11-x", "symptom": "x",
        "instance": {"name": "alpha"}, "surface": "B", "line": "7.x", "lane": "plan",
        "security": False,
        "fleet": {"line": "7.x", "overlay_version": "7.2", "platform": "ubuntu",
                  "source_silent": [], "drift": False},
        "rubric": {"severity": "medium", "scale": "Small", "kind": "bug", "affected_components": []},
        "claims": [],
    }
    t.update(overrides)
    return t


def test_bug_sample_valid():
    assert vt.validate_ticket(_load(_SAMPLES / "qualified-ticket.bug.example.json")) == []


def test_feature_sample_valid():
    assert vt.validate_ticket(_load(_SAMPLES / "qualified-ticket.feature.example.json")) == []


def test_11_rejects_any_line_but_7x_or_unknown():
    """A host that is not on 7.x is refused before a ticket exists (spec D-1),
    so no 1.1 ticket may carry another line."""
    assert vt.validate_ticket(_minimal_11(line="unknown")) == []
    for line in ("4.x", "5.x", "6.x", "not-7.x", "8.x"):
        assert any("line" in e for e in vt.validate_ticket(_minimal_11(line=line))), line


def test_qualification_disprove_and_overlay_ref_shapes():
    ok = _minimal_11(qualification={"overlay_ref": "fixture", "disprove": {"verdict": "weakened", "notes": ["claim 1: n"]}})
    assert vt.validate_ticket(ok) == []
    for ref in ("cache", "local", "none", "230dddcd294244e0f96e1c89ca95e36a629d9aa6"):
        assert vt.validate_ticket(_minimal_11(qualification={"overlay_ref": ref})) == [], ref
    bad = vt.validate_ticket(_minimal_11(qualification={"overlay_ref": 7}))
    assert any("overlay_ref" in e for e in bad)
    bad = vt.validate_ticket(_minimal_11(qualification={"disprove": {"verdict": "maybe", "notes": []}}))
    assert any("disprove.verdict" in e for e in bad)
    bad = vt.validate_ticket(_minimal_11(qualification={"disprove": {"verdict": "stands", "notes": "n"}}))
    assert any("disprove.notes" in e for e in bad)


def test_sibling_10_sample_still_valid():
    assert _SIBLING_10.exists(), "the 1.0 sample moved; update the relative path"
    assert vt.validate_ticket(_load(_SIBLING_10)) == []


def test_11_requires_surface_line_lane():
    t = _minimal_11()
    for key in ("surface", "line", "lane"):
        broken = dict(t)
        del broken[key]
        assert any(key in e for e in vt.validate_ticket(broken)), key


def test_10_does_not_require_surface_line_lane():
    t = _minimal_11(schema_version="1.0")
    for key in ("surface", "line", "lane", "fleet", "security"):
        t.pop(key, None)
    assert vt.validate_ticket(t) == []


def test_instance_name_required_on_every_ticket():
    t = _minimal_11(instance={})
    assert any("instance.name" in e for e in vt.validate_ticket(t))
    t = _minimal_11(instance={"name": "platform"})
    assert vt.validate_ticket(t) == []


def test_fleet_allowlist_enforced():
    t = _minimal_11()
    t["fleet"]["host"] = "h"
    assert any("fleet.host" in e for e in vt.validate_ticket(t))


def test_fleet_drift_must_be_boolean_and_source_silent_strings():
    t = _minimal_11()
    t["fleet"]["drift"] = [{"field": "version"}]
    assert any("fleet.drift" in e for e in vt.validate_ticket(t))
    t = _minimal_11()
    t["fleet"]["source_silent"] = [{"x": 1}]
    assert any("source_silent" in e for e in vt.validate_ticket(t))


def test_top_level_host_and_posture_forbidden():
    for key in ("host", "posture"):
        t = _minimal_11()
        t[key] = "x"
        assert any(key in e for e in vt.validate_ticket(t)), key


def test_bad_enums_rejected():
    assert any("severity" in e for e in vt.validate_ticket(_minimal_11(rubric={"severity": "sev1", "scale": "Small", "kind": "bug"})))
    assert any("surface" in e for e in vt.validate_ticket(_minimal_11(surface="Z")))
    assert any("line" in e for e in vt.validate_ticket(_minimal_11(line="8.x")))
    assert any("lane" in e for e in vt.validate_ticket(_minimal_11(lane="run")))
    assert any("closing_state" in e for e in vt.validate_ticket(_minimal_11(closing_state="DONE")))
    assert any("recommendation_hint" in e for e in vt.validate_ticket(_minimal_11(recommendation_hint="GO")))


def test_claims_enums():
    t = _minimal_11(claims=[{"claim": "c", "claim_type": "guess", "kind": "Hard"}])
    assert any("claim_type" in e for e in vt.validate_ticket(t))
    t = _minimal_11(claims=[{"claim": "c", "claim_type": "quantitative-estimate", "kind": "Soft"}])
    assert vt.validate_ticket(t) == []


def test_cli_prints_valid(tmp_path, capsys):
    p = tmp_path / "t.json"
    p.write_text(json.dumps(_minimal_11()))
    assert vt._main(["validate_ticket.py", str(p)]) == 0
    assert "VALID" in capsys.readouterr().out
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_validate_ticket.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'validate_ticket'`

- [ ] **Step 4: Write the validator**

```python
# plugins/eregulations/skills/eregulations-issue/scripts/validate_ticket.py
"""Stdlib-only conformance validator for qualified-ticket.json (1.0 and 1.1).

1.0 is the contract the autopilot reads (bpa-mcp/skills/ereg-issue); every 1.0
requirement is kept. 1.1 adds surface/line/lane/security/jira_key, the
qualification.overlay_ref and qualification.disprove shapes, and an ALLOWLIST
for `fleet`, so a host, an address or a posture can never leave the machine
inside a ticket. The 1.1 line enum is `7.x` or `unknown` only: a host that is
not on 7.x is refused before a ticket exists (spec D-1). No jsonschema
dependency: the schema file documents the contract, this module enforces the
load-bearing parts deterministically.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SEVERITY = {"critical", "high", "medium", "low", "info"}
SCALE = {"Small", "Medium", "Large", "Architectural"}
KIND = {"bug", "feature", "refactor", "design", "docs", "infra", "unknown"}
CLAIM_TYPE = {"code-fact", "environment-mapping", "future-prescription",
              "quantitative-estimate", "runtime-observation"}
CONSTRAINT_KIND = {"Hard", "Soft", "Assumption"}
# The 1.0 enum verbatim (bpa-mcp/skills/ereg-issue/qualified-ticket.schema.json);
# this skill only ever emits the first two values (spec D-1).
RECOMMENDATION = {"PROCEED", "NEEDS-MORE-INFO", "OUT-OF-SCOPE"}
CLOSING = {None, "FIXED", "NOT_A_BUG", "INTENTIONAL_DESIGN", "WONT_FIX",
           "PENDING_DECISION", "PENDING_BACKEND"}
CONFIDENCE = {"high", "medium", "low"}
DISPROVE = {"stands", "weakened", "refuted"}

SURFACES = {"A", "B", "C", "SPA", "deploy", "monitor", "unknown"}
LINES = {"7.x", "unknown"}
LANES = {"plan", "build", "execute"}
FLEET_ALLOWED = {"line", "overlay_version", "platform", "source_silent", "drift"}
TOP_FORBIDDEN = {"host", "posture", "address", "vpn"}
JIRA_KEY = re.compile(r"^ERN-\d+$")

_TOP_REQUIRED = ["schema_version", "slug", "symptom", "instance", "rubric", "claims"]
_11_REQUIRED = ["surface", "line", "lane"]


def validate_ticket(ticket: dict) -> list[str]:
    errors: list[str] = []
    for key in _TOP_REQUIRED:
        if key not in ticket:
            errors.append(f"missing required key: {key}")
    for key in TOP_FORBIDDEN & set(ticket):
        errors.append(f"forbidden top-level key: {key} (fleet data never leaves the machine)")

    inst = ticket.get("instance")
    if not isinstance(inst, dict) or not inst.get("name"):
        errors.append("instance.name is required (hard-floor; use the sentinel 'platform' for a platform-wide feature)")

    rubric = ticket.get("rubric") or {}
    if rubric.get("severity") not in SEVERITY:
        errors.append(f"rubric.severity {rubric.get('severity')!r} not in {sorted(SEVERITY)}")
    if rubric.get("scale") not in SCALE:
        errors.append(f"rubric.scale {rubric.get('scale')!r} not in {sorted(SCALE)}")
    if rubric.get("kind") not in KIND:
        errors.append(f"rubric.kind {rubric.get('kind')!r} not in {sorted(KIND)}")
    if not isinstance(rubric.get("affected_components", []), list):
        errors.append("rubric.affected_components must be a list")

    for i, claim in enumerate(ticket.get("claims") or []):
        if claim.get("claim_type") not in CLAIM_TYPE:
            errors.append(f"claims[{i}].claim_type {claim.get('claim_type')!r} invalid")
        if claim.get("kind") not in CONSTRAINT_KIND:
            errors.append(f"claims[{i}].kind {claim.get('kind')!r} invalid")

    if "recommendation_hint" in ticket and ticket["recommendation_hint"] not in RECOMMENDATION:
        errors.append(f"recommendation_hint {ticket['recommendation_hint']!r} not in {sorted(RECOMMENDATION)}")
    if "closing_state" in ticket and ticket["closing_state"] not in CLOSING:
        errors.append(f"closing_state {ticket['closing_state']!r} invalid")
    qual = ticket.get("qualification") or {}
    if "confidence" in qual and qual["confidence"] not in CONFIDENCE:
        errors.append(f"qualification.confidence {qual['confidence']!r} invalid")
    if "overlay_ref" in qual and not isinstance(qual["overlay_ref"], str):
        errors.append("qualification.overlay_ref must be a string (blob sha, cache, local, fixture or none)")
    if "disprove" in qual:
        disprove = qual["disprove"]
        if not isinstance(disprove, dict) or disprove.get("verdict") not in DISPROVE:
            errors.append(f"qualification.disprove.verdict must be one of {sorted(DISPROVE)}")
        notes = disprove.get("notes") if isinstance(disprove, dict) else None
        if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
            errors.append("qualification.disprove.notes must be a list of strings")

    if ticket.get("schema_version") == "1.1":
        fleet = ticket.get("fleet")
        if isinstance(fleet, dict):
            for key in set(fleet) - FLEET_ALLOWED:
                errors.append(f"fleet.{key} is not in the allowlist {sorted(FLEET_ALLOWED)}")
            if "drift" in fleet and not isinstance(fleet["drift"], bool):
                errors.append("fleet.drift must be a boolean (raw drift entries never leave the machine)")
            ss = fleet.get("source_silent", [])
            if not isinstance(ss, list) or not all(isinstance(x, str) for x in ss):
                errors.append("fleet.source_silent must be a list of strings")
        for key in _11_REQUIRED:
            if key not in ticket:
                errors.append(f"1.1 requires {key}")
        if "surface" in ticket and ticket["surface"] not in SURFACES:
            errors.append(f"surface {ticket['surface']!r} not in {sorted(SURFACES)}")
        if "line" in ticket and ticket["line"] not in LINES:
            errors.append(f"line {ticket['line']!r} not in {sorted(LINES)}")
        if "lane" in ticket and ticket["lane"] not in LANES:
            errors.append(f"lane {ticket['lane']!r} not in {sorted(LANES)}")
        if "security" in ticket and not isinstance(ticket["security"], bool):
            errors.append("security must be a boolean")
        if ticket.get("jira_key") is not None and not JIRA_KEY.match(str(ticket["jira_key"])):
            errors.append("jira_key must match ERN-<digits>")
    return errors


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_ticket.py <ticket.json>", file=sys.stderr)
        return 2
    ticket = json.loads(Path(argv[1]).read_text())
    errors = validate_ticket(ticket)
    if errors:
        print("INVALID:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print("VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
```

- [ ] **Step 5: Write the schema file (documentation of the contract)**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "eRegulations qualified-ticket 1.1",
  "description": "Additive over bpa-mcp/skills/ereg-issue qualified-ticket 1.0. Enforced by scripts/validate_ticket.py.",
  "type": "object",
  "required": ["schema_version", "slug", "symptom", "instance", "rubric", "claims", "surface", "line", "lane"],
  "not": {"anyOf": [{"required": ["host"]}, {"required": ["posture"]}, {"required": ["address"]}, {"required": ["vpn"]}]},
  "properties": {
    "schema_version": {"const": "1.1"},
    "slug": {"type": "string"},
    "reporter": {"type": "string"},
    "timestamp": {"type": "string"},
    "symptom": {"type": "string"},
    "instance": {"type": "object", "required": ["name"],
                 "properties": {"name": {"type": "string", "description": "slug, or the sentinel 'platform'"}, "url": {"type": "string"}}},
    "surface": {"enum": ["A", "B", "C", "SPA", "deploy", "monitor", "unknown"]},
    "line": {"enum": ["7.x", "unknown"], "description": "a not-7.x host is refused before a ticket exists (spec D-1)"},
    "lane": {"enum": ["plan", "build", "execute"]},
    "security": {"type": "boolean", "default": false},
    "jira_key": {"type": ["string", "null"], "pattern": "^ERN-[0-9]+$"},
    "fleet": {"type": "object", "additionalProperties": false,
              "properties": {"line": {"type": "string"}, "overlay_version": {"type": ["string", "null"]},
                             "platform": {"type": ["string", "null"]},
                             "source_silent": {"type": "array", "items": {"type": "string"}},
                             "drift": {"type": "boolean"}}},
    "ids": {"type": "object"},
    "observed": {"type": "object"},
    "expected": {"type": "string"},
    "actual": {"type": "string"},
    "scope": {"type": "object"},
    "rubric": {"type": "object", "required": ["severity", "scale", "kind"],
               "properties": {"severity": {"enum": ["critical", "high", "medium", "low", "info"]},
                              "scale": {"enum": ["Small", "Medium", "Large", "Architectural"]},
                              "kind": {"enum": ["bug", "feature", "refactor", "design", "docs", "infra", "unknown"]},
                              "affected_components": {"type": "array", "items": {"type": "string"}}}},
    "qualification": {"type": "object",
                      "properties": {"candidate_repos": {"type": "array", "items": {"type": "string"}},
                                     "version_branch": {"type": ["string", "null"]},
                                     "version_mismatch": {"type": "boolean", "description": "overlay version and probed line disagree"},
                                     "match_score": {"type": "number"},
                                     "confidence": {"enum": ["high", "medium", "low"]},
                                     "first_evidence_source": {"type": "string"},
                                     "read_via": {"type": ["string", "null"]},
                                     "also_check_and_disprove": {"type": "array", "items": {"type": "string"}},
                                     "gotcha_hits": {"type": "array", "items": {"type": "string"}},
                                     "memory_refs": {"type": "array", "items": {"type": "string"}},
                                     "overlay_ref": {"type": "string", "description": "which defect memory routed the ticket: a blob sha, cache, local, fixture or none (spec D-5)"},
                                     "disprove": {"type": "object", "required": ["verdict", "notes"],
                                                  "properties": {"verdict": {"enum": ["stands", "weakened", "refuted"]},
                                                                 "notes": {"type": "array", "items": {"type": "string"}}}}}},
    "claims": {"type": "array", "items": {"type": "object", "required": ["claim", "claim_type", "kind"],
               "properties": {"claim": {"type": "string"},
                              "claim_type": {"enum": ["code-fact", "runtime-observation", "environment-mapping", "quantitative-estimate", "future-prescription"]},
                              "kind": {"enum": ["Hard", "Soft", "Assumption"]},
                              "evidence": {"type": "string"},
                              "needs_live_verification": {"type": "boolean"}}}},
    "recommendation_hint": {"enum": ["PROCEED", "NEEDS-MORE-INFO", "OUT-OF-SCOPE"], "description": "the 1.0 enum verbatim; this skill only emits PROCEED or NEEDS-MORE-INFO (spec D-1)"},
    "closing_state": {"enum": [null, "FIXED", "NOT_A_BUG", "INTENTIONAL_DESIGN", "WONT_FIX", "PENDING_DECISION", "PENDING_BACKEND"]}
  }
}
```

- [ ] **Step 6: Write the two samples**

`samples/qualified-ticket.bug.example.json`:

```json
{
  "schema_version": "1.1",
  "slug": "2026-09-11-widget-save-500",
  "reporter": "ops@example.org",
  "timestamp": "2026-09-11T10:00:00Z",
  "symptom": "Saving the widget on a step of the public site editor fails with HTTP 500.",
  "instance": {
    "name": "alpha",
    "url": "https://<public-host>/procedure/12/step/34"
  },
  "surface": "B",
  "line": "7.x",
  "lane": "plan",
  "security": false,
  "jira_key": null,
  "fleet": {
    "line": "7.x",
    "overlay_version": "7.2",
    "platform": "ubuntu",
    "source_silent": [
      "docker logs (plan lane)"
    ],
    "drift": false
  },
  "ids": {
    "procedure_id": "12",
    "step_id": "34"
  },
  "observed": {
    "endpoint": "/api/procedure/12/step/34/widget",
    "status": 500,
    "error": "Internal Server Error",
    "reproduced": false,
    "steps": [
      "open the step editor",
      "change the widget",
      "save"
    ]
  },
  "expected": "Widget saved and reflected on the public page.",
  "actual": "Request fails with 500; nothing saved.",
  "scope": {
    "breadth": "all steps",
    "condition": "always"
  },
  "rubric": {
    "severity": "medium",
    "scale": "Small",
    "kind": "bug",
    "affected_components": [
      "Project/WebAppCore/Controllers/"
    ]
  },
  "qualification": {
    "candidate_repos": [
      "eRegulations-4.0-Public"
    ],
    "version_branch": "main",
    "version_mismatch": false,
    "match_score": 4,
    "confidence": "high",
    "first_evidence_source": "browser network tab",
    "read_via": "git show main:Project/WebAppCore/Controllers/",
    "also_check_and_disprove": [
      "Confirm the widget is the failing control."
    ],
    "gotcha_hits": [],
    "memory_refs": [
      "api-surfaces#8 fixture"
    ],
    "overlay_ref": "fixture",
    "disprove": {
      "verdict": "stands",
      "notes": []
    }
  },
  "claims": [
    {
      "claim": "The widget save posts to a route that answers 500",
      "claim_type": "runtime-observation",
      "kind": "Soft",
      "evidence": "reporter's console capture (redacted)",
      "needs_live_verification": true
    },
    {
      "claim": "The reporter's URL host is the instance 'alpha'",
      "claim_type": "environment-mapping",
      "kind": "Assumption",
      "evidence": "reporter statement",
      "needs_live_verification": true
    }
  ],
  "recommendation_hint": "PROCEED",
  "closing_state": null
}
```

`samples/qualified-ticket.feature.example.json`:

```json
{
  "schema_version": "1.1",
  "slug": "2026-09-11-export-procedure-csv",
  "reporter": "pm@example.org",
  "timestamp": "2026-09-11T10:00:00Z",
  "symptom": "Feature: export a procedure's step list as CSV from the admin SPA.",
  "instance": {"name": "platform"},
  "surface": "C",
  "line": "7.x",
  "lane": "plan",
  "security": false,
  "jira_key": "ERN-1234",
  "fleet": {"line": "7.x", "overlay_version": null, "platform": null, "source_silent": ["no instance probed (feature)", "no defect overlay loaded"], "drift": false},
  "expected": "A CSV download of the objective tree for one procedure.",
  "actual": "The SPA shows the tree but offers no export.",
  "scope": {"breadth": "platform", "condition": "all 7.x instances"},
  "rubric": {"severity": "low", "scale": "Medium", "kind": "feature",
             "affected_components": ["Project/WebAppCore/Controllers/", "src/app/features/"]},
  "qualification": {
    "candidate_repos": ["eRegulations-4.0-Admin", "eRegulations-5.0-Admin-SPA"],
    "version_branch": "main",
    "version_mismatch": false,
    "match_score": 0,
    "confidence": "low",
    "first_evidence_source": "GET /api/objective tree endpoint already returns the data to export (api-surfaces.md §4.4)",
    "read_via": "git show main:Project/WebAppCore/Controllers/",
    "also_check_and_disprove": ["Confirm no existing export endpoint exists on admin-api before adding one."],
    "gotcha_hits": [],
    "memory_refs": [],
    "overlay_ref": "none"
  },
  "claims": [
    {"claim": "The objective tree is readable through the Admin API", "claim_type": "code-fact", "kind": "Soft",
     "evidence": "api-surfaces.md §4.4 objective endpoints", "needs_live_verification": false}
  ],
  "recommendation_hint": "PROCEED",
  "closing_state": null
}
```

There is no third sample: a host that is not on 7.x is refused before a ticket exists (spec D-1), so there is no legacy ticket shape to document.

- [ ] **Step 7: Run the tests**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_validate_ticket.py -q`
Expected: `14 passed`

- [ ] **Step 8: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue
git commit -m "feat(eregulations-issue): validator, schema 1.1 and samples"
```

---

### Task 2: Redaction

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/scripts/redact.py`
- Test: `plugins/eregulations/skills/eregulations-issue/tests/test_issue_redact.py`

**Interfaces:**
- Produces: `redact.redact(text: str) -> str`; CLI reads stdin, writes stdout. Used by Task 5 (probe evidence) and by `SKILL.md` for log excerpts.

- [ ] **Step 1: Write the failing tests**

```python
# plugins/eregulations/skills/eregulations-issue/tests/test_issue_redact.py
"""Every pattern the spec lists must be scrubbed before an evidence string is
written to disk, because the ticket ends up in a GitHub issue."""
from __future__ import annotations

import redact


def test_ipv4_and_ipv6():
    assert "192.0.2.3" not in redact.redact("upstream 192.0.2.3:8080 refused")
    assert "[REDACTED-IP]" in redact.redact("upstream 192.0.2.3:8080 refused")
    assert "2001:db8::1" not in redact.redact("host 2001:db8::1 down")
    assert "fe80:0:0:0:1:2:3:4" not in redact.redact("via fe80:0:0:0:1:2:3:4")


def test_log_timestamps_survive():
    assert "10:00:00.123" in redact.redact("2026-09-11 10:00:00.123 warn something")
    assert "[11/Sep/2026:10:00:01 +0000]" in redact.redact("[11/Sep/2026:10:00:01 +0000] GET / 200")


def test_auth_and_cookie_headers():
    out = redact.redact("Authorization: Bearer abc.def.ghi\nCookie: .AspNetCore.Cookies=xyz")
    assert "abc.def.ghi" not in out and "xyz" not in out
    assert "Authorization: [REDACTED]" in out and "Cookie: [REDACTED]" in out


def test_connection_string():
    out = redact.redact("Server=db;Database=x;User Id=sa;Password=Sup3r!;")
    assert "Sup3r!" not in out and "[REDACTED-CONNSTRING]" in out


def test_jwt_shaped_token():
    tok = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcDEF123_-xyz"
    assert tok not in redact.redact("token " + tok)


def test_email():
    assert "someone@example.org" not in redact.redact("user someone@example.org failed")


def test_env_secret_values():
    out = redact.redact("SA_PASSWORD=hunter2 SECRETKEY=abc API_KEY='k' SSO_TOKEN=t")
    for v in ("hunter2", "abc", "'k'", "=t"):
        assert v not in out
    assert "SA_PASSWORD=[REDACTED]" in out
    assert "sortKey=name" in redact.redact("?sortKey=name&monkey=1")


def test_url_query_credentials():
    out = redact.redact("GET /example/signin?user=ann&pwd=hunter2&token=abc HTTP/1.1")
    assert "hunter2" not in out and "=abc" not in out
    assert "pwd=[REDACTED]" in out and "user=ann" in out


def test_strip_query():
    assert redact.strip_query("https://example.test/example/signin?user=a&pwd=b#x") == "https://example.test/example/signin"
    assert redact.strip_query("https://example.test/procedure/12") == "https://example.test/procedure/12"


def test_clean_string_untouched():
    s = "GET /release.json -> 200 {\"track\":\"admin-api-core\"}"
    assert redact.redact(s) == s


def test_idempotent():
    s = "Authorization: Bearer x 192.0.2.1"
    assert redact.redact(redact.redact(s)) == redact.redact(s)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_redact.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'redact'` (11 tests collected)

- [ ] **Step 3: Write the module**

```python
# plugins/eregulations/skills/eregulations-issue/scripts/redact.py
"""Scrub evidence before it is written anywhere (ticket, NOTES.md, issue body).

Order matters: connection strings and header lines are whole-line patterns and
run first, so a token inside them is removed with its context; the narrower
patterns then catch what is left. Every replacement is a fixed marker so a
second pass is a no-op.
"""
from __future__ import annotations

import re
import sys

_PATTERNS = [
    (re.compile(r"(?im)^(\s*(authorization|cookie|set-cookie|x-api-key)\s*:\s*).*$"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b[A-Za-z _]*(server|data source|host)=[^;\n]+;[^\n]*(password|pwd)=[^;\n]*;?[^\n]*"), "[REDACTED-CONNSTRING]"),
    (re.compile(r"(?i)\b((?:[A-Z0-9]+_)*(?:PASSWORD|SECRET|KEY|TOKEN)[A-Z0-9_]*)=(\"[^\"]*\"|'[^']*'|\S+)"), r"\1=[REDACTED]"),
    # URL query values whose name says credential; other parameters survive.
    (re.compile(r"(?i)([?&](?:pwd|password|passwd|token|key|secret|apikey|api[_-]?key|access_token)=)[^&\s#]*"), r"\1[REDACTED]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b"), "[REDACTED-TOKEN]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED-EMAIL]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED-IP]"),
    # IPv6 only when the candidate carries `::` or a hex letter, so log timestamps (10:00:00) survive.
    (re.compile(r"\b(?=[0-9a-fA-F:]*(?:::|[a-fA-F]))(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{1,4}\b"), "[REDACTED-IP]"),
]


def redact(text: str) -> str:
    out = text
    for pattern, replacement in _PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def strip_query(url: str) -> str:
    """The reporter's URL without query or fragment: what is probed, stored and shown."""
    return url.split("#", 1)[0].split("?", 1)[0]


if __name__ == "__main__":
    sys.stdout.write(redact(sys.stdin.read()))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_redact.py -q`
Expected: `11 passed`. The env-var stem must sit at a `_` or word boundary (`sortKey` is not redacted, `SECRETKEY` is); the IPv6 lookahead is what keeps `10:00:00` intact.

- [ ] **Step 5: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue/scripts/redact.py plugins/eregulations/skills/eregulations-issue/tests/test_issue_redact.py
git commit -m "feat(eregulations-issue): evidence redaction"
```

---

### Task 3: Routing table, surface defaults, fixture overlay, rules loader

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/routing-table.json` (three gotchas)
- Create: `plugins/eregulations/skills/eregulations-issue/surface-defaults.json`
- Create: `plugins/eregulations/skills/eregulations-issue/fixtures/defects.sample.json`
- Create: `plugins/eregulations/skills/eregulations-issue/scripts/rules.py`
- Modify: `plugins/eregulations/skills/eregulations-issue/tests/conftest.py` (point CI at the fixture overlay — already written in Task 1, confirm it)
- Test: `plugins/eregulations/skills/eregulations-issue/tests/test_issue_routing_table.py`
- **Never committed:** the overlay itself (fetched at runtime), its cache `~/.ereg/defects.cache.json`, or a manual `~/.ereg/defects.local.json` (see *Where the defect rules are*).

**Interfaces:**
- Rule shape (public table and overlay alike): `id, surface, line (always `["7.x"]`), match{keywords, discriminators}, candidate_repos, version_branch (always the string `main`), read_via, first_evidence_source, also_check_and_disprove, closing_state_hint (null|enum), memory_ref`, optional `security: true`. No placeholder in `read_via`: every routing target is on `main` (spec D-4).
- `rules.load_overlay(path=None, runner=None) -> {rules, corpus, loaded, ref, reason, path}` resolving, first hit wins (spec D-5): the `path` argument (the `--defects` flag) → `EREG_DEFECTS` → a fresh `gh api` fetch of `defects.json` from `UNCTAD-eRegistrations/eregulations-knowledge-base` (subprocess, 10 s timeout, `runner` injectable for tests), written to the cache `~/.ereg/defects.cache.json` as `{sha, fetched_at, data}` → the last cache when the fetch fails → `~/.ereg/defects.local.json` → not loaded. `ref` is the blob sha, `cache`, `local`, `fixture` (the loaded path is `fixtures/defects.sample.json`) or `none`; `reason` is `null` after a fresh fetch, else why the fetch was not used: `no-gh`, `not-authenticated`, `no-access`, `network`, or `none` (an explicit path that does not exist; nothing was fetched). A malformed source raises `ValueError` naming it (file, cache or repository). `rules.load_rules(table_path, defects_path=None, runner=None) -> (rules, overlay)`; raises on an id present in both. Constants `rules.DEFAULT_TABLE`, `rules.DEFAULT_DEFAULTS`, `rules.FIXTURE`, `rules.OVERLAY_REPO`, `rules.FETCH_COMMAND`, `rules.CACHE_PATH`, `rules.LOCAL_PATH`. Consumed by Task 4 `route.py` and by these tests.
- `surface-defaults.json`: `{surface: {candidate_repos, version_branch: "main"}}` for `B`, `C`, `SPA`, `deploy`, `monitor` (no line dimension, no Surface A), consumed by `route.py` when nothing matches.

**Where the defect rules are.** The 27 defect rules (23 open, four `FIXED` gotchas whose keywords describe defects still open on legacy lines or retired images) and their 27-entry corpus live in the private knowledge base `UNCTAD-eRegistrations/eregulations-knowledge-base` as `defects.json` (`{"schema_version": 1, "rules": [...], "corpus": [...]}`, same rule shape as the public table plus an optional `security: true`), created 2026-09-11 (spec D-5). `rules.py` fetches it at runtime with the operator's `gh` credential, so access is repository membership and nothing is copied by hand. The rules are not reproduced here because this file is public. Read the file only to check shapes and counts, never to copy content into the repository: `gh api repos/UNCTAD-eRegistrations/eregulations-knowledge-base/contents/defects.json -H 'Accept: application/vnd.github.raw' | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['rules']), len(d['corpus']))"` (expect `27 27`).

- [ ] **Step 1: Write the failing table tests**

```python
# plugins/eregulations/skills/eregulations-issue/tests/test_issue_routing_table.py
"""The routing table is institutional memory encoded as routing power. These
tests keep it well-formed and keep every rule distinguishable from its
neighbours on the same surface, so a symptom can never tie by construction.
Every rule is 7.x and reads `main` (spec D-4), so a rule's branch is data,
never a probe result. The rules under test are the public table (gotchas
only) plus whatever overlay conftest selected: the synthetic fixture in CI,
the file fetched from the private repository on an operator's machine. The
loader's resolution order (spec D-5) is exercised with a stub `gh` runner, so
no test touches the network."""
from __future__ import annotations

import base64
import json
import re
import subprocess
from pathlib import Path

import pytest
import rules
import validate_ticket as vt

_SKILL = Path(__file__).resolve().parent.parent
TARGETS = {
    "eRegulations-4.0-Admin", "eRegulations-4.0-Public", "eRegulations-5.0-Admin-SPA",
    "eRegulations-Statistics", "eRegulations-deploy", "eRegulations-Monitor",
}
KNOWN_REPOS = TARGETS | {"eRegulations-4.0-API", "eRegulations-CR-Alerts"}
REQUIRED = {"id", "surface", "line", "match", "candidate_repos", "version_branch", "read_via",
            "first_evidence_source", "also_check_and_disprove", "closing_state_hint", "memory_ref"}
OPTIONAL = {"security"}
GOTCHA = {None, "NOT_A_BUG", "INTENTIONAL_DESIGN", "WONT_FIX", "FIXED"}
SHA = "0123456789abcdef0123456789abcdef01234567"
FIXTURE_DATA = json.loads((_SKILL / "fixtures" / "defects.sample.json").read_text())


def _public() -> list:
    return json.loads((_SKILL / "routing-table.json").read_text())


def _table() -> list:
    return rules.load_rules()[0]


def _runner(code=0, out="", err="", raises=None):
    """A stub for rules.default_runner: records every call, returns or raises."""
    calls = []

    def run(cmd, timeout):
        calls.append((list(cmd), timeout))
        if raises is not None:
            raise raises
        return code, out, err

    run.calls = calls
    return run


def _contents(data, sha=SHA) -> str:
    """What `gh api repos/../contents/defects.json` prints without the raw header."""
    return json.dumps({"sha": sha, "encoding": "base64",
                       "content": base64.b64encode(json.dumps(data).encode()).decode()})


def _paths(tmp_path):
    return {"cache_path": tmp_path / "defects.cache.json", "local_path": tmp_path / "defects.local.json"}


def test_public_table_holds_only_gotchas():
    """An open defect never sits in a committed file (spec C-1)."""
    public = _public()
    assert len(public) == 3
    assert all(r["closing_state_hint"] for r in public), [r["id"] for r in public if not r["closing_state_hint"]]
    assert "b7-retired-roxana-image" in {r["id"] for r in public}


def test_flag_and_env_win_over_the_fetch(tmp_path, monkeypatch):
    copy = tmp_path / "copy.json"
    copy.write_text(json.dumps(FIXTURE_DATA))
    run = _runner(out=_contents(FIXTURE_DATA))
    monkeypatch.delenv("EREG_DEFECTS", raising=False)
    out = rules.load_overlay(copy, runner=run, **_paths(tmp_path))
    assert (out["loaded"], out["ref"], out["reason"], out["path"]) == (True, "local", None, str(copy))
    monkeypatch.setenv("EREG_DEFECTS", str(copy))
    assert rules.load_overlay(runner=run, **_paths(tmp_path))["ref"] == "local"
    monkeypatch.setenv("EREG_DEFECTS", str(rules.FIXTURE))
    assert rules.load_overlay(runner=run, **_paths(tmp_path))["ref"] == "fixture"
    assert run.calls == []
    absent = rules.load_overlay(tmp_path / "absent.json", runner=run, **_paths(tmp_path))
    assert (absent["loaded"], absent["ref"], absent["reason"], absent["rules"]) == (False, "none", "none", [])


def test_fetch_is_one_gh_api_call_and_writes_the_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("EREG_DEFECTS", raising=False)
    run = _runner(out=_contents(FIXTURE_DATA))
    out = rules.load_overlay(runner=run, **_paths(tmp_path))
    assert (out["loaded"], out["ref"], out["reason"]) == (True, SHA, None)
    assert [r["id"] for r in out["rules"]] == [r["id"] for r in FIXTURE_DATA["rules"]]
    assert run.calls == [(rules.FETCH_COMMAND, rules.FETCH_TIMEOUT)]
    cmd = run.calls[0][0]
    assert cmd[:2] == ["gh", "api"] and cmd[2].endswith("/contents/defects.json") and len(cmd) == 3
    cache = json.loads((tmp_path / "defects.cache.json").read_text())
    assert cache["sha"] == SHA and isinstance(cache["fetched_at"], int) and cache["data"]["rules"]


def test_fetch_failure_falls_back_to_cache_and_names_the_reason(tmp_path, monkeypatch):
    monkeypatch.delenv("EREG_DEFECTS", raising=False)
    rules.load_overlay(runner=_runner(out=_contents(FIXTURE_DATA)), **_paths(tmp_path))   # seed the cache
    out = rules.load_overlay(runner=_runner(code=1, err="error connecting to api.github.com"), **_paths(tmp_path))
    assert (out["loaded"], out["ref"], out["reason"]) == (True, "cache", "network")
    assert [r["id"] for r in out["rules"]] == [r["id"] for r in FIXTURE_DATA["rules"]]
    timeout = rules.load_overlay(runner=_runner(raises=subprocess.TimeoutExpired(rules.FETCH_COMMAND, 10)), **_paths(tmp_path))
    assert (timeout["ref"], timeout["reason"]) == ("cache", "network")


def test_no_gh_is_not_loaded_or_falls_back_to_the_local_file(tmp_path, monkeypatch):
    monkeypatch.delenv("EREG_DEFECTS", raising=False)
    out = rules.load_overlay(runner=_runner(raises=FileNotFoundError("gh")), **_paths(tmp_path))
    assert (out["loaded"], out["ref"], out["reason"], out["rules"], out["corpus"]) == (False, "none", "no-gh", [], [])
    (tmp_path / "defects.local.json").write_text(json.dumps(FIXTURE_DATA))
    out = rules.load_overlay(runner=_runner(raises=FileNotFoundError("gh")), **_paths(tmp_path))
    assert (out["loaded"], out["ref"], out["reason"]) == (True, "local", "no-gh")


def test_no_access_and_not_authenticated_are_named(tmp_path, monkeypatch):
    monkeypatch.delenv("EREG_DEFECTS", raising=False)
    denied = rules.load_overlay(runner=_runner(code=1, err="gh: Not Found (HTTP 404)"), **_paths(tmp_path))
    assert (denied["loaded"], denied["reason"]) == (False, "no-access")
    anon = rules.load_overlay(runner=_runner(code=4, err="You are not logged into any GitHub hosts. To log in, run: gh auth login"), **_paths(tmp_path))
    assert (anon["loaded"], anon["reason"]) == (False, "not-authenticated")


def test_malformed_source_raises_naming_it(tmp_path, monkeypatch):
    monkeypatch.delenv("EREG_DEFECTS", raising=False)
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    with pytest.raises(ValueError, match=re.escape(str(bad))):
        rules.load_overlay(bad)
    with pytest.raises(ValueError, match="eregulations-knowledge-base"):
        rules.load_overlay(runner=_runner(out=_contents("not an object")), **_paths(tmp_path))
    (tmp_path / "defects.cache.json").write_text("{")
    with pytest.raises(ValueError, match="defects.cache.json"):
        rules.load_overlay(runner=_runner(code=1, err="network"), **_paths(tmp_path))


def test_table_non_empty_and_ids_unique(tmp_path):
    table, overlay = rules.load_rules()
    assert overlay["loaded"], "no overlay loaded (reason: %s); with EREG_DEFECTS_REAL=1 check gh auth status" % overlay["reason"]
    assert len(table) >= 7   # 3 public + >=4 from whichever overlay is loaded
    ids = [r["id"] for r in table]
    assert len(ids) == len(set(ids))
    assert "b7-retired-roxana-image" in ids
    dup = tmp_path / "dup.json"
    dup.write_text(json.dumps({"rules": [_public()[0]]}))
    with pytest.raises(ValueError, match="duplicated"):
        rules.load_rules(defects_path=dup)


def test_every_rule_well_formed():
    for rule in _table():
        missing = REQUIRED - set(rule)
        assert not missing, f"{rule.get('id')}: missing {sorted(missing)}"
        extra = set(rule) - REQUIRED - OPTIONAL
        assert not extra, f"{rule['id']}: unexpected keys {sorted(extra)} (every rule is main; no per-line map, no placeholder)"
        assert rule["surface"] in vt.SURFACES - {"unknown", "A"}, rule["id"]
        assert rule["line"] == ["7.x"], rule["id"]
        kw = rule["match"]["keywords"]
        disc = rule["match"]["discriminators"]
        assert isinstance(kw, list) and kw and isinstance(disc, list) and disc, rule["id"]
        assert rule["candidate_repos"] and set(rule["candidate_repos"]) <= TARGETS, rule["id"]
        assert rule["version_branch"] == "main", rule["id"]
        assert "<" not in rule["read_via"], f"{rule['id']}: read_via carries a placeholder"
        assert rule["also_check_and_disprove"], rule["id"]
        assert rule["closing_state_hint"] in GOTCHA, rule["id"]
        assert rule["memory_ref"].startswith("api-surfaces#"), rule["id"]
        assert rule.get("security", False) in (False, True), rule["id"]
    assert TARGETS <= KNOWN_REPOS


def test_surface_defaults_cover_every_7x_surface_on_main():
    defaults = json.loads((_SKILL / "surface-defaults.json").read_text())
    assert set(defaults) == vt.SURFACES - {"unknown", "A"}
    for surface, entry in defaults.items():
        assert set(entry) == {"candidate_repos", "version_branch"}, surface
        assert entry["candidate_repos"] and set(entry["candidate_repos"]) <= TARGETS, surface
        assert entry["version_branch"] == "main", surface


def test_each_rule_has_a_discriminator_no_same_surface_rule_shares():
    table = _table()
    for rule in table:
        mine = {d.lower() for d in rule["match"]["discriminators"]}
        others = set()
        for other in table:
            if other is not rule and other["surface"] == rule["surface"]:
                others |= {d.lower() for d in other["match"]["discriminators"]}
        assert mine - others, f"{rule['id']}: every discriminator is shared with a rule on the same surface"


def test_no_keyword_looks_like_a_credential_pair():
    """Structural check, no literal here: nothing shaped like user:password may
    be a keyword in a public table."""
    for rule in _table():
        for kw in rule["match"]["keywords"] + rule["match"]["discriminators"]:
            assert not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_.-]+", kw), f"{rule['id']}: {kw!r} looks like user:password"
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_routing_table.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'rules'`

- [ ] **Step 3a: Write the rules loader**

```python
# plugins/eregulations/skills/eregulations-issue/scripts/rules.py
"""Load the routing rules: the public table (gotchas only) plus the defect
overlay from the private knowledge base UNCTAD-eRegistrations/eregulations-knowledge-base.

Resolution order (spec D-5), first hit wins:
  1. an explicit path (the --defects flag)
  2. EREG_DEFECTS (CI points it at fixtures/defects.sample.json)
  3. a fresh `gh api` fetch of defects.json, written to the cache with its blob sha
  4. the last cache (~/.ereg/defects.cache.json) when the fetch fails
  5. ~/.ereg/defects.local.json, a manual fallback
  6. not loaded, with the reason: no-gh | not-authenticated | no-access | network | none

Why one `gh api` call WITHOUT the raw Accept header: the JSON form of the
contents endpoint carries the blob `sha` and the base64 `content` in the same
response, so the cache can never pair a sha from one revision with bytes from
another, and a second metadata call (one more auth check, one more way to
fail) is not needed. The raw form is what a human uses to read the file. The
contents endpoint inlines files up to 1 MB; the overlay is ~30 KB.

A missing overlay is a real answer (no defect memory loaded); a malformed one
raises naming its source (file, cache or repository), so it is never mistaken
for "nothing"."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DEFAULT_TABLE = SKILL / "routing-table.json"
DEFAULT_DEFAULTS = SKILL / "surface-defaults.json"
FIXTURE = SKILL / "fixtures" / "defects.sample.json"
OVERLAY_REPO = "UNCTAD-eRegistrations/eregulations-knowledge-base"
OVERLAY_FILE = "defects.json"
FETCH_COMMAND = ["gh", "api", "repos/%s/contents/%s" % (OVERLAY_REPO, OVERLAY_FILE)]
FETCH_TIMEOUT = 10
EREG_DIR = Path(os.path.expanduser("~")) / ".ereg"
CACHE_PATH = EREG_DIR / "defects.cache.json"
LOCAL_PATH = EREG_DIR / "defects.local.json"
REASONS = ("no-gh", "not-authenticated", "no-access", "network", "none")


class FetchFailed(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _check(data, source):
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ValueError("defects overlay from %s must be a JSON object with a rules list" % source)
    return data


def _parse(text, source):
    try:
        return _check(json.loads(text), source)
    except ValueError as exc:
        if isinstance(exc, json.JSONDecodeError):
            raise ValueError("could not parse defects overlay from %s: %s" % (source, exc))
        raise


def _loaded(data, ref, path, reason=None):
    return {"rules": data["rules"], "corpus": list(data.get("corpus") or []),
            "loaded": True, "ref": ref, "reason": reason, "path": path}


def _not_loaded(reason, path=None):
    return {"rules": [], "corpus": [], "loaded": False, "ref": "none", "reason": reason, "path": path}


def _from_file(path, reason=None):
    p = Path(path)
    ref = "fixture" if p.resolve() == FIXTURE.resolve() else "local"
    return _loaded(_parse(p.read_text(), p), ref, str(p), reason)


def default_runner(cmd, timeout):
    """Run gh; (returncode, stdout, stderr). FileNotFoundError when gh is absent,
    subprocess.TimeoutExpired after `timeout` seconds -- both classified by fetch()."""
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def _classify(stderr):
    s = (stderr or "").lower()
    if "not logged in" in s or "gh auth login" in s or "authentication" in s:
        return "not-authenticated"
    if "404" in s or "not found" in s or "403" in s or "forbidden" in s or "not accessible" in s:
        return "no-access"
    return "network"


def fetch(runner=None, timeout=FETCH_TIMEOUT):
    """One call to the contents endpoint; returns (data, blob sha) or raises FetchFailed."""
    run = runner or default_runner
    try:
        code, out, err = run(FETCH_COMMAND, timeout)
    except FileNotFoundError:
        raise FetchFailed("no-gh")
    except subprocess.TimeoutExpired:
        raise FetchFailed("network")
    if code != 0:
        raise FetchFailed(_classify(err))
    try:
        meta = json.loads(out)
        sha = str(meta["sha"])
        text = base64.b64decode(meta["content"]).decode("utf-8")
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("unexpected contents response from %s for %s: %s" % (OVERLAY_REPO, OVERLAY_FILE, exc))
    return _parse(text, "%s (blob %s)" % (OVERLAY_REPO, sha[:12])), sha


def _write_cache(data, sha, cache_path):
    try:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps({"sha": sha, "fetched_at": int(time.time()), "data": data}, indent=1))
    except OSError:
        pass   # a cache that cannot be written must not fail a fetch that worked


def _read_cache(cache_path, reason):
    p = Path(cache_path)
    if not p.exists():
        return None
    try:
        blob = json.loads(p.read_text())
    except ValueError as exc:
        raise ValueError("could not parse the defects cache at %s: %s" % (p, exc))
    if not isinstance(blob, dict) or "data" not in blob:
        raise ValueError("defects cache at %s must hold {sha, fetched_at, data}" % p)
    return _loaded(_check(blob["data"], p), "cache", str(p), reason)


def load_overlay(path=None, runner=None, cache_path=CACHE_PATH, local_path=LOCAL_PATH):
    explicit = path if path is not None else os.environ.get("EREG_DEFECTS")
    if explicit:
        p = Path(explicit)
        if not p.exists():
            return _not_loaded("none", str(p))
        return _from_file(p)
    try:
        data, sha = fetch(runner)
    except FetchFailed as failed:
        reason = failed.reason
    else:
        _write_cache(data, sha, cache_path)
        return _loaded(data, sha, "%s:%s" % (OVERLAY_REPO, OVERLAY_FILE))
    cached = _read_cache(cache_path, reason)
    if cached is not None:
        return cached
    if Path(local_path).exists():
        return _from_file(local_path, reason)
    return _not_loaded(reason)


def load_rules(table_path=DEFAULT_TABLE, defects_path=None, runner=None):
    public = json.loads(Path(table_path).read_text())
    overlay = load_overlay(defects_path, runner=runner)
    merged = public + overlay["rules"]
    ids = [r["id"] for r in merged]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError("rule ids duplicated between the public table and the overlay: %s" % dup)
    return merged, overlay


def load_defaults(path=DEFAULT_DEFAULTS):
    return json.loads(Path(path).read_text())
```

- [ ] **Step 3b: Write the public table (three gotchas, nothing else)**

Every rule is traceable to `api-surfaces.md` in the private knowledge base (§8 unless the `memory_ref` names another section), as read at the 7.4.2 tips. Keep the ids exactly; the corpus references them. Three rules, each with a non-null `closing_state_hint`: nothing here describes an open defect.

```json
[
 {
  "id": "deploy-basic-auth-prelaunch-gate",
  "surface": "deploy",
  "line": [
   "7.x"
  ],
  "match": {
   "keywords": [
    "basic auth",
    "WWW-Authenticate",
    "401 on every page",
    "password prompt",
    "BASIC_AUTH_ENABLED",
    "BASIC_AUTH_USERS",
    "pre-launch",
    "browser asks for a password"
   ],
   "discriminators": [
    "BASIC_AUTH_ENABLED",
    "WWW-Authenticate"
   ]
  },
  "candidate_repos": [
   "eRegulations-deploy"
  ],
  "version_branch": "main",
  "read_via": "git show main:instances/_template/.env.example",
  "first_evidence_source": "401 + WWW-Authenticate: Basic realm=\"eRegulations\" on GET / of the public site while /release.json still answers 200",
  "also_check_and_disprove": [
   "This is the pre-launch gate (main since 7.3.2), configuration not a defect; there is no built-in credential, so an empty BASIC_AUTH_USERS refuses everyone — check the list before anything else."
  ],
  "closing_state_hint": "NOT_A_BUG",
  "memory_ref": "api-surfaces#3.5 Basic-auth gate"
 },
 {
  "id": "b7-fixed-null-menuid",
  "surface": "B",
  "line": [
   "7.x"
  ],
  "match": {
   "keywords": [
    "resume",
    "menuId",
    "'null'",
    "400",
    "procedure.resume.js",
    "resume page"
   ],
   "discriminators": [
    "procedure.resume",
    "menuId"
   ]
  },
  "candidate_repos": [
   "eRegulations-4.0-Public"
  ],
  "version_branch": "main",
  "read_via": "git show main:Project/WebAppCore/ (procedure.resume.js; locate with git ls-tree)",
  "first_evidence_source": "GET /release.json on the instance: fixed on main by #58 (2026-09-05..11)",
  "also_check_and_disprove": [
   "Read the release from /release.json; older than 7.4.2 → redeploy from channel/stable, do not file. 7.4.2 or later and still reproducible → a regression: file with the release in the title."
  ],
  "closing_state_hint": "FIXED",
  "memory_ref": "api-surfaces#8 B 7.x main (fixed list)"
 },
 {
  "id": "b7-retired-roxana-image",
  "surface": "B",
  "line": [
   "7.x"
  ],
  "match": {
   "keywords": [
    "retired roxana image",
    "no release.json",
    "hand-built image",
    "dot-net8-roxana"
   ],
   "discriminators": [
    "retired roxana image",
    "dot-net8-roxana"
   ]
  },
  "candidate_repos": [
   "eRegulations-deploy"
  ],
  "version_branch": "main",
  "read_via": "git show main:docs/ (redeploy procedure; channel/stable pins)",
  "first_evidence_source": "probe: /release.json 404, then the Basic-auth gate on a later probe → image built from the retired dot-net8-roxana-user-rights branch (the only gated 7.x build without /release.json)",
  "also_check_and_disprove": [
   "Never patch the retired branch (34 commits not on main). Redeploy the instance from channel/stable and re-probe; only file what still reproduces on main."
  ],
  "closing_state_hint": "WONT_FIX",
  "memory_ref": "api-surfaces#3.6"
 }
]
```

- [ ] **Step 3c: Write the surface defaults**

```json
# plugins/eregulations/skills/eregulations-issue/surface-defaults.json
{
 "B": {
  "candidate_repos": [
   "eRegulations-4.0-Public"
  ],
  "version_branch": "main"
 },
 "C": {
  "candidate_repos": [
   "eRegulations-4.0-Admin"
  ],
  "version_branch": "main"
 },
 "SPA": {
  "candidate_repos": [
   "eRegulations-5.0-Admin-SPA"
  ],
  "version_branch": "main"
 },
 "deploy": {
  "candidate_repos": [
   "eRegulations-deploy"
  ],
  "version_branch": "main"
 },
 "monitor": {
  "candidate_repos": [
   "eRegulations-Monitor"
  ],
  "version_branch": "main"
 }
}
```

No line dimension and no Surface A: every routing target is on `main` and ERegWebApi has no 7.x (spec D-4).

- [ ] **Step 3d: Write the fixture overlay (synthetic, what CI loads)**

```json
# plugins/eregulations/skills/eregulations-issue/fixtures/defects.sample.json
{
 "schema_version": "1",
 "rules": [
  {
   "id": "fx-b7-widget-500",
   "surface": "B",
   "line": [
    "7.x"
   ],
   "match": {
    "keywords": [
     "widget",
     "500",
     "save"
    ],
    "discriminators": [
     "widget"
    ]
   },
   "candidate_repos": [
    "eRegulations-4.0-Public"
   ],
   "version_branch": "main",
   "read_via": "git show main:Project/WebAppCore/Controllers/",
   "first_evidence_source": "browser network tab",
   "also_check_and_disprove": [
    "Confirm the widget is the failing control."
   ],
   "closing_state_hint": null,
   "memory_ref": "api-surfaces#8 fixture"
  },
  {
   "id": "fx-b7-gizmo-404",
   "surface": "B",
   "line": [
    "7.x"
   ],
   "match": {
    "keywords": [
     "gizmo",
     "404",
     "save"
    ],
    "discriminators": [
     "gizmo"
    ]
   },
   "candidate_repos": [
    "eRegulations-4.0-Public"
   ],
   "version_branch": "main",
   "read_via": "git show main:Project/WebAppCore/Api/Presentation/Controllers/",
   "first_evidence_source": "server log",
   "also_check_and_disprove": [
    "Confirm the gizmo route is registered."
   ],
   "closing_state_hint": null,
   "memory_ref": "api-surfaces#8 fixture"
  },
  {
   "id": "fx-c7-sprocket-401",
   "surface": "C",
   "line": [
    "7.x"
   ],
   "match": {
    "keywords": [
     "sprocket",
     "401",
     "anonymous"
    ],
    "discriminators": [
     "sprocket"
    ]
   },
   "candidate_repos": [
    "eRegulations-4.0-Admin"
   ],
   "version_branch": "main",
   "read_via": "git show main:Project/WebAppCore/Controllers/",
   "first_evidence_source": "anonymous GET on the sprocket route",
   "also_check_and_disprove": [
    "Confirm no token was sent."
   ],
   "closing_state_hint": null,
   "security": true,
   "memory_ref": "api-surfaces#8 fixture"
  },
  {
   "id": "fx-d7-flywheel-restart-loop",
   "surface": "deploy",
   "line": [
    "7.x"
   ],
   "match": {
    "keywords": [
     "flywheel",
     "restart",
     "loop"
    ],
    "discriminators": [
     "flywheel"
    ]
   },
   "candidate_repos": [
    "eRegulations-deploy"
   ],
   "version_branch": "main",
   "read_via": "git show main:instances/_template/",
   "first_evidence_source": "docker logs of the flywheel service",
   "also_check_and_disprove": [
    "Confirm the restart loop is not a health check refused by the pre-launch gate."
   ],
   "closing_state_hint": null,
   "memory_ref": "api-surfaces#8 fixture"
  }
 ],
 "corpus": [
  {
   "id": "fx-b7-widget-500",
   "surface": "B",
   "line": "7.x",
   "symptom": "Saving the widget fails with a 500."
  },
  {
   "id": "fx-b7-gizmo-404",
   "surface": "B",
   "line": "7.x",
   "symptom": "Saving the gizmo answers 404."
  },
  {
   "id": "fx-c7-sprocket-401",
   "surface": "C",
   "line": "7.x",
   "symptom": "The sprocket route answers 200 to an anonymous call instead of 401."
  },
  {
   "id": "fx-d7-flywheel-restart-loop",
   "surface": "deploy",
   "line": "7.x",
   "symptom": "The flywheel service is stuck in a restart loop after the deploy."
  }
 ]
}
```

Four rules, all `line: ["7.x"]` and `version_branch: "main"`, one with `security: true`; two on Surface B so the same-surface discriminator test has something to distinguish, one on `deploy` next to the public Basic-auth gotcha.

- [ ] **Step 4: Run the table tests, over the fixture and over the fetched overlay**

Run: `python3 -c "import json;print(len(json.load(open('plugins/eregulations/skills/eregulations-issue/routing-table.json'))))" && python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_routing_table.py -q`
Expected: `3` then `12 passed` (fixture loaded by conftest; the loader tests use the stub runner and never call `gh`).

Then, over the private repository (needs `gh auth status` green and membership of `UNCTAD-eRegistrations`): `EREG_DEFECTS_REAL=1 python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_routing_table.py -q`
Expected: `12 passed` over 30 rules (3 public + 27 fetched), and `~/.ereg/defects.cache.json` now exists with the blob sha. If the discriminator test names a rule, give that rule one discriminator no same-surface rule uses (never by deleting another rule's) — **as a pull request on the private repository**, never in this one; until it merges, the local run stays red and says so in the commit message.

- [ ] **Step 5: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue/routing-table.json plugins/eregulations/skills/eregulations-issue/surface-defaults.json plugins/eregulations/skills/eregulations-issue/fixtures/defects.sample.json plugins/eregulations/skills/eregulations-issue/scripts/rules.py plugins/eregulations/skills/eregulations-issue/tests/conftest.py plugins/eregulations/skills/eregulations-issue/tests/test_issue_routing_table.py
git status --short | grep -v '^A\|^M' ; git diff --cached --name-only | grep -cE 'defects\.(local|cache)\.json'   # expect 0: neither the cache nor a local overlay is ever staged
git commit -m "feat(eregulations-issue): gotcha table, surface defaults and the defect-overlay loader

The three gotchas are the only rules safe to publish. Open defects are fetched
at runtime from the private knowledge base with the operator's gh credential
and cached; a local file is only a manual fallback."
```

---
### Task 4: Router script and corpus

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/scripts/route.py`
- Test: `plugins/eregulations/skills/eregulations-issue/tests/test_issue_route.py`
- The defect corpus is **not a repo file**: the gotcha entries below go into the public table's companion list `tests/corpus.gotchas.json`; the defect entries are the overlay's `corpus` key (the fixture in CI, the fetched overlay locally).

**Interfaces:**
- Consumes: `rules.load_rules`, `rules.load_defaults` (Task 3), `validate_ticket.LINES` (Task 1).
- Produces: `route.route(table, surface, line, branch_hint, text, defaults=None, overlay_loaded=True, overlay_ref="none") -> dict` with keys `rule_ids, candidate_repos, match_score, confidence, version_branch, read_via, first_evidence_source, also_check_and_disprove, closing_state_hint, security, memory_refs, line_unknown, surface_unknown, overlay_loaded, overlay_ref`; `line` is `7.x` or `unknown` (a `not-7.x` host was refused before routing); with no scoring winner and `defaults` given, the surface default at `confidence: low` (`rule_ids: []`); `route.filter_rules(table, surface)` filters by surface only (every rule is 7.x); `route.resolve_branch(rule) -> str` returns the rule's `version_branch`; constant `route.RETIRED = "retired-roxana-image"`; CLI `python3 route.py --probe probe.json --text "…" [--table path] [--defects path]` prints the dict as JSON, with `overlay_loaded` and `overlay_ref` taken from the loader. Consumed by `SKILL.md` Step 5.

- [ ] **Step 1: Write the failing tests**

```python
# plugins/eregulations/skills/eregulations-issue/tests/test_issue_route.py
"""Routing is deterministic: filter by surface, count distinct keywords,
count discriminators again (so they weigh double), and derive confidence from
whether the winner is unique and led on a discriminator. A tie is `low` with
every tied repo listed -- never one repo presented as settled. `line` is 7.x
or unknown (a not-7.x host was refused before routing, spec D-1); unknown
caps confidence at medium. The branch is data on the rule and always `main`
(spec D-4); the probe's only branch signal, `retired-roxana-image`, forces
the WONT_FIX gotcha. `overlay_ref` names the defect memory that routed the
ticket (spec D-5). The corpus proves each keyword rule is reachable by a
plausible symptom."""
from __future__ import annotations

import json
from pathlib import Path

import route
import rules

_SKILL = Path(__file__).resolve().parent.parent
# public gotchas plus whatever overlay conftest selected (the fixture in CI, the fetched file locally)
TABLE, OVERLAY = rules.load_rules()
CORPUS = json.loads((_SKILL / "tests" / "corpus.gotchas.json").read_text()) + OVERLAY["corpus"]


def _mini(id_, surface, kw, disc, repos=("R",)):
    return {"id": id_, "surface": surface, "line": ["7.x"], "match": {"keywords": kw, "discriminators": disc},
            "candidate_repos": list(repos), "version_branch": "main", "read_via": "git show main:x",
            "first_evidence_source": "e", "also_check_and_disprove": ["a"], "closing_state_hint": None, "memory_ref": "api-surfaces#8"}


def test_filter_by_surface_only():
    t = [_mini("a", "B", ["x"], ["x"]), _mini("b", "C", ["x"], ["x"])]
    assert [r["id"] for r in route.filter_rules(t, "B")] == ["a"]
    assert route.filter_rules(t, "A") == []


def test_line_unknown_caps_medium():
    t = [_mini("a", "B", ["cog", "wheel"], ["cogwheel"]), _mini("b", "B", ["lever"], ["gasket"])]
    out = route.route(t, "B", "unknown", None, "the cogwheel widget fails")
    assert out["rule_ids"] == ["a"] and out["confidence"] == "medium" and out["line_unknown"] is True
    assert out["version_branch"] == "main"
    assert route.route(t, "B", "7.x", None, "the cogwheel widget fails")["confidence"] == "high"


def test_discriminators_weigh_double_and_give_high():
    t = [_mini("a", "B", ["save", "fails"], ["gasket"]),
         _mini("b", "B", ["save", "fails", "slow"], ["timeout"])]
    out = route.route(t, "B", "7.x", None, "save fails with gasket")
    assert out["rule_ids"] == ["a"] and out["match_score"] == 4 and out["confidence"] == "high"


def test_generic_only_winner_is_medium():
    t = [_mini("a", "B", ["save", "fails"], ["gasket"]), _mini("b", "B", ["slow"], ["timeout"])]
    out = route.route(t, "B", "7.x", None, "save fails")
    assert out["rule_ids"] == ["a"] and out["confidence"] == "medium"


def test_tie_is_low_with_all_repos():
    t = [_mini("a", "B", ["save"], ["x"], repos=("R1",)), _mini("b", "B", ["save"], ["y"], repos=("R2",))]
    out = route.route(t, "B", "7.x", None, "save")
    assert out["confidence"] == "low" and set(out["rule_ids"]) == {"a", "b"}
    assert out["candidate_repos"] == ["R1", "R2"] and out["version_branch"] == "main" and out["read_via"] is None


def test_no_match_is_low_with_no_repo():
    t = [_mini("a", "B", ["save"], ["x"])]
    out = route.route(t, "B", "7.x", None, "nothing relevant")
    assert out["confidence"] == "low" and out["rule_ids"] == [] and out["candidate_repos"] == []
    assert route.route(t, "unknown", "7.x", None, "save")["surface_unknown"] is True


def test_no_overlay_falls_back_to_surface_default():
    out = route.route([], "C", "7.x", None, "anything", defaults=rules.load_defaults(), overlay_loaded=False, overlay_ref="none")
    assert out["rule_ids"] == [] and out["candidate_repos"] == ["eRegulations-4.0-Admin"]
    assert out["version_branch"] == "main" and out["confidence"] == "low"
    assert out["overlay_loaded"] is False and out["overlay_ref"] == "none"


def test_overlay_ref_passes_through():
    out = route.route([_mini("a", "B", ["save"], ["x"])], "B", "7.x", None, "save", overlay_ref="0123456789abcdef")
    assert out["overlay_ref"] == "0123456789abcdef" and out["overlay_loaded"] is True


def test_branch_is_the_rules_version_branch():
    rule = _mini("s", "C", ["x"], ["x"])
    assert route.resolve_branch(rule) == "main"
    out = route.route([rule], "C", "7.x", None, "x")
    assert out["version_branch"] == "main" and out["read_via"] == "git show main:x"


def test_gotcha_hint_and_memory_refs_pass_through():
    g = _mini("g", "deploy", ["basic auth"], ["WWW-Authenticate"]); g["closing_state_hint"] = "NOT_A_BUG"
    out = route.route([g], "deploy", "7.x", None, "WWW-Authenticate basic auth prompt")
    assert out["closing_state_hint"] == "NOT_A_BUG" and out["memory_refs"] == ["api-surfaces#8"]


def test_security_passes_through_from_rule():
    s = _mini("s", "C", ["sprocket"], ["sprocket"]); s["security"] = True
    assert route.route([s], "C", "7.x", None, "sprocket")["security"] is True
    assert route.route([_mini("a", "C", ["x"], ["x"])], "C", "7.x", None, "x")["security"] is False


def test_retired_image_forces_the_wont_fix_gotcha():
    out = route.route(TABLE, "B", "7.x", route.RETIRED, "saving the gizmo answers 404")
    assert out["rule_ids"] == ["b7-retired-roxana-image"] and out["closing_state_hint"] == "WONT_FIX"
    assert out["confidence"] == "high" and out["candidate_repos"] == ["eRegulations-deploy"]


def test_corpus_covers_every_keyword_rule():
    assert {e["id"] for e in CORPUS} == {r["id"] for r in TABLE} - {"b7-retired-roxana-image"}


def test_corpus_routes_to_intended_rule_uniquely():
    for entry in CORPUS:
        out = route.route(TABLE, entry["surface"], entry["line"], None, entry["symptom"])
        assert out["rule_ids"] == [entry["id"]], f"{entry['id']}: routed to {out['rule_ids']} (score {out['match_score']})"
        assert out["confidence"] == "high", f"{entry['id']}: confidence {out['confidence']}"
        assert out["version_branch"] == "main", entry["id"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_route.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'route'`

- [ ] **Step 3: Write `route.py`**

```python
# plugins/eregulations/skills/eregulations-issue/scripts/route.py
"""Deterministic pre-qualification over the public table plus the defect overlay.

filter by surface -> score -> confidence -> branch from the rule. Nothing here
reads the network or guesses: `line` is `7.x` or `unknown` (a not-7.x host was
refused before routing, spec D-1); an unknown line keeps every rule of the
surface and caps confidence at medium; a tie is reported as low with every
tied repository, so the human picks. Every rule is on `main` (spec D-4), so
the branch is rule data. The probe's only branch signal is RETIRED (an image
built from the retired roxana branch), which selects the WONT_FIX gotcha
outright. `overlay_ref` says which defect memory routed the ticket (D-5).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import rules

DEFAULT_TABLE = rules.DEFAULT_TABLE
RETIRED = "retired-roxana-image"
RETIRED_RULE = "b7-retired-roxana-image"
LINES = ("7.x", "unknown")


def load_table(path=DEFAULT_TABLE, defects_path=None):
    """Public gotchas plus the defect overlay; see rules.load_rules."""
    merged, _overlay = rules.load_rules(path, defects_path)
    return merged


def filter_rules(table, surface):
    return [r for r in table if r["surface"] == surface]


def score(rule, text):
    """Distinct matched terms (keywords ∪ discriminators) + matched discriminators
    again, so a discriminator weighs double whether or not it is also a keyword."""
    needle = text.lower()
    kw = {k.lower() for k in rule["match"]["keywords"] if k.lower() in needle}
    disc = [d for d in dict.fromkeys(rule["match"]["discriminators"]) if d.lower() in needle]
    return len(kw | {d.lower() for d in disc}) + len(disc), sorted(kw), disc


def resolve_branch(rule):
    """Every routing target is on main (spec D-4): the branch is rule data."""
    return rule["version_branch"]


def _empty(line_unknown, surface_unknown, surface=None, defaults=None):
    """No rule matched: the surface default when one exists, at low confidence."""
    entry = (defaults or {}).get(surface) or {}
    return {"rule_ids": [], "candidate_repos": list(entry.get("candidate_repos", [])), "match_score": 0,
            "confidence": "low", "version_branch": entry.get("version_branch"), "read_via": None,
            "first_evidence_source": None, "also_check_and_disprove": [], "closing_state_hint": None,
            "security": False, "memory_refs": [], "line_unknown": line_unknown, "surface_unknown": surface_unknown}


def _single(rule, score_, confidence, line_unknown, surface_unknown):
    return {"rule_ids": [rule["id"]], "candidate_repos": list(rule["candidate_repos"]),
            "match_score": score_, "confidence": confidence,
            "version_branch": resolve_branch(rule), "read_via": rule["read_via"],
            "first_evidence_source": rule["first_evidence_source"],
            "also_check_and_disprove": list(rule["also_check_and_disprove"]),
            "closing_state_hint": rule.get("closing_state_hint"), "security": bool(rule.get("security", False)),
            "memory_refs": [rule["memory_ref"]], "line_unknown": line_unknown, "surface_unknown": surface_unknown}


def route(table, surface, line, branch_hint, text, defaults=None, overlay_loaded=True, overlay_ref="none"):
    if line not in LINES:
        raise ValueError("line must be one of %s; a not-7.x host is refused before routing (spec D-1)" % (LINES,))
    out = _route(table, surface, line, branch_hint, text, defaults)
    out["overlay_loaded"] = bool(overlay_loaded)
    out["overlay_ref"] = str(overlay_ref)
    return out


def _route(table, surface, line, branch_hint, text, defaults):
    line_unknown = line == "unknown"
    surface_unknown = surface == "unknown"
    if branch_hint == RETIRED:
        rule = next((r for r in table if r["id"] == RETIRED_RULE), None)
        if rule is not None:
            return _single(rule, 0, "high", line_unknown, surface_unknown)
    scored = []
    for rule in filter_rules(table, surface):
        s, _, disc = score(rule, text)
        if s > 0:
            scored.append((s, rule, disc))
    if not scored:
        return _empty(line_unknown, surface_unknown, surface, defaults)
    best = max(s for s, _, _ in scored)
    winners = [(rule, disc) for s, rule, disc in scored if s == best]
    if len(winners) == 1:
        rule, disc = winners[0]
        confidence = "high" if disc else "medium"
        if line_unknown and confidence == "high":
            confidence = "medium"
        return _single(rule, best, confidence, line_unknown, surface_unknown)
    repos, also = [], []
    for rule, _ in winners:
        for r in rule["candidate_repos"]:
            if r not in repos:
                repos.append(r)
        also.extend(rule["also_check_and_disprove"])
    branches = {resolve_branch(rule) for rule, _ in winners}
    return {"rule_ids": [rule["id"] for rule, _ in winners], "candidate_repos": repos,
            "match_score": best, "confidence": "low",
            "version_branch": branches.pop() if len(branches) == 1 else None, "read_via": None,
            "first_evidence_source": None, "also_check_and_disprove": also, "closing_state_hint": None,
            "security": any(rule.get("security", False) for rule, _ in winners),
            "memory_refs": [rule["memory_ref"] for rule, _ in winners],
            "line_unknown": line_unknown, "surface_unknown": surface_unknown}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pre-qualify a symptom against the public table plus the defect overlay.")
    parser.add_argument("--probe", required=True, help="probe_surface.py output (JSON file)")
    parser.add_argument("--text", required=True, help="symptom + url + captured error text")
    parser.add_argument("--table", default=str(DEFAULT_TABLE))
    parser.add_argument("--defects", default=None, help="defect overlay path; default: EREG_DEFECTS, else the gh fetch / cache / local fallback (rules.py)")
    args = parser.parse_args(argv)
    probe = json.loads(Path(args.probe).read_text())
    merged, overlay = rules.load_rules(args.table, args.defects)
    out = route(merged, probe.get("surface", "unknown"), probe.get("line", "unknown"),
                probe.get("branch_hint"), args.text, defaults=rules.load_defaults(),
                overlay_loaded=overlay["loaded"], overlay_ref=overlay["ref"])
    out["overlay_reason"] = overlay["reason"]
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Write the gotcha corpus**

The corpus test walks the public gotcha corpus **plus** the loaded overlay's `corpus` (the fixture in CI; the 27 entries fetched from the private repository locally with `EREG_DEFECTS_REAL=1`). One entry per keyword rule; the retired-image gotcha is selected by `branch_hint`, not by text. Each symptom names at least one discriminator of its rule and none of a same-surface rule's. Only the gotcha entries are a repo file:

`tests/corpus.gotchas.json`:

```json
[
 {
  "id": "deploy-basic-auth-prelaunch-gate",
  "surface": "deploy",
  "line": "7.x",
  "symptom": "The browser asks for a password on every page: 401 with WWW-Authenticate basic auth because BASIC_AUTH_ENABLED is on and BASIC_AUTH_USERS is empty."
 },
 {
  "id": "b7-fixed-null-menuid",
  "surface": "B",
  "line": "7.x",
  "symptom": "The procedure resume page gets a 400: procedure.resume.js sends the literal string 'null' as menuId."
 }
]
```

- [ ] **Step 5: Run the tests**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_route.py -q`
Expected: `14 passed` over the fixture. Then `EREG_DEFECTS_REAL=1 python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_route.py -q` over the fetched overlay (`gh` authenticated; the corpus is then the two gotcha entries plus the 27 fetched ones). If `test_corpus_routes_to_intended_rule_uniquely` names a rule, the failure message shows the competing ids and score; sharpen that corpus symptom by adding one more of the intended rule's discriminators, or move a plain English keyword out of a competing rule's `discriminators` into its `keywords` — as a pull request on the private repository when the rule is overlay content, never by copying the rule here.

- [ ] **Step 6: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue/scripts/route.py plugins/eregulations/skills/eregulations-issue/tests/corpus.gotchas.json plugins/eregulations/skills/eregulations-issue/tests/test_issue_route.py
git commit -m "feat(eregulations-issue): deterministic routing with corpus"
```

---
### Task 5: Surface probe

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/scripts/probe_surface.py`
- Test: `plugins/eregulations/skills/eregulations-issue/tests/test_issue_probe_surface.py`

**Interfaces:**
- Consumes: `redact.redact` (Task 2).
- Produces: `probe_surface.probe(base_url, opener, api_url=None, timeout=5) -> dict` with keys `surface, line (7.x | not-7.x | unknown), branch_hint (None | "retired-roxana-image"), release (str | None), evidence (list of {host, probe, status, conclusion}), unresolved (list[str])`; `probe_surface.Response(status, headers, body)`; constants `MAIN`, `NOT7`, `RETIRED`, `LINES`; opener contract `opener(url: str, timeout: float) -> Response | None` (None = unreachable/timeout), the only thing the tests stub. CLI `python3 probe_surface.py --url U [--api-url A] [--timeout 5]` prints the dict as JSON. The probe answers one question (spec D-3): is this host on 7.x, and which surface; it never tells legacy lines apart.

- [ ] **Step 1: Write the failing tests**

```python
# plugins/eregulations/skills/eregulations-issue/tests/test_issue_probe_surface.py
"""The probe is the only network code in the skill. These tests pin the rules
the spec makes non-negotiable (D-3): GET only and never an Authorization
header; /release.json first, because it is exempt from the Basic-auth gate and
decides `main` even on a fully gated host; a Basic 401 after /release.json
answered 404 is a retired roxana image, not a branch to file against; every
legacy host is one answer, `not-7.x`, reached without any procedure, stylesheet
or spelling request; an undecidable line is reported as unknown, never picked
in the permissive direction -- because the line feeds the unsupported_version
gate."""
from __future__ import annotations

import json

import probe_surface as ps

BASIC = (401, {"WWW-Authenticate": 'Basic realm="eRegulations"'}, "")


class Stub:
    """Maps full URL -> (status, headers, body). Unlisted URLs return `default`
    (404 unless overridden). Records every call so tests can assert what was
    (not) requested."""

    def __init__(self, mapping, unreachable=False, default=(404, {}, "")):
        self.mapping, self.unreachable, self.default, self.calls = mapping, unreachable, default, []

    def __call__(self, url, timeout):
        self.calls.append(url)
        if self.unreachable:
            return None
        status, headers, body = self.mapping.get(url, self.default)
        return ps.Response(status, {k.lower(): v for k, v in headers.items()}, body)


PUB = "https://public.example"
API = "https://api.example"
ADM = "https://admin.example"


def _j(obj, status=200):
    return (status, {"content-type": "application/json"}, json.dumps(obj))


def test_release_json_track_admin_api_core_is_c7():
    out = ps.probe(API, Stub({API + "/release.json": _j({"track": "admin-api-core", "version": "7.4.2", "release": "7.4.2"})}))
    assert (out["surface"], out["line"], out["branch_hint"]) == ("C", "7.x", None)


def test_release_json_on_public_is_b7_main():
    out = ps.probe(PUB, Stub({PUB + "/release.json": _j({"version": "7.4.2", "release": "7.4.2"})}))
    assert (out["surface"], out["line"], out["branch_hint"]) == ("B", "7.x", None)


def test_gated_main_is_decided_by_release_json_alone():
    stub = Stub({PUB + "/release.json": _j({"version": "7.4.2", "release": "7.4.2"})}, default=BASIC)
    out = ps.probe(PUB, stub)
    assert (out["surface"], out["line"], out["branch_hint"]) == ("B", "7.x", None)
    assert stub.calls == [PUB + "/release.json"]


def test_basic_401_after_release_404_is_retired_image_and_stops():
    stub = Stub({PUB + "/release.json": (404, {}, "")}, default=BASIC)
    out = ps.probe(PUB, stub)
    assert (out["surface"], out["line"], out["branch_hint"]) == ("B", "7.x", ps.RETIRED)
    assert stub.calls == [PUB + "/release.json", PUB + "/health"]


def test_basic_401_with_release_unreachable_is_b7_undecided():
    class Flaky(Stub):
        def __call__(self, url, timeout):
            self.calls.append(url)
            return None if url.endswith("/release.json") else ps.Response(*BASIC[:1], {"www-authenticate": BASIC[1]["WWW-Authenticate"]}, "")
    out = ps.probe(PUB, Flaky({}))
    assert (out["surface"], out["line"], out["branch_hint"]) == ("B", "7.x", None)
    assert any("release.json" in u for u in out["unresolved"])


def test_admin_web_hops_to_api_url_from_env_script():
    index = '<html><script>window.__env={"apiUrl":"%s"}</script></html>' % API
    stub = Stub({ADM + "/release.json": _j({"release": "7.4.2"}),
                 ADM + "/": (200, {"content-type": "text/html"}, index),
                 API + "/release.json": _j({"track": "admin-api-core", "version": "7.4.1"})})
    out = ps.probe(ADM, stub)
    assert (out["surface"], out["line"]) == ("C", "7.x")
    assert any(e["host"] == API for e in out["evidence"])


def test_admin_web_without_reachable_api_is_spa():
    stub = Stub({ADM + "/release.json": _j({"release": "7.4.2"}), ADM + "/": (200, {"content-type": "text/html"}, "<html>no env</html>")})
    out = ps.probe(ADM, stub)
    assert (out["surface"], out["line"], out["branch_hint"]) == ("SPA", "7.x", None)
    assert out["unresolved"]


def test_api_url_flag_overrides_hop():
    stub = Stub({ADM + "/health": (200, {"content-type": "text/plain"}, "ok"),
                 API + "/swagger/v1/swagger.json": _j({"paths": {"/api/user": {}}})})
    out = ps.probe(ADM, stub, api_url=API)
    assert (out["surface"], out["line"]) == ("C", ps.NOT7)


def test_health_json_ok_is_c7():
    assert ps.probe(API, Stub({API + "/health": _j({"status": "ok"})}))["surface"] == "C"


def test_swagger_variants():
    """One 7.x signature (api/permission); every other swagger shape is one answer, not-7.x."""
    assert ps.probe(API, Stub({API + "/swagger/v1/swagger.json": _j({"paths": {"/api/permission": {}, "/api/user": {}}})}))["line"] == "7.x"
    c_old = ps.probe(API, Stub({API + "/swagger/v1/swagger.json": _j({"paths": {"/api/user": {}}})}))
    assert (c_old["surface"], c_old["line"]) == ("C", ps.NOT7)
    a_new = ps.probe(API, Stub({API + "/swagger/v1.1/swagger.json": _j({"paths": {"/Procedures/{id}": {}}})}))
    assert (a_new["surface"], a_new["line"]) == ("A", ps.NOT7)
    a_old = ps.probe(API, Stub({API + "/swagger/docs/v1": _j({"paths": {"/Procedures/{id}": {}}})}))
    assert (a_old["surface"], a_old["line"]) == ("A", ps.NOT7)


def test_country_is_a_not_7x():
    out = ps.probe(API, Stub({API + "/Country": _j({"id": 1, "name": "x", "links": []})}))
    assert (out["surface"], out["line"]) == ("A", ps.NOT7)


def test_legacy_public_is_b_not_7x_without_extra_requests():
    """A Public host with no 7.x signature is refused as not-7.x; the probe does not
    try to tell which legacy line it is (spec D-3)."""
    stub = Stub({PUB + "/api/isauthenticated": (401, {}, "")})
    out = ps.probe(PUB, stub)
    assert (out["surface"], out["line"], out["branch_hint"]) == ("B", ps.NOT7, None)
    assert not any("/api/procedure" in c or "/Home/" in c for c in stub.calls), stub.calls
    assert ps.probe(PUB, Stub({PUB + "/api/isauthenticated": (200, {}, "false")}))["line"] == ps.NOT7


def test_legacy_public_with_release_json_unreachable_is_unknown():
    class Flaky(Stub):
        def __call__(self, url, timeout):
            self.calls.append(url)
            if url.endswith("/release.json"):
                return None
            return ps.Response(401, {}, "") if url.endswith("/api/isauthenticated") else ps.Response(404, {}, "")
    out = ps.probe(PUB, Flaky({}))
    assert (out["surface"], out["line"]) == ("B", "unknown")
    assert any("release.json" in u for u in out["unresolved"])


def test_unreachable_is_unknown_with_unresolved():
    out = ps.probe(PUB, Stub({}, unreachable=True))
    assert out["surface"] == "unknown" and out["unresolved"]


def test_never_calls_tariffs_and_default_opener_sends_no_authorization():
    stub = Stub({PUB + "/api/isauthenticated": (401, {}, "")})
    ps.probe(PUB, stub)
    assert not any("/api/tariffs" in c for c in stub.calls)
    req = ps.build_request(PUB + "/release.json")
    assert req.get_method() == "GET"
    assert not req.has_header("Authorization") and not req.has_header("Cookie")


def test_evidence_is_redacted_including_host():
    stub = Stub({PUB + "/release.json": (500, {"content-type": "text/plain"}, "db at 192.0.2.9 refused")})
    assert "192.0.2.9" not in json.dumps(ps.probe(PUB, stub))
    assert "192.0.2.7" not in json.dumps(ps.probe("http://192.0.2.7", Stub({})))


def test_empty_release_json_is_not_admin_web():
    stub = Stub({PUB + "/release.json": _j({})})
    out = ps.probe(PUB, stub)
    assert out["surface"] != "SPA" and (PUB + "/") not in stub.calls


def test_release_string_is_exposed():
    out = ps.probe(PUB, Stub({PUB + "/release.json": _j({"version": "7.4.2", "release": "7.4.2"})}))
    assert out["release"] == "7.4.2"
    assert ps.probe(PUB, Stub({PUB + "/release.json": _j({"version": "7.4.1"})}))["release"] == "7.4.1"
    assert ps.probe(PUB, Stub({PUB + "/release.json": (404, {}, "")}))["release"] is None


def test_nothing_decisive_is_unknown():
    out = ps.probe(PUB, Stub({}))
    assert (out["surface"], out["line"], out["branch_hint"]) == ("unknown", "unknown", None)
    assert out["unresolved"] and out["line"] in ps.LINES
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_probe_surface.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'probe_surface'`

- [ ] **Step 3: Write `probe_surface.py`**

```python
# plugins/eregulations/skills/eregulations-issue/scripts/probe_surface.py
"""Read-only identification of an eRegulations host: which surface (A/B/C/SPA)
and whether it is on 7.x, following api-surfaces.md §1.1 (private knowledge base copy,
7.4.2 tips). The line is one of three answers (spec D-3): "7.x", "not-7.x" or
"unknown". The skill refuses anything that is not 7.x, so the probe never
tells 4.x, 5.x and 6.x apart and sends no procedure, stylesheet or spelling
request.

Rules that are not negotiable:
- GET only, anonymous. No Authorization, no Cookie, no body, no redirects
  into a login page. Never /api/tariffs/* (rate-limited external proxy).
- /release.json first: it is exempt from the Basic-auth gate, so it decides
  `main` even on a fully gated host, and it exposes the running release.
- A 401 carrying WWW-Authenticate: Basic realm="eRegulations" on any later
  probe, after /release.json answered 404, is a Public image built from the
  retired roxana branch (the only gated 7.x build without /release.json):
  branch_hint RETIRED, stop. If /release.json was unreachable, say B 7.x with
  branch_hint None and an unresolved note.
- Admin-api, admin-web and public are three hosts. An admin-web answer makes
  the script read window.__env.apiUrl from the index and probe that host.
- Not 7.x is one answer: swagger with api/user and no api/permission -> C
  not-7.x; a swagger or /Country shaped like ERegWebApi -> A not-7.x;
  /api/isauthenticated answering 200/401 without any 7.x signature -> B
  not-7.x, provided /release.json actually answered (a 404); if it was
  unreachable the absence proves nothing and the line stays unknown.
- Undecidable stays undecided: line "unknown" + an `unresolved` entry. unknown
  is not 7.x: the gate then runs on the overlay's word (spec D-2).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections import namedtuple

import redact

Response = namedtuple("Response", "status headers body")

MAIN = "main"
NOT7 = "not-7.x"
RETIRED = "retired-roxana-image"
LINES = ("7.x", NOT7, "unknown")
USER_AGENT = "eregulations-issue-probe (read-only)"
_ENV_RE = re.compile(r"window\.__env\s*=\s*(\{.*?\})", re.S)


class _Decisive(Exception):
    def __init__(self, surface, line, branch_hint):
        super().__init__(surface)
        self.surface, self.line, self.branch_hint = surface, line, branch_hint


def build_request(url):
    return urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT, "Accept": "*/*"})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def default_opener(url, timeout):
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(build_request(url), timeout=timeout) as resp:
            return Response(resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read(65536).decode("utf-8", "replace"))
    except urllib.error.HTTPError as err:
        return Response(err.code, {k.lower(): v for k, v in err.headers.items()}, err.read(65536).decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _json(resp):
    try:
        return json.loads(resp.body)
    except (ValueError, TypeError):
        return None


class _Session:
    def __init__(self, opener, timeout):
        self.opener, self.timeout = opener, timeout
        self.evidence, self.unresolved = [], []
        self.release_status = {}   # base -> status of /release.json (None = unreachable)
        self.release = None        # release string from the first 200 /release.json, for the FIXED gotchas

    def get(self, base, path, note=""):
        url = base.rstrip("/") + path
        resp = self.opener(url, self.timeout)
        if path == "/release.json":
            self.release_status[base] = None if resp is None else resp.status
        if resp is None:
            self.evidence.append({"host": redact.redact(base), "probe": path, "status": None, "conclusion": "unreachable or timeout"})
            self.unresolved.append("%s: unreachable or timeout" % path)
            return None
        www = resp.headers.get("www-authenticate", "")
        if resp.status == 401 and 'basic realm="eregulations"' in www.lower():
            if self.release_status.get(base) == 404:
                self.evidence.append({"host": redact.redact(base), "probe": path, "status": 401,
                                      "conclusion": "Basic-auth gate without /release.json -> image built from the retired roxana branch"})
                raise _Decisive("B", "7.x", RETIRED)
            self.evidence.append({"host": redact.redact(base), "probe": path, "status": 401, "conclusion": "Basic-auth pre-launch gate -> B 7.x"})
            self.unresolved.append("/release.json was unreachable, so main vs a retired roxana image is undecided behind the Basic-auth gate")
            raise _Decisive("B", "7.x", None)
        self.evidence.append({"host": redact.redact(base), "probe": path, "status": resp.status,
                              "conclusion": redact.redact((note + " " + resp.body[:200]).strip())})
        return resp


def _result(surface, line, branch_hint):
    return {"surface": surface, "line": line, "branch_hint": branch_hint}


def _probe_host(s, base, api_url, allow_hop):
    # 1. /release.json (exempt from the Basic-auth gate): the application answering
    r = s.get(base, "/release.json")
    j = _json(r) if r is not None and r.status == 200 else None
    if isinstance(j, dict):
        if s.release is None:
            s.release = j.get("release") or j.get("version") or None
        if j.get("track") == "admin-api-core":
            return _result("C", "7.x", None)
        if set(j) == {"release"}:
            return _hop(s, base, api_url) if allow_hop else _result("SPA", "7.x", None)
        return _result("B", "7.x", None)
    # 2. /health
    r = s.get(base, "/health")
    if r is not None and r.status == 200:
        j = _json(r)
        if isinstance(j, dict) and j.get("status") == "ok":
            return _result("C", "7.x", None)
        if r.body.strip() == "ok" or (isinstance(j, dict) and j.get("status") == "up"):
            return _hop(s, base, api_url) if allow_hop else _result("SPA", "7.x", None)
    # 3. swagger: one 7.x signature, else one not-7.x reading per surface
    r = s.get(base, "/swagger/v1/swagger.json")
    j = _json(r) if r is not None and r.status == 200 else None
    if isinstance(j, dict):
        paths = " ".join(j.get("paths", {}).keys()).lower()
        if "api/permission" in paths:
            return _result("C", "7.x", None)
        if "api/user" in paths:
            return _result("C", NOT7, None)
    for swagger in ("/swagger/v1.1/swagger.json", "/swagger/docs/v1"):
        r = s.get(base, swagger)
        j = _json(r) if r is not None and r.status == 200 else None
        if isinstance(j, dict) and "/Procedures/{id}" in j.get("paths", {}):
            return _result("A", NOT7, None)
    # 4. /Country (Surface A, swagger off)
    r = s.get(base, "/Country")
    j = _json(r) if r is not None and r.status == 200 else None
    if isinstance(j, dict) and "id" in j and "links" in j:
        return _result("A", NOT7, None)
    # 5. Surface B without any 7.x signature (we only get here when /release.json was not 200)
    r = s.get(base, "/api/isauthenticated")
    if r is not None and r.status in (200, 401):
        if s.release_status.get(base) is None:
            s.unresolved.append("/release.json was unreachable, so the missing 7.x signature proves nothing: B line undecided")
            return _result("B", "unknown", None)
        return _result("B", NOT7, None)
    s.unresolved.append("no decisive probe answered on %s" % redact.redact(base))
    return _result("unknown", "unknown", None)


def _hop(s, base, api_url):
    target = api_url
    if not target:
        r = s.get(base, "/", note="admin-web index")
        m = _ENV_RE.search(r.body) if r is not None else None
        env = _json(Response(200, {}, m.group(1))) if m else None
        target = env.get("apiUrl") if isinstance(env, dict) else None
    if not target:
        s.unresolved.append("admin-web answered but no admin-api URL could be read from window.__env")
        return _result("SPA", "7.x", None)
    out = _probe_host(s, target.rstrip("/"), None, allow_hop=False)
    if out["surface"] in ("unknown", "SPA"):
        s.unresolved.append("admin-api at the URL read from admin-web is unreachable")
        return _result("SPA", "7.x", None)
    return out


def probe(base_url, opener=default_opener, api_url=None, timeout=5):
    s = _Session(opener, timeout)
    try:
        out = _probe_host(s, base_url.rstrip("/"), api_url, allow_hop=True)
    except _Decisive as d:
        out = _result(d.surface, d.line, d.branch_hint)
    assert out["line"] in LINES
    out["release"] = s.release
    out["evidence"] = s.evidence
    out["unresolved"] = s.unresolved
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Identify the surface of an eRegulations host and whether it is on 7.x (GET only).")
    parser.add_argument("--url", required=True)
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)
    json.dump(probe(args.url, api_url=args.api_url, timeout=args.timeout), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_probe_surface.py -q`
Expected: `19 passed`. `test_basic_401_after_release_404_is_retired_image_and_stops` depends on `_Session.get` recording the `/release.json` status **before** the Basic-auth check runs on the next probe; `test_gated_main_is_decided_by_release_json_alone` depends on `/release.json` being the very first request; `test_legacy_public_is_b_not_7x_without_extra_requests` proves the probe stops at the first legacy signature instead of trying to tell legacy lines apart (spec D-3).

- [ ] **Step 5: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue/scripts/probe_surface.py plugins/eregulations/skills/eregulations-issue/tests/test_issue_probe_surface.py
git commit -m "feat(eregulations-issue): read-only surface/line probe (7.4.2 probe table)"
```

---
### Task 6: Gate context builder and gate cases

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/scripts/gate_context.py`
- Test: `plugins/eregulations/skills/eregulations-issue/tests/test_issue_gate_cases.py`

**Interfaces:**
- Consumes: `gates.evaluate(context) -> list[decision]` from `ereg-router/scripts/gates.py` (on `sys.path` via conftest); `fleet_resolve.py` output shape (`host, version, platform, posture, version_major, drift, unresolved, known_instance, known_slugs, source`).
- Produces: `gate_context.major(v) -> str|None`; `line_major(overlay_version, probed_line) -> str|None` (the D-2 rule: probe `7.x` → `"7"`; probe `not-7.x` → the overlay's major when it is not `"7"`, else the literal `"not-7"`, which `gates.py` blocks non-overridably; probe `unknown`/`None` → the overlay's major); `version_mismatch(overlay_version, probed_line) -> bool` (overlay major ≠ `"7"` while the probe says `7.x`, or overlay `"7"` while the probe says `not-7.x`); `build_bug_context(resolve, probed_line=None, secondary_kinds=()) -> dict`; `build_feature_context(secondary_kinds=()) -> dict` (always 7.x); `honoured(decisions, feature) -> list`; `blocking(decisions) -> list`. CLI `python3 gate_context.py --resolve resolve.json [--probe probe.json] [--upgrade]` or `--feature` prints the context JSON for `gates.py`; `--honour feature` filters `gates.py` decisions on stdin.

- [ ] **Step 1: Write the failing tests**

```python
# plugins/eregulations/skills/eregulations-issue/tests/test_issue_gate_cases.py
"""The spec's line rule (D-2) in code, exercised end-to-end through the
router's real gates.py: a 200 from /release.json is the application answering
and decides the line; a probe that says not-7.x makes the gate block
non-overridably whatever the overlay says; a probe that could not decide
leaves the overlay's word standing; a feature is judged on
unsupported_version alone and is always 7.x."""
from __future__ import annotations

import gate_context as gc
import gates


def _resolve(**over):
    base = {"instance": "alpha", "host": "host-safe", "version": "7.2", "platform": "ubuntu", "posture": "ok",
            "version_major": "7", "source": "overlay", "drift": [], "unresolved": [],
            "known_instance": True, "known_slugs": ["alpha", "bravo"]}
    base.update(over)
    return base


def _gate(decisions, name):
    return next(d for d in decisions if d["gate"] == name)


def test_major_parsing():
    assert gc.major("7.2") == "7" and gc.major("7.x") == "7" and gc.major("5") == "5"
    assert gc.major("unknown") is None and gc.major(None) is None and gc.major("") is None


def test_line_rule_d2():
    """The table in spec Step 3, row by row."""
    assert gc.line_major("7.2", "7.x") == "7"
    assert gc.line_major("7.2", "not-7.x") == "not-7"
    assert gc.line_major("5.1", "7.x") == "7"
    assert gc.line_major("5.1", "not-7.x") == "5"
    assert gc.line_major("7.2", "unknown") == "7"
    assert gc.line_major("5.1", "unknown") == "5"
    assert gc.line_major("7.2", None) == "7"
    assert gc.line_major(None, "7.x") == "7"
    assert gc.line_major(None, "not-7.x") == "not-7"
    assert gc.line_major(None, "unknown") is None


def test_version_mismatch_flag():
    assert gc.version_mismatch("5.1", "7.x") is True
    assert gc.version_mismatch("7.2", "not-7.x") is True
    assert gc.version_mismatch("7.2", "7.x") is False
    assert gc.version_mismatch("5.1", "not-7.x") is False
    assert gc.version_mismatch("7.2", "unknown") is False
    assert gc.version_mismatch(None, "7.x") is False


def test_bug_context_never_copies_resolution_metadata():
    ctx = gc.build_bug_context(_resolve(), probed_line="7.x")
    assert "known_instance" not in ctx and "known_slugs" not in ctx and "drift" not in ctx
    assert ctx["kind"] == "bugfix" and ctx["secondary_kinds"] == []
    assert ctx["touches_admin_public"] is False and ctx["targets_admin_deploy"] is False
    assert ctx["branch_pair_valid"] is None and ctx["media_mount"] is None
    assert ctx["posture"] == "ok" and ctx["platform"] == "ubuntu" and ctx["version_major"] == "7"


def test_overlay_7_probe_not_7x_blocks_non_overridably():
    """The overlay is stale; the application answered. gates.py blocks the literal
    "not-7" as an unresolved version; the skill words the refusal itself."""
    ctx = gc.build_bug_context(_resolve(), probed_line="not-7.x")
    assert ctx["version_major"] == "not-7"
    d = _gate(gates.evaluate(ctx), "unsupported_version")
    assert d["status"] == "block" and d["overridable"] is False


def test_overlay_5_probe_7x_passes_with_mismatch():
    resolve = _resolve(version="5.1", version_major="5")
    ctx = gc.build_bug_context(resolve, probed_line="7.x")
    assert ctx["version_major"] == "7"
    assert _gate(gates.evaluate(ctx), "unsupported_version")["status"] == "pass"
    assert gc.version_mismatch(resolve["version"], "7.x") is True


def test_overlay_7_probe_unknown_passes_on_the_overlays_word():
    ctx = gc.build_bug_context(_resolve(), probed_line="unknown")
    assert ctx["version_major"] == "7"
    assert _gate(gates.evaluate(ctx), "unsupported_version")["status"] == "pass"


def test_overlay_5_probe_unknown_blocks():
    ctx = gc.build_bug_context(_resolve(version="5.1", version_major="5"), probed_line="unknown")
    assert _gate(gates.evaluate(ctx), "unsupported_version")["status"] == "block"


def test_clean_7x_passes_and_compromised_blocks():
    ok = gates.evaluate(gc.build_bug_context(_resolve(), probed_line="7.x"))
    assert not gc.blocking(ok)
    bad = gates.evaluate(gc.build_bug_context(_resolve(posture="compromised"), probed_line=None))
    assert _gate(bad, "host_posture")["status"] == "block"


def test_feature_context_is_judged_on_unsupported_version_only():
    decisions = gc.honoured(gates.evaluate(gc.build_feature_context()), feature=True)
    assert [d["gate"] for d in decisions] == ["unsupported_version"] and decisions[0]["status"] == "pass"
    ctx = gc.build_feature_context()
    assert ctx["kind"] == "dev" and ctx["version_major"] == "7" and "posture" not in ctx


def test_honoured_for_bug_returns_everything():
    decisions = gates.evaluate(gc.build_bug_context(_resolve(), probed_line="7.x"))
    assert len(gc.honoured(decisions, feature=False)) == len(decisions)


def test_cli_honour_feature_filters_stdin(monkeypatch, capsys):
    import io, json as _json
    decisions = gates.evaluate(gc.build_feature_context())
    monkeypatch.setattr("sys.stdin", io.StringIO(_json.dumps(decisions)))
    assert gc.main(["--honour", "feature"]) == 0
    out = _json.loads(capsys.readouterr().out)
    assert [d["gate"] for d in out] == ["unsupported_version"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests/test_issue_gate_cases.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gate_context'` (if instead `No module named 'gates'`, the conftest path to `../ereg-router/scripts` is wrong — fix Task 1's conftest)

- [ ] **Step 3: Write `gate_context.py`**

```python
# plugins/eregulations/skills/eregulations-issue/scripts/gate_context.py
"""Build the gate context for gates.py from fleet_resolve.py output and the
probe, applying the spec's line rule (D-2) in code (router Rule 1: no gate
decided from prose).

Line rule: a 200 from /release.json is the application itself answering, so
when the probe decides, its answer is the line; the overlay keeps host and
posture, never the line against a probe that answered.
  probe 7.x     -> version_major "7"; a lower overlay is reported as
                   version_mismatch with the remedy "correct the overlay"
  probe not-7.x -> the overlay's major when it is not "7", else the literal
                   "not-7": gates.py blocks it non-overridably ("target version
                   is unresolved") and the skill words the refusal itself
  probe unknown -> the overlay's major; the probe added no information, the
                   ticket says the line was not confirmed

Resolution metadata (known_instance, known_slugs, drift, unresolved, source)
never enters the context: the gates do not read it and it is not a fact
about a host.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_CONTEXT_FROM_RESOLVE = ("host", "version", "platform", "posture")
NOT7 = "not-7.x"
NOT7_MAJOR = "not-7"


def major(value):
    if not value:
        return None
    head = str(value).strip().split(".")[0]
    return head if head.isdigit() else None


def line_major(overlay_version, probed_line):
    o = major(overlay_version)
    if probed_line == "7.x":
        return "7"
    if probed_line == NOT7:
        return o if (o is not None and o != "7") else NOT7_MAJOR
    return o


def version_mismatch(overlay_version, probed_line):
    o = major(overlay_version)
    if o is None:
        return False
    if probed_line == "7.x":
        return o != "7"
    if probed_line == NOT7:
        return o == "7"
    return False


def build_bug_context(resolve, probed_line=None, secondary_kinds=()):
    ctx = {key: resolve.get(key) for key in _CONTEXT_FROM_RESOLVE}
    ctx.update({
        "kind": "bugfix",
        "secondary_kinds": list(secondary_kinds),
        "version_major": line_major(resolve.get("version"), probed_line),
        "touches_admin_public": False,
        "targets_admin_deploy": False,
        "branch_pair_valid": None,
        "media_mount": None,
    })
    return ctx


def build_feature_context(secondary_kinds=()):
    """A feature is always judged on 7.x (spec D-1): there is no other line to ask for."""
    return {
        "kind": "dev",
        "secondary_kinds": list(secondary_kinds),
        "version_major": "7",
        "touches_admin_public": False,
        "targets_admin_deploy": False,
        "branch_pair_valid": None,
        "media_mount": None,
    }


def honoured(decisions, feature):
    if feature:
        return [d for d in decisions if d["gate"] == "unsupported_version"]
    return list(decisions)


def blocking(decisions):
    return [d for d in decisions if d["status"] == "block"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assemble the gates.py context for eregulations-issue.")
    parser.add_argument("--resolve", help="fleet_resolve.py output (JSON file); omit for a feature")
    parser.add_argument("--probe", help="probe_surface.py output (JSON file)")
    parser.add_argument("--feature", action="store_true", help="build the feature context (always 7.x)")
    parser.add_argument("--upgrade", action="store_true", help="the request is itself the upgrade to 7.x")
    parser.add_argument("--honour", choices=["feature"], help="filter gates.py decisions read on stdin: keep only what a feature is judged on")
    args = parser.parse_args(argv)
    if args.honour:
        decisions = json.load(sys.stdin)
        json.dump(honoured(decisions, feature=True), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    secondary = ("upgrade",) if args.upgrade else ()
    if args.feature:
        ctx = build_feature_context(secondary)
    else:
        if not args.resolve:
            parser.error("--resolve is required for a bug")
        resolve = json.loads(Path(args.resolve).read_text())
        probed = json.loads(Path(args.probe).read_text()).get("line") if args.probe else None
        ctx = build_bug_context(resolve, probed, secondary)
    json.dump(ctx, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests -q`
Expected: `82 passed` (14 validator + 11 redact + 12 table + 14 route + 19 probe + 12 gate cases, over the fixture overlay)

- [ ] **Step 5: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue/scripts/gate_context.py plugins/eregulations/skills/eregulations-issue/tests/test_issue_gate_cases.py
git commit -m "feat(eregulations-issue): gate context with the line rule

A 200 from /release.json is the application answering: the probe decides the
line, the overlay keeps host and posture. A not-7.x reading blocks
non-overridably; an unknown one leaves the overlay's word standing."
```

---

### Task 7: SKILL.md, command, README, plugin version

**Files:**
- Create: `plugins/eregulations/skills/eregulations-issue/SKILL.md`
- Create: `plugins/eregulations/commands/issue.md`
- Modify: `plugins/eregulations/README.md` (add a section before `## Verified (2026-08-26)`)
- Modify: `plugins/eregulations/.claude-plugin/plugin.json` (`"version": "0.2.1"` → `"0.3.0"`)

**Interfaces:**
- Consumes: every CLI from Tasks 1–6 by its exact flags; the router's `fleet_resolve.py` and `gates.py` (never `audit.py`: there is no override to record).
- Produces: the skill the router's Step 5 (Task 8) dispatches to, named `eregulations-issue`.

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: eregulations-issue
description: >
  Report a 7.x eRegulations (Admin, Public/TradePortal, Admin SPA, deploy,
  Monitor) runtime issue or feature request — standardized and pre-qualified
  into a verified qualified-ticket (surface, line, candidate repo, first
  evidence, things to disprove) and filed as a GitHub issue on the right
  UNCTAD-eRegistrations/eRegulations-* repository. 7.x only: an instance that
  is not on 7.x is refused with a pointer to the migration tracking, never
  ticketed. TRIGGER when a human reports a country portal or admin problem
  ("the public site of <instance> shows an error when saving a step", "the
  admin API does not start after the deploy", "a page is reachable without
  logging in"), asks to file or standardize an eRegulations ticket, or requests
  a new eRegulations capability. This is the `bugfix` dispatch target of
  `ereg-router`. DO NOT TRIGGER for eRegistrations 2.x (BPA, DS, GDB, Keycloak,
  Camunda — use bpa-mcp:ereg-issue), for a defect in an MCP tool (bpa-mcp:mcp-issue),
  or for a pure how-to question (answer directly).
allowed-tools: Read, Write, Grep, Glob, Agent, Bash(mkdir -p *), Bash(mktemp *), Bash(python3 *), Bash(git show *), Bash(git ls-tree *), Bash(git -C *), Bash(git rev-parse *), Bash(gh *), Bash(docker logs *), Bash(ssh *), Bash(cat *), Bash(tee *), Bash(echo *), Bash(date *), mcp__atlassian__addCommentToJiraIssue
metadata:
  version: "0.1.0"
  version-date: "2026-09-11"
  argument-hint: "[symptom, instance and url] or [feature: desired behaviour, surface]"
  changelog:
    - "0.1.0 (2026-09-11): initial release — resolve → gate → probe → ground → qualify → emit → validate → disprove → file; 7.x only, a not-7.x host is refused; schema 1.1; three public gotcha rules plus the defect overlay fetched at runtime from the private repository UNCTAD-eRegistrations/eregulations-knowledge-base (cached; ~/.ereg/defects.local.json as a manual fallback)."
---

# eRegulations issue reporting (eregulations-issue)

Turn a vague human report about a **7.x** instance into a verified,
pre-qualified `qualified-ticket`. You PRE-QUALIFY (surface, line, candidate
repo, first evidence, things to disprove); you do NOT diagnose, fix, deploy or
write to any instance. You never send anything but anonymous GET requests to
a host, and only after Step 3 says you may. An instance that is not on 7.x is
refused, not ticketed: the policy since 2026-09-03 is to migrate legacy
instances, never to fix them, and there is no override.

**Order is load-bearing:** resolve → gate → probe → ground → qualify → emit →
validate → disprove → file. Every runnable block below re-assigns `$PLUGIN` and `$RUN`
because shell state does not persist between tool calls; substitute the real
plugin path (the directory holding `skills/eregulations-issue`) and paste each
block whole.

Two rules from `ereg-router` that are not negotiable here either:

1. **Gate decisions come from running `gates.py`**, never from reading prose.
2. **A blocking gate stops the run.** `host_posture` blocks before any host
   contact; `unsupported_version` blocks before anything is filed. Neither is
   overridden here: a refusal states what was seen and files nothing.

## Step 1 — Hard floor (BLOCKS until present)

Ask one question at a time, only for what is missing.

**Bug**
- `symptom` — plain language, user-visible ("saving a step's visibility fails").
- `instance` — the slug the operator overlay knows.
- `url` — the exact page or endpoint. Keep it **without its query string**
  (`redact.strip_query`; run it through `python3 -c` if in doubt): a pasted
  URL can carry a credential in its query string, and it must be neither
  replayed nor filed. The
  probe base URL is derived from it; never ask for a base URL separately.

**Feature**
- `desired_behaviour`, `surface` (B / C / SPA / deploy / monitor — Surface A,
  ERegWebApi, has no 7.x and is refused), `instance` (the one the reporter has
  in mind, or the sentinel `platform` for a platform-wide request), and **one
  of**: a cited existing capability (endpoint, setting, UI element —
  `api-surfaces.md` §2–§4 has the indexes) or an observable behaviour the
  feature changes. Neither → `recommendation_hint: NEEDS-MORE-INFO`; write the
  ticket, file nothing. There is no `line` question: a feature is always 7.x.

**Both:** `expected` vs `actual`, `scope` (one procedure / one instance /
fleet-wide; condition), optional `jira_key` (`ERN-<digits>` only; anything else
is not a key).

The lane is stated after Step 2, not here: it needs the overlay's host.

## Step 2 — Resolve (bugs only; features go to Step 3)

```bash
PLUGIN=<path-to>/plugins/eregulations
RUN=$(mktemp -d /tmp/eregulations-issue.XXXXXX); echo "$RUN"
python3 "$PLUGIN/skills/ereg-router/scripts/fleet_resolve.py" <slug> > "$RUN/resolve.json"; cat "$RUN/resolve.json"
```

- Report every `drift` entry to the user, in chat. Never fill an `unresolved`
  field by inference — not from the country, not from a sibling, not from memory.
- `known_instance: false` → offer the nearest `known_slugs`, ask which was
  meant, stop.
- When `ereg-router` dispatched you, it hands over the `resolve.json` path;
  copy it into `$RUN` and skip the command above. Run Step 3 yourself anyway.

Now state the lane, from **two local checks** only: the repos the routing
rule will name are present on disk (`plan` if not), and the VPN interface
for the overlay's host is up — read from the interface list, **no packet to
the host** (`build` if not, else `execute`). Do **not** test SSH here: an SSH
attempt is host contact, and nothing touches the host before Step 3. SSH
usability is confirmed lazily in Step 4's `execute` grounding. The lane
limits Step 4; it never bypasses Step 3.

## Step 3 — Gate (before any host contact)

Bug (add `--upgrade` when the report asks for the upgrade to 7.x):

```bash
PLUGIN=<path-to>/plugins/eregulations; RUN=<the RUN directory from Step 2>
python3 "$PLUGIN/skills/eregulations-issue/scripts/gate_context.py" --resolve "$RUN/resolve.json" > "$RUN/context.json"
python3 "$PLUGIN/skills/ereg-router/scripts/gates.py" < "$RUN/context.json" | tee "$RUN/gates.json"
```

Feature (the filter keeps only the decision a feature is judged on; the
context has no host, so `host_posture` would otherwise block by construction):

```bash
PLUGIN=<path-to>/plugins/eregulations; RUN=$(mktemp -d /tmp/eregulations-issue.XXXXXX)
python3 "$PLUGIN/skills/eregulations-issue/scripts/gate_context.py" --feature > "$RUN/context.json"
python3 "$PLUGIN/skills/ereg-router/scripts/gates.py" < "$RUN/context.json" \
  | python3 "$PLUGIN/skills/eregulations-issue/scripts/gate_context.py" --honour feature | tee "$RUN/gates.json"
```

Read the decisions (the JSON is the verdict; the exit status only says whether
evaluation ran):

- **Bug, `host_posture: block`** (compromised or unresolved) → report gate,
  reason and remedy verbatim. **No probe, no grounding, no filing.** You may
  write `NOTES.md` with what the reporter said, nothing more. Stop.
- **Bug, `host_posture: warn`** → say the host is degraded; continue read-only.
- **Bug, `unsupported_version: block`** on this first pass (the overlay records
  a legacy version) → note it; Step 5 re-evaluates with the probed line, which
  is the reading that decides (a `200` from `/release.json` is the application
  answering; a stale overlay does not refuse a host that answers 7.x).
- **Feature** → `gates.json` holds the single `unsupported_version` decision,
  `pass` by construction (a feature is always 7.x). Record
  `fleet.source_silent: ["no instance probed (feature)"]`; never copy a gate
  reason into the ticket. Go to Step 5.

The context never contains `known_instance`, `known_slugs` or `drift`
(`gate_context.py` guarantees it), and this skill never sets
`touches_admin_public` or `targets_admin_deploy`: it builds and deploys nothing.

## Step 4 — Probe and light grounding (read-only; bugs only)

```bash
PLUGIN=<path-to>/plugins/eregulations; RUN=<the RUN directory>
python3 "$PLUGIN/skills/eregulations-issue/scripts/probe_surface.py" \
  --url "<scheme://host of the reporter's url, query string already dropped>" \
  [--api-url <admin-api base, if the reporter's url is the admin SPA and you know it>] > "$RUN/probe.json"; cat "$RUN/probe.json"
```

What the probe does and does not do: GET only, anonymous, no redirects into a
login page, never `/api/tariffs/*`. It answers one question — is this host on
7.x, and which surface — with `line` ∈ `7.x` | `not-7.x` | `unknown`; it never
tells legacy lines apart. `/release.json` goes first and is exempt from the
Basic-auth gate, so a gated `main` is decided by it alone. A Basic `401` after
`/release.json` answered `404` means an image built from the retired roxana
branch: `branch_hint: retired-roxana-image`, and Step 5 will return the
`WONT_FIX` gotcha (redeploy from `channel/stable`, never patch that branch).
An admin-web host makes it read `window.__env.apiUrl` and probe the admin-api.
`release` carries the running release when `/release.json` answered (the
`FIXED` gotcha in Step 5 compares it with 7.4.2). When nothing decisive
answered it says `unknown` and names what did not answer in `unresolved`;
never pick a line yourself.

- `line: not-7.x` → the host is not on 7.x. Finish Step 5's second gate pass
  (it records the refusal from `gates.py`, not from prose) and refuse there;
  do no grounding.
- If the overlay `version` and the probed `line` disagree, tell the user (this
  is drift); the ticket will carry `fleet.overlay_version` and `line` and
  `qualification.version_mismatch: true` — never the raw `drift` object.
- Record the slug ↔ URL pairing as a claim: `environment-mapping`,
  `Assumption`, `needs_live_verification: true`.

Then ground by lane, still read-only:

| Lane | Allowed |
| --- | --- |
| `plan` | the probe; one anonymous GET on the reporter's URL to capture the real status and body |
| `build` | plus `git show <branch>:<path>` on local checkouts, at the path the routing rule names |
| `execute` | plus `docker logs <service>` on the resolved host, read-only |

Every captured body or log excerpt passes through the redactor **before** it is
written anywhere:

```bash
PLUGIN=<path-to>/plugins/eregulations; RUN=<the RUN directory>
python3 "$PLUGIN/skills/eregulations-issue/scripts/redact.py" < "$RUN/raw-excerpt.txt" > "$RUN/excerpt.txt"
```

In `build` lane, locate a file the routing rule names only by directory before
reading it: `git -C <checkout> ls-tree -r --name-only <branch> | grep <file>`,
then `git -C <checkout> show <branch>:<path>`.

HARD RULE: log silence ≠ healthy. Record what you observed and which source was
silent (`fleet.source_silent`); never assert health.

## Step 5 — Pre-qualify

```bash
PLUGIN=<path-to>/plugins/eregulations; RUN=<the RUN directory>
python3 "$PLUGIN/skills/eregulations-issue/scripts/route.py" --probe "$RUN/probe.json" \
  --text "<symptom + url + captured error text>" > "$RUN/route.json"; cat "$RUN/route.json"
```

For a feature there is no probe: write `$RUN/probe.json` by hand as
`{"surface": "<reporter surface>", "line": "7.x", "branch_hint": null}`
and run the same command.

`route.py` reads the three public gotchas plus the defect overlay through
`rules.py`, in this order, first hit wins: `--defects <path>`; `EREG_DEFECTS`;
a fresh read of `defects.json` from the private knowledge base
`UNCTAD-eRegistrations/eregulations-knowledge-base` with your `gh` credential (one
`gh api` call, 10 s timeout), cached as `~/.ereg/defects.cache.json` with the
blob sha; the last cache when the fetch fails; `~/.ereg/defects.local.json`
as a manual fallback; else not loaded. Access is membership of the private
knowledge base repository — nothing to copy by hand. Read `route.json`:

- `overlay_ref` — which defect memory routed the ticket: the blob sha (fresh
  fetch), `cache`, `local`, `fixture` or `none`. It goes into
  `qualification.overlay_ref` so a maintainer knows what the router knew.
  `overlay_reason` (when not a fresh fetch) says why: `no-gh`,
  `not-authenticated`, `no-access`, `network`.
- `overlay_loaded: false` — no defect memory could be read (say the reason):
  the result is the surface default at `low`. Add
  `"no defect overlay loaded"` to `fleet.source_silent` and go on: the ticket
  is still worth filing, it just carries no institutional memory.
- `confidence: high` — one rule led on a discriminator. `medium` — generic
  tokens only, or the line is unknown. `low` — a tie or no match: **every**
  tied repo is listed; never present one as settled.
- `version_branch` / `read_via` come from the rule and are always `main`
  (every routing target renamed its 7.x branch on 2026-09-07). `read_via` is
  `null` on a tie; say so in the ticket, do not invent a path.
- `closing_state_hint` set → a known non-defect: `NOT_A_BUG` (the Basic-auth
  pre-launch gate), `FIXED` (a B 7.x defect fixed on `main` between
  2026-09-05 and 2026-09-11 — read the release from `/release.json`; older
  than 7.4.2 means redeploy, not a ticket; 7.4.2+ still reproducing is a
  regression you file **with the release in the title**), or `WONT_FIX`
  (retired roxana image — redeploy from `channel/stable`). The release to
  compare is `probe.json`'s `release`; `null` means `/release.json` did not
  answer and the gotcha cannot be applied — file as a normal ticket and say so.
  Carry the hint into `closing_state`, emit and validate (Steps 7–8); Step 8
  stops there and nothing is filed, except the regression case, which clears
  `closing_state` back to `null` and continues.
- `security: true` — the rule is security-relevant: `severity: high` by
  default and `security: true` in the ticket (Step 6).

**Second gate pass with the probed line (bugs; repeat `--upgrade` if you
passed it in Step 3):**

```bash
PLUGIN=<path-to>/plugins/eregulations; RUN=<the RUN directory>
python3 "$PLUGIN/skills/eregulations-issue/scripts/gate_context.py" --resolve "$RUN/resolve.json" --probe "$RUN/probe.json" [--upgrade] > "$RUN/context.json"
python3 "$PLUGIN/skills/ereg-router/scripts/gates.py" < "$RUN/context.json" | tee "$RUN/gates.json"
```

The gate now sees the line rule's answer: the probe decides when it answered
(`7.x` → `7`, `not-7.x` → not 7), the overlay's value stands when the probe
could not decide. `unsupported_version`:

- `pass` → `recommendation_hint: PROCEED`. If the overlay recorded a lower
  version (`qualification.version_mismatch: true`), tell the user the overlay
  is stale — "the overlay records `<version>`, the host answers 7.x: correct
  the overlay" — and carry `fleet.overlay_version` into the ticket.
- `block` → **refused**, and the refusal is terminal. Tell the user, in this
  order: what the probe saw (surface, `line`, the evidence lines), that the
  policy since 2026-09-03 is to migrate legacy instances rather than fix them,
  where the migration wave is tracked (the operator's
  `INSTANCE-UPGRADE-TRACKING.md`), and that nothing is filed. Write `NOTES.md`
  only (Step 7's headings, `## Status: refused — not on 7.x`); no
  `qualified-ticket.json`, no issue body, no override, no `audit.py` entry, no
  Jira comment. When the overlay records 7 and the probe says `not-7.x`, add
  that the overlay is stale and should be corrected. Stop here.

**Branch pair, evidence only.** If the symptom is a build of Admin and Public
together, run the router's `branch_pair.py` as its Step 4a describes and record
the verdict as an `environment-mapping` claim (`Hard` when the csproj reference
was read). It is never a gate input here.

## Step 6 — Claims and rubric

For each factual statement: `{claim, claim_type, kind, evidence,
needs_live_verification}` with `claim_type` ∈ code-fact | runtime-observation |
environment-mapping | quantitative-estimate | future-prescription and `kind` ∈
Hard | Soft | Assumption (`Hard` needs a `file:line` or a probe evidence entry).
Runtime observations and environment mappings get `needs_live_verification: true`.

Rubric enums are exact: `severity` ∈ critical|high|medium|low|info, `scale` ∈
Small|Medium|Large|Architectural, `kind` ∈ bug|feature|refactor|design|docs|infra|unknown.
`affected_components` = repo-relative paths from the routing rule's `read_via`
plus the claims.

`security: true` and `severity: high` by default when `route.json` says
`security: true` (the overlay marks the rule; which rules are
security-relevant is overlay content, never written here).

## Step 7 — Emit

Issues root: `issues/<slug>/` if the working tree has `issues/CLAUDE.md`,
otherwise `~/Desktop/eregulations-issue-reports/<slug>/`. Slug:
`ERN-1234-<short>` with a Jira key, else `YYYY-MM-DD-<short>`.

```bash
ROOT=<issues root>/<slug>; mkdir -p "$ROOT"
```

Write three files:

- `qualified-ticket.json` — schema 1.1 (`$PLUGIN/skills/eregulations-issue/qualified-ticket.schema.json`;
  the two files under `samples/` are the shapes for a bug and a feature).
  `qualification.overlay_ref` is `route.json`'s `overlay_ref`. `fleet` carries **only** `line`,
  `overlay_version`, `platform`, `source_silent`, `drift` (a boolean).
  **Never** `host`, `posture`, an address, a VPN name, a gate reason that names
  a posture, or an unredacted excerpt. `instance.name` is always present.
- `NOTES.md` — `# <symptom>`, `## Context` (instance, surface/line as probed,
  overlay version if different, lane, reporter), `## Repro`, then stub headings
  `## Findings`, `## Hypotheses-refuted`, `## Fix-options`, `## Verification`,
  `## Status`.
- `issue-body.md` — the human-first report (symptom; surface and line as
  probed; overlay version when it differs; lane; expected vs actual; scope;
  candidate repos with confidence; `also_check_and_disprove`; first evidence
  source; which defect memory routed it — `overlay_ref`), followed by the
  machine block:

  ````
  ```qualified-ticket
  { ...the verbatim contents of qualified-ticket.json... }
  ```
  ````

## Step 8 — Validate (HARD GATE)

```bash
PLUGIN=<path-to>/plugins/eregulations; ROOT=<issues root>/<slug>
python3 "$PLUGIN/skills/eregulations-issue/scripts/validate_ticket.py" "$ROOT/qualified-ticket.json"
```

It MUST print `VALID`. Fix and re-run otherwise. Then re-read the claims: any
`Assumption` presented as fact in the prose gets downgraded in the prose.

- `closing_state` ∈ `NOT_A_BUG` | `INTENTIONAL_DESIGN` | `WONT_FIX` | `FIXED`
  → report the known-non-defect verdict and **stop**. Nothing is filed.
- There is no override path: a ticket only reaches this step for a host the
  gate passed (7.x, or unknown on the overlay's word), so nothing here can
  turn a refusal into a filing.

## Step 8b — Disprove (read-only, before you ask to file)

Spawn **one** fresh subagent (`Agent`, general-purpose) with: the validated
`qualified-ticket.json`, `probe.json`, and the rule's `also_check_and_disprove`
list. Its brief: *try to disprove this ticket; you may read local checkouts
(`git show`) and issue anonymous GETs to the reporter's host only; never send
credentials, never write anything, never contact any other host; answer as
`{"verdict": "stands" | "weakened" | "refuted", "notes": [...]}` where every
note names the claim it touches.* Record the answer under
`qualification.disprove` and re-run Step 8's validator.

- `refuted` → `recommendation_hint: NEEDS-MORE-INFO`; the notes go to
  `NOTES.md` under `## Hypotheses-refuted`; nothing is filed; tell the user
  what would make the report stand.
- `weakened` → downgrade every named claim to `Assumption`, append the notes
  to the issue body under *Open questions*, continue.
- `stands` → continue.

Skip this step only when Step 8 already stopped on a gotcha. Step 8's
self-scan is not this step.

## Step 9 — File (explicit, opt-in)

Ask the user whether to file. Then, in order:

```bash
gh auth status
gh repo view UNCTAD-eRegistrations/<candidate> --json visibility --jq .visibility
```

- Visibility must be `PRIVATE`. If it is not: **stop for any ticket** (the
  body carries the instance slug) and ask the user how to proceed; a
  `security: true` ticket is never filed on a public repo — point the user to
  GitHub private vulnerability reporting or a private channel and leave the
  files on disk.
- `confidence: low` with several candidates → ask the user which repo. If they
  do not know, save and stop: a ticket in the wrong repo is worse than none.

```bash
ROOT=<issues root>/<slug>
gh label create eregulations-issue --repo UNCTAD-eRegistrations/<candidate> --force --description "Filed by the eregulations-issue skill" 2>/dev/null && LABELS="--label eregulations-issue" || LABELS=""
gh issue create --repo UNCTAD-eRegistrations/<candidate> --title "<symptom>" --body-file "$ROOT/issue-body.md" $LABELS
```

Only when the ticket has `security: true`, run this **before** the
`gh issue create` line above and append its label:

```bash
gh label create security --repo UNCTAD-eRegistrations/<candidate> --force 2>/dev/null && LABELS="$LABELS --label security"
```

If label creation is refused (no write permission), file without labels and say
so — the fenced `qualified-ticket` block is the machine contract, the label is
a convenience.

**Jira, opt-in.** Only if `jira_key` is set **and** something was filed **and**
`mcp__atlassian__addCommentToJiraIssue` is available: post one comment on that
key containing the router-style handoff block **without** its host and posture
lines, plus the GitHub issue URL. No key → no Jira. Nothing filed → no Jira.
Tool unavailable → say so; the filing still stands.

## References

| File | What it holds |
| --- | --- |
| `routing-table.json`, `surface-defaults.json` | the three public gotchas (one `NOT_A_BUG`, one `FIXED`, one `WONT_FIX`) and the surface → repo defaults (always `main`); the defect rules are fetched from the private repository `UNCTAD-eRegistrations/eregulations-knowledge-base` by `scripts/rules.py` (cache `~/.ereg/defects.cache.json`, manual fallback `~/.ereg/defects.local.json`) |
| `qualified-ticket.schema.json`, `samples/` | the 1.1 contract and two worked shapes |
| `api-surfaces.md` in the private knowledge base: `gh api repos/UNCTAD-eRegistrations/eregulations-knowledge-base/contents/api-surfaces.md -H 'Accept: application/vnd.github.raw'` | §1 probe table, §2–§4 endpoint indexes, §8 known defects, §9 things you must not do |
| `../ereg-router/references/gates.md`, `resolution.md` | what each gate means; overlay schema, drift, unresolved |
```

- [ ] **Step 2: Write `commands/issue.md`**

```markdown
---
description: Report a 7.x eRegulations runtime issue or feature request — pre-qualified into a qualified-ticket and filed as a GitHub issue on the right eRegulations-* repository after the router's gates pass; an instance that is not on 7.x is refused, never ticketed.
argument-hint: "[symptom, instance and url] or [feature: desired behaviour, surface]"
effort: medium
allowed-tools: Read, Write, Grep, Glob, Agent, Bash(mkdir -p *), Bash(mktemp *), Bash(python3 *), Bash(git show *), Bash(git ls-tree *), Bash(git -C *), Bash(git rev-parse *), Bash(gh *), Bash(docker logs *), Bash(ssh *), Bash(cat *), Bash(tee *), Bash(echo *), Bash(date *), mcp__atlassian__addCommentToJiraIssue
---

Invoke the `eregulations-issue` skill to report an eRegulations runtime issue or
feature request. It resolves the instance, runs the router's gates before any
host contact, probes the surface and line read-only, pre-qualifies the report
against the routing table, validates the qualified-ticket and, only on explicit
confirmation, files it with `gh`.

This is the explicit entry point (`/eregulations:issue`). Plain English reaches
the same skill: describing an eRegulations problem triggers it, and `ereg-router`
dispatches `bugfix` requests here in every lane.

If the user supplied details, pass them as the initial report:

$ARGUMENTS
```

- [ ] **Step 3: Add the README section**

Insert before `## Verified (2026-08-26)` in `plugins/eregulations/README.md`:

```markdown
## Reporting an issue

`/eregulations:issue <symptom, instance, url>` — or plain English — runs the
`eregulations-issue` skill for **7.x instances**: it resolves the instance from
your overlay, runs the router's gates **before** touching any host, probes the
surface and line with anonymous GETs only, pre-qualifies the report against
three public gotcha rules plus the defect rules fetched at runtime from the
private knowledge base `UNCTAD-eRegistrations/eregulations-knowledge-base` (access is
membership of that repository — `gh auth status` must be green; the file is
cached in `~/.ereg/defects.cache.json`, and without any access every ticket
routes to the surface default at low confidence), validates a
`qualified-ticket` 1.1, has a fresh read-only subagent try to disprove it and,
on your confirmation, files it with `gh` on the candidate `eRegulations-*`
repository. Feature requests take the same path without a probe. A Jira
comment is posted only when the report named an `ERN-…` key.

What never leaves your machine: host names, addresses, postures, VPN names,
raw drift entries, unredacted logs. The validator refuses a ticket that carries
any of them. An instance that is not on 7.x is refused, not ticketed: the skill
says what it found and points at the migration tracking — the 7.x-only policy
applies to tickets as it does to work.
```

- [ ] **Step 4: Bump the plugin version**

In `plugins/eregulations/.claude-plugin/plugin.json` change `"version": "0.2.1"` to `"version": "0.3.0"`.

- [ ] **Step 5: Validate frontmatter (under 3.13 — the validator crashes on 3.9 before reading any file, which would make this check pass vacuously)**

Run: `uv run --python 3.13 python scripts/validate-plugins.py 2>&1 | tee /dev/stderr | grep -E "eregulations"; echo "grep exit=$?"`
Expected: the validator's summary line is printed (proof it ran) and no line mentions `eregulations` (grep exit 1). Pre-existing errors in other plugins are the baseline (see the README's Verified section).

- [ ] **Step 6: Commit**

```bash
git add plugins/eregulations/skills/eregulations-issue/SKILL.md plugins/eregulations/commands/issue.md plugins/eregulations/README.md plugins/eregulations/.claude-plugin/plugin.json
git commit -m "feat(eregulations): eregulations-issue skill and /eregulations:issue command"
```

---

### Task 8: Router wiring

**Files:**
- Modify: `plugins/eregulations/skills/ereg-router/SKILL.md:5-7` (metadata) and `:303` (Step 5 table row), plus the "In `plan` or `build` lane" paragraph that follows the table.

**Interfaces:**
- Consumes: the skill name `eregulations-issue` and the per-run `resolve.json` it accepts in its Step 2.

- [ ] **Step 1: Bump the router metadata and add a changelog**

Replace lines 5–8 (the whole `metadata:` block including its `argument-hint` line, so nothing is duplicated):

```yaml
metadata:
  version: "0.2.0"
  version-date: "2026-09-11"
  argument-hint: "[request] or --dry-run [request]"
  changelog:
    - "0.2.0 (2026-09-11): `bugfix` dispatches to `eregulations-issue` in every lane with no blocking gate (the skill is read-only in plan/build); the router hands over its per-run resolve.json instead of stopping at the handoff block."
    - "0.1.1 (2026-09-11): Step 1 reads api-surfaces.md from the private knowledge base; versions.md corrected (PR #81)."
```

- [ ] **Step 2: Replace the Step 5 table row**

Replace the line

```
| `bugfix`, `upgrade`, `provision` | no dedicated skill yet — work from the resolved context, or hand off |
```

with

```
| `bugfix` | `eregulations-issue` — **in every lane with no blocking gate** (a block still stops here, as for every kind); write Step 2's resolver output to a per-run directory (`RUN=$(mktemp -d)`; `resolve.json`) and hand that path over (the skill re-evaluates the gates with its own context, so `gates.json` is not needed). The skill is read-only in `plan`/`build` and never files without an explicit yes. |
| `upgrade`, `provision` | no dedicated skill yet — work from the resolved context, or hand off |
```

- [ ] **Step 3: Amend the plan/build paragraph**

Find the paragraph starting `**In \`plan\` or \`build\` lane** — stop and emit the handoff block:` and insert immediately before it:

```markdown
**Exception — `bugfix` in any lane, once no gate blocks.** Dispatch to `eregulations-issue` first;
it produces the ticket the handoff block would otherwise summarise, and emits
its own handoff when it cannot file. Only if that skill is not installed do
the plan/build rules below apply.
```

- [ ] **Step 4: Run the router's own tests (nothing in scripts changed; this is the regression net)**

Run: `python3 -m pytest plugins/eregulations/skills/ereg-router/tests -q`
Expected: `R passed` — the router count recorded in Task 0 Step 3: `107` with `main` as it is today, `110` once PR #76 (`fix/branch-pair-case-diagnosis`) is merged. Any other number is a regression.

- [ ] **Step 5: Commit**

```bash
git add plugins/eregulations/skills/ereg-router/SKILL.md
git commit -m "feat(ereg-router): dispatch bugfix to eregulations-issue in every lane"
```

---

### Task 9: Manifests, spec amendment, full verification

**Files:**
- Modify (generated): `plugins/eregulations/.kimi-plugin/plugin.json`
- Modify: `docs/superpowers/specs/2026-09-11-eregulations-issue-skill-design.md` (Layout block and Tests table)

- [ ] **Step 1: Regenerate the Kimi manifests**

`--check` is already red on this branch for six other plugins' `.kimi-plugin/plugin.json` and the two root catalogs (`kimi-marketplace.json`, `kimi-marketplace.local.json`, which carry per-plugin versions). Regenerating fixes that drift too; commit everything the generator touched — the files are generated, never hand-edited (`CLAUDE.md`).

Run: `python3 scripts/generate-kimi-manifests.py && python3 scripts/generate-kimi-manifests.py --check; git status --short`
Expected: `--check` exits 0; the modified set is `plugins/eregulations/.kimi-plugin/plugin.json` (now `0.3.0`), the two root catalogs, and the six pre-existing stale manifests.

- [ ] **Step 2: Confirm the spec matches what was built, and register the suite in CI**

The spec was amended on 2026-09-11 (Appendices C and D) for everything this plan now does: `gate_context.py` and `rules.py` in the layout, the line-rule table of Step 3 (D-2), the three-answer probe (D-3), `main` everywhere (D-4), the runtime fetch and `overlay_ref` (D-5), the Step 10 visibility wording, the disprove step, the test rows. Re-read its `## Layout` and `## Tests` against the tree and fix any drift in the spec, in this commit.

Also add the new suite to the CI's required list (a renamed or deleted suite must fail the build), in `.github/workflows/test-plugin-scripts.yml` inside `REQUIRED_SUITES=(`:

```
            "plugins/eregulations/skills/eregulations-issue/tests"
```

- [ ] **Step 3: Full verification on both Python versions**

Run:
```bash
uv run --python 3.9 --with pytest python -m pytest plugins/eregulations/skills -q
uv run --python 3.13 --with pytest python -m pytest plugins/eregulations/skills -q
uv run --python 3.9 python -m compileall plugins/eregulations -q
uv run --python 3.13 python scripts/validate-plugins.py 2>&1 | grep -cE "eregulations"
```
Expected: `R + 19 + 82` passed on both, with R from Task 0 Step 3 — `208 passed` while PR #76 is not in `main` (107 router), `211 passed` once it is (110 router); 19 langadmin and 82 this skill over the fixture overlay; compileall silent; the last command prints `0` (and the validator's own summary line appears on stderr, proving it ran under 3.13).

If `uv` is not installed, run the same suites with `python3 -m pytest plugins/eregulations/skills -q` and record which interpreter ran in the commit message.

Then the private side, on this machine only (it fetches from the private repository, so `gh auth status` must be green and the account a member of `UNCTAD-eRegistrations`):

```bash
EREG_DEFECTS_REAL=1 python3 -m pytest plugins/eregulations/skills/eregulations-issue/tests -q
python3 -c "import json,os;c=json.load(open(os.path.expanduser('~/.ereg/defects.cache.json')));print(c['sha'], len(c['data']['rules']))"
```

Expected: `82 passed` over the fetched overlay (30 rules = 3 public + 27 fetched, 29 corpus entries = 2 gotchas + 27 fetched), and the second line prints the blob sha and `27`. Confirm `git status --short` shows nothing under `~/.ereg` (it is outside the tree) and that `grep -rlE "defects\.(local|cache)" plugins/eregulations/skills/eregulations-issue` lists only `rules.py`, `SKILL.md`, the README and the table test.

- [ ] **Step 4: Update the README's Verified block**

Append to the bullet list in `## Verified (2026-08-26)` of `plugins/eregulations/README.md`:

```markdown
- 2026-09-11, `eregulations-issue` added: `python -m pytest plugins/eregulations/skills -q` — <R + 19 + 82, the number actually observed: 208 without PR #76, 211 with it> passed on 3.9 and 3.13 (82 in `eregulations-issue/tests`, over the fixture overlay; the same 82 over the overlay fetched from the private knowledge base with `EREG_DEFECTS_REAL=1`).
```

- [ ] **Step 5: Commit and open the PR**

```bash
git add plugins/*/.kimi-plugin/plugin.json kimi-marketplace.json kimi-marketplace.local.json .github/workflows/test-plugin-scripts.yml docs/superpowers/specs/2026-09-11-eregulations-issue-skill-design.md plugins/eregulations/README.md
git commit -m "chore(eregulations): manifests, spec amendment and verification for eregulations-issue"
git push -u origin feature/eregulations-issue-skill
gh pr create --title "eregulations 0.3.0: eregulations-issue skill" --body-file - <<'PR'
Adds the `eregulations-issue` skill (bugfix dispatch target of `ereg-router`) and `/eregulations:issue`, for 7.x instances only.

- resolve → gate → probe → ground → qualify → emit → validate → disprove → file; no host contact before `host_posture` passes; a host that is not on 7.x is refused, never ticketed
- `probe_surface.py` (GET only, three hosts, `/release.json` first and gate-exempt, retired roxana images detected, `7.x` / `not-7.x` / `unknown`, release exposed), `rules.py` (public gotchas plus the defect overlay fetched from the private overlays repository with `gh`, cached, local file as a manual fallback), `route.py` (deterministic, `overlay_ref`), `redact.py` (evidence and URL), `validate_ticket.py` (schema 1.1, fleet allowlist), `gate_context.py` (the line rule: the application's own answer decides)
- a read-only disprove pass by a fresh subagent before the filing question
- router 0.2.0: `bugfix` dispatches in every lane with no blocking gate
- 82 new tests over the fixture overlay, the same 82 over the fetched overlay; spec: docs/superpowers/specs/2026-09-11-eregulations-issue-skill-design.md
- the defect rules themselves are not in this PR: they live in the private repository and are read at runtime (spec Appendix D)
PR
```

---

## Self-review notes (done while writing)

- **Spec coverage:** Steps 1–10 of the spec map to Tasks 1–7; schema 1.1 → Task 1; routing table, overlay fetch and keyword discipline → Tasks 3–4; probe contract (D-3) → Task 5; line rule (D-2) and feature gating → Task 6; router wiring → Task 8; manifests and verification → Task 9. The spec's `security` label and `PRIVATE` check → Task 7 Step 9. Redaction patterns → Task 2. The 7.x-only refusal (D-1) → Task 7 Steps 1, 3, 4 and 5.
- **Type consistency:** `probe()` returns `surface/line/branch_hint/release/evidence/unresolved` with `line` ∈ `7.x | not-7.x | unknown`; `route.route()` reads `surface/line/branch_hint` from that file and refuses a `not-7.x` line (the skill refuses before routing); `gate_context.build_bug_context(resolve, probed_line)` reads `probe.json["line"]`; `rules.load_overlay()["ref"]` feeds `route.json["overlay_ref"]` and `qualification.overlay_ref`; `validate_ticket` enums are the source for `test_issue_routing_table.py` (`vt.SURFACES`, `vt.LINES`).
- **Counts:** test totals per task are 14, 11, 12, 14, 19, 12 = 82 (plus router R — 107 on `main` today, 110 once PR #76 is merged — and langadmin 19 = 208 or 211); adjust the expected number in Task 6 Step 4 and Task 9 Step 3 if a test is added during execution, and say so in the commit.
- **Adversarial review of the plan (2026-09-11, two reviewers, one of them executed Tasks 1–6 in a scratch tree: 61/61 green on 3.9 and 3.13 before these amendments):** Task 0 added for the uncommitted router baseline and the credential scrub; stale sibling counts (110/19) corrected; evidence `host` redacted; feature gate filtered by `--honour feature` instead of prose; IPv6 regex no longer eats log timestamps; env-var stem anchored; `validate-plugins.py` run under 3.13; `fleet.drift` boolean enforced; credential test made structural; visibility check stops any ticket on a non-private repo; `--upgrade` repeated on the second pass; the legacy-line inference from absences was named in `unresolved` (superseded by revision D: the probe no longer infers a legacy line at all); lane detection no longer SSHes before the gate; `$RUN`/`$ROOT` assigned in every block; unverifiable `read_via` paths pointed at documented directories with `git ls-tree`; router row hands over `resolve.json` only; Kimi regeneration scoped to what the generator really touches; CI `REQUIRED_SUITES` updated; RFC 5737 test addresses. Second execution pass on the amended plan: 64/66 green; the two failures (raw base URL in the fallback `unresolved` string; credential-pair regex matching an XML transform attribute) fixed with one line each, counts corrected to 9/66/195.
- **Third review (2026-09-11, spec Appendix C):** the defect rules and the corpus were lifted out of this document into a private overlay file (the repository is public); the plan then carried three gotchas, `surface-defaults.json`, a synthetic fixture overlay and `rules.py`; attribution trailers removed; `allowed-tools` scoped; URL query redaction and `strip_query`; `release` in the probe; a remedy-rewriting `--annotate` pass (superseded by revision D: the line rule makes a stale overlay a `pass` with `version_mismatch`, so there is no remedy to rewrite); Step 8b disprove; router row qualified with "no blocking gate"; a rebase recipe for the squash-merge case (superseded: the branch now starts from `main` and Task 0 is a plain rebase); counts 68/197 → 77/206.
- **Re-alignment on PR 79 (2026-09-11):** `api-surfaces.md` re-read at the 7.4.2 tips changed the branch model (7.x = `main` everywhere, roxana retired, no default credential, `/release.json` gate-exempt, `/Home/CustomCss` on `main`, five B 7.x defects fixed). Task 0 rewritten as a merge of PR 79's branch; Tasks 3–5 rewritten: 49 rules with `version_branch` always from the rule and a per-line branch map (`version_branch_by_line`) for multi-line rules, five `FIXED` gotchas and one `WONT_FIX` retired-image gotcha, probe decision order `/release.json` → gate → CustomCss/usecontactpage/requirements; `--reporter-branch` and the `branch` filter removed; counts 12/18 → 68/197. **Superseded by revision D:** the per-line branch map, the legacy probe branches (`--procedure-id`, `/Home/CustomCss`, `usecontactpage`, the `requeriments` spelling probe) and the legacy rules are gone; every rule is `main`.
- **Revision D (2026-09-11, spec Appendix D):** 7.x only — a `not-7.x` host is refused with no override, no `audit.py` entry and no Jira comment (D-1); the legacy sample and the legacy fixture rule dropped, `line` enum `7.x, unknown`, validator accepts `qualification.overlay_ref` and `qualification.disprove`; the line rule replaced the "more restrictive of overlay and probe" merge — the probe decides when `/release.json` answered, `gate_context.line_major` sends the literal `not-7` so `gates.py` blocks non-overridably, a lower overlay is a `pass` with `version_mismatch` (D-2); the probe answers `7.x | not-7.x | unknown` and lost `--procedure-id` and the legacy discriminators (D-3); every rule and `surface-defaults.json` is `main`, no line dimension, Surface A and `eRegulations-4.0-API` leave the routing targets (D-4); `rules.py` fetches `defects.json` from the private repository with one `gh api` call (blob sha and content in one response), caches it, falls back to the cache then a local file, and names the reason when nothing loads; `overlay_ref` in `route.json` and the ticket (D-5); Task 0 waits for PR 79's scrubbed revision to be squash-merged into `main` and never merges its branch, whose history still holds the old section 8 (D-6); the private repository was renamed to `eregulations-knowledge-base` and the public branch was recreated from `main` as `feature/eregulations-issue-skill` without the earlier history, so no commit hash of this repository appears in the plan; the router baseline is R = 107 on `main` today, 110 once PR #76 is merged; the disprove pass, scoped `allowed-tools`, URL redaction, `release`, router hand-off and lane-after-resolution kept (D-7); counts 77/206 → 82/211; estimate about 3 h.
- **D-9 (2026-09-11):** `api-surfaces.md` moved whole into the private knowledge base; PR 79 closed and replaced by #81. Task 0 now waits for #81 and checks that the knowledge base is readable; the credential-literal check on the public reference is gone; every citation names the reference instead of a repository path.
