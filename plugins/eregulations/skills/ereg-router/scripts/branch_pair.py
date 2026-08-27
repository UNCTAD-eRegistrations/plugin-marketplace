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


def _case_divergent_segment(path):
    """Walk `path` segment by segment against real directory listings.

    os.path.exists follows the host filesystem's case-folding — case-
    insensitive by default on macOS, case-sensitive on Linux (and in the
    actual dotnet build toolchain). A verdict built on os.path.exists alone
    would therefore say `valid=True` on one host for a reference that
    `dotnet build` rejects on another. Comparing each segment against
    os.listdir() is a plain Python string comparison, so it gives the same
    answer regardless of the host's case-folding.

    Returns the first segment that is not present verbatim in its parent
    directory's listing, or None if every segment matches exactly. Callers
    only reach this after confirming the path exists (case-insensitively),
    so a non-None result here means "case mismatch", not "missing".
    """
    path = os.path.normpath(path)
    drive, rest = os.path.splitdrive(path)
    is_abs = rest.startswith(os.sep)
    segments = [part for part in rest.split(os.sep) if part]
    current = (drive + os.sep) if is_abs else (drive or ".")
    for segment in segments:
        try:
            entries = os.listdir(current)
        except OSError:
            return segment
        if segment not in entries:
            return segment
        current = os.path.join(current, segment)
    return None


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
        with open(public_csproj, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except (IOError, OSError, ValueError):
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

    if not os.path.exists(target):
        result["valid"] = False
        result["reason"] = "referenced project does not exist at %s" % target
        return result

    diverging = _case_divergent_segment(target)
    if diverging is not None:
        result["valid"] = False
        result["reason"] = (
            "referenced project resolves only case-insensitively; "
            "%r does not appear verbatim on disk (path %s)" % (diverging, target)
        )
        return result

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
