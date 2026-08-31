#!/usr/bin/env python3
"""
Consolidate several legacy Multilang family files into LangAdmin.txt, so
that the Admin SPA (hardcoded to read only the LangAdmin family) can reach
translations that already exist under other legacy module names.

Rules:
- LangAdmin.txt is the destination; its existing rows/cells are never
  regressed.
- Source files are processed in a fixed priority order (as given). For a
  key not yet in the accumulated destination, the row is added whole from
  the first source file that has it.
- For a key already present in the destination (from LangAdmin.txt itself,
  or from an earlier source file in this pass): for each language cell, if
  the destination's cell is blank or equal to the destination's own English
  anchor text (i.e. "untranslated"), and the source has a real, distinct
  value, fill it in from source. If the destination already has a real
  value that differs from source's, keep the destination and log a
  conflict for human review.
- English ("en") is treated as anchor text: differences are logged as
  conflicts but the destination's English is always kept (never
  overwritten), to avoid corrupting the SPA's default label text.
"""
import os
import sys
from collections import OrderedDict


def read_table(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        content = f.read()
    lines = content.splitlines()
    if not lines:
        return [], OrderedDict()
    header = lines[0].split("|")
    rows = OrderedDict()
    for line in lines[1:]:
        if line == "":
            continue
        cols = line.split("|")
        rid = cols[0]
        if rid == "id":
            continue
        if len(cols) < len(header):
            cols = cols + [""] * (len(header) - len(cols))
        elif len(cols) > len(header):
            cols = cols[: len(header)]
        rows[rid] = cols
    return header, rows


def cell(row, header, lang):
    if lang not in header:
        return ""
    idx = header.index(lang)
    if idx >= len(row):
        return ""
    return row[idx]


def is_blank_or_english_mirror(row, header, lang, en_value):
    v = cell(row, header, lang)
    if v.strip() == "":
        return True
    if v == en_value:
        return True
    return False


def consolidate(src_dir, source_files):
    """Merge source_files into src_dir/LangAdmin.txt, in the given priority order.

    Returns (langadmin_header, dest_rows, stats, conflicts). Nothing is written
    to disk here — main() owns the output side, so tests can exercise the merge
    rules without touching a live translation repository.

    Raises ValueError if the destination names no languages; see below.
    """
    langadmin_path = os.path.join(src_dir, "LangAdmin.txt")
    langadmin_header, dest_rows = read_table(langadmin_path)
    langs = langadmin_header[1:]

    # The destination's header is what names the languages, so an empty
    # `langs` is not an empty merge — it is a merge that writes every source
    # row as a bare id with no language cells, discarding every translation
    # while still reporting a healthy `new_keys` count. A zero-byte file
    # (`touch LangAdmin.txt`) reaches this, and so does any header that
    # carries no language column, which is the same hole by another door.
    #
    # Same reasoning as main()'s zero-source arity check: a no-op that would
    # still overwrite the destination is refused, not reported as a merge.
    # A header-only LangAdmin.txt is NOT this case — it names its languages,
    # so the merge has everything it needs and every source row arrives whole.
    # `not langs` alone would let a header whose language names are blank
    # through -- `id|` parses to one empty name, which is truthy as a list but
    # names nothing. That header writes every row with an empty cell and loses
    # every translation, exactly as a missing header does. Nothing in this repo
    # emits that shape, but the guard should match what it claims to refuse.
    langs = [lang for lang in langs if lang.strip()]

    if not langs:
        raise ValueError(
            "LangAdmin.txt at %s names no languages (its header row is %s). "
            "Merging into it would write every source row without any "
            "language cells, discarding every translation. Give the "
            "destination a real header row, e.g. 'id|en|fr', and retry."
            % (langadmin_path, "empty" if not langadmin_header else repr("|".join(langadmin_header)))
        )

    stats = []
    conflicts = []

    for fname in source_files:
        path = os.path.join(src_dir, fname)
        src_header, src_rows = read_table(path)
        new_keys = 0
        filled = 0
        conflict_count = 0

        for rid, srow in src_rows.items():
            src_en = cell(srow, src_header, "en")
            if rid not in dest_rows:
                out = [rid]
                for lang in langs:
                    out.append(cell(srow, src_header, lang))
                dest_rows[rid] = out
                new_keys += 1
                continue

            drow = dest_rows[rid]
            dest_en = cell(drow, langadmin_header, "en")
            for lang in langs:
                if lang == "en":
                    s_val = cell(srow, src_header, "en")
                    if s_val.strip() != "" and s_val != dest_en:
                        conflicts.append(dict(file=fname, id=rid, lang=lang,
                                              dest=dest_en, src=s_val,
                                              reason="english text differs"))
                        conflict_count += 1
                    continue
                d_val = cell(drow, langadmin_header, lang)
                s_val = cell(srow, src_header, lang)
                dest_untranslated = is_blank_or_english_mirror(drow, langadmin_header, lang, dest_en)
                src_real = (s_val.strip() != "") and (s_val != src_en)
                if not dest_untranslated:
                    if src_real and s_val != d_val:
                        conflicts.append(dict(file=fname, id=rid, lang=lang,
                                              dest=d_val, src=s_val,
                                              reason="both have differing real translations"))
                        conflict_count += 1
                    # keep destination value, no change
                elif src_real:
                    idx = langadmin_header.index(lang)
                    drow[idx] = s_val
                    filled += 1

        stats.append(dict(file=fname, new_keys=new_keys, filled=filled,
                          conflicts=conflict_count))

    return langadmin_header, dest_rows, stats, conflicts


def write_langadmin(path, header, dest_rows):
    with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
        f.write("|".join(header) + "\n")
        for row in dest_rows.values():
            f.write("|".join(row) + "\n")


def write_conflicts(path, conflicts):
    with open(path, "w", encoding="utf-8") as f:
        if not conflicts:
            f.write("No conflicts found.\n")
        else:
            f.write(f"{len(conflicts)} conflicts found. LangAdmin (destination) value was kept in every case.\n\n")
            for c in conflicts:
                f.write(f"[{c['file']}] id={c['id']} lang={c['lang']} reason={c['reason']}\n")
                f.write(f"    langadmin (kept): {c['dest']!r}\n")
                f.write(f"    source (dropped): {c['src']!r}\n\n")


USAGE = (
    "usage: consolidate_into_langadmin.py <src-dir> <out-langadmin> "
    "<conflicts-report> <source-file> [<source-file> ...]\n"
    "\n"
    "  <src-dir>           directory holding LangAdmin.txt and every source file\n"
    "  <out-langadmin>     path to write the merged LangAdmin.txt to\n"
    "  <conflicts-report>  path to write the human-review conflicts report to\n"
    "  <source-file>       one or more family filenames, in priority order\n"
)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)

    # Arity check: three paths plus at least one source file. Consolidating
    # zero sources is a no-op that would still overwrite the destination, so
    # it is refused rather than reported as a successful merge.
    if len(argv) < 4:
        sys.stderr.write(USAGE)
        return 2

    src_dir, out_langadmin, conflicts_path = argv[0], argv[1], argv[2]
    source_files = argv[3:]

    langadmin_path = os.path.join(src_dir, "LangAdmin.txt")
    if not os.path.isfile(langadmin_path):
        sys.stderr.write("error: no LangAdmin.txt in %s\n" % src_dir)
        return 1
    missing = [f for f in source_files if not os.path.isfile(os.path.join(src_dir, f))]
    if missing:
        sys.stderr.write("error: source file(s) not found in %s: %s\n"
                         % (src_dir, ", ".join(missing)))
        return 1

    try:
        header, dest_rows, stats, conflicts = consolidate(src_dir, source_files)
    except ValueError as exc:
        # Refused before anything is written: neither output file is created,
        # so a destination that cannot be merged into cannot be overwritten
        # by a merge that silently dropped its contents.
        sys.stderr.write("error: %s\n" % exc)
        return 1

    write_langadmin(out_langadmin, header, dest_rows)
    write_conflicts(conflicts_path, conflicts)

    print(f"{'file':30s} {'new_keys':>9s} {'filled':>7s} {'conflicts':>9s}")
    tot_new = tot_filled = tot_conf = 0
    for s in stats:
        print(f"{s['file']:30s} {s['new_keys']:9d} {s['filled']:7d} {s['conflicts']:9d}")
        tot_new += s['new_keys']
        tot_filled += s['filled']
        tot_conf += s['conflicts']
    print(f"{'TOTAL':30s} {tot_new:9d} {tot_filled:7d} {tot_conf:9d}")
    print(f"\nFinal LangAdmin.txt row count: {len(dest_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
