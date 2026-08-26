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
