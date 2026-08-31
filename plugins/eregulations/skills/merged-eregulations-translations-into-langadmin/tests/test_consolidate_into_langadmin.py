"""Tests for the LangAdmin consolidation script.

The script runs against a live, shared translation repository used by real
country instances, so the properties worth pinning are the ones whose failure
is silent and hard to undo: never regress an existing translation, never
overwrite English, and never report a no-op as a successful merge.
"""
import consolidate_into_langadmin as mod


def write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def make_repo(tmp_path):
    """A destination plus two source families, covering every merge branch."""
    d = tmp_path / "repo"
    d.mkdir()
    write(d / "LangAdmin.txt", [
        "id|en|fr|es",
        "btn.save|Save|Save|Guardar",      # fr mirrors en -> untranslated, fillable
        "btn.cancel|Cancel||",             # fr/es blank -> fillable
        "lbl.only.here|Only Here|Seulement ici|",
    ])
    write(d / "Common.txt", [
        "id|en|fr|es",
        "btn.save|Save|Enregistrer|Guardar SRC",   # fr fills; es conflicts
        "btn.cancel|Cancel|Annuler|Cancelar",      # both fill
        "new.key|Brand New|Tout neuf|Nuevo",       # new row
    ])
    write(d / "Users.txt", [
        "id|en|fr|es",
        "new.key|Brand New DIFFERENT|Autre|Otro",  # en differs -> conflict, kept
        "users.only|Users Only|Utilisateurs|",     # new row
    ])
    return d


# --- arity / usage -----------------------------------------------------------

def test_no_arguments_prints_usage_and_returns_2(capsys):
    assert mod.main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_three_arguments_is_not_enough(tmp_path, capsys):
    """Three paths but no source file is a no-op that would still overwrite
    the destination — refused rather than reported as a successful merge."""
    d = make_repo(tmp_path)
    rc = mod.main([str(d), str(tmp_path / "out.txt"), str(tmp_path / "conf.txt")])
    assert rc == 2
    assert "usage:" in capsys.readouterr().err
    assert not (tmp_path / "out.txt").exists()


def test_missing_langadmin_returns_1(tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    rc = mod.main([str(empty), str(tmp_path / "o.txt"), str(tmp_path / "c.txt"), "Common.txt"])
    assert rc == 1
    assert "LangAdmin.txt" in capsys.readouterr().err


def test_missing_source_file_returns_1(tmp_path, capsys):
    d = make_repo(tmp_path)
    rc = mod.main([str(d), str(tmp_path / "o.txt"), str(tmp_path / "c.txt"), "Nope.txt"])
    assert rc == 1
    assert "Nope.txt" in capsys.readouterr().err
    assert not (tmp_path / "o.txt").exists()


# --- the merge rules ---------------------------------------------------------

def test_full_consolidation(tmp_path):
    d = make_repo(tmp_path)
    header, rows, stats, conflicts = mod.consolidate(d, ["Common.txt", "Users.txt"])

    assert header == ["id", "en", "fr", "es"]

    def get(rid, lang):
        return mod.cell(rows[rid], header, lang)

    # a blank cell and an English-mirroring cell are both "untranslated" -> filled
    assert get("btn.save", "fr") == "Enregistrer"
    assert get("btn.cancel", "fr") == "Annuler"
    assert get("btn.cancel", "es") == "Cancelar"

    # an existing real translation is never regressed
    assert get("btn.save", "es") == "Guardar"
    assert get("lbl.only.here", "fr") == "Seulement ici"

    # new keys arrive whole, from the first source file that has them
    assert get("new.key", "fr") == "Tout neuf"
    assert get("users.only", "fr") == "Utilisateurs"

    # English is anchor text: the later file's differing en is logged, not applied
    assert get("new.key", "en") == "Brand New"

    by_file = {s["file"]: s for s in stats}
    assert by_file["Common.txt"]["new_keys"] == 1
    assert by_file["Common.txt"]["filled"] == 3
    assert by_file["Common.txt"]["conflicts"] == 1
    assert by_file["Users.txt"]["new_keys"] == 1
    assert by_file["Users.txt"]["filled"] == 0

    reasons = {c["reason"] for c in conflicts}
    assert "both have differing real translations" in reasons
    assert "english text differs" in reasons
    # every conflict keeps the destination value
    es_conflict = next(c for c in conflicts if c["id"] == "btn.save" and c["lang"] == "es")
    assert es_conflict["dest"] == "Guardar" and es_conflict["src"] == "Guardar SRC"


def test_priority_order_first_file_wins(tmp_path):
    d = make_repo(tmp_path)
    _, rows_a, _, _ = mod.consolidate(d, ["Common.txt", "Users.txt"])
    _, rows_b, _, _ = mod.consolidate(d, ["Users.txt", "Common.txt"])
    header = ["id", "en", "fr", "es"]
    assert mod.cell(rows_a["new.key"], header, "en") == "Brand New"
    assert mod.cell(rows_b["new.key"], header, "en") == "Brand New DIFFERENT"


def test_run_is_idempotent(tmp_path):
    """Re-running against an already-merged destination changes nothing."""
    d = make_repo(tmp_path)
    header, rows, _, _ = mod.consolidate(d, ["Common.txt", "Users.txt"])
    merged = d / "LangAdmin.txt"
    mod.write_langadmin(str(merged), header, rows)
    first = merged.read_bytes()

    header2, rows2, stats2, _ = mod.consolidate(d, ["Common.txt", "Users.txt"])
    mod.write_langadmin(str(merged), header2, rows2)
    assert merged.read_bytes() == first
    assert all(s["filled"] == 0 and s["new_keys"] == 0 for s in stats2)


# --- output side -------------------------------------------------------------

def test_main_writes_both_outputs(tmp_path, capsys):
    d = make_repo(tmp_path)
    out, conf = tmp_path / "merged.txt", tmp_path / "conf.txt"
    rc = mod.main([str(d), str(out), str(conf), "Common.txt", "Users.txt"])
    assert rc == 0

    text = out.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0] == "id|en|fr|es"
    assert len(text.splitlines()) == 6          # header + 5 rows
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")   # BOM preserved

    report = conf.read_text(encoding="utf-8")
    assert "LangAdmin (destination) value was kept in every case." in report

    stdout = capsys.readouterr().out
    assert "TOTAL" in stdout
    assert "Final LangAdmin.txt row count: 5" in stdout


