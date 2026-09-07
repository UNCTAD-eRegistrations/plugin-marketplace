#!/usr/bin/env python3
"""Every label on a screen drawn 'as the person sees it' must exist on its form's
'in BPA, every component' drawing. Two drawings of one form must not drift.

Usage: screen-labels-check.py <change-document.html>
Reads: every <details class="group"> whose direct drawings carry the data-kind
attribute ("ds" on a citizen screen, "canvas" on the BPA drawing). Groups with
no canvas are reported, not failed. Returns 0 when nothing is missing."""
import re, sys, html
from html.parser import HTMLParser

def text(s): return ' '.join(html.unescape(re.sub('<[^>]+>', ' ', s)).split())

def labels(fragment):
    out = set()
    for m in re.finditer(r'class="[^"]*\b(control-label|fieldset-legend|panel-header|fieldset-title)\b[^"]*"[^>]*>(.*?)</(label|div|legend|span)>', fragment, re.S):
        t = text(m.group(2)).rstrip(' *i').strip()
        if t: out.add(t)
    return out

def main(path):
    h = open(path, encoding='utf-8').read()
    groups = [(m.group(1), m.start()) for m in re.finditer(r'<details class="group" id="([^"]+)"', h)]
    groups.append(('END', len(h)))
    missing_total = 0
    for (gid, s), (_, e) in zip(groups, groups[1:]):
        body = h[s:e]
        ds = re.findall(r'<div class="ds"[^>]*data-form="([^"]+)"[^>]*>(.*?)<!--/ds-->', body, re.S)
        canvas = re.findall(r'<div class="canvas"[^>]*data-form="([^"]+)"[^>]*>(.*?)<!--/canvas-->', body, re.S)
        if not ds and not canvas: continue
        cv = {}
        for form, frag in canvas: cv.setdefault(form, set()).update(labels(frag))
        for form, frag in ds:
            if form not in cv:
                print(f"[{gid}] form '{form}': citizen screen(s) but no BPA canvas drawn"); continue
            miss = labels(frag) - cv[form]
            if miss:
                missing_total += len(miss)
                print(f"[{gid}] form '{form}': {len(miss)} label(s) on a citizen screen and not on the canvas: " + ' · '.join(sorted(miss)))
    print(f"TOTAL: {missing_total}")
    return 0 if missing_total == 0 else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
