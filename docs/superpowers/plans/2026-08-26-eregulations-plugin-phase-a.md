# eRegulations Plugin — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the `eregulations` plugin — a `/ereg` router whose safety gates are enforced by tested, stdlib-only Python helpers rather than by prose — to the public UNCTAD marketplace.

**Architecture:** The router's markdown orchestrates four small Python modules that hold all load-bearing logic: gate evaluation (pure, fail-closed), fleet resolution (Monitor + operator overlay + drift), branch-pair derivation (from the `csproj` reference), and override auditing. Prose gates depend on the model remembering to check; a fail-closed safety gate must not. Everything that can be asserted is asserted in pytest; only orchestration lives in markdown.

**Tech Stack:** Markdown skills/commands; Python 3.9-compatible, **stdlib-only** helper scripts; pytest colocated per skill; `validate-plugins.py` for packaging.

**Spec:** `docs/superpowers/specs/2026-08-26-eregulations-plugin-design.md`

**Phase:** 1 of 2. Phase B (the `mcp_eregulations_monitor` server) gets its own plan and is blocked on two `eRegulations-Monitor` changes: a `viewer` service account and a `posture` field.

## Global Constraints

Copied verbatim from the spec and the repo's own CI policy. Every task's requirements implicitly include these.

- **`plugin-marketplace` is a PUBLIC GitHub repo.** No credential values, no server addresses (IPs, SSH targets, VPN endpoints), and no security posture may appear in any committed file. Use `<host>` placeholders. Verified: `gh repo view --json visibility` → `PUBLIC`.
- **Bundled scripts are stdlib-only.** `.github/workflows/test-plugin-scripts.yml` states this explicitly: *"If a bundled script ever needs a third-party package, that is a design problem to fix in the script, not in this workflow."* No `requests`, no PyYAML. Use `urllib.request` and `json`.
- **Scripts must run on Python 3.9 and 3.13.** CI runs both, because operators are told to use plain `python3` and stock macOS is 3.9. No `zip(strict=)`, no `match`, no PEP 604 `X | None` in runtime-evaluated positions. Start every module with `from __future__ import annotations`.
- **`python -m compileall plugins/ -q` must pass on 3.9** for every bundled `.py`.
- **Skill frontmatter must carry** `name`, `description`, `allowed-tools`, and a `metadata` block with `version` and `version-date`.
- **Validator baseline is 14 errors across 149 files**, all pre-existing in other plugins. This work must not increase that count.
- **Validator needs Python ≥3.10**; the system Python is 3.9. Always run it as `uv run --python 3.12 scripts/validate-plugins.py`.
- **Local test command** (matches CI's per-suite invocation): `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q`
- **Overlay and fixtures are JSON**, never YAML — a direct consequence of stdlib-only.
- **Gate directions:** `host_posture`, `branch_pair`, `media_mount`, `unsupported_version` fail **closed** (unresolved input blocks). `windows_target` fails **open** (warns). Only `unsupported_version` is overridable, and only with a stated reason.

## File Structure

```
plugins/eregulations/
├── .claude-plugin/plugin.json          # packaging
├── .kimi-plugin/plugin.json            # mirror, validator-enforced
├── README.md                           # documents the ~/.ereg/ overlay operators create
├── commands/
│   └── ereg.md                         # /ereg front door, argument-hint, allowed-tools
└── skills/
    ├── ereg-router/
    │   ├── SKILL.md                    # orchestration only: classify → resolve → lane → gates → dispatch
    │   ├── references/
    │   │   ├── versions.md             # version lineage + support policy (human hint, not source of truth)
    │   │   ├── gates.md                # what each gate means and why its direction is what it is
    │   │   ├── resolution.md           # HOW to resolve fleet facts; overlay file format
    │   │   └── access.md               # credential NAMES and VPN profile names; no addresses
    │   ├── scripts/
    │   │   ├── gates.py                # pure gate evaluation — no I/O
    │   │   ├── fleet_resolve.py        # Monitor + overlay merge + drift detection
    │   │   ├── branch_pair.py          # derive Admin↔Public pair from the csproj reference
    │   │   └── audit.py                # override records to ~/.ereg/audit.jsonl
    │   ├── fixtures/
    │   │   ├── fleet.sample.json       # synthetic fleet; no real hosts
    │   │   └── csproj/                 # sample WebAppCore.csproj files for branch_pair tests
    │   └── tests/
    │       ├── conftest.py             # puts ../scripts on sys.path (repo convention)
    │       ├── test_gates.py
    │       ├── test_fleet_resolve.py
    │       ├── test_branch_pair.py
    │       └── test_audit.py
    ├── deploying-legacy-eregulations-instance/   # migrated from Drive, split
    ├── adding-mule3-webservice/                  # migrated from Drive
    └── merged-eregulations-translations-into-langadmin/  # migrated from Drive
```

Modified outside the plugin:
- `.claude-plugin/marketplace.json` — add the plugin entry
- `kimi-marketplace.json` — add the mirror entry
- `.github/workflows/test-plugin-scripts.yml:REQUIRED_SUITES` — register the new suite so deletion fails the build

---

### Task 1: Plugin skeleton and marketplace registration

Establishes the package so every later task has somewhere to land, and proves the validator stays at baseline.

**Files:**
- Create: `plugins/eregulations/.claude-plugin/plugin.json`
- Create: `plugins/eregulations/.kimi-plugin/plugin.json`
- Create: `plugins/eregulations/README.md`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `kimi-marketplace.json`

**Interfaces:**
- Consumes: nothing
- Produces: plugin directory `plugins/eregulations/`; plugin name `eregulations` (must match the directory — the validator enforces it)

- [ ] **Step 1: Record the validator baseline**

Run: `uv run --python 3.12 scripts/validate-plugins.py 2>&1 | tail -2`
Expected: `14 error(s) in 149 file(s)`. Write this number down — every later task compares against it.

- [ ] **Step 2: Create `plugins/eregulations/.claude-plugin/plugin.json`**

```json
{
  "name": "eregulations",
  "description": "One front door for eRegulations work — /ereg routes a request to the right knowledge, resolves which instance and version it concerns, and blocks on unsafe hosts, mismatched Admin/Public branches, and unsupported versions before anything runs.",
  "version": "0.1.0",
  "author": {
    "name": "UNCTAD Trade Facilitation Section"
  }
}
```

- [ ] **Step 3: Create the kimi mirror at `plugins/eregulations/.kimi-plugin/plugin.json`**

Read a sibling first — `cat plugins/devops/.kimi-plugin/plugin.json` — and match its field set exactly. The validator checks that `name` matches the directory and that every declared path exists and stays inside the plugin root, so declare only paths created by this task.

- [ ] **Step 4: Add the entry to `.claude-plugin/marketplace.json`**

Insert into the `plugins` array, matching the shape of the existing entries:

```json
{
  "name": "eregulations",
  "description": "One front door for eRegulations work — /ereg routes development, deployment and bugfix requests, resolves instance and version context, and enforces safety gates before anything runs.",
  "author": {
    "name": "UNCTAD Trade Facilitation Section"
  },
  "source": "./plugins/eregulations",
  "category": "integration"
}
```

- [ ] **Step 5: Add the mirror entry to `kimi-marketplace.json`**

Match the existing entries' `id` / `source` shape. The validator checks every local source path exists.

- [ ] **Step 6: Write `plugins/eregulations/README.md`**

Must cover, and must contain no addresses:
- what `/ereg` is and the five steps it runs
- that the marketplace repo is public, so the plugin holds no fleet data
- how to create the operator overlay, with this exact template:

````markdown
## Operator setup

The plugin ships no fleet data — this repository is public. Create your own
overlay at `~/.ereg/fleet.local.json` (JSON, never committed anywhere):

```json
{
  "instances": {
    "<instance-slug>": {
      "host": "<host-name>",
      "version": "7.2",
      "platform": "ubuntu"
    }
  },
  "hosts": {
    "<host-name>": {
      "posture": "ok",
      "address": "<address>",
      "vpn": "<vpn-profile-name>"
    }
  }
}
```

`posture` is one of `ok`, `degraded`, `compromised`. **A host you do not list
resolves as unknown, and unknown blocks** — that is deliberate. See
`skills/ereg-router/references/gates.md`.
````

- [ ] **Step 7: Run the validator**

Run: `uv run --python 3.12 scripts/validate-plugins.py 2>&1 | tail -3`
Expected: still `14 error(s)` — the same baseline, with no `plugins/eregulations` lines among them.

- [ ] **Step 8: Verify no addresses leaked**

Run: `grep -rEn '([0-9]{1,3}\.){3}[0-9]{1,3}' plugins/eregulations || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 9: Commit**

```bash
git add plugins/eregulations .claude-plugin/marketplace.json kimi-marketplace.json
git commit -m "feat(eregulations): plugin skeleton and marketplace registration"
```

---

### Task 2: Gate evaluation — the fail-closed core

The single most important module. Pure logic, no I/O, so every direction is directly assertable. Also establishes the test suite and wires it into CI.

**Files:**
- Create: `plugins/eregulations/skills/ereg-router/scripts/gates.py`
- Create: `plugins/eregulations/skills/ereg-router/tests/conftest.py`
- Create: `plugins/eregulations/skills/ereg-router/tests/test_gates.py`
- Modify: `.github/workflows/test-plugin-scripts.yml` (`REQUIRED_SUITES`)

**Interfaces:**
- Consumes: nothing
- Produces:
  - `BLOCK: str = "block"`, `WARN: str = "warn"`, `PASS: str = "pass"`
  - `evaluate(context: dict) -> list` — each element `{"gate": str, "status": str, "reason": str, "remedy": str, "overridable": bool}`
  - `blocking(decisions: list) -> list`
  - Context keys read: `kind`, `secondary_kinds`, `posture`, `touches_admin_public`, `branch_pair_valid`, `targets_admin_deploy`, `media_mount`, `version_major`, `platform`

- [ ] **Step 1: Create the conftest that puts `scripts/` on the path**

`plugins/eregulations/skills/ereg-router/tests/conftest.py` — identical in shape to `plugins/bpa-mcp/skills/columns-normalization-migration/tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
```

- [ ] **Step 2: Write the failing tests**

`plugins/eregulations/skills/ereg-router/tests/test_gates.py`:

```python
"""Gate evaluation, with the fail-closed directions asserted explicitly.

The spec's whole point is that an UNRESOLVED input to a safety gate must
block exactly as hard as a confirmed-bad one. A first draft of the design
let unresolved posture through with a warning, which meant the gate
silently never fired whenever Monitor was unreachable. These tests exist
so that regression cannot recur.
"""

from __future__ import annotations

import gates


def _ctx(**overrides):
    """A context that passes every gate, so each test varies one thing."""
    base = {
        "kind": "bugfix",
        "secondary_kinds": [],
        "posture": "ok",
        "touches_admin_public": False,
        "branch_pair_valid": None,
        "targets_admin_deploy": False,
        "media_mount": None,
        "version_major": "7",
        "platform": "ubuntu",
    }
    base.update(overrides)
    return base


def _by_gate(decisions, name):
    for d in decisions:
        if d["gate"] == name:
            return d
    raise AssertionError("no decision for gate %r in %r" % (name, decisions))


def test_clean_context_blocks_nothing():
    assert gates.blocking(gates.evaluate(_ctx())) == []


def test_compromised_host_blocks():
    d = _by_gate(gates.evaluate(_ctx(posture="compromised")), "host_posture")
    assert d["status"] == gates.BLOCK
    assert d["overridable"] is False


def test_unknown_posture_blocks_identically_to_compromised():
    unknown = _by_gate(gates.evaluate(_ctx(posture="unknown")), "host_posture")
    missing = _by_gate(gates.evaluate(_ctx(posture=None)), "host_posture")
    assert unknown["status"] == gates.BLOCK
    assert missing["status"] == gates.BLOCK
    assert missing["overridable"] is False


def test_degraded_host_warns_but_does_not_block():
    d = _by_gate(gates.evaluate(_ctx(posture="degraded")), "host_posture")
    assert d["status"] == gates.WARN


def test_branch_pair_gate_only_applies_to_admin_public_builds():
    d = _by_gate(gates.evaluate(_ctx(touches_admin_public=False)), "branch_pair")
    assert d["status"] == gates.PASS


def test_underivable_branch_pair_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid=None)),
        "branch_pair",
    )
    assert d["status"] == gates.BLOCK


