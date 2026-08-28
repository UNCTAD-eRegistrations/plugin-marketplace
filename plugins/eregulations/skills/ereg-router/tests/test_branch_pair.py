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
    assert "could not read" in result["reason"]


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


def test_case_mismatch_in_the_reference_is_invalid_even_on_case_insensitive_hosts(tmp_path):
    """os.path.exists follows the host filesystem's case-folding (case-insensitive
    by default on macOS); the verdict must not depend on that. dotnet build on
    Linux CI is case-sensitive, so a reference that only matches case-insensitively
    is a build that Linux CI will reject.
    """
    admin = tmp_path / "Admin"
    lib = admin / "Unctad.eRegulations.Library"
    lib.mkdir(parents=True)
    (lib / "Unctad.eRegulations.Library.csproj").write_text("<Project />")

    public = tmp_path / "Public" / "src"
    public.mkdir(parents=True)
    csproj = public / "WebAppCore.csproj"
    csproj.write_text(
        '<Project><ItemGroup><ProjectReference Include='
        '"..\\..\\Admin\\unctad.eregulations.library\\Unctad.eRegulations.Library.csproj" />'
        "</ItemGroup></Project>"
    )

    result = branch_pair.derive(str(csproj), str(admin), _reader({}))
    assert result["valid"] is False


def test_public_root_is_found_regardless_of_csproj_depth(tmp_path):
    """public_root used to be dirname(dirname(csproj)), which assumes the
    csproj sits exactly one directory below the repo root. The real Public
    layout nests it two levels down (Project/WebApp/), landing one
    directory short of the actual root -- it only ever "worked" because
    `git -C` walks upward on its own. This pins the root down explicitly
    by locating `.git`, at whatever depth.
    """
    repo_root = tmp_path / "Public"
    (repo_root / ".git").mkdir(parents=True)
    project_dir = repo_root / "Project" / "WebApp"
    project_dir.mkdir(parents=True)
    csproj = project_dir / "WebApp.csproj"
    csproj.write_text((FIXTURES / "no-reference.csproj").read_text())

    seen_roots = []

    def reader(root):
        seen_roots.append(str(root))
        return "feature/public-branch"

    admin = tmp_path / "Admin"
    admin.mkdir()

    branch_pair.derive(str(csproj), str(admin), reader)

    old_wrong_root = str(project_dir.parent)  # repo_root/Project -- one short
    assert str(repo_root) in seen_roots
    assert old_wrong_root not in seen_roots


def test_public_root_falls_back_to_the_containing_directory_without_a_git_repo(tmp_path):
    """No `.git` anywhere above the csproj (e.g. an unversioned checkout,
    as in most of these fixtures) -- fall back to the csproj's own
    directory rather than guessing a fixed depth upward."""
    public = tmp_path / "Public" / "src"
    public.mkdir(parents=True)
    csproj = public / "WebAppCore.csproj"
    csproj.write_text((FIXTURES / "no-reference.csproj").read_text())

    seen_roots = []

    def reader(root):
        seen_roots.append(str(root))
        return "feature/x"

    branch_pair.derive(str(csproj), str(tmp_path / "Admin"), reader)

    assert str(public) in seen_roots


def test_detached_head_is_reported_as_none_not_the_literal_string(monkeypatch):
    """`git rev-parse --abbrev-ref HEAD` returns the literal "HEAD" in a
    detached checkout -- indistinguishable from a branch actually named
    "HEAD" if passed through as-is. Must normalise to None instead."""

    def fake_check_output(cmd, **kwargs):
        return b"HEAD\n"

    monkeypatch.setattr(branch_pair.subprocess, "check_output", fake_check_output)
    assert branch_pair.git_branch("/some/checkout") is None


def test_a_branch_literally_named_head_would_be_indistinguishable_but_real_branches_pass_through(monkeypatch):
    """Regression guard: ordinary branch names must still pass through
    unchanged -- only the exact sentinel "HEAD" is normalised."""

    def fake_check_output(cmd, **kwargs):
        return b"feature/head-hunting\n"

    monkeypatch.setattr(branch_pair.subprocess, "check_output", fake_check_output)
    assert branch_pair.git_branch("/some/checkout") == "feature/head-hunting"


def test_invalid_when_the_reference_resolves_outside_admin_root(tmp_path):
    """A reference that happens to resolve into some OTHER Admin-shaped checkout
    must not be reported valid just because a Library.csproj exists there — the
    admin_branch reported has to belong to the same tree that resolved.
    """
    admin_root = tmp_path / "Admin"
    admin_root.mkdir()

    other_admin = tmp_path / "OtherAdmin"
    lib = other_admin / "Unctad.eRegulations.Library"
    lib.mkdir(parents=True)
    (lib / "Unctad.eRegulations.Library.csproj").write_text("<Project />")

    public = tmp_path / "Public" / "src"
    public.mkdir(parents=True)
    csproj = public / "WebAppCore.csproj"
    csproj.write_text(
        '<Project><ItemGroup><ProjectReference Include='
        '"..\\..\\OtherAdmin\\Unctad.eRegulations.Library\\Unctad.eRegulations.Library.csproj" />'
        "</ItemGroup></Project>"
    )

    result = branch_pair.derive(str(csproj), str(admin_root), _reader({}))
    assert result["valid"] is False
