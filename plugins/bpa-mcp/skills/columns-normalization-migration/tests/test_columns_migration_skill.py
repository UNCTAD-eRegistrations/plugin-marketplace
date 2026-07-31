"""Tests for the thin columns-normalization migration skill.

Spec ("What changes"): add the thin migration skill: scan (form_get) -> plan
file -> analyst hash-check review -> off-hours apply window driving form_patch
per row with live re-verification + first-use canary rollback -> verify ->
per-service serialized, human-gated publish.

The skill is a SAFETY-CRITICAL document; these tests gate its text on the
spec invariants and edge cases (all unenforceable at the code layer, hence
they must be spelled out in prose the operator/agent reads):

  - Only the instance allowlist is platform-enforced; off-hours window,
    one-operator-per-instance, and plan review are procedural / NOT enforced.
  - Envers history + the form_patch audit log are authoritative; plan files
    are per-operator and non-authoritative.
  - The apply half is now ENABLED but gated on per-instance DEPLOYMENT of
    TOBE-18004 / DS-Frontend#173 (DS >= 2.18.326 on the 2.18 line, >= 2.19.188
    on develop) — the deployed DS version on the resolved instance must be
    verified before any write.
  - Backend is last-write-wins: no @Version / ETag / If-Match; no conflict
    detection may be assumed.
  - Allowlist targets els-dev, never jamaica / lesotho2; the resolved
    instance is checked and an explicit allowlisted instance is required
    (no instance=None default).
  - Pre-write re-verify scope (whole-form vs per-row hash) chosen + trade-off
    stated. Re-read narrows but does not close the LWW window.
  - First-use canary rollback is itself a whole-form LWW write, scoped to
    re-read-then-restore only when the live form still matches the canary's
    post-write hash; it cannot recover a concurrent third-party edit and does
    not undo the whole batch (earlier rows need Envers rollback).
  - No 'clean-check' terminology; publish gates on Envers audit history /
    PublishReadinessResult.
  - Keycloak token expiry mid-batch -> refresh/re-auth + resume path.
  - _invalidate_form_cache failure after a write -> verify must not trust a
    cached form_get.
  - Network partition between re-verify and next write -> detect ambiguous
    state and resume, not blind retry.

If the sibling SKILL.md is missing or is not the columns-migration skill, the
locator fails with a clear assertion (not a bare FileNotFoundError).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _skill_text() -> str:
    """Read the sibling SKILL.md and confirm it is the columns-migration one."""
    if not SKILL_MD.is_file():
        pytest.fail(f"SKILL.md not found at {SKILL_MD}")
    text = SKILL_MD.read_text(encoding="utf-8").lower()
    if "form_patch" in text and (
        "column" in text or "normalize" in text or "normali" in text
    ):
        return text
    pytest.fail(
        f"{SKILL_MD} is not the columns-normalization migration skill "
        "(expected a SKILL.md referencing form_patch + columns)."
    )
    raise AssertionError  # pragma: no cover


def _assert_any(text: str, keywords: list[str], msg: str) -> None:
    assert any(k in text for k in keywords), msg


def test_skill_exists_and_describes_scan_plan_flow() -> None:
    text = _skill_text()
    assert "form_get" in text, "skill must describe the read-only scan via form_get"
    assert "plan" in text, "skill must describe producing a plan file"


def test_skill_flags_only_allowlist_is_platform_enforced() -> None:
    text = _skill_text()
    _assert_any(
        text,
        ["allowlist", "allow-list", "allowlisted"],
        "skill must name the instance allowlist as the enforced control",
    )
    # The unenforceable gates must be explicitly called out as procedural.
    _assert_any(
        text,
        ["not platform-enforced", "not enforced", "unenforceable", "procedural"],
        "skill must state off-hours/one-operator/plan-review are not enforced",
    )
    assert "off-hours" in text or "off hours" in text
    assert "one operator" in text or "one-operator" in text or "per operator" in text


def test_skill_marks_envers_and_audit_log_authoritative() -> None:
    text = _skill_text()
    assert "envers" in text, "skill must cite Envers history as authoritative"
    assert "audit" in text
    _assert_any(
        text,
        ["non-authoritative", "not authoritative", "per-operator", "per operator"],
        "skill must state plan files are non-authoritative / per-operator",
    )


def test_skill_gates_apply_on_platform_precondition_and_deploy() -> None:
    text = _skill_text()
    _assert_any(
        text,
        ["tobe-18004", "ds-frontend#173", "ds-frontend #173", "173"],
        "skill must gate apply on the platform precondition (TOBE-18004/#173)",
    )
    _assert_any(
        text,
        [
            "deployed",
            "deployment",
            "2.18.326",
            "2.19.188",
            "before any write",
            "verify the resolved instance",
            "abort",
        ],
        "skill must gate apply on per-instance DEPLOYMENT of the platform "
        "precondition, not just the code having merged",
    )


def test_skill_states_last_write_wins_no_conflict_detection() -> None:
    text = _skill_text()
    _assert_any(
        text,
        ["last-write-wins", "last write wins", "lww"],
        "skill must state the backend is last-write-wins",
    )
    _assert_any(
        text,
        ["no @version", "no etag", "no if-match", "no optimistic", "no conflict"],
        "skill must state there is no optimistic locking / conflict detection",
    )


def test_skill_requires_resolved_allowlisted_instance_never_none() -> None:
    text = _skill_text()
    assert "els-dev" in text or "elsalvador-dev" in text, (
        "skill must show an allowlisted target instance"
    )
    # The permitted set is the pinned set from the identifiers table, not
    # els-dev alone: cuba and kenya-test are migration targets too (#54), and
    # the operator checklist must name them as permitted, not just the canary.
    assert "cuba" in text and "kenya-test" in text, (
        "skill must name cuba and kenya-test as permitted migration targets, "
        "not just the els-dev canary"
    )
    # Never-write set: vucecuba (sovereign CAS prod) plus jamaica/lesotho2.
    assert "vucecuba" in text, (
        "skill must name vucecuba as a never-write target"
    )
    assert "jamaica" in text and "lesotho2" in text, (
        "skill must name jamaica/lesotho2 as forbidden targets"
    )
    _assert_any(
        text,
        ["resolved instance", "resolve the instance", "check_autopilot_allowlist"],
        "skill must check the resolved instance against the allowlist",
    )
    _assert_any(
        text,
        [
            "explicit",
            "never instance=none",
            "no instance=none",
            "not none",
            "no default",
        ],
        "skill must require an explicit allowlisted instance (never instance=None)",
    )
    # The operator checklist's abort rule must name the pinned permitted set
    # (elsalvador-dev, cuba, kenya-test), not "els-dev" as the sole target —
    # otherwise the checklist would tell the operator to abort on cuba and
    # kenya-test, which the pinned table marks as migration targets.
    _assert_any(
        text,
        ["permitted", "permitted set", "pinned permitted set"],
        "skill's abort rule must name the pinned permitted set (elsalvador-dev, "
        "cuba, kenya-test), not els-dev alone, so it does not abort on the "
        "instances the migration actually targets",
    )


def test_skill_pins_instance_identifiers_cuba_target_vucecuba_never_write() -> None:
    text = _skill_text()
    # cuba is the migration target; vucecuba (sovereign CAS production) must
    # be pinned as never-write and distinguished from cuba.
    assert "cuba.eregistrations.org" in text, (
        "skill must pin the cuba target instance to its exact host"
    )
    assert "vucecuba.mincex.gob.cu" in text, "skill must pin the vucecuba host"
    _assert_any(
        text,
        ["never write", "never-write", "never  write"],
        "skill must mark vucecuba as never-write",
    )
    # The doc must explicitly distinguish cuba (target) from vucecuba
    # (forbidden) so the two are not conflated.
    assert "not `vucecuba`" in text or "not vucecuba" in text, (
        "skill must explicitly warn cuba is NOT vucecuba"
    )
    assert "kenya-test" in text or "test.kenya.eregistrations.org" in text
    assert "dev.els.eregistrations.org" in text or "elsalvador-dev" in text


def test_skill_canary_states_target_instance_before_write() -> None:
    text = _skill_text()
    assert "canary" in text, "skill must describe the first-use canary"
    _assert_any(
        text,
        ["resolved target instance", "prints the resolved target instance"],
        "skill must require the canary to state the resolved target instance",
    )
    _assert_any(
        text,
        ["before the canary write", "before the write", "before the batch"],
        "skill must require the target instance be stated BEFORE the write, "
        "so a wrong target is visible before the batch",
    )


def test_skill_documents_reverify_scope_and_tradeoff() -> None:
    text = _skill_text()
    _assert_any(
        text,
        ["whole-form hash", "whole form hash", "per-row hash", "per row hash"],
        "skill must state the re-verify hash scope (whole-form vs per-row)",
    )
    _assert_any(
        text,
        ["trade-off", "tradeoff", "narrows", "does not close", "residual"],
        "skill must state the re-read window is narrowed, not closed",
    )


def test_skill_scopes_canary_rollback_and_its_limits() -> None:
    text = _skill_text()
    assert "canary" in text, "skill must describe the first-use canary"
    assert "rollback" in text
    _assert_any(
        text,
        ["matches the canary", "post-write hash", "re-read", "still matches"],
        "canary rollback must be scoped to re-read-then-restore on hash match",
    )
    _assert_any(
        text,
        [
            "cannot recover",
            "cannot undo the whole batch",
            "earlier rows",
            "envers rollback",
        ],
        "skill must state canary rollback cannot recover concurrent edits / "
        "earlier committed rows",
    )


def test_skill_publish_step_avoids_clean_check_uses_envers_readiness() -> None:
    text = _skill_text()
    assert "clean-check" not in text and "clean check" not in text, (
        "skill must not invent a non-existent 'clean-check' API/step"
    )
    _assert_any(
        text,
        ["publishreadiness", "publish readiness", "servicepublishcontroller", "envers"],
        "publish step must gate on the real Envers-based readiness result",
    )
    _assert_any(
        text,
        ["per-service", "per service", "serialized"],
        "publish must be per-service serialized",
    )
    _assert_any(
        text,
        ["human-gated", "human gated", "human review", "manual"],
        "publish must be human-gated",
    )


def test_skill_handles_token_expiry_and_resume() -> None:
    text = _skill_text()
    _assert_any(
        text,
        ["token", "re-auth", "reauth", "refresh", "401"],
        "skill must describe a token-refresh/re-auth path mid-batch",
    )
    _assert_any(
        text,
        ["resume", "resumable", "partial batch", "half-applied"],
        "skill must describe a resumable/partial-batch recovery path",
    )


def test_skill_documents_managed_determinant_replication_step() -> None:
    text = _skill_text()
    # References the behaviour-clone tool (#458).
    _assert_any(
        text,
        ["componentbehaviour_generate_newkeys", "generate_newkeys"],
        "skill must document the managed-determinant replication via "
        "componentbehaviour_generate_newkeys",
    )
    # Load-bearing ordering: clone runs AFTER the structural form_patch, once
    # the new keys exist.
    _assert_any(
        text,
        [
            "after the `form_patch`",
            "after the form_patch",
            "new container keys must already",
        ],
        "skill must state the clone runs AFTER form_patch / the new keys must "
        "exist first",
    )
    # Orphaned source behaviour recorded as tracked debt, not deleted/gated.
    _assert_any(
        text,
        ["orphaned-but-intact", "orphaned source", "tracked debt"],
        "skill must record the orphaned source behaviour as tracked debt",
    )
    assert "recover_orphaned_config" in text, (
        "skill must note the orphaned source behaviour is invisible to "
        "recover_orphaned_config"
    )


def test_skill_documents_over12_split_track_with_caller() -> None:
    text = _skill_text()
    # The over-12 split track is now wired end-to-end: the scan surfaces the
    # split worklist and a real caller applies it (Erick's "split-apply has no
    # caller" is closed).
    assert "scan_form_for_splits" in text, (
        "skill must document scanning over-12 splits via scan_form_for_splits"
    )
    assert "plan_to_split_operations" in text, (
        "skill must document applying splits via plan_to_split_operations "
        "(the caller now exists)"
    )
    # Both tracks are named so the split is a real, delineated track.
    _assert_any(
        text,
        ["over-12 split", "split track", "split sub-track", "split apply"],
        "skill must present the over-12 split as its own track",
    )
    _assert_any(
        text,
        ["under-12 pad", "pad track", "pad sub-track", "pad apply"],
        "skill must keep the under-12 pad track distinct",
    )


def test_skill_documents_behaviour_reattach_and_post_apply_assertion() -> None:
    text = _skill_text()
    # After the clone, the returned behaviourId is WRITTEN BACK onto the
    # container (the clone does not attach itself). Accept either the
    # form_patch SET write-back or the form_component_update alternative.
    _assert_any(
        text,
        [
            'set", "key"',
            '"set"',
            "second `form_patch`",
            "form_component_update",
        ],
        "skill must document writing behaviourId back onto each container "
        "(form_patch set / form_component_update)",
    )
    _assert_any(
        text,
        ["write the pointer back", "write them back", "written back", "write it back"],
        "skill must state the clone does not attach itself and the id is written back",
    )
    # Post-apply assertion: every managed container must come back with a
    # non-empty behaviourId; empty -> failed apply.
    _assert_any(
        text,
        ["post-apply assertion", "non-empty `behaviourid`", "did not attach"],
        "skill must document a post-apply assertion that each managed "
        "container has a non-empty behaviourId",
    )
    _assert_any(
        text,
        ["failed apply", "treat that row as", "treat as a failed"],
        "an empty behaviourId after write-back must be treated as a failed "
        "apply for that row",
    )


def test_skill_handles_stale_cache_and_network_partition() -> None:
    text = _skill_text()
    _assert_any(
        text,
        ["invalidate", "stale cache", "cached form_get", "force_refresh"],
        "verify step must not trust a possibly-stale cached form_get",
    )
    _assert_any(
        text,
        [
            "partition",
            "ambiguous",
            "re-read-and-compare",
            "not blindly retry",
            "idempot",
        ],
        "skill must define ambiguous-state detection instead of blind retry",
    )


# The two SCAN modules, whose reasons are PHASE 1 vocabulary. The apply modules
# are deliberately NOT here: they emit their own skip reasons (row_not_found,
# modified_since_apply, ...) which belong to PHASE 3, and requiring those in
# PHASE 1 would be wrong, not merely stricter.
_SCAN_SCRIPTS = ("columns_logic.py", "columns_split.py")


def _literal_choices(node: ast.AST) -> set[str]:
    """The str literals a value expression can evaluate TO.

    Deliberately NOT ``ast.walk``: walking the whole subtree of

        reason = ("grid_direct_child"
                  if grid_context == "direct_child"
                  else "inside_grid_nested")

    also harvests ``"direct_child"`` out of the CONDITION, which is a
    comparison operand and not a reason the module can emit. Only the branches
    of a conditional are values.

    Anything non-literal (a Name, Attribute, Call) yields nothing, which is
    correct: ``{"reason": verdict.reason}`` is a passthrough whose value is
    already covered where the literal was assigned.
    """
    if isinstance(node, ast.Constant):
        return {node.value} if isinstance(node.value, str) else set()
    if isinstance(node, ast.IfExp):
        return _literal_choices(node.body) | _literal_choices(node.orelse)
    if isinstance(node, ast.BoolOp):  # e.g. `reason or "fallback"`
        return set().union(*(_literal_choices(v) for v in node.values))
    return set()


def _emitted_scan_reasons() -> dict[str, set[str]]:
    """Collect every literal ``reason`` the two scan modules can emit.

    Parsed with ``ast``, NOT grepped. The regex predecessor matched only
    ``"reason": "..."`` dict literals, so when TOBE-18037 added the pad track's
    ``reason = ("grid_direct_child" if ... else "inside_grid_nested")`` the
    guard could not see it at all (marketplace #61 review). An AST walk covers
    every form this codebase uses -- dict literal, ``reason=`` keyword, and
    plain or conditional assignment -- and as a bonus stops matching reason
    names that merely appear quoted inside a docstring.

    Known limitation, recorded rather than silently accepted: a reason passed
    POSITIONALLY (``Verdict("skip", "x")``) would still be missed. Every call
    site here uses keywords, and `Verdict` has 7 fields, so positional use is
    not a realistic style for this module.
    """
    collected: dict[str, set[str]] = {}
    for name in _SCAN_SCRIPTS:
        source = (SKILL_DIR / "scripts" / name).read_text(encoding="utf-8")
        found: set[str] = set()
        for node in ast.walk(ast.parse(source, filename=name)):
            # Verdict(action="skip", reason="no_key")
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "reason":
                        found |= _literal_choices(kw.value)
            # {"action": "review", "reason": "all_columns_empty"}
            elif isinstance(node, ast.Dict):
                # NB: a `{**spread}` entry has key None, hence the isinstance.
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "reason":
                        found |= _literal_choices(value)
            # reason = "complete" if base_sum == TARGET_SUM else "over_12"
            elif isinstance(node, ast.Assign):
                if any(
                    isinstance(t, ast.Name) and t.id == "reason" for t in node.targets
                ):
                    found |= _literal_choices(node.value)
        collected[name] = found
    return collected


def _documents(phase1: str, reason: str) -> bool:
    """Is ``reason`` present in ``phase1`` as a whole token?

    A bare substring test is not enough: it let `inside_grid` count as
    documented purely because `inside_grid_nested` appears, so the shorter
    reason could vanish from the runbook without failing anything.

    The REVERSE assertion covers two structural shapes (#66 review, round 2):
    markdown TABLE ROWS (first-column code span) and DEFINITION BULLETS — a
    bullet whose leading element is a bold code span (`- **\`reason\`**`),
    the prose analogue of a table row. The bullet shape is what caught the
    `in_grid_nested` retirement gap: the reason's bullet survived in PHASE 1
    prose after the scripts stopped emitting it, and table-row scraping alone
    passed green. Scraping every backticked token instead would
    false-positive on non-reason identifiers (`base_sum`, `grid_context`,
    ...) — the two structural shapes carry definition intent; running prose
    does not. Residual, recorded: a retired reason mentioned in FREE prose
    (neither shape) is still uncaught, so retiring a reason keeps a human
    sweep of PHASE 1 prose in its checklist.
    """
    return (
        re.search(rf"(?<![a-z0-9_]){re.escape(reason)}(?![a-z0-9_])", phase1) is not None
    )


def test_skill_documents_every_scan_reason_the_scanners_can_emit() -> None:
    """Lockstep guard (marketplace #59, widened per the #61 review).

    The PHASE 1 runbook is the only place a scanned row becomes visible to a
    human: the apply side skips any row it does not own, silently. So every
    reason either scanner can emit must be documented there, or rows sit
    unnormalized with nobody aware a decision is pending. Third occurrence of
    the drift class #55 paid down for the allowlist checklist -- which is why
    this is a test and not a review checklist item.

    Both scan modules are read, and the reason names come out of the source, so
    adding one without documenting it fails HERE rather than in a later review.
    """
    text = _skill_text()  # NB: _skill_text() lowercases the file
    # A missing anchor must raise, not silently yield an empty slice that makes
    # every assertion below vacuously true.
    start = text.index("## phase 1")
    end = text.index("## phase 2")
    phase1 = text[start:end]

    # Scoping to the section is load-bearing: a mention in the changelog is not
    # operator-facing documentation, and satisfying the guard from the changelog
    # is exactly the false positive the #59 review caught.
    assert "## phase 3" not in phase1, "PHASE 1 slice must stop before PHASE 3"

    by_script = _emitted_scan_reasons()
    undocumented: dict[str, list[str]] = {}
    for script, reasons in sorted(by_script.items()):
        assert reasons, f"expected {script} to emit at least one reason"
        missing = sorted(r for r in reasons if not _documents(phase1, r))
        if missing:
            undocumented[script] = missing

    assert not undocumented, (
        "SKILL.md PHASE 1 must document every reason the scanners can emit "
        f"(as a whole token); missing from the PHASE 1 section: {undocumented}"
    )

    # Reverse direction (#64 review, Erick). The forward assertion alone
    # enforces emitted -> documented only; a vocabulary row describing a
    # reason nothing emits fails nothing (`totally_bogus_orphan` passed all
    # 205 tests). So a rename or removal in code could strand its doc row in
    # PHASE 1 forever, and operators would look for a reason that can never
    # appear in a plan. Every reason-shaped token documented as a
    # first-column code span in a PHASE 1 table must be in the emitted set.
    #
    # The header row (| `reason` | Meaning |) is excluded structurally — the
    # line after it is the |---| separator — rather than via a hardcoded
    # token list, which would itself be a small drift vector.
    emitted_all: set[str] = set().union(*by_script.values())
    lines = phase1.splitlines()
    claimed: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^\|\s*`([a-z0-9_]+)`\s*\|", line)
        if not m:
            continue
        if i + 1 < len(lines) and re.match(r"^\|\s*-", lines[i + 1]):
            continue  # header row
        claimed.add(m.group(1))
    assert claimed, "expected the PHASE 1 vocabulary table to have rows"

    # Definition bullets: `- **\`reason\`**` — the prose shape PHASE 1 uses
    # to define a reason outside the table. `[a-z0-9_]+` must span the WHOLE
    # code span, so `action:"review"` bullets are not grabbed; identifiers in
    # running prose (`base_sum`, `grid_context`) are inline code spans, never
    # bullet-leading bold definitions.
    claimed |= set(re.findall(r"^\s*-\s*\*\*`([a-z0-9_]+)`\*\*", phase1, re.M))
    orphaned = sorted(claimed - emitted_all)
    assert not orphaned, (
        "PHASE 1 documents reasons no scan module emits (orphaned vocabulary "
        f"rows — rename or remove them): {orphaned}"
    )
