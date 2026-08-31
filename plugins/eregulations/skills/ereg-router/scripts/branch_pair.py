"""Derive the Admin/Public branch pair from the csproj project reference.

Public's web project carries a ProjectReference to Admin's
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


def _case_divergent_segment(path, base):
    """Walk `path` below `base`, segment by segment, against real listings.

    os.path.exists follows the host filesystem's case-folding — case-
    insensitive by default on macOS, case-sensitive on Linux (and in the
    actual dotnet build toolchain). A verdict built on os.path.exists alone
    would therefore say `valid=True` on one host for a reference that
    `dotnet build` rejects on another. Comparing each segment against
    os.listdir() is a plain Python string comparison, so it gives the same
    answer regardless of the host's case-folding.

    The walk starts at `base` — the Admin checkout — and NOT at the
    filesystem root. Only the segments below the checkout come from the
    csproj reference, and only those can say anything about whether the
    build will resolve it. Ancestors above the checkout are whatever the
    operator happened to type: on a case-folding host `/Users/...` typed as
    `/USERS/...` resolves and the pair is fine, but walking from `/` found
    `USERS` absent from `/`'s listing and condemned the pair for it. That
    verdict then reached gates.py as `valid is False` — confirmed-bad
    evidence, which outranks the applicability flag — and blocked requests
    that never build Admin + Public at all, with a remedy nothing could act
    on because the reference did resolve.

    A `path` that is not under `base` is not this function's question:
    containment is a separate verdict with its own reason, so that case
    returns None rather than inventing a case complaint.

    Returns the first segment that is not present verbatim in its parent
    directory's listing, or None if every segment matches exactly. Callers
    only reach this after confirming the path exists (case-insensitively),
    so a non-None result here means "case mismatch", not "missing".
    """
    path = os.path.normpath(os.path.abspath(path))
    base = os.path.normpath(os.path.abspath(base))
    try:
        relative = os.path.relpath(path, base)
    except ValueError:
        # Different drives on Windows — nothing below `base` to walk.
        return None
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return None
    segments = [part for part in relative.split(os.sep) if part and part != os.curdir]
    current = base
    for segment in segments:
        try:
            entries = os.listdir(current)
        except OSError:
            return segment
        if segment not in entries:
            return segment
        current = os.path.join(current, segment)
    return None


#: What `git rev-parse --abbrev-ref HEAD` prints when the checkout is not on
#: a branch at all. It is a sentinel, not a name.
DETACHED_HEAD = "HEAD"


def _reported_branch(value):
    """Normalise a reader's answer into the branch name to report, or None.

    `git rev-parse --abbrev-ref HEAD` prints the literal string `HEAD` when
    the checkout is detached. Passed through, that is indistinguishable
    from a checkout genuinely on a branch called `HEAD`, so a detached pair
    was reported to the operator as being on a branch — the one thing it is
    not, and the state in which "which branches am I on" has no answer.

    None is the value these fields already carry when there is no branch
    name to report (the path is not a git checkout), and both consumers —
    SKILL.md 4a and references/versions.md, which only print the two fields
    — read it as "no branch". Nothing in gates.py reads either field, so
    the gate outcomes are untouched by this.

    Only the exact sentinel is normalised: `Head`, `HEADS` and
    `feature/head-hunting` are real branch names and are reported as such.
    """
    if value == DETACHED_HEAD:
        return None
    return value


def git_branch(root):
    """Current branch of a checkout, or None if it is not on one.

    None covers both "not a git checkout" and "detached HEAD" — see
    `_reported_branch`. Neither is a branch name, and the caller's only use
    for this value is to print it.
    """
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.STDOUT,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return _reported_branch(out.decode("utf-8").strip())


def derive(public_csproj, admin_root, branch_reader=git_branch):
    """Resolve the reference and report whether the pair holds."""
    result = {
        "valid": None,
        "reason": "",
        "reference": None,
        # Normalised here as well as in git_branch, because the contract
        # ("this field never names a branch that does not exist") belongs to
        # the field an operator reads, not to whichever reader filled it.
        "admin_branch": _reported_branch(branch_reader(admin_root)),
        "public_branch": None,
    }

    try:
        with open(public_csproj, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except (IOError, OSError, ValueError):
        result["reason"] = "could not read %s" % public_csproj
        return result

    public_root = os.path.dirname(os.path.dirname(os.path.abspath(public_csproj)))
    result["public_branch"] = _reported_branch(branch_reader(public_root))

    reference = extract_library_reference(text)
    if reference is None:
        result["reason"] = "no Unctad.eRegulations.Library ProjectReference found"
        return result
    result["reference"] = reference

    # csproj paths are Windows-style; the router runs on macOS and Linux.
    relative = reference.replace("\\", os.sep).replace("/", os.sep)
    target = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(public_csproj)), relative))

    if not os.path.exists(target):
        result["valid"] = False
        result["reason"] = "referenced project does not exist at %s" % target
        return result

    # Containment is settled BEFORE the case walk, because the walk needs a
    # base to start from and admin_root is that base. Checking case first
    # would mean walking from the filesystem root, which drags in ancestors
    # that belong to neither checkout.
    admin_root_abs = os.path.abspath(str(admin_root))
    try:
        inside_admin_root = os.path.commonpath([admin_root_abs, target]) == admin_root_abs
    except ValueError:
        inside_admin_root = False
    if not inside_admin_root:
        result["valid"] = False
        result["reason"] = (
            "reference resolves outside admin_root (%s): %s" % (admin_root_abs, target)
        )
        return result

    diverging = _case_divergent_segment(target, admin_root_abs)
    if diverging is not None:
        result["valid"] = False
        result["reason"] = (
            "referenced project resolves only case-insensitively; "
            "%r does not appear verbatim on disk (path %s)" % (diverging, target)
        )
        return result

    result["valid"] = True
    result["reason"] = "reference resolves to %s" % target
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