def test_invalid_branch_pair_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid=False)),
        "branch_pair",
    )
    assert d["status"] == gates.BLOCK


def test_valid_branch_pair_passes():
    d = _by_gate(
        gates.evaluate(_ctx(touches_admin_public=True, branch_pair_valid=True)),
        "branch_pair",
    )
    assert d["status"] == gates.PASS


def test_admin_deploy_without_media_mount_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(kind="deploy", targets_admin_deploy=True, media_mount=False)),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK


def test_admin_deploy_with_unknown_media_mount_blocks():
    d = _by_gate(
        gates.evaluate(_ctx(kind="deploy", targets_admin_deploy=True, media_mount=None)),
        "media_mount",
    )
    assert d["status"] == gates.BLOCK


def test_unsupported_version_blocks_but_is_overridable():
    for major in ("4", "5", "6"):
        d = _by_gate(gates.evaluate(_ctx(version_major=major)), "unsupported_version")
        assert d["status"] == gates.BLOCK, major
        assert d["overridable"] is True, major


def test_unresolved_version_blocks_and_is_not_overridable():
    d = _by_gate(gates.evaluate(_ctx(version_major=None)), "unsupported_version")
    assert d["status"] == gates.BLOCK
    assert d["overridable"] is False


def test_windows_target_warns_and_fails_open():
    d = _by_gate(gates.evaluate(_ctx(platform="windows")), "windows_target")
    assert d["status"] == gates.WARN
    unresolved = _by_gate(gates.evaluate(_ctx(platform=None)), "windows_target")
    assert unresolved["status"] != gates.BLOCK


def test_secondary_kinds_are_gated_too():
    """A bugfix that is also an upgrade must still hit the version gate."""
    ctx = _ctx(kind="bugfix", secondary_kinds=["upgrade"], version_major="5")
    assert _by_gate(gates.evaluate(ctx), "unsupported_version")["status"] == gates.BLOCK


