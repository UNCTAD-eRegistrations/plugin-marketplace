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


def _is_upgrade_request(context):
    kinds = list(context.get("secondary_kinds") or ())
    kinds.append(context.get("kind"))
    return "upgrade" in kinds


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
