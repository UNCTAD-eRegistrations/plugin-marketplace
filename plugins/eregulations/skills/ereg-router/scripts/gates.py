"""Gate evaluation for the /ereg router.

Pure logic: no network, no filesystem, no subprocess. Everything this
module needs arrives in the context dict, which is what makes every
branch directly testable.

Each gate declares a FAILURE DIRECTION:

  fail closed - if the input cannot be verified, BLOCK. Used wherever
                proceeding on stale data could damage a system or touch a
                compromised host.
  fail open   - if the input cannot be verified, it does not block. Used
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


APPLIES = "applies"
DOES_NOT_APPLY = "does-not-apply"
UNDETERMINED = "undetermined"


def _applicability(context, key):
    """Classify an applicability flag three ways, never by truthiness.

    Truthiness collapses three distinct statements -- "this gate applies",
    "it does not", and "the flag is garbage" -- into two, and it lands the
    garbage on the permissive side. That is backwards for a safety gate: a
    value nobody can read is the one case where the gate must fire. So
    only an exact `True` activates a gate, only an exact `False` or an
    absent key deactivates it, and anything else is UNDETERMINED.

    `is True` / `is False` rather than `==` on purpose: `1 == True` in
    Python, and an integer 1 arriving in a JSON context is a malformed
    flag, not an affirmation.
    """
    value = context.get(key)
    if value is True:
        return APPLIES
    if value is False or value is None:
        return DOES_NOT_APPLY
    return UNDETERMINED


def _undetermined_applicability(gate, key):
    return _decision(
        gate,
        BLOCK,
        "%s is neither true nor false, so whether this gate applies "
        "cannot be determined" % key,
        "set %s to a JSON true or false in the context, then retry" % key,
    )


def _branch_pair(context):
    valid = context.get("branch_pair_valid")
    if valid is False:
        # Negative evidence outranks the applicability flag. Somebody
        # derived the pair and it does not resolve; that finding stands on
        # its own and is not withdrawn by a flag saying "never mind".
        return _decision(
            "branch_pair",
            BLOCK,
            "the checked-out Admin and Public branches were derived and are "
            "not a compatible pair",
            "check out a pair whose csproj project reference resolves, then retry",
        )
    applicability = _applicability(context, "touches_admin_public")
    if applicability == UNDETERMINED:
        return _undetermined_applicability("branch_pair", "touches_admin_public")
    if applicability == DOES_NOT_APPLY:
        return _decision("branch_pair", PASS, "request does not build Admin + Public")
    if valid is True:
        return _decision("branch_pair", PASS, "derived Admin/Public pair resolves")
    return _decision(
        "branch_pair",
        BLOCK,
        "the Admin/Public pair could not be derived",
        "check out both repos, then locate the Public web project's csproj by "
        "discovery -- its filename is branch-dependent, so do not assume one",
    )


def _media_mount(context):
    mount = context.get("media_mount")
    if mount is False:
        # As above: somebody read the compose and the mount is absent.
        # Discarding that because `targets_admin_deploy` was never set
        # would deploy an Admin that crashes on startup.
        return _decision(
            "media_mount",
            BLOCK,
            "the /app/media bind mount was checked and is absent; Admin "
            "crashes on startup without it",
            "add the /app/media bind mount to the compose file before deploying",
        )
    applicability = _applicability(context, "targets_admin_deploy")
    if applicability == UNDETERMINED:
        return _undetermined_applicability("media_mount", "targets_admin_deploy")
    if applicability == DOES_NOT_APPLY:
        return _decision("media_mount", PASS, "request is not an Admin deploy")
    if mount is True:
        return _decision("media_mount", PASS, "/app/media is bind-mounted")
    return _decision(
        "media_mount",
        BLOCK,
        "could not confirm the /app/media bind mount",
        "read the instance compose file and confirm the mount, then retry",
    )


def _is_upgrade_request(context):
    """Whether this request is itself the upgrade the version gate demands.

    Type-checked, because this grants an EXEMPTION from a blocking gate and
    so is the one place where a sloppy read buys a pass. A bare `in` test
    is far too generous here: `"upgrade" in {"upgrade": ...}` matches a
    dict's keys, and `"upgrade" in "upgrades"` matches a substring. Only a
    list or tuple carrying the exact string counts.
    """
    if context.get("kind") == "upgrade":
        return True
    secondary = context.get("secondary_kinds")
    if not isinstance(secondary, (list, tuple)):
        return False
    for entry in secondary:
        if isinstance(entry, str) and entry == "upgrade":
            return True
    return False


def _unsupported_version(context):
    major = context.get("version_major")
    if major == SUPPORTED_MAJOR:
        return _decision("unsupported_version", PASS, "target is 7.x")
    if major in UNSUPPORTED_MAJORS:
        if _is_upgrade_request(context):
            return _decision(
                "unsupported_version",
                PASS,
                "target is %s.x, but this request is itself the upgrade to 7.x" % major,
            )
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


def main(argv=None):
    """Read a JSON context on stdin, print the decisions as JSON.

    Exit status answers "did the evaluation run", NOT "what did it decide".
    A blocking verdict is this tool's normal, expected output, so it exits
    0 like any other verdict; only a context that cannot be read exits
    non-zero. Conflating the two would let a caller under `set -e` abort on
    a legitimate block, and would invite the calling layer to read non-zero
    as "the command failed" and discard stdout -- throwing away the very
    reasons and remedies an operator needs to act on. The verdict lives in
    the JSON, and nowhere else.
    """
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="Evaluate the /ereg safety gates against a JSON context on stdin."
    )
    parser.parse_args(argv)

    try:
        context = json.load(sys.stdin)
    except ValueError as exc:
        sys.stderr.write("gates.py: could not read a JSON context on stdin: %s\n" % exc)
        return 2
    if not isinstance(context, dict):
        sys.stderr.write(
            "gates.py: the context on stdin must be a JSON object, got %s\n"
            % type(context).__name__
        )
        return 2

    print(json.dumps(evaluate(context), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