def test_every_decision_carries_a_remedy():
    for d in gates.evaluate(_ctx(posture="compromised", version_major="4")):
        if d["status"] == gates.BLOCK:
            assert d["remedy"], d
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q`
Expected: FAIL — collection error, `ModuleNotFoundError: No module named 'gates'`

- [ ] **Step 4: Implement `scripts/gates.py`**

```python
"""Gate evaluation for the /ereg router.

Pure logic: no network, no filesystem, no subprocess. Everything this
module needs arrives in the context dict, which is what makes every
branch directly testable.

Each gate declares a FAILURE DIRECTION:

  fail closed - if the input cannot be verified, BLOCK. Used wherever
                proceeding on stale data could damage a system or touch a
                compromised host.
  fail open   - if the input cannot be verified, WARN and proceed. Used
                only for advisory facts.

Unresolved input to a fail-closed gate is treated exactly as harshly as
confirmed-bad input. That is the design, not an oversight.
"""

from __future__ import annotations

BLOCK = "block"
WARN = "warn"
PASS = "pass"

SUPPORTED_MAJOR = "7"
UNSUPPORTED_MAJORS = ("4", "5", "6")


def _decision(gate, status, reason, remedy="", overridable=False):
    return {
        "gate": gate,
        "status": status,
        "reason": reason,
        "remedy": remedy,
        "overridable": overridable,
    }


def _host_posture(context):
    posture = context.get("posture")
    if posture == "ok":
        return _decision("host_posture", PASS, "host posture is ok")
    if posture == "degraded":
        return _decision(
            "host_posture", WARN, "host is degraded", "proceed with care"
        )
    if posture == "compromised":
        return _decision(
            "host_posture",
            BLOCK,
            "host is recorded as compromised",
            "migrate the instance off this host; do not repair in place",
        )
    return _decision(
        "host_posture",
        BLOCK,
        "host posture is unresolved",
        "record the host in ~/.ereg/fleet.local.json, or restore Monitor access",
    )


def _branch_pair(context):
    if not context.get("touches_admin_public"):
        return _decision("branch_pair", PASS, "request does not build Admin + Public")
    valid = context.get("branch_pair_valid")
    if valid is True:
        return _decision("branch_pair", PASS, "derived Admin/Public pair resolves")
    if valid is False:
        return _decision(
            "branch_pair",
            BLOCK,
            "the checked-out Admin and Public branches are not a compatible pair",
            "check out a pair whose csproj project reference resolves, then retry",
        )
    return _decision(
        "branch_pair",
        BLOCK,
        "the Admin/Public pair could not be derived",
        "verify both repos are checked out and WebAppCore.csproj is readable",
    )


def _media_mount(context):
    if not context.get("targets_admin_deploy"):
        return _decision("media_mount", PASS, "request is not an Admin deploy")
    mount = context.get("media_mount")
    if mount is True:
        return _decision("media_mount", PASS, "/app/media is bind-mounted")
    if mount is False:
        return _decision(
            "media_mount",
            BLOCK,
            "/app/media is not bind-mounted; Admin crashes on startup without it",
            "add the /app/media bind mount to the compose file before deploying",
        )
    return _decision(
        "media_mount",
        BLOCK,
        "could not confirm the /app/media bind mount",
        "read the instance compose file and confirm the mount, then retry",
    )


def _unsupported_version(context):
    major = context.get("version_major")
    if major == SUPPORTED_MAJOR:
        return _decision("unsupported_version", PASS, "target is 7.x")
    if major in UNSUPPORTED_MAJORS:
        return _decision(
            "unsupported_version",
            BLOCK,
            "policy is 7.x only; this targets %s.x" % major,
            "upgrade the instance to 7.x as part of this change",
            overridable=True,
        )
    return _decision(
        "unsupported_version",
        BLOCK,
        "target version is unresolved",
        "resolve the instance version before proceeding",
    )


def _windows_target(context):
    if context.get("platform") == "windows":
        return _decision(
            "windows_target",
            WARN,
            "target is Windows/IIS, which is transitional",
            "plan the move to Ubuntu; this is not a long-term target",
        )
    return _decision("windows_target", PASS, "target is not Windows")


_GATES = (_host_posture, _branch_pair, _media_mount, _unsupported_version, _windows_target)

_ORDER = {BLOCK: 0, WARN: 1, PASS: 2}


def evaluate(context):
    """Return one decision per gate, blocking decisions first."""
    decisions = [gate(context) for gate in _GATES]
    return sorted(decisions, key=lambda d: _ORDER[d["status"]])


def blocking(decisions):
    """Return only the decisions that block."""
    return [d for d in decisions if d["status"] == BLOCK]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q`
Expected: PASS, 15 passed

- [ ] **Step 6: Verify Python 3.9 compatibility**

Run: `python3 --version && python3 -m compileall plugins/eregulations -q && echo "3.9 OK"`
Expected: `Python 3.9.x` then `3.9 OK`. If `compileall` reports a syntax error, the module used syntax newer than 3.9 — fix the module, not the check.

- [ ] **Step 7: Register the suite in CI**

In `.github/workflows/test-plugin-scripts.yml`, add to `REQUIRED_SUITES` so an accidental deletion fails the build rather than silently shrinking coverage:

```bash
          REQUIRED_SUITES=(
            "plugins/bpa-mcp/skills/columns-normalization-migration/tests"
            "plugins/eregulations/skills/ereg-router/tests"
          )
```

- [ ] **Step 8: Commit**

```bash
git add plugins/eregulations/skills/ereg-router .github/workflows/test-plugin-scripts.yml
git commit -m "feat(eregulations): fail-closed gate evaluation with tests"
```

---

### Task 3: Fleet resolution — Monitor, overlay, drift

**Files:**
- Create: `plugins/eregulations/skills/ereg-router/scripts/fleet_resolve.py`
- Create: `plugins/eregulations/skills/ereg-router/fixtures/fleet.sample.json`
- Create: `plugins/eregulations/skills/ereg-router/tests/test_fleet_resolve.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `load_overlay(path: str) -> dict`
  - `resolve(slug: str, monitor_record, overlay: dict) -> dict` — returns keys `instance`, `host`, `version`, `version_major`, `platform`, `posture`, `source`, `drift`, `unresolved`
  - `fetch_instance(base_url: str, token, slug: str, opener) -> dict or None`
  - Feeds Task 2's `gates.evaluate` — `posture`, `version_major`, `platform` are the shared keys

- [ ] **Step 1: Create the synthetic fixture**

`plugins/eregulations/skills/ereg-router/fixtures/fleet.sample.json`. Synthetic on purpose: the design's first draft pinned its host-gate test to a real instance whose migration is the top operational priority, so the test would have gone green while testing nothing. No real slugs, no real hosts, no addresses.

```json
{
  "instances": {
    "alpha": { "host": "host-safe", "version": "7.2", "platform": "ubuntu" },
    "bravo": { "host": "host-bad", "version": "5.1", "platform": "windows" },
    "charlie": { "host": "host-unlisted", "version": "7.2", "platform": "ubuntu" },
    "delta": { "host": "host-safe", "platform": "ubuntu" }
  },
  "hosts": {
    "host-safe": { "posture": "ok" },
    "host-bad": { "posture": "compromised" },
    "host-tired": { "posture": "degraded" }
  }
}
```

