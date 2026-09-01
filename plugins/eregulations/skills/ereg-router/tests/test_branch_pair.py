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


def _filesystem_folds_case(tmp_path):
    probe = tmp_path / "CaseProbe"
    probe.mkdir()
    return (tmp_path / "caseprobe").exists()


def test_ancestors_outside_both_checkouts_are_not_case_checked(tmp_path):
    """The case walk must start inside the checkouts, not at the filesystem root.

    It used to compare every segment from `/` upward, including ancestors
    the operator merely typed. On a case-folding host, `/Users/...` typed
    as `/USERS/...` resolves, so the pair is genuinely fine -- but `USERS`
    is not in `/`'s listing, so the walk reported it as case-divergent and
    returned `valid: false`.

    That is not a cosmetic wrong answer. `gates.py` reads `valid is False`
    as confirmed-bad evidence, which outranks the applicability flag, so
    it blocked even requests that never build Admin + Public -- with a
    remedy ("check out a pair whose csproj project reference resolves")
    that nothing could act on, because the reference did resolve.

    Only the segments below the checkout can say anything about whether
    `dotnet build` will resolve the reference on case-sensitive Linux.
    """
    if not _filesystem_folds_case(tmp_path):
        import pytest

        pytest.skip("needs a case-folding filesystem to re-case an ancestor")

    outer = tmp_path / "Outer"
    lib = outer / "Admin" / "Unctad.eRegulations.Library"
    lib.mkdir(parents=True)
    (lib / "Unctad.eRegulations.Library.csproj").write_text("<Project />")
    public = outer / "Public" / "src"
    public.mkdir(parents=True)
    csproj = public / "WebAppCore.csproj"
    csproj.write_text(
        '<Project><ItemGroup><ProjectReference Include='
        '"..\\..\\Admin\\Unctad.eRegulations.Library\\Unctad.eRegulations.Library.csproj" />'
        "</ItemGroup></Project>"
    )

    # The operator typed the shared ancestor in a different case. It resolves.
    recased = str(tmp_path / "OUTER")
    result = branch_pair.derive(
        recased + "/Public/src/WebAppCore.csproj", recased + "/Admin", _reader({})
    )
    assert result["valid"] is True, result["reason"]


def test_case_divergence_below_the_base_is_still_reported(tmp_path):
    """Narrowing the walk must not stop it seeing what it exists to see."""
    base = tmp_path / "Admin"
    (base / "Unctad.eRegulations.Library").mkdir(parents=True)

    good = base / "Unctad.eRegulations.Library" / "x.csproj"
    assert branch_pair._case_divergent_segment(str(good), str(base)) == "x.csproj"

    (base / "Unctad.eRegulations.Library" / "x.csproj").write_text("<Project />")
    assert branch_pair._case_divergent_segment(str(good), str(base)) is None

    bad = base / "unctad.eregulations.library" / "x.csproj"
    assert (
        branch_pair._case_divergent_segment(str(bad), str(base))
        == "unctad.eregulations.library"
    )


def test_case_walk_ignores_a_target_that_is_not_under_the_base(tmp_path):
    """Containment is a separate verdict with its own reason; the case walk
    does not also try to answer it."""
    base = tmp_path / "Admin"
    base.mkdir()
    assert branch_pair._case_divergent_segment(str(tmp_path / "Elsewhere" / "x"), str(base)) is None
