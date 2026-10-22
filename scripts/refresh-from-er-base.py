#!/usr/bin/env python3
"""Refresh the plugin copies of the eR templates from their source, before a plugin release.

Since 23-10-2026 the source of these models and method files is the eR knowledge base
(`2 - eR services/templates/` in the maintainers' workspace, private repository
UNCTAD-eRegistrations/er-knowledge). Each plugin below keeps a copy, so a user who installs
the plugin from this marketplace never needs the base. Run this before bumping the version
of change-document or leaflets:

    python3 scripts/refresh-from-er-base.py            # copy what changed, list it
    python3 scripts/refresh-from-er-base.py --check    # exit 1 if a plugin copy differs
    python3 scripts/refresh-from-er-base.py --base "<path to 2 - eR services>"

The base is found with --base, else $ER_BASE, else ../2 - eR services beside this repository.
Only the files listed in COPIES travel; the base's notes stay in the base.
"""
import filecmp
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CD = 'plugins/change-document/skills/change-document'
LF = 'plugins/leaflets/skills'
T = 'templates'
BRIEFS = ['README.md', 'stage-1-adversarial-read-of-the-document.md', 'stage-2-adversarial-read-of-the-plan.md',
          'stage-2-builders-pass-devices-and-impact.md', 'closure-pass-both-stages.md',
          'method-report-from-the-reviewers.md']
LEAFLET = ['document-template.html', 'poster-template.html', 'comparison-template.html', 'brand.css',
           'avatar-default.webp', 'guide-config.example.json']

# (file in the base, its copy in this repository)
COPIES = [
    (f'{T}/design-and-change/criteria.md', f'{CD}/knowledge/criteria-change-document.md'),
    (f'{T}/design-and-change/criteria.html', f'{CD}/knowledge/criteria-change-document.html'),
    (f'{T}/design-and-change/review-method.md', f'{CD}/knowledge/readiness/methodology.md'),
    (f'{T}/design-and-change/review-method.html', f'{CD}/knowledge/readiness/methodology.html'),
    (f'{T}/design-and-change/model/bpa-mockup-rendering.md', f'{CD}/knowledge/bpa-mockup-rendering.md'),
    (f'{T}/design-and-change/model/bpa-mockup-kit.css', f'{CD}/tools/bpa-mockup-kit.css'),
    (f'{T}/design-and-change/model/ds-mockup-kit.css', f'{CD}/tools/ds-mockup-kit.css'),
] + [(f'{T}/design-and-change/model/review-briefs/{b}', f'{CD}/knowledge/readiness/briefs/{b}') for b in BRIEFS] + [
    (f'{T}/leaflet/model/{a}', f'{LF}/service-leaflet/assets/{a}') for a in LEAFLET] + [
    (f'{T}/leaflet/model/content-map-template.md', f'{LF}/service-concept-brief/assets/content-map-template.md'),
    (f'{T}/leaflet/model/journey-map-template.md', f'{LF}/service-journey-brief/assets/journey-map-template.md'),
]


def base_path(argv):
    if '--base' in argv:
        return argv[argv.index('--base') + 1]
    if os.environ.get('ER_BASE'):
        return os.environ['ER_BASE']
    return os.path.join(os.path.dirname(REPO), '2 - eR services')


def main(argv):
    base = base_path(argv)
    check = '--check' in argv
    if not os.path.isdir(os.path.join(base, T)):
        sys.exit(f'eR base not found at {base!r}: pass --base or set ER_BASE. Nothing refreshed.')
    changed, missing = [], []
    for src, dst in COPIES:
        s, d = os.path.join(base, src), os.path.join(REPO, dst)
        if not os.path.exists(s):
            missing.append(src)
            continue
        if os.path.exists(d) and filecmp.cmp(s, d, shallow=False):
            continue
        changed.append(dst)
        if not check:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
    for m in missing:
        print(f'missing in the base: {m}')
    for c in changed:
        print(('differs: ' if check else 'refreshed: ') + c)
    print(f'{len(COPIES)} files checked, {len(changed)} {"differ" if check else "refreshed"}, {len(missing)} missing.')
    if missing or (check and changed):
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