Note `charlie` points at a host absent from `hosts`, and `delta` has no version. Both exist so the fail-closed paths have fixtures.

- [ ] **Step 2: Write the failing tests**

`plugins/eregulations/skills/ereg-router/tests/test_fleet_resolve.py`:

```python
"""Fleet resolution: Monitor is authoritative for state, the operator
overlay fills gaps, and anything neither supplies is UNRESOLVED.

`resolve` is pure — the caller passes in the Monitor record — so these
tests never touch the network. `fetch_instance` takes an injectable
opener for the same reason.
"""

from __future__ import annotations

import json
from pathlib import Path

import fleet_resolve

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _overlay():
    return json.loads((FIXTURES / "fleet.sample.json").read_text())


def test_overlay_only_resolves_host_and_posture():
    ctx = fleet_resolve.resolve("alpha", None, _overlay())
    assert ctx["host"] == "host-safe"
    assert ctx["posture"] == "ok"
    assert ctx["version_major"] == "7"
    assert ctx["source"] == "overlay"


def test_host_absent_from_overlay_leaves_posture_unresolved():
    ctx = fleet_resolve.resolve("charlie", None, _overlay())
    assert ctx["posture"] is None
    assert "posture" in ctx["unresolved"]


def test_missing_version_is_unresolved_not_guessed():
    ctx = fleet_resolve.resolve("delta", None, _overlay())
    assert ctx["version_major"] is None
    assert "version" in ctx["unresolved"]


def test_unknown_instance_resolves_nothing():
    ctx = fleet_resolve.resolve("nosuch", None, _overlay())
    assert ctx["host"] is None
    assert ctx["posture"] is None
    assert "host" in ctx["unresolved"]


def test_monitor_wins_over_overlay_for_state():
    record = {"slug": "bravo", "host": "host-safe", "version": "7.3", "platform": "ubuntu"}
    ctx = fleet_resolve.resolve("bravo", record, _overlay())
    assert ctx["host"] == "host-safe"
    assert ctx["version"] == "7.3"
    assert ctx["source"] == "monitor"


def test_disagreement_is_reported_as_drift():
    record = {"slug": "bravo", "host": "host-safe", "version": "7.3", "platform": "ubuntu"}
    ctx = fleet_resolve.resolve("bravo", record, _overlay())
    drifted = dict((d["field"], d) for d in ctx["drift"])
    assert drifted["version"]["monitor"] == "7.3"
    assert drifted["version"]["overlay"] == "5.1"
    assert drifted["host"]["overlay"] == "host-bad"


def test_agreement_produces_no_drift():
    record = {"slug": "alpha", "host": "host-safe", "version": "7.2", "platform": "ubuntu"}
    assert fleet_resolve.resolve("alpha", record, _overlay())["drift"] == []


def test_monitor_posture_beats_overlay_posture():
    record = {"slug": "bravo", "host": "host-bad", "version": "5.1", "posture": "ok"}
    assert fleet_resolve.resolve("bravo", record, _overlay())["posture"] == "ok"


def test_version_major_is_the_leading_component():
    record = {"slug": "alpha", "version": "7.10.2"}
    assert fleet_resolve.resolve("alpha", record, _overlay())["version_major"] == "7"


def test_missing_overlay_file_is_empty_not_an_error():
    assert fleet_resolve.load_overlay("/nonexistent/fleet.local.json") == {}


def test_malformed_overlay_raises_rather_than_resolving_silently(tmp_path):
    bad = tmp_path / "fleet.local.json"
    bad.write_text("{not json")
    try:
        fleet_resolve.load_overlay(str(bad))
    except ValueError as exc:
        assert "fleet.local.json" in str(exc)
    else:
        raise AssertionError("a malformed overlay must raise, not resolve to {}")


def test_fetch_instance_returns_none_on_http_error():
    class Boom(Exception):
        pass

    def opener(request, timeout=None):
        raise Boom("unreachable")

    assert fleet_resolve.fetch_instance("https://example.invalid", "t", "alpha", opener) is None


def test_fetch_instance_sends_bearer_token():
    seen = {}

    class FakeResponse(object):
        def read(self):
            return b'{"slug": "alpha", "version": "7.2"}'

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(request, timeout=None):
        seen["auth"] = request.get_header("Authorization")
        return FakeResponse()

    record = fleet_resolve.fetch_instance("https://example.invalid", "tok", "alpha", opener)
    assert seen["auth"] == "Bearer tok"
    assert record["version"] == "7.2"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests/test_fleet_resolve.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'fleet_resolve'`

- [ ] **Step 4: Implement `scripts/fleet_resolve.py`**

```python
"""Resolve fleet facts for the /ereg router.

Order: Monitor (authoritative for state) -> operator overlay -> UNRESOLVED.
There is no third source and no guessing. "Unresolved" is a real outcome
that the fail-closed gates in gates.py act on.

Monitor's read endpoints sit behind `authenticate`, so the live path needs
a token. Without one this module still works from the overlay alone, which
is the baseline mode the plugin ships in.

stdlib-only: urllib + json. No requests, no PyYAML — hence a JSON overlay.
"""

from __future__ import annotations

import json
import os
import urllib.request

STATE_FIELDS = ("host", "version", "platform", "posture")

DEFAULT_OVERLAY = os.path.join(os.path.expanduser("~"), ".ereg", "fleet.local.json")


def load_overlay(path):
    """Read the operator overlay. Absent is fine; malformed is not."""
    try:
        with open(path, "r") as handle:
            text = handle.read()
    except (IOError, OSError):
        return {}
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ValueError("could not parse fleet.local.json at %s: %s" % (path, exc))


def fetch_instance(base_url, token, slug, opener=urllib.request.urlopen):
    """GET one instance from Monitor. Returns None if unreachable.

    Unreachable is not an error here — it degrades to the overlay, and the
    gates block on whatever stays unresolved.
    """
    url = "%s/api/instances/%s" % (base_url.rstrip("/"), slug)
    request = urllib.request.Request(url)
    if token:
        request.add_header("Authorization", "Bearer %s" % token)
    try:
        response = opener(request, timeout=10)
    except Exception:
        return None
    try:
        with response as handle:
            return json.loads(handle.read().decode("utf-8"))
    except Exception:
        return None


def _major(version):
    if not version:
        return None
    return str(version).split(".")[0]


def resolve(slug, monitor_record, overlay):
    """Merge Monitor and overlay into one context, reporting drift."""
    overlay_instance = (overlay.get("instances") or {}).get(slug) or {}
    overlay_host = overlay_instance.get("host")
    overlay_hosts = overlay.get("hosts") or {}
    overlay_view = {
        "host": overlay_host,
        "version": overlay_instance.get("version"),
        "platform": overlay_instance.get("platform"),
        "posture": (overlay_hosts.get(overlay_host) or {}).get("posture"),
    }

    monitor_view = {}
    if monitor_record:
        monitor_host = monitor_record.get("host") or monitor_record.get("server")
        monitor_view = {
            "host": monitor_host,
            "version": monitor_record.get("version"),
            "platform": monitor_record.get("platform"),
            "posture": monitor_record.get("posture"),
        }

    resolved = {}
    drift = []
    for field in STATE_FIELDS:
        from_monitor = monitor_view.get(field)
        from_overlay = overlay_view.get(field)
        resolved[field] = from_monitor if from_monitor is not None else from_overlay
        if from_monitor is not None and from_overlay is not None and from_monitor != from_overlay:
            drift.append({"field": field, "monitor": from_monitor, "overlay": from_overlay})

    unresolved = [f for f in STATE_FIELDS if resolved.get(f) is None]

    context = {
        "instance": slug,
        "source": "monitor" if monitor_record else "overlay",
        "drift": drift,
        "unresolved": unresolved,
        "version_major": _major(resolved.get("version")),
    }
    context.update(resolved)
    return context


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Resolve fleet context for one instance.")
    parser.add_argument("slug")
    parser.add_argument("--overlay", default=DEFAULT_OVERLAY)
    parser.add_argument("--monitor-url", default=os.environ.get("EREG_MONITOR_URL"))
    parser.add_argument("--token", default=os.environ.get("EREG_MONITOR_TOKEN"))
    args = parser.parse_args(argv)

    overlay = load_overlay(args.overlay)
    record = None
    if args.monitor_url:
        record = fetch_instance(args.monitor_url, args.token, args.slug)
    print(json.dumps(resolve(args.slug, record, overlay), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q`
