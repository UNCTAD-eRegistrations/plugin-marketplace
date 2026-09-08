#!/usr/bin/env python3
"""logic-check: the letters on the canvases against the prose that claims to list them.

A change document draws its logic as letters on the BPA canvases (E = a determinant's effect,
V = a validation, A = an action) and lists it again in prose: the effects table ("The logic,
spelled out"), the bot grid ("The bots"), the counts ("Changes at a glance"). Tonight's lesson
(08-09-2026): the prose drifts from the drawings unless a machine compares them. This check does.

Reads only the drawings of the page (div.canvas and div.ds); ignores nothing else, since a page
holds one copy of everything (criterion C68). Returns the number of faults; 0 is the gate.

usage: python3 logic-check.py change.html
"""
import re, sys, html

def strip(x):
    return html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', x))).strip()

def main(path):
    s = open(path, encoding='utf-8').read()
    faults = []
    # 1. every named determinant on a canvas, and every bot named in a tip or a compkey
    det_on_canvas, bots_named = {}, {}
    for m in re.finditer(r'<div class="canvas" data-form="([^"]*)"(.*?)<!--/canvas-->', s, re.S):
        form, body = m.group(1), m.group(2)
        for b in re.finditer(r'class="bpa-badge ([eva])"[^>]*data-tip="([^"]*)"', body):
            tip = html.unescape(b.group(2))
            n = re.search(r"determinant\b[^']{0,40}'([^']+)'", tip, re.I)
            if b.group(1) == 'e':
                name = n.group(1) if n else None
                if not name:
                    faults.append(f"{form}: an E letter whose note names no determinant in quotes: {tip[:70]}")
                else:
                    det_on_canvas.setdefault(name, set()).add(form)
        for t in re.finditer(r'\b([A-Z][A-Z ]{3,}[A-Z]) (read|list|exists|update|create|update or create)\b[^.·<]*', body):
            bots_named.setdefault(strip(t.group(0))[:60], set()).add(form)
    # 2. the effects table: rows whose text names a determinant in the canvases' words
    table = None
    for m in re.finditer(r'<table[^>]*>(.*?)</table>', s, re.S):
        if '<th>Where</th>' in m.group(1):
            table = m.group(1)
    if table is None:
        faults.append('no effects table with a Where column')
        rows_text = ''
    else:
        rows_text = strip(table)
    for name, forms in sorted(det_on_canvas.items()):
        if name not in rows_text:
            faults.append(f"determinant '{name}' drawn on {', '.join(sorted(forms))} has no row in the effects table")
    # 3. the bot grid: every bot named in the drawings has a row, in bold
    grid = None
    for m in re.finditer(r'<table[^>]*>(.*?)</table>', s, re.S):
        if '<th>Bot</th>' in m.group(1):
            grid = m.group(1)
    grid_names = [strip(x) for x in re.findall(r'<td><b>([^<]+)</b>', grid or '')]
    for bn in sorted(bots_named):
        head = ' '.join(bn.split()[:4])
        if not any(head.split()[0] in g and head.split()[1] in g for g in grid_names):
            faults.append(f"bot named on a canvas has no row in the bot grid: {bn}")
    # 4. the counts
    m = re.search(r'<tr><td><b>Determinants</b></td><td>(\d+)', s)
    if m and int(m.group(1)) != len(det_on_canvas):
        faults.append(f"Changes at a glance says {m.group(1)} determinants, the canvases draw {len(det_on_canvas)} distinct")
    m = re.search(r'<tr><td><b>Bots</b></td><td>(\d+)', s)
    builds = len(re.findall(r'class="todo build">build</span>', grid or ''))
    if m and grid and int(m.group(1)) != builds and int(m.group(1)) != builds + 2:  # a messages row holds three bots
        faults.append(f"Changes at a glance says {m.group(1)} bots to build, the grid holds {builds} build rows (a messages row may hold three)")
    for f in faults:
        print('  ' + f)
    print(f"=== {path}: {len(faults)} to fix\nTOTAL: {len(faults)}")
    return len(faults)

if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)