def test_no_conflicts_report_says_so(tmp_path):
    d = tmp_path / "repo"
    d.mkdir()
    write(d / "LangAdmin.txt", ["id|en|fr", "a|A|"])
    write(d / "Common.txt", ["id|en|fr", "a|A|Aa"])
    conf = tmp_path / "c.txt"
    assert mod.main([str(d), str(tmp_path / "o.txt"), str(conf), "Common.txt"]) == 0
    assert conf.read_text(encoding="utf-8") == "No conflicts found.\n"


# --- table parsing edge cases ------------------------------------------------

def test_read_table_pads_short_and_truncates_long_rows(tmp_path):
    p = tmp_path / "t.txt"
    write(p, ["id|en|fr|es", "short|Only", "long|A|B|C|D|E"])
    header, rows = mod.read_table(str(p))
    assert rows["short"] == ["short", "Only", "", ""]
    assert rows["long"] == ["long", "A", "B", "C"]
    assert len(rows["long"]) == len(header)


def test_read_table_skips_repeated_header_and_blank_lines(tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("id|en\n\nid|en\na|A\n", encoding="utf-8-sig")
    _, rows = mod.read_table(str(p))
    assert list(rows) == ["a"]


def test_read_table_on_empty_file(tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("", encoding="utf-8")
    assert mod.read_table(str(p)) == ([], {})


def test_cell_handles_unknown_language(tmp_path):
    assert mod.cell(["a", "A"], ["id", "en"], "zz") == ""
    assert mod.cell(["a"], ["id", "en"], "en") == ""


def test_is_blank_or_english_mirror():
    header = ["id", "en", "fr"]
    assert mod.is_blank_or_english_mirror(["a", "A", ""], header, "fr", "A")
    assert mod.is_blank_or_english_mirror(["a", "A", "   "], header, "fr", "A")
    assert mod.is_blank_or_english_mirror(["a", "A", "A"], header, "fr", "A")
    assert not mod.is_blank_or_english_mirror(["a", "A", "Aa"], header, "fr", "A")


# --- an empty destination is refused, not silently emptied --------------------

def test_empty_langadmin_is_refused_rather_than_discarding_every_translation(tmp_path, capsys):
    """A zero-byte destination has no header, so it names no languages.

    The merge would then write every source row as a bare id with no
    language cells -- every translation silently discarded -- and still
    exit 0 with counts (`new_keys 2`) plausible enough to survive the
    skill's own "sanity-check the counts" step, after which the skill
    copies that file over the live per-country LangAdmin.txt.

    `touch LangAdmin.txt` in a repo with no LangAdmin family yet, then
    running the consolidation expecting it to be populated, is an
    ordinary move. Same reasoning as the zero-source arity check: a
    no-op that would still overwrite the destination is refused.
    """
    d = tmp_path / "repo"
    d.mkdir()
    (d / "LangAdmin.txt").write_text("", encoding="utf-8")
    write(d / "Common.txt", ["id|en|fr", "greeting|Hello|Bonjour", "farewell|Bye|Au revoir"])

    out, conf = tmp_path / "out.txt", tmp_path / "conf.txt"
    rc = mod.main([str(d), str(out), str(conf), "Common.txt"])

    assert rc == 1
    err = capsys.readouterr().err
    assert "LangAdmin.txt" in err
    assert not out.exists()
    assert not conf.exists()


def test_header_only_langadmin_still_merges(tmp_path):
    """A destination that is only a header row is FINE, and must stay so.

    It names its languages, so the merge has everything it needs and every
    source row arrives whole. This is the case the empty-file refusal must
    not swallow.
    """
    d = tmp_path / "repo"
    d.mkdir()
    write(d / "LangAdmin.txt", ["id|en|fr|es"])
    write(d / "Common.txt", ["id|en|fr|es", "greeting|Hello|Bonjour|Hola"])

    out, conf = tmp_path / "out.txt", tmp_path / "conf.txt"
    assert mod.main([str(d), str(out), str(conf), "Common.txt"]) == 0

    lines = out.read_text(encoding="utf-8-sig").splitlines()
    assert lines == ["id|en|fr|es", "greeting|Hello|Bonjour|Hola"]


def test_langadmin_with_no_language_columns_is_refused(tmp_path, capsys):
    """The same data loss, reached by a header that names no languages.

    `read_table` happily returns `["id"]` (or `[""]` for a lone newline)
    as a header, and `langs` is then empty for exactly the same reason it
    is empty for a zero-byte file. Guarding the byte count alone would
    leave this hole open.
    """
    for header_line in ("id", ""):
        d = tmp_path / ("repo" + str(len(header_line)))
        d.mkdir()
        (d / "LangAdmin.txt").write_text(header_line + "\n", encoding="utf-8")
        write(d / "Common.txt", ["id|en|fr", "greeting|Hello|Bonjour"])

        out = tmp_path / ("out%d.txt" % len(header_line))
        rc = mod.main([str(d), str(out), str(tmp_path / "c.txt"), "Common.txt"])
        assert rc == 1, header_line
        assert "LangAdmin.txt" in capsys.readouterr().err
        assert not out.exists()