Expected: PASS, 28 passed (15 from Task 2 plus 13 here)

- [ ] **Step 6: Verify 3.9 compatibility and cleanliness**

Run: `python3 -m compileall plugins/eregulations -q && grep -rEn '([0-9]{1,3}\.){3}[0-9]{1,3}' plugins/eregulations || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 7: Commit**

```bash
git add plugins/eregulations/skills/ereg-router
git commit -m "feat(eregulations): fleet resolution with overlay fallback and drift detection"
```

---

### Task 4: Branch-pair derivation

Replaces a static table that would rot with a fact derived from the code itself.

**Files:**
- Create: `plugins/eregulations/skills/ereg-router/scripts/branch_pair.py`
- Create: `plugins/eregulations/skills/ereg-router/fixtures/csproj/valid.csproj`
- Create: `plugins/eregulations/skills/ereg-router/fixtures/csproj/no-reference.csproj`
- Create: `plugins/eregulations/skills/ereg-router/tests/test_branch_pair.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `extract_library_reference(csproj_text: str) -> str or None`
  - `derive(public_csproj: str, admin_root: str, branch_reader) -> dict` with keys `valid` (True/False/None), `reason`, `reference`, `admin_branch`, `public_branch`
  - `derive()["valid"]` feeds Task 2's context key `branch_pair_valid`

- [ ] **Step 1: Create the csproj fixtures**

`fixtures/csproj/valid.csproj` — the real shape, reduced to what matters:

```xml
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="..\..\Admin\Unctad.eRegulations.Library\Unctad.eRegulations.Library.csproj" />
  </ItemGroup>
</Project>
```

`fixtures/csproj/no-reference.csproj` — same file with the `ProjectReference` removed entirely, keeping the `PropertyGroup`.

- [ ] **Step 2: Write the failing tests**

`plugins/eregulations/skills/ereg-router/tests/test_branch_pair.py`:

```python
"""Deriving the Admin/Public pair from the csproj project reference.

A static pairing table rots with nothing to correct it — there is no
Monitor equivalent for branches. Deriving the pair from the reference that
actually has to resolve at build time makes the gate correct by
construction.

`valid is None` means "could not determine", which the gate treats as
blocking. It is deliberately distinct from `valid is False`.
"""

from __future__ import annotations

from pathlib import Path

import branch_pair

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "csproj"


def _reader(mapping):
    def read(root):
        return mapping.get(str(root))
    return read


def test_extracts_the_library_reference():
    text = (FIXTURES / "valid.csproj").read_text()
    ref = branch_pair.extract_library_reference(text)
    assert ref is not None
    assert ref.endswith("Unctad.eRegulations.Library.csproj")


def test_returns_none_when_there_is_no_reference():
    text = (FIXTURES / "no-reference.csproj").read_text()
    assert branch_pair.extract_library_reference(text) is None


def test_valid_when_the_reference_resolves_into_the_admin_checkout(tmp_path):
    admin = tmp_path / "Admin"
    lib = admin / "Unctad.eRegulations.Library"
    lib.mkdir(parents=True)
    (lib / "Unctad.eRegulations.Library.csproj").write_text("<Project />")

    public = tmp_path / "Public" / "src"
    public.mkdir(parents=True)
    csproj = public / "WebAppCore.csproj"
    csproj.write_text(
        '<Project><ItemGroup><ProjectReference Include='
        '"..\\..\\Admin\\Unctad.eRegulations.Library\\Unctad.eRegulations.Library.csproj" />'
        "</ItemGroup></Project>"
    )

    result = branch_pair.derive(
        str(csproj),
        str(admin),
        _reader({str(admin): "feature/x", str(tmp_path / "Public"): "feature/y"}),
    )
    assert result["valid"] is True
    assert result["admin_branch"] == "feature/x"


def test_invalid_when_the_reference_does_not_resolve(tmp_path):
    admin = tmp_path / "Admin"
    admin.mkdir()
    public = tmp_path / "Public" / "src"
    public.mkdir(parents=True)
    csproj = public / "WebAppCore.csproj"
    csproj.write_text(
        '<Project><ItemGroup><ProjectReference Include='
        '"..\\..\\Admin\\Unctad.eRegulations.Library\\Unctad.eRegulations.Library.csproj" />'
        "</ItemGroup></Project>"
    )

    result = branch_pair.derive(str(csproj), str(admin), _reader({}))
    assert result["valid"] is False
    assert "does not exist" in result["reason"]


def test_undeterminable_when_the_csproj_is_missing(tmp_path):
    result = branch_pair.derive(str(tmp_path / "nope.csproj"), str(tmp_path), _reader({}))
    assert result["valid"] is None


def test_undeterminable_when_there_is_no_project_reference(tmp_path):
    csproj = tmp_path / "WebAppCore.csproj"
    csproj.write_text((FIXTURES / "no-reference.csproj").read_text())
    result = branch_pair.derive(str(csproj), str(tmp_path), _reader({}))
    assert result["valid"] is None
    assert result["reference"] is None


def test_windows_separators_in_the_reference_are_normalised(tmp_path):
    """csproj paths use backslashes; the router runs on macOS and Linux."""
    admin = tmp_path / "Admin"
    lib = admin / "Unctad.eRegulations.Library"
    lib.mkdir(parents=True)
    (lib / "Unctad.eRegulations.Library.csproj").write_text("<Project />")
    csproj = tmp_path / "Public" / "WebAppCore.csproj"
    csproj.parent.mkdir()
    csproj.write_text(
        '<Project><ItemGroup><ProjectReference Include='
        '"..\\Admin\\Unctad.eRegulations.Library\\Unctad.eRegulations.Library.csproj" />'
        "</ItemGroup></Project>"
    )
    assert branch_pair.derive(str(csproj), str(admin), _reader({}))["valid"] is True
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests/test_branch_pair.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'branch_pair'`

- [ ] **Step 4: Implement `scripts/branch_pair.py`**

