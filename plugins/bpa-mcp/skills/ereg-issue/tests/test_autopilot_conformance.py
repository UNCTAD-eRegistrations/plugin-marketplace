"""Drift guard: validate_ticket.py enums must stay in sync with autopilot's live collections.

This test imports the autopilot package from its source tree and asserts set-equality
between the validator's hardcoded enums and autopilot's authoritative frozensets /
Literals. If autopilot adds a 6th claim type this test FAILS — that is the intended
behaviour. The day this test catches a mismatch is the day the validator would have
silently accepted stale enums.

When autopilot is not importable (standalone plugin CI without the adjacent repo on
disk) the test is skipped — it must never break an offline test run.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import get_args

# ---------------------------------------------------------------------------
# Pull the validator's enum constants directly from its module.
# validate_ticket.py lives alongside this file; inserting its directory lets
# us import it without installing anything.
# ---------------------------------------------------------------------------
_TESTS_DIR = Path(__file__).parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from validate_ticket import (  # noqa: E402
    _SEVERITY as _V_SEVERITY,
    _SCALE as _V_SCALE,
    _KIND as _V_KIND,
    _CLAIM_TYPE as _V_CLAIM_TYPE,
    _CONSTRAINT_KIND as _V_CONSTRAINT_KIND,
)

# ---------------------------------------------------------------------------
# Autopilot source path (adjacent repo, not installed as a package).
# ---------------------------------------------------------------------------
_AUTOPILOT_SRC = Path("~/PROJECTS/software-factory/autopilot/src").expanduser()


def test_enums_match_live_autopilot() -> None:
    """Assert set-equality between validator enums and live autopilot collections.

    Enum sources cited by file:line so the next reader knows exactly where to
    look when a mismatch surfaces:

      - severity / scale / kind   → autopilot/src/autopilot/triage/rubric.py:37-43
      - claim_type                → autopilot/src/autopilot/triage/isc.py:54-62
      - constraint kind           → autopilot/src/autopilot/triage/constraints.py:34
                                    (ConstraintKind is a Literal; members via get_args)
    """
    try:
        if str(_AUTOPILOT_SRC) not in sys.path:
            sys.path.insert(0, str(_AUTOPILOT_SRC))
        from autopilot.triage import rubric, isc, constraints  # type: ignore[import]
    except ImportError as exc:
        import pytest  # type: ignore[import]
        pytest.skip(f"autopilot not importable — skipping drift guard ({exc})")

    # rubric.py:37 — _VALID_SEVERITY frozenset
    assert frozenset(_V_SEVERITY) == rubric._VALID_SEVERITY, (
        f"_SEVERITY mismatch\n"
        f"  validator : {sorted(_V_SEVERITY)}\n"
        f"  autopilot : {sorted(rubric._VALID_SEVERITY)}"
    )

    # rubric.py:40 — _VALID_SCALE frozenset
    assert frozenset(_V_SCALE) == rubric._VALID_SCALE, (
        f"_SCALE mismatch\n"
        f"  validator : {sorted(_V_SCALE)}\n"
        f"  autopilot : {sorted(rubric._VALID_SCALE)}"
    )

    # rubric.py:41-43 — _VALID_KIND frozenset
    assert frozenset(_V_KIND) == rubric._VALID_KIND, (
        f"_KIND mismatch\n"
        f"  validator : {sorted(_V_KIND)}\n"
        f"  autopilot : {sorted(rubric._VALID_KIND)}"
    )

    # isc.py:54-62 — _VALID_CLAIM_TYPES frozenset
    assert frozenset(_V_CLAIM_TYPE) == isc._VALID_CLAIM_TYPES, (
        f"_CLAIM_TYPE mismatch\n"
        f"  validator : {sorted(_V_CLAIM_TYPE)}\n"
        f"  autopilot : {sorted(isc._VALID_CLAIM_TYPES)}"
    )

    # constraints.py:34 — ConstraintKind = Literal["Hard", "Soft", "Assumption"]
    # get_args extracts the members of the Literal at runtime.
    constraint_kind_members = frozenset(get_args(constraints.ConstraintKind))
    assert frozenset(_V_CONSTRAINT_KIND) == constraint_kind_members, (
        f"_CONSTRAINT_KIND mismatch\n"
        f"  validator : {sorted(_V_CONSTRAINT_KIND)}\n"
        f"  autopilot : {sorted(constraint_kind_members)}"
    )
