#!/usr/bin/env python3
"""Anti-slop check: block the AI verbal tics Frank banned, by machine.

    python3 slop-check.py <file> [<file> ...]     # draft mode: check files
    python3 slop-check.py --hook                  # Stop-hook mode: check the reply

Born 20-08-2026, Frank: "we have anti AI slop rules also, they need to be
applied" — said right after the eR vocabulary check gained its pre-check
discipline. Same architecture: sessions check their DRAFT before sending
(no duplicate reply on Frank's screen), and this hook is the backstop.

Sources of authority (this file holds only the mechanical subset):
- memory feedback_anti_slop_writing.md (banned vocabulary, structures)
- skill ~/.claude/skills/writing-unslop/SKILL.md (hard replacement tables
  EN + FR; the skill stays the judgment pass for long documents)
- memory feedback_glance_format.md (no em dashes in replies)

Scope: EVERY session, every reply (the anti-slop rules apply to all text
output, unlike the eR vocabulary check which is eR-scoped).
Known carve-out: an em dash is allowed on a markdown H1 line (the handover
title exception, memory feedback-em-dash-ban-handover-title-exception).
"""
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

CODE_SPAN = re.compile(r"`[^`]*`|```.*?```", re.S)
MD_LINK_TARGET = re.compile(r"(?<=\]\()[^)\s]*")
# An HTML page is mostly not prose. Style, script and comments carry em dashes
# and banned words as code (a CSS comment, a JS placeholder "—") and flagging
# them teaches sessions to ignore the check. Added 20-08-2026 after two such
# false hits on 2 - eR services/knowledge/choose-what-you-enter.html.
HTML_CODE = re.compile(
    r"<style\b.*?</style>|<script\b.*?</script>|<!--.*?-->", re.S | re.I)
MIN_REPLY_CHARS = 40


def blank(match):
    return "".join("\n" if ch == "\n" else " " for ch in match.group())


def normalize(line):
    """Lowercase, strip accents, fold oe — so one pattern matches all spellings."""
    line = line.replace("œ", "oe").replace("Œ", "OE")
    line = unicodedata.normalize("NFD", line)
    line = "".join(ch for ch in line if not unicodedata.combining(ch))
    return line.lower()