```python
"""Derive the Admin/Public branch pair from the csproj project reference.

Public's WebAppCore.csproj carries a ProjectReference to Admin's
Unctad.eRegulations.Library. That reference has to resolve for the build to
succeed, so resolving it is the same question as "are these two checkouts
a compatible pair" — asked of the code rather than of a table someone has
to remember to update.

Three outcomes, and the difference between the last two matters:
  valid=True  - the reference resolves
  valid=False - it does not; the pair is wrong
  valid=None  - could not determine; the gate treats this as blocking
"""

from __future__ import annotations

import os
import re
import subprocess

REFERENCE_RE = re.compile(
    r'<ProjectReference\s+Include\s*=\s*"([^"]*Unctad\.eRegulations\.Library\.csproj)"',
    re.IGNORECASE,
)


def extract_library_reference(csproj_text):
    """Return the raw Include path of the Library reference, or None."""
    match = REFERENCE_RE.search(csproj_text)
    if not match:
        return None
    return match.group(1)


def git_branch(root):
    """Current branch of a checkout, or None if it is not a repo."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.STDOUT,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return out.decode("utf-8").strip()


def derive(public_csproj, admin_root, branch_reader=git_branch):
    """Resolve the reference and report whether the pair holds."""
    result = {
        "valid": None,
        "reason": "",
        "reference": None,
        "admin_branch": branch_reader(admin_root),
        "public_branch": None,
    }

    try:
        with open(public_csproj, "r") as handle:
            text = handle.read()
    except (IOError, OSError):
        result["reason"] = "could not read %s" % public_csproj
        return result

    public_root = os.path.dirname(os.path.dirname(os.path.abspath(public_csproj)))
    result["public_branch"] = branch_reader(public_root)

    reference = extract_library_reference(text)
    if reference is None:
        result["reason"] = "no Unctad.eRegulations.Library ProjectReference found"
        return result
    result["reference"] = reference

    # csproj paths are Windows-style; the router runs on macOS and Linux.
    relative = reference.replace("\\", os.sep).replace("/", os.sep)
    target = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(public_csproj)), relative))

    if os.path.exists(target):
        result["valid"] = True
        result["reason"] = "reference resolves to %s" % target
    else:
        result["valid"] = False
        result["reason"] = "referenced project does not exist at %s" % target
    return result


def main(argv=None):
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Derive the Admin/Public branch pair.")
    parser.add_argument("public_csproj")
    parser.add_argument("admin_root")
    args = parser.parse_args(argv)
    print(json.dumps(derive(args.public_csproj, args.admin_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q`
Expected: PASS, 35 passed

- [ ] **Step 6: Sanity-check against the real checkouts**

Run:
```bash
uv run --python 3.12 python plugins/eregulations/skills/ereg-router/scripts/branch_pair.py \
  "$(find /Users/melux/Work/UN/GIT/eRegulations-4.0-Public -name WebAppCore.csproj | head -1)" \
  /Users/melux/Work/UN/GIT/eRegulations-4.0-Admin
```
Expected: JSON reporting `admin_branch` and `public_branch`. This is a smoke check, not an assertion — record what it prints. The clones are on `database-layer-update-NET8` and `tradeportal`, which the spec identifies as an invalid pair; if `valid` comes back `true`, investigate before continuing, because either the checkouts moved or the derivation is too permissive.

- [ ] **Step 7: Commit**

```bash
git add plugins/eregulations/skills/ereg-router
git commit -m "feat(eregulations): derive Admin/Public branch pair from the csproj reference"
```

---

### Task 5: Override auditing

**Files:**
- Create: `plugins/eregulations/skills/ereg-router/scripts/audit.py`
- Create: `plugins/eregulations/skills/ereg-router/tests/test_audit.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `build_record(gate: str, reason: str, context: dict, clock) -> dict`
  - `append(path: str, record: dict) -> None`
  - `record_override(path, gate, reason, context, clock) -> dict`
  - Raises `ValueError` when `reason` is empty or whitespace

- [ ] **Step 1: Write the failing tests**

`plugins/eregulations/skills/ereg-router/tests/test_audit.py`:

```python
"""Override auditing.

Only one gate is overridable, and it bypasses the platform's headline
policy. An override with no stated reason is refused outright; an accepted
one leaves a line behind. This is a local memory aid and an
incident-reconstruction trail, not an access control.
"""

from __future__ import annotations

import json

import audit


def _clock():
    return "2026-08-26T10:00:00+00:00"


def test_refuses_an_override_with_no_reason(tmp_path):
    log = tmp_path / "audit.jsonl"
    for empty in ("", "   ", None):
        try:
            audit.record_override(str(log), "unsupported_version", empty, {}, _clock)
        except ValueError as exc:
            assert "reason" in str(exc).lower()
        else:
            raise AssertionError("empty reason %r must be refused" % (empty,))
    assert not log.exists()


def test_accepted_override_writes_one_line(tmp_path):
    log = tmp_path / "audit.jsonl"
    audit.record_override(
        str(log), "unsupported_version", "hotfix for a live outage",
        {"instance": "alpha", "version_major": "5"}, _clock,
    )
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["gate"] == "unsupported_version"
    assert entry["reason"] == "hotfix for a live outage"
    assert entry["timestamp"] == _clock()
    assert entry["context"]["instance"] == "alpha"


def test_appends_rather_than_truncates(tmp_path):
    log = tmp_path / "audit.jsonl"
    for i in range(3):
        audit.record_override(str(log), "unsupported_version", "reason %d" % i, {}, _clock)
    assert len(log.read_text().strip().splitlines()) == 3


def test_creates_the_parent_directory(tmp_path):
    log = tmp_path / "nested" / "deeper" / "audit.jsonl"
    audit.record_override(str(log), "unsupported_version", "because", {}, _clock)
    assert log.exists()


