#!/usr/bin/env python3
"""screen_truth.py — what a BPA container actually puts on the citizen's screen.

Feed it the raw JSON of a container, as returned by
    form_component_get(service_id=..., component_key=..., summary=False)
(the harness saves large responses to a file; pass that file).

It prints the facts a contract drawing needs, and nothing else:
  - every node, whether it renders, and why not
  - every headerComponents array, which no tree walk reports
  - each grid's fieldsShownInGrid and its hide-if-empty
  - each panel's collapsed state and whether its effect opens it
  - the custom classes that change how a thing is drawn

Rule of use: anything absent from this report does not go in the drawing,
and anything in it that the drawing omits is justified in one line.

Born 21-08-2026, after eight fidelity errors in one contract drawing.
"""
import json, sys

DRAW_CLASSES = ("hide-if-empty", "datagrid-hide-column-label", "remove-vertical-lines",
                "deactivated", "hide", "hide-on-edit-mode", "button-status",
                "horizontal-align-center", "horizontal-align-right", "background-blue")

def cls(node):
    c = node.get("customClasses") or []
    if isinstance(c, str): c = [c]
    return [x for x in c if x in DRAW_CLASSES]

def label_of(node):
    for k in ("title", "label"):
        v = node.get(k)
        if v: return str(v)
    return node.get("key") or node.get("type") or "?"

def children(node):
    out = []
    for key in ("components", "columns"):
        v = node.get(key)
        if isinstance(v, list):
            for c in v:
                if isinstance(c, dict):
                    # a column is a wrapper, descend without printing it
                    if c.get("type") == "column":
                        out.extend(children(c))
                    else:
                        out.append(c)
    return out

GRIDS = ("editgrid", "datagrid")

def walk(node, depth, ancestors_off, in_grid=False):
    pad = "  " * depth
    key   = node.get("key") or "(no key)"
    typ   = node.get("type") or "?"
    hidden = node.get("hidden") is True
    eff    = node.get("effectsIds") or node.get("behaviourId")
    off_by_ancestor = ancestors_off

    verdict = "RENDERS"
    why = []
    if off_by_ancestor:
        verdict = "not rendered"; why.append("an ancestor is switched off")
    elif in_grid and hidden:
        verdict = "grid decides"
        why.append("hidden:true inside a grid proves NOTHING: row components carry it and still render. "
                   "The parent grid's fieldsShownInGrid is the authority.")
    elif hidden and not eff:
        verdict = "not rendered"; why.append("hidden:true and no effect to reveal it")
    elif hidden and eff:
        verdict = "renders IF its effect fires"; why.append("hidden:true, revealed by an effect")

    line = f"{pad}{verdict:<26} {typ:<10} {key:<44} {label_of(node)[:58]}"
    print(line)
    if why:
        print(f"{pad}    why: {'; '.join(why)}")

    c = cls(node)
    if c:
        print(f"{pad}    classes that change the drawing: {', '.join(c)}")

    if typ == "panel":
        collapsed = node.get("collapsedDS")
        if collapsed:
            print(f"{pad}    collapsedDS:true  -> renders SHUT unless an effect sets collapsed:false. "
                  f"CHECK the effect's property_effects.")
    if typ in ("editgrid", "datagrid"):
        fs = node.get("fieldsShownInGrid")
        if fs is not None:
            print(f"{pad}    fieldsShownInGrid (the authority on what a row shows): {fs}")
        else:
            print(f"{pad}    no fieldsShownInGrid: every non-hidden child is a column")
        if "hide-if-empty" not in (node.get("customClasses") or []):
            print(f"{pad}    no hide-if-empty: an empty grid still draws its headers")

    hc = node.get("headerComponents")
    if hc:
        print(f"{pad}    HEADER COMPONENTS on this block's title line "
              f"(invisible to every tree walk):")
        for h in hc:
            h_hidden = h.get("hidden") is True
            print(f"{pad}      {'not rendered' if h_hidden else 'RENDERS':<14} "
                  f"{h.get('key')} = {h.get('label')!r} -> target {h.get('targetServiceId')}")

    now_in_grid = in_grid or typ in GRIDS
    child_off = off_by_ancestor or (hidden and not eff and not in_grid and typ not in GRIDS)
    for ch in children(node):
        walk(ch, depth + 1, child_off, now_in_grid)

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    doc = json.load(open(sys.argv[1]))
    raw = doc.get("raw", doc)
    print("=" * 110)
    print("SCREEN TRUTH for", doc.get("component_key") or raw.get("key"))
    print("=" * 110)
    walk(raw, 0, False, False)
    print()
    print("Not answered here, and it must be read separately for every effect above:")
    print("  componentbehaviour_get_by_component -> the determinant AND its property_effects.")
    print("  An effect that sets show/activate but not collapsed:false leaves a panel SHUT.")
    print("  A block that is off is itself a fact: draw it striped and give it its badge.")
    print("  Inside a grid, hidden:true means nothing. Read fieldsShownInGrid.")

if __name__ == "__main__":
    main()
