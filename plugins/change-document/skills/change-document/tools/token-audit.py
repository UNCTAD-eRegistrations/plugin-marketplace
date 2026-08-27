#!/usr/bin/env python3
"""Token audit: every font-size / margin / padding / gap / line-height /
letter-spacing / max-width value (CSS + inline styles) must trace to a token.
Elements carrying data-specimen (quoted sick values) are exempt.
SVG presentation attributes are drawing geometry (viewBox units) and are
audited separately: text font-size attrs must be 16 (caption) or the wound."""
import re, sys

AUDITED = r'(?:font-size|margin(?:-[a-z]+)?|padding(?:-[a-z]+)?|gap|row-gap|column-gap|line-height|letter-spacing|max-width)'
ALLOWED_PARTS = {'0','auto','none','inherit','1em','100%',
                 '.5em','0.5em',      # glyph constant: chevron/dot = x-height
                 '.06em','0.06em',    # label tracking constant
                 '16px',              # SVG caption constant (natural width)
                 '112.5%'}            # reading-document root base (18px): prose set for pleasure
SVG_TEXT_SIZES = {'16','16.5','120','96'}  # caption / wound glyph (viewBox units)

def check_value(val):
    v = val.strip()
    if 'calc(' in v:
        # calc passes when every length inside it comes from a token (no raw px/rem/ch/em)
        stripped = re.sub(r'var\(--[a-zA-Z0-9-]+\)', '', v)
        return [] if not re.search(r'\d*\.?\d+(px|rem|ch|em)', stripped) else [v]
    bad = []
    for part in v.split():
        p = part.strip().rstrip(';').lower()
        if p.startswith('var(--') or p in ALLOWED_PARTS:
            continue
        bad.append(part)
    return bad

def audit(path):
    html = open(path, encoding='utf-8').read()
    violations = []
    # 1 · <style> block
    m = re.search(r'<style>(.*?)</style>', html, re.S)
    if m:
        css = re.sub(r'@media[^{]*', '@media ', m.group(1))       # drop media conditions
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)           # drop comments
        for sel_body in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
            sel, body = sel_body.group(1).strip(), sel_body.group(2)
            for d in re.finditer(r'(?:^|;)\s*(' + AUDITED + r')\s*:\s*([^;}{]+)', body):
                prop, val = d.group(1), d.group(2)
                bad = check_value(val)
                if bad:
                    violations.append((path.split('/')[-1], 'css', f'{sel} {{ {prop}: {val.strip()} }}', bad))
    # 2 · inline styles (skip data-specimen)
    for tag in re.finditer(r'<[a-z][^>]*style="([^"]*)"[^>]*>', html):
        if 'data-specimen' in tag.group(0):
            continue
        for d in re.finditer(r'(?:^|;)\s*(' + AUDITED + r')\s*:\s*([^;"]+)', tag.group(1)):
            prop, val = d.group(1), d.group(2)
            bad = check_value(val)
            if bad:
                violations.append((path.split('/')[-1], 'inline', f'{tag.group(0)[:90]}', bad))
    # 3 · SVG text font-size attributes
    for t in re.finditer(r'<text[^>]*font-size="([^"]+)"[^>]*>', html):
        if t.group(1) not in SVG_TEXT_SIZES:
            violations.append((path.split('/')[-1], 'svg', t.group(0)[:90], [t.group(1)]))
    return violations

if __name__ == '__main__':
    total = 0
    for path in sys.argv[1:]:
        vs = audit(path)
        print(f'\n=== {path.split("/")[-1]}: {len(vs)} violation(s)')
        for v in vs:
            print('  [%s] %s -> %s' % (v[1], v[2], v[3]))
        total += len(vs)
    print(f'\nTOTAL: {total}')
