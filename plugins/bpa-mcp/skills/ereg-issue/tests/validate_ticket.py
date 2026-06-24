"""Stdlib-only conformance validator for qualified-ticket.json.

Checks required keys + that the `rubric` block uses autopilot's EXACT enums
(autopilot/src/autopilot/triage/rubric.py:33-43). No jsonschema dependency:
the schema file documents the contract; this validator enforces the load-bearing
parts deterministically.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

_SEVERITY = {"critical", "high", "medium", "low", "info"}
_SCALE = {"Small", "Medium", "Large", "Architectural"}
_KIND = {"bug", "feature", "refactor", "design", "docs", "infra", "unknown"}
_CLAIM_TYPE = {"code-fact", "runtime-observation", "environment-mapping", "future-prescription"}
_CONSTRAINT_KIND = {"Hard", "Soft", "Assumption"}
_TOP_REQUIRED = ["schema_version", "slug", "symptom", "instance", "rubric", "claims"]


def validate_ticket(ticket: dict) -> list[str]:
    errors: list[str] = []
    for key in _TOP_REQUIRED:
        if key not in ticket:
            errors.append(f"missing required key: {key}")
    rubric = ticket.get("rubric", {})
    if rubric.get("severity") not in _SEVERITY:
        errors.append(f"rubric.severity {rubric.get('severity')!r} not in {sorted(_SEVERITY)}")
    if rubric.get("scale") not in _SCALE:
        errors.append(f"rubric.scale {rubric.get('scale')!r} not in {sorted(_SCALE)}")
    if rubric.get("kind") not in _KIND:
        errors.append(f"rubric.kind {rubric.get('kind')!r} not in {sorted(_KIND)}")
    if not isinstance(rubric.get("affected_components", []), list):
        errors.append("rubric.affected_components must be a list")
    inst = ticket.get("instance", {})
    if not isinstance(inst, dict) or not inst.get("name"):
        errors.append("instance.name is required (hard-floor)")
    for i, claim in enumerate(ticket.get("claims", [])):
        if claim.get("claim_type") not in _CLAIM_TYPE:
            errors.append(f"claims[{i}].claim_type {claim.get('claim_type')!r} invalid")
        if claim.get("kind") not in _CONSTRAINT_KIND:
            errors.append(f"claims[{i}].kind {claim.get('kind')!r} invalid")
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


def test_valid_sample_passes() -> None:
    sample = Path(__file__).parent.parent / "samples" / "qualified-ticket.example.json"
    assert validate_ticket(json.loads(sample.read_text())) == []


def test_bad_severity_fails() -> None:
    assert any("severity" in e for e in validate_ticket(
        {"schema_version": "1.0", "slug": "x", "symptom": "x",
         "instance": {"name": "x"}, "claims": [],
         "rubric": {"severity": "sev1", "scale": "Small", "kind": "bug"}}))


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
