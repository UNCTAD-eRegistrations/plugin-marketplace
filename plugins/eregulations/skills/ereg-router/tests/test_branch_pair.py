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
