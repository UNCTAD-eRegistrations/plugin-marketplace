#!/usr/bin/env python3
"""Vocabulary check: does this text use the house terms.

    python3 check.py <file> [<file> ...] [--quiet]

Reads terms.md beside this script: one row per house term with the substitutes
a session writes when it forgets. Prints every hit with its line, the phrase
found, and what to say instead. Exit 1 when anything is found, so it can gate
a delivery the way the token audit gates a page.

Why it exists: Frank, 03-08-2026, on a document that said "fill a registry
column" for sending data to a GDB table and "text the citizen reads" for a
content field. Words drift like shape drifts, and a check catches what
discipline forgets.
"""
import re
import sys
from pathlib import Path

TERMS = Path(__file__).parent / "terms.md"
CODE_SPAN = re.compile(r"`[^`]*`|```.*?```", re.S)
# A markdown link is a phrase plus an address. Only the phrase is written for a
# human, so the address is masked the way an HTML tag's address already is --
# otherwise every link into services/register-a-business/ reads as drift, and a
# document that cites its evidence is punished for citing it.
MD_LINK_TARGET = re.compile(r"(?<=\]\()[^)\s]*")
# A page is markup around prose. Only the prose is written for a human, so the
# tags, their addresses and their styles are masked the way code spans are --
# otherwise <table>, a /database/ URL and font-weight:400 all read as drift.
HTML_BLOCK = re.compile(r"<(script|style)\b.*?</\1\s*>", re.S | re.I)
HTML_TAG = re.compile(r"<[^>]*>", re.S)
# Except these: a tooltip or an alt text IS prose, and Frank reads it.
KEEP_ATTR = re.compile(
    r'\b(?:data-tip|data-logic|title|alt|aria-label|placeholder)\s*=\s*"([^"]*)"', re.I)
# An element carrying data-vocab="skip" is not written for a human: the for-AI
# technical block of a change document is the case this exists for.
# A rules file must name the words it bans, so a span between these markers is
# not checked. The one legitimate case: the eR rules and this tool's own pages.
MD_SKIP = re.compile(r"<!--\s*vocab:skip\s*-->.*?<!--\s*vocab:endskip\s*-->", re.S | re.I)
SKIP_OPEN = re.compile(r'<(\w+)[^>]*\bdata-vocab\s*=\s*"skip"[^>]*>', re.I)
# A jargon term made only of digits is an HTTP status code, and a status code
# travels with a word saying so. Bare digits are money and share counts.
NUM_CONTEXT = re.compile(
    r"\b(?:https?|error|errors|status|response|responses|code|codes"
    r"|returns|returned|fails|failed|refused)\b", re.I)


def blank(match):
    """Replace a span with spaces, keeping its newlines so line numbers hold."""
    return "".join("\n" if ch == "\n" else " " for ch in match.group())


def blank_skipped(text):
    """Blank every element marked data-vocab="skip", its own nesting included."""
    while True:
        opening = SKIP_OPEN.search(text)
        if not opening:
            return text
        tag = opening.group(1)
        deeper = re.compile(rf"<{tag}\b", re.I)
        closing = re.compile(rf"</{tag}\s*>", re.I)
        depth, at, end = 1, opening.end(), len(text)
        while depth:
            nxt_open, nxt_close = deeper.search(text, at), closing.search(text, at)
            if not nxt_close:
                break
            if nxt_open and nxt_open.start() < nxt_close.start():
                depth, at = depth + 1, nxt_open.end()
            else:
                depth, at = depth - 1, nxt_close.end()
                end = at
        span = text[opening.start():end]
        text = (text[:opening.start()]
                + "".join("\n" if ch == "\n" else " " for ch in span) + text[end:])


def blank_tag(match):
    """Blank a tag, but leave the words of the attributes a human reads."""
    text = match.group()
    out = ["\n" if ch == "\n" else " " for ch in text]
    for attr in KEEP_ATTR.finditer(text):
        out[attr.start(1):attr.end(1)] = text[attr.start(1):attr.end(1)]
    return "".join(out)