# (pattern, what to do instead). Matched on normalized text, word-bounded.
PHRASES = [
    # -- banned vocabulary EN (memory feedback_anti_slop_writing) --
    (r"\bactually\b", "cut the word"),
    (r"\badditionally\b", "say: also, or cut"),
    (r"\btestament\b", "state the fact directly"),
    (r"\blandscapes?\b", "cut, or say the specific thing"),
    (r"\bshowcas(?:e|es|ed|ing)\b", "say: show"),
    (r"\bdelv(?:e|es|ed|ing)\b", "say: look at"),
    (r"\bunderscor(?:es|ed|ing)\b", "state the point directly"),
    (r"\bvital\b", "say why it matters, or cut"),
    (r"\bcrucial\b", "say why it matters, or cut"),
    (r"\bintricate\b", "say what is complex, or cut"),
    (r"\bleverag(?:e|es|ed|ing)\b", "say: use"),
    (r"\bseamless(?:ly)?\b", "cut"),
    (r"\bgame[- ]changer\b", "be specific, or cut"),
    (r"\bparadigm shifts?\b", "be specific, or cut"),
    (r"\bholistic\b", "say what you mean"),
    (r"\bsynerg(?:y|ies)\b", "say what combines and why"),
    (r"\bunpack\b", "say: break down, explain"),
    (r"\bdeep dive\b", "say what you will examine"),
    (r"\bactionable insights?\b", "say the actual actions"),
    (r"\bever-(?:changing|evolving)\b", "cut, or be specific"),
    (r"\bin an effort to\b", "say: to"),
    (r"\bfoster a culture\b", "be specific"),
    (r"\bnavigat(?:e|ing) the complexit(?:y|ies)\b", "say what is complex"),
    (r"\bmoving forward\b", "cut"),
    (r"\bin conclusion\b", "cut"),
    (r"\bat the end of the day\b", "cut"),
    (r"\b(?:it'?s |it is )?worth noting\b", "just say the thing"),
    (r"\bit bears mentioning\b", "just say it"),
    # -- authority tropes + signposting EN --
    (r"\bat its core\b", "state the point"),
    (r"\bhere'?s the thing\b", "state the point"),
    (r"\bhere'?s what you need to know\b", "start with the content"),
    (r"\blet'?s dive\b", "cut"),
    (r"\blet'?s explore\b", "cut"),
    (r"\blet'?s unpack\b", "cut"),
    # -- sycophancy EN + FR --
    (r"\bgreat question\b", "respond directly"),
    (r"\bexcellent (?:question|point)\b", "respond directly"),
    (r"\byou'?re absolutely right\b", "respond directly"),
    (r"\bexcellente question\b", "respond directly"),
    (r"\btres bonne question\b", "respond directly"),
    (r"\b(?:vous avez|tu as) tout a fait raison\b", "respond directly"),
    # -- negative parallelism + tailing negations --
    (r"\b(?:it'?s|it is|this is|that'?s) not just\b", "state the point positively"),
    (r"\bnot just about\b", "state the point positively"),
    (r"\bce n'est pas (?:juste|seulement)\b", "formuler positivement"),
    (r", no guessing\b", "cut the tail"),
    (r", not a coincidence\b", "cut the tail"),
    # -- hard phrases FR (skill writing-unslop, hard table) --
    (r"\bil convient de noter\b", "dire la chose directement"),
    (r"\bil est important de (?:souligner|noter)\b", "dire la chose directement"),
    (r"\bil est a noter\b", "dire la chose"),
    (r"\bforce est de constater\b", "dire le constat"),
    (r"\bil va sans dire\b", "ne pas le dire"),
    (r"\bdans un monde ou\b", "couper ou etre specifique"),
    (r"\ba l'ere de\b", "couper ou etre specifique"),
    (r"\bdans un contexte ou\b", "couper ou etre specifique"),
    (r"\bn'hesitez pas a\b", "imperatif direct"),
    (r"\bde surcroit\b", "couper"),
    (r"\bqui plus est\b", "couper"),
    (r"\bmettre en lumiere\b", "dire: montrer"),
    (r"\bjou(?:e|ent|er|ant) un role (?:cle|crucial|majeur)\b", "dire ce que ca fait"),
    (r"\bau c(?:oe|œ)ur de\b", "etre specifique"),
    (r"\bs'inscri(?:t|re|vent) dans une demarche\b", "dire ce qu'on fait"),
    (r"\bconstitu(?:e|er|ent) un levier\b", "dire ce que ca permet"),
    (r"\bun enjeu (?:majeur|de taille)\b", "dire quel est l'enjeu"),
    (r"\bincontournable\b", "dire pourquoi c'est important"),
    (r"\ben somme\b", "couper"),
    (r"\ben definitive\b", "couper"),
    (r"\ba cet egard\b", "couper"),
    (r"\bdans cette optique\b", "couper ou etre specifique"),
    (r"\bveritable\b", "couper l'intensifieur"),
    (r"\bbel et bien\b", "couper"),
    (r"\bni plus ni moins\b", "couper"),
    (r"\btout un chacun\b", "dire: chacun"),
    (r"\bse positionn(?:e|er|ent) comme\b", "dire: etre, devenir"),
    (r"\bcre(?:e|er|ent) de la valeur\b", "dire quelle valeur"),
    (r"\bmont(?:e|er|ent) en competences\b", "dire: apprendre, se former"),
    (r"\bl'avenir nous le dira\b", "couper"),
    (r"\bseul le temps nous dira\b", "couper"),
    (r"\ba l'heure ou\b", "couper ou etre specifique"),
    (r"\bil est essentiel de\b", "dire ce qu'il faut faire"),
    (r"\bil apparait clairement\b", "dire la chose"),
    (r"\bon ne peut que constater\b", "constater directement"),
    (r"\bautant d'elements qui\b", "couper, lister les elements"),
    (r"\bun tournant decisif\b", "dire ce qui change"),
    (r"\bplus que jamais\b", "couper"),
    (r"\bqu'il s'agisse de\b", "lister normalement"),
]

# Paragraph openers FR: flagged only at the start of a line (after list marks).
FR_OPENERS = re.compile(
    r"^[^a-z0-9(]*(?:ainsi|des lors|de plus|en outre|par consequent"
    r"|toutefois|neanmoins|en effet|par ailleurs)\s*,")

COMPILED = [(re.compile(p), advice) for p, advice in PHRASES]


def check_text(text, html=False):
    masked = HTML_CODE.sub(blank, text) if html else text
    masked = CODE_SPAN.sub(blank, masked)
    masked = MD_LINK_TARGET.sub(blank, masked)
    hits = []
    for number, raw in enumerate(masked.splitlines(), 1):
        # Em dash: banned everywhere except a markdown H1 (handover title).
        if "—" in raw and not raw.lstrip().startswith("# "):
            hits.append((number, "— (em dash)", "use a comma, a colon or a period"))
        line = normalize(raw)
        # The handover template's own fixed section name is not slop.
        if line.strip() in ("## deep dive", "### deep dive"):
            continue
        for rx, advice in COMPILED:
            for m in rx.finditer(line):
                hits.append((number, m.group(), advice))
        m = FR_OPENERS.match(line)
        if m:
            hits.append((number, m.group().strip(), "couper l'ouverture, dire la chose"))
    return hits


def report(name, hits):
    print(f"\n=== {name}: {len(hits)} slop to fix")
    for number, found, advice in hits:
        print(f"  line {number}: {found!r} -> {advice}")