def test_each_line_is_independently_parseable(tmp_path):
    """JSONL, so a truncated write costs one record, not the whole log."""
    log = tmp_path / "audit.jsonl"
    audit.record_override(str(log), "unsupported_version", "one\nwith a newline", {}, _clock)
    audit.record_override(str(log), "unsupported_version", "two", {}, _clock)
    lines = log.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["reason"] == "one\nwith a newline"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests/test_audit.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'audit'`

- [ ] **Step 3: Implement `scripts/audit.py`**

```python
"""Record gate overrides to ~/.ereg/audit.jsonl.

JSONL rather than JSON so an interrupted write costs one record instead of
the whole log, and so appending never requires reading what is already
there.

The clock is injectable purely so tests can assert an exact timestamp.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

DEFAULT_LOG = os.path.join(os.path.expanduser("~"), ".ereg", "audit.jsonl")


def _now():
    return datetime.now().astimezone().isoformat()


def build_record(gate, reason, context, clock=_now):
    if reason is None or not str(reason).strip():
        raise ValueError("an override requires a stated reason")
    return {
        "timestamp": clock(),
        "gate": gate,
        "reason": reason,
        "context": context or {},
    }


def append(path, record):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def record_override(path, gate, reason, context, clock=_now):
    """Validate, then append. Raises ValueError before writing anything."""
    record = build_record(gate, reason, context, clock)
    append(path, record)
    return record


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Record a gate override.")
    parser.add_argument("--gate", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--context", default="{}")
    parser.add_argument("--log", default=DEFAULT_LOG)
    args = parser.parse_args(argv)
    record = record_override(args.log, args.gate, args.reason, json.loads(args.context))
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --python 3.12 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q`
Expected: PASS, 40 passed

- [ ] **Step 5: Verify 3.9 compatibility**

Run: `python3 -m compileall plugins/eregulations -q && echo "3.9 OK"`
Expected: `3.9 OK`

- [ ] **Step 6: Commit**

```bash
git add plugins/eregulations/skills/ereg-router
git commit -m "feat(eregulations): audit gate overrides, refusing those with no reason"
```

---

### Task 6: The router skill, references, and the `/ereg` command

The markdown that orchestrates Tasks 2–5. It holds no logic the scripts already hold.

**Files:**
- Create: `plugins/eregulations/skills/ereg-router/SKILL.md`
- Create: `plugins/eregulations/skills/ereg-router/references/versions.md`
- Create: `plugins/eregulations/skills/ereg-router/references/gates.md`
- Create: `plugins/eregulations/skills/ereg-router/references/resolution.md`
- Create: `plugins/eregulations/skills/ereg-router/references/access.md`
- Create: `plugins/eregulations/commands/ereg.md`

**Interfaces:**
- Consumes: `gates.evaluate` / `gates.blocking` (Task 2); `fleet_resolve.load_overlay` / `fetch_instance` / `resolve` (Task 3); `branch_pair.derive` (Task 4); `audit.record_override` (Task 5)
- Produces: the `/ereg` command surface, including `--dry-run`

- [ ] **Step 1: Write `SKILL.md` with validator-required frontmatter**

```markdown
---
name: ereg-router
description: Use when handling any eRegulations or TradePortal request — a bug on a country portal, a deploy, a version upgrade, a code change, or a translation fix. Classifies the request, resolves which instance and version it concerns, detects what the current environment can actually do, and evaluates the safety gates before any work starts. Triggered by /ereg.
allowed-tools: Read, Bash, Grep, Glob
metadata:
  version: 0.1.0
  version-date: 2026-08-26
  argument-hint: "[request] or --dry-run [request]"
---
```

The body documents the five steps. Two rules the body must state explicitly, because they are the difference between this skill working and quietly not:

1. **Gate decisions come from `scripts/gates.py`, never from reading the prose and deciding.** The skill runs the script and acts on its output. Prose gates depend on the model remembering to check; these gates must hold every time.
2. **A blocking decision stops the run.** The only exception is `unsupported_version` with an explicit user-stated reason, which requires `scripts/audit.py` to be run first — and it refuses a blank reason, so a rejected override cannot silently proceed.

Body sections, in order:

- **Step 1 — Classify** into a primary kind plus optional secondary kinds from `bugfix`, `deploy`, `upgrade`, `dev`, `provision`, `translations`. Compound requests are the norm in incident work; carry the secondaries into the context so gates see the whole request. Ask one question only when the *primary* is ambiguous and the two candidates dispatch differently.
- **Step 2 — Resolve** by running `scripts/fleet_resolve.py <slug>`. Report any `drift` entries to the user. Never fill an `unresolved` field by inference.
- **Step 3 — Detect lane** — probe in order: repos present, VPN up, SSH usable, Monitor reachable. Outcomes `plan`, `build`, `execute`. State the detected lane before acting.
- **Step 4 — Gate** by running `scripts/gates.py` against the assembled context. For any request touching both Admin and Public, populate `branch_pair_valid` from `scripts/branch_pair.py` first.
- **Step 5 — Dispatch or hand off** — in `execute`, load the matching skill; otherwise emit the handoff block. Post to Jira only if the request named an ERN key.

- [ ] **Step 2: Write `references/gates.md`**

One section per gate: what it means, its failure direction, why that direction, and what the user should do when it fires. State plainly that `host_posture` treats unknown as compromised, and why: a stale record reading "not compromised" means the gate silently never fires.

- [ ] **Step 3: Write `references/resolution.md`**

The resolution order (Monitor → overlay → unresolved), the overlay JSON schema from the README, the drift rule, and — with no addresses — how to populate the overlay from what the operator already knows.

- [ ] **Step 4: Write `references/versions.md`**

The 4.x/5.x/6.x/7.x lineage and the 7.x-only policy, from spec §Constraints. Label it explicitly as a human-facing hint: the enforceable version fact comes from `fleet_resolve`, and the enforceable pairing fact from `branch_pair`.

- [ ] **Step 5: Write `references/access.md`**

Credential **names** and VPN **profile names** only. No addresses, no usernames, no values. State that addresses live in the operator's `~/.ereg/fleet.local.json`, and that this file is public.

- [ ] **Step 6: Write `commands/ereg.md`**

Per the marketplace `CLAUDE.md` conventions:

```markdown
---
description: Route an eRegulations request — bugfix, deploy, upgrade, dev, translations — through classification, context resolution and safety gates.
argument-hint: "[request] or --dry-run [request]"
allowed-tools: Read, Bash, Grep, Glob
---
```

Body: invoke the `ereg-router` skill with `$ARGUMENTS`. If the first argument is `--dry-run`, run steps 1–4 and print the decision — classification, resolved context, lane, every gate decision with its reason — then stop before dispatch.

- [ ] **Step 7: Validate**

Run: `uv run --python 3.12 scripts/validate-plugins.py 2>&1 | grep -E 'eregulations|error\(s\)'`
Expected: `14 error(s)`, with no `eregulations` lines. If a skill is flagged, it is missing `allowed-tools` or the `metadata.version` / `metadata.version-date` block.

- [ ] **Step 8: Verify no addresses leaked**

Run: `grep -rEn '([0-9]{1,3}\.){3}[0-9]{1,3}' plugins/eregulations || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 9: Commit**

```bash
git add plugins/eregulations
git commit -m "feat(eregulations): /ereg router skill, references and command"
```

---

### Task 7: Migrate the three skills out of Drive

**Files:**
- Create: `plugins/eregulations/skills/deploying-legacy-eregulations-instance/SKILL.md` + `references/`
- Create: `plugins/eregulations/skills/adding-mule3-webservice/SKILL.md`
- Create: `plugins/eregulations/skills/merged-eregulations-translations-into-langadmin/SKILL.md` + `scripts/`

**Interfaces:**
- Consumes: nothing
- Produces: three dispatch targets the router's Step 5 names

- [ ] **Step 1: Fetch the three sources from Drive**

Exact file IDs — do not search by title, the titles are all `SKILL.md`:

| Skill | Drive file ID | Size |
| --- | --- | --- |
| deploying-legacy-eregulations-instance | `16dD5R387LL3H2UpoT2y3pmwU5TutVoFe` | 51459 |
| adding-mule3-webservice | `1z0Lhy8yYCkZfIiX2yTVAc86DCpTx_zhz` | 9456 |
| merged-eregulations-translations-into-langadmin | `1C9eap-bbBDTdBsHcyW7_AeQ1F47_voKO` | 8569 |

The third has a sibling `scripts` folder, ID `1w9tdbUbi_s3ohQOUqH4hp-_LancRczQp` — enumerate and fetch its contents too.

Use `mcp__claude_ai_Google_Drive__read_file_content` with each `fileId`. Write each into its skill directory before editing.

- [ ] **Step 2: Redact before committing anything**

These came from a folder that also holds a plaintext credentials document, so treat every line as suspect:

```bash
grep -rEn '([0-9]{1,3}\.){3}[0-9]{1,3}|password|passwd|secret|ssh [a-z_]+@' \
  plugins/eregulations/skills/deploying-legacy-eregulations-instance \
  plugins/eregulations/skills/adding-mule3-webservice \
  plugins/eregulations/skills/merged-eregulations-translations-into-langadmin
```

Every hit must become a `<host>` / `<user>` placeholder or a credential *name* before the commit. **This repo is public.** Do not commit and clean up afterwards — a pushed commit cannot be un-published.

- [ ] **Step 3: Add validator-required frontmatter to each**

The Drive originals predate these conventions. Each needs `name`, `description`, `allowed-tools`, and `metadata` with `version: 0.1.0` and `version-date: 2026-08-26`. Write each `description` in the trigger style the marketplace uses — see `plugins/devops/skills/*/SKILL.md` for the house voice.

- [ ] **Step 4: Split the 51 KB skill**

`deploying-legacy-eregulations-instance/SKILL.md` is 51459 bytes. Loaded whole it dominates context on every invocation, for a procedure where a typical run needs a fraction of it. Keep in `SKILL.md`: the nine-phase flow, the input checklist, and the decision points. Move per-phase detail into `references/`, one file per phase, each linked from the flow.

Target: `SKILL.md` under 8 KB.

Run: `wc -c plugins/eregulations/skills/deploying-legacy-eregulations-instance/SKILL.md`
Expected: under 8192.

- [ ] **Step 5: Validate**

Run: `uv run --python 3.12 scripts/validate-plugins.py 2>&1 | grep -E 'eregulations|error\(s\)'`
Expected: `14 error(s)`, no `eregulations` lines.

- [ ] **Step 6: Re-run the redaction check across the whole plugin**

Run: `grep -rEn '([0-9]{1,3}\.){3}[0-9]{1,3}|password|passwd|secret' plugins/eregulations || echo CLEAN`
Expected: `CLEAN`

- [ ] **Step 7: Commit**

```bash
git add plugins/eregulations/skills
git commit -m "feat(eregulations): migrate the three Drive skills into the plugin"
```

---

### Task 8: Acceptance run and publication

**Files:**
- Modify: `plugins/eregulations/.claude-plugin/plugin.json` (version, if anything changed since Task 1)
- Modify: `plugins/eregulations/README.md` (record the verified scenarios)

**Interfaces:**
- Consumes: everything above
- Produces: a plugin installable from the marketplace

- [ ] **Step 1: Run the full suite on both CI interpreters**

Run:
```bash
uv run --python 3.9 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q
uv run --python 3.13 --with pytest python -m pytest plugins/eregulations/skills/ereg-router/tests -q
```
Expected: PASS on both. 3.9 is not decoration — the CI comment records a `zip(strict=True)` that reached a released skill and broke a recovery path while the forward path looked fine.

- [ ] **Step 2: Compile every bundled script on 3.9**

Run: `uv run --python 3.9 python -m compileall plugins/ -q && echo OK`
Expected: `OK`

- [ ] **Step 3: Confirm the validator is still at baseline**

Run: `uv run --python 3.12 scripts/validate-plugins.py 2>&1 | tail -2`
Expected: `14 error(s) in <n> files` — the same 14, none from `eregulations`.

- [ ] **Step 4: Install locally and run the spec's gate scenarios**

Add the local path as a marketplace source, enable the plugin, then run each scenario against `fixtures/fleet.sample.json` with `--dry-run`, recording actual output:

| # | Command | Must |
| --- | --- | --- |
| 1 | `/ereg --dry-run bugfix on bravo` | Block: host posture compromised |
| 2 | `/ereg --dry-run bugfix on charlie` | Block: posture unresolved — the fail-closed assertion |
| 3 | `/ereg --dry-run build admin and public` | Block on the derived pair, citing the actual csproj reference |
| 4 | `/ereg --dry-run status of alpha` with no overlay and no Monitor | Advisory facts unverified; fail-closed gates block |
| 5 | `/ereg --dry-run deploy delta` | Block: version unresolved |
| 6 | `/ereg --dry-run upgrade bravo` then override with no reason | Override refused; nothing appended to the log |
| 7 | `/ereg --dry-run bravo is down and it is on 5.x, migrate it` | Both `bugfix` and `upgrade` resolved; gates see both |

Scenario 8 from the spec (Monitor credential, no retry) belongs to Phase B — there is no login path in Phase A.

- [ ] **Step 5: Record the results in the README**

Add a "Verified" section listing each scenario and its observed outcome, dated. A scenario that did not behave as specified is a **stop**: fix the code, do not amend the expectation.

- [ ] **Step 6: Commit and open the PR**

```bash
git add plugins/eregulations
git commit -m "test(eregulations): record acceptance scenario results"
git push -u origin feat/eregulations-plugin
gh pr create --title "feat: eregulations plugin — /ereg front door with fail-closed gates" --body "Implements docs/superpowers/specs/2026-08-26-eregulations-plugin-design.md (Phase A).

Phase B (Monitor MCP server) is a separate plan, blocked on two eRegulations-Monitor changes: a viewer service account and a posture field.

Note for reviewers: this repo is public. The plugin deliberately ships no fleet data, no addresses and no posture — those come from an operator-local ~/.ereg/fleet.local.json. Please check any added file for leaked hosts."
```

- [ ] **Step 7: Confirm CI is green**

Run: `gh pr checks --watch`
Expected: `validate-plugins`, `test-plugin-scripts` (3.9 and 3.13) all pass.

---

## Phase B — not in this plan

Blocked on two changes to `eRegulations-Monitor`:

1. A `viewer` service account for the MCP server. Monitor has no service-account concept today — a feature request, not an admin action.
2. A `posture` field on the server record, so the host gate resolves posture from live state instead of the operator overlay.

Neither blocks Phase A. When both land, write `docs/superpowers/plans/<date>-eregulations-plugin-phase-b.md` covering the `mcp_eregulations_monitor` package (seven read-only tools, auth with refresh, the no-retry lockout rule, the shape probe), its `.mcp.json` registration, and the router's seam swap in Step 2 of `SKILL.md`.

## Follow-up — not in this plan

**Seven repo `CLAUDE.md` pointers.** The spec scopes these as non-blocking: the canonical facts live in the plugin, so Phase A is fully functional if these never merge. Each is a five-line file in a repo outside this one, pointing at the plugin — seven PRs, review-paced, in `eRegulations-4.0-Admin`, `-4.0-API`, `-4.0-Public`, `-CR-Alerts`, `-Monitor`, `-Statistics`, `-deploy`. (`eRegulations-5.0-Admin-SPA` already has one.) Land them at whatever pace review allows.

## Deliberately untested

**Lane detection** (Step 3) is prose, with no script and no suite. This is a considered exception to the rule that drives the rest of the plan. Lane detection is *context* — it reports what the environment can currently do — not a gate. Nothing downstream trusts it for safety: a request that reaches `execute` lane on a bad probe still meets every gate, and the gates are what fail closed. Gate logic lives in tested scripts precisely because it is what stands between a request and a production system; lane detection does not carry that weight.
