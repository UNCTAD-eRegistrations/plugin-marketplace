#!/usr/bin/env python3
"""phase-coverage: every element of the contract must be built in a named step of the phases.

Seed of the stage-2 check (change build review), written by the page session on 14-09-2026 when Frank
asked whether anyone had reviewed the phases: nobody had, and this check found the panel Recover a
licence built in no step, 26 of 37 determinants named in no phase, two desk formulas missing.
Reads the page only: the bot grid (every <td><b>name</b>), the determinants drawn (the E letters on the
canvases), the formulas counted (Changes at a glance) and a list of role and message words, and says
which are not named inside the Phases band. Returns the number of misses; 0 is the gate.

usage: python3 phase-coverage.py change.html
"""
import re, sys, html
def strip(x): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',x))).strip()
def main(path):
    s=open(path,encoding='utf-8').read()
    def pos(idv):
        m=re.search(r'<div class="bandwrap"[^>]*id="%s"[^>]*>'%idv, s) or re.search(r'<details[^>]*id="%s"[^>]*>'%idv, s); return m.start() if m else None
    a,b=pos('phases'),pos('finaltest')
    if a is None or b is None: print("no phases band"); return 1
    ph=strip(s[a:b]).lower(); miss=[]
    grids=[m.group(1) for m in re.finditer(r'<table[^>]*>(.*?)</table>', s, re.S) if '<th>Bot</th>' in m.group(1)]
    bots=[strip(x) for x in re.findall(r'<td><b>([^<]+)</b>', grids[0])] if grids else []
    miss += [("bot",x) for x in bots if x.lower() not in ph and not x.lower().startswith('nothing to duplicate')]
    dets=set()
    for m in re.finditer(r'<div class="canvas" data-form="([^"]*)"(.*?)<!--/canvas-->', s, re.S):
        for bdg in re.finditer(r'class="bpa-badge e"[^>]*data-tip="([^"]*)"', m.group(2)):
            n=re.search(r"determinant\b[^']{0,40}'([^']+)'", html.unescape(bdg.group(1)), re.I)
            if n: dets.add(n.group(1))
    miss += [("determinant",d) for d in sorted(dets) if d.lower() not in ph]
    frow=re.search(r'<tr><td><b>Formulas</b></td><td>(.*?)</td>', s, re.S)
    forms=[strip(x) for x in re.findall(r'<em>([^<]+)</em>', frow.group(1))] if frow else []
    miss += [("formula",f) for f in forms if f.lower() not in ph]
    for k in ['registration','institution','start role','botrole','translation','publish']:
        if k not in ph: miss.append(("plan word",k))
    for kind,name in miss: print(f"  {kind} built in no named step: {name}")
    print(f"=== {path}: {len(miss)} to fix\nTOTAL: {len(miss)}"); return len(miss)
if __name__=="__main__": sys.exit(1 if main(sys.argv[1]) else 0)