def hook_mode():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("stop_hook_active"):
        sys.exit(0)
    tp = data.get("transcript_path")
    if not tp or not Path(tp).exists():
        sys.exit(0)
    try:
        lines = Path(tp).read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        sys.exit(0)
    reply = None
    for raw in reversed(lines):
        try:
            e = json.loads(raw)
        except Exception:
            continue
        if e.get("isSidechain"):
            continue
        etype = e.get("type")
        if etype == "assistant":
            blocks = (e.get("message") or {}).get("content") or []
            texts = [b.get("text", "") for b in blocks
                     if isinstance(b, dict) and b.get("type") == "text" and b.get("text")]
            if texts:
                reply = "\n".join(texts)
                break
        elif etype == "user":
            break
    if not reply or len(reply.strip()) < MIN_REPLY_CHARS:
        sys.exit(0)
    hits = check_text(reply)
    if not hits:
        sys.exit(0)

    # REPORT, NEVER REFUSE (Frank's yes, 20-08-2026). A Stop hook fires after
    # the reply is already on his screen, so refusing it can only put a second,
    # near-identical copy underneath. He caught exactly that: two replies
    # differing in one place, where an em dash had been. The findings are
    # parked here and handed to the session at the start of its next turn,
    # before it writes anything, by precheck-feedback.py.
    out = "\n".join(f"  {f!r} -> {a}" for _, f, a in hits[:12])
    more = "" if len(hits) <= 12 else f"\n  ... and {len(hits) - 12} more"
    pending = Path.home() / ".claude" / "hooks" / ".slop-pending"
    try:
        pending.write_text(
            f"[anti-slop] Your PREVIOUS reply carried {len(hits)} banned "
            "pattern(s). Do NOT resend that reply: Frank has already read it. "
            "Keep these out of this reply and of everything you write from "
            "now on.\n" + out + more + "\n", encoding="utf-8")
    except Exception:
        pass
    sys.exit(0)


def wrote_mode():
    """PostToolUse on Write|Edit: check the prose FILE that was just written.

    The reply hook covers what Frank reads in the chat. It does not cover what
    a session writes to disk, and that is where the slop of 19-08-2026 lived:
    a knowledge page headed "Two writers, one truth", never checked by anyone.

    Flags once per (path, content) and then lets it pass: a legitimate quote
    keeps its wording without the hook looping on the same file forever.
    """
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        sys.exit(0)
    p = Path(path)
    if p.suffix.lower() not in (".md", ".html", ".htm", ".txt"):
        sys.exit(0)
    # Machine files and other people's words are not ours to rewrite.
    # tmp and scratchpad hold test fixtures that QUOTE slop on purpose.
    parts = {s.lower() for s in p.parts}
    if parts & {"_archive", "zarchive", "node_modules", "assets", "skills",
                "tmp", "scratchpad"}:
        sys.exit(0)
    # Judge what THIS call wrote, never the file's history. Editing one line of
    # a long legacy document must not report every old em dash in it: that is
    # noise, and noise is how a check loses its authority (proved on CLAUDE.md,
    # 47 pre-existing hits on a two-line edit, 20-08-2026).
    if "content" in ti:                       # Write: the whole new file is ours
        text = ti.get("content") or ""
    elif "edits" in ti:                       # MultiEdit
        text = "\n".join(e.get("new_string", "") for e in ti.get("edits") or [])
    elif "new_string" in ti:                  # Edit
        text = ti.get("new_string") or ""
    elif "new_source" in ti:                  # NotebookEdit
        text = ti.get("new_source") or ""
    else:
        if not p.exists():
            sys.exit(0)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            sys.exit(0)
    if len(text.strip()) < MIN_REPLY_CHARS:
        sys.exit(0)

    hits = check_text(text, html=p.suffix.lower() in (".html", ".htm"))
    if not hits:
        sys.exit(0)

    seen = Path.home() / ".claude" / "hooks" / ".slop-seen"
    # A stable digest: Python's hash() is salted per process, so it would never
    # match on the next run and the guard would never fire.
    digest = hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:16]
    stamp = f"{p.resolve()}|{digest}"
    try:
        already = seen.read_text(encoding="utf-8").splitlines()
    except Exception:
        already = []
    if stamp in already:
        sys.exit(0)
    try:
        seen.write_text("\n".join((already + [stamp])[-200:]), encoding="utf-8")
    except Exception:
        pass

    out = "\n".join(f"  line {n}: {found!r} -> {advice}"
                    for n, found, advice in hits[:25])
    more = "" if len(hits) <= 25 else f"\n  … and {len(hits) - 25} more"
    sys.stderr.write(
        f"The file you just wrote breaks the anti-slop rules "
        f"({len(hits)} hit(s) in {p.name}). These rules apply to every text "
        "we write, not only to replies (memory feedback_anti_slop_writing, "
        "skill writing-unslop). Fix them in the file now, keeping the meaning "
        "unchanged. A phrase inside a verbatim quotation of someone else "
        "stays as it is; rephrase around it.\n\n" + out + more + "\n")
    sys.exit(2)


def main():
    if "--hook" in sys.argv:
        hook_mode()
        return
    if "--wrote" in sys.argv:
        wrote_mode()
        return
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not files:
        sys.exit(__doc__)
    total = 0
    for path in files:
        p = Path(path)
        hits = check_text(p.read_text(encoding="utf-8"),
                          html=p.suffix.lower() in (".html", ".htm"))
        total += len(hits)
        report(p.name, hits)
    print(f"\nTOTAL: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