def load_terms():
    """The table rows, the allowed-in-context phrases, and the jargon list."""
    rows, jargon, allowed = [], [], []
    section = None
    for line in TERMS.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("## programmer jargon"):
            section = "jargon"
            continue
        if low.startswith("## howto"):
            section = "howto"
            continue
        if low.startswith("## allowed in context"):
            section = "allowed"
            continue
        if stripped.startswith("##"):
            section = None
            continue
        if section == "allowed" and stripped and not stripped.startswith("A banned"):
            allowed.append(stripped)
            continue
        if section == "jargon" and stripped and not low.startswith("allowed"):
            jargon += [w.strip(" .") for w in stripped.split(",") if w.strip(" .")]
            continue
        # Only the first table is the term list. Later sections (how to say it,
        # allowed, jargon) carry tables of their own and must not be read as terms.
        if section is not None or not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2 or set("".join(cells)) <= set("-: ") or cells[0] == "say":
            continue
        substitutes = [s.strip() for s in cells[1].split(",") if s.strip()]
        rows.append((cells[0], substitutes))
    return rows, [j for j in jargon if len(j) > 2], allowed


def pattern_for(phrase):
    """Match the phrase and its plural: 'robot' catches 'robots', 'table'
    catches 'tables'. The blind spot that let 'robots' through a clean run
    on 03-08-2026. Only the last word takes the ending, so 'GDB table'
    still catches 'GDB tables'."""
    words = phrase.lower().split()
    head = r"\s+".join(re.escape(w) for w in words[:-1])
    tail = re.escape(words[-1]) + r"(?:e?s)?"
    return rf"\b{head + r'[ ]+' if head else ''}{tail}\b"


def covered(start, end, spans):
    """A hit sitting inside an allowed phrase is not a hit."""
    return any(s <= start and end <= e for s, e in spans)


def check(path, rows, jargon, allowed):
    text = Path(path).read_text(encoding="utf-8")
    # Identifiers and code are exempt: a key or a command may say anything.
    # Blank each line of the span but keep its newlines: flattening a fenced
    # block swallows them, and every hit after it reports a short line number.
    masked = CODE_SPAN.sub(blank, text)
    masked = MD_LINK_TARGET.sub(blank, masked)
    masked = MD_SKIP.sub(blank, masked)
    if Path(path).suffix.lower() in (".html", ".htm"):
        masked = blank_skipped(masked)
        masked = HTML_BLOCK.sub(blank, masked)
        masked = HTML_TAG.sub(blank_tag, masked)
    hits = []
    for number, line in enumerate(masked.splitlines(), 1):
        low = line.lower()
        spans = [(m.start(), m.end()) for phrase in allowed
                 for m in re.finditer(pattern_for(phrase), low)]
        for say, substitutes in rows:
            for bad in substitutes:
                for m in re.finditer(pattern_for(bad), low):
                    if not covered(m.start(), m.end(), spans):
                        hits.append((number, bad, f"say: {say}"))
        for word in jargon:
            if word.isdigit() and not NUM_CONTEXT.search(low):
                continue
            for m in re.finditer(pattern_for(word), low):
                if not covered(m.start(), m.end(), spans):
                    hits.append((number, word, "programmer jargon, not for a designer"))
    return hits


def main():
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not files:
        sys.exit(__doc__)
    rows, jargon, allowed = load_terms()
    total = 0
    for path in files:
        if Path(path).resolve() == TERMS.resolve():
            print(f"\n=== {Path(path).name}: skipped, it is the term list itself")
            continue
        hits = check(path, rows, jargon, allowed)
        total += len(hits)
        if hits or "--quiet" not in sys.argv:
            print(f"\n=== {Path(path).name}: {len(hits)} to fix")
        for number, found, advice in hits:
            print(f"  line {number}: {found!r} -> {advice}")
    print(f"\nTOTAL: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
