#!/bin/bash
# Compare a country's Conf-LIVE compose + haproxy against a known-working
# Keycloak reference (default: kenya). Prints auth-related env-var deltas per
# service and flags haproxy `use_backend` ordering anomalies.
#
# READ-ONLY — never mutates. Run before any cas-to-keycloak cutover.
#
# Usage:
#   ./verify-against-reference.sh <repo-root> <country> [reference-country]
#
# Example:
#   ./verify-against-reference.sh /home/jenkins/eregistrations cuba kenya
#
# What it catches (from LESSONS.md):
#   * `migrate-apps-from-cas-to-keycloak` skill recipe drift — vars the recipe
#     prescribes wrong or omits entirely
#   * Pre-existing haproxy ordering bugs that were always wrong but only
#     surface when other haproxy edits force a config reload (e.g. formio
#     path-rule trapped behind display_system host catch-all)
#
# Limitations:
#   * Compares only env-var presence + non-trivial value drift; doesn't flag
#     domain/realm/secret value changes (those are expected to differ).
#   * Assumes the reference country is currently healthy on Keycloak. If your
#     reference has a bug, this tool inherits it.

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "usage: $0 <repo-root> <country> [reference-country]" >&2
    exit 2
fi

REPO_ROOT="$1"
COUNTRY="$2"
REF="${3:-kenya}"

# Find country compose (compose vs swarm)
find_compose() {
    local country="$1"
    for f in "$REPO_ROOT/Conf-LIVE/compose/$country/docker-stack.yml" \
             "$REPO_ROOT/Conf-LIVE/compose/$country/docker-compose.yml"; do
        [[ -f "$f" ]] && { echo "$f"; return; }
    done
    return 1
}

TARGET_COMPOSE=$(find_compose "$COUNTRY") || { echo "no compose for $COUNTRY" >&2; exit 2; }
REF_COMPOSE=$(find_compose "$REF") || { echo "no compose for reference $REF" >&2; exit 2; }
TARGET_HAPROXY="$REPO_ROOT/Conf-LIVE/haproxy/$COUNTRY/haproxy.cfg"
REF_HAPROXY="$REPO_ROOT/Conf-LIVE/haproxy/$REF/haproxy.cfg"

echo "=== Comparing $COUNTRY against $REF ==="
echo "  target compose : $TARGET_COMPOSE"
echo "  ref compose    : $REF_COMPOSE"
echo "  target haproxy : $TARGET_HAPROXY"
echo "  ref haproxy    : $REF_HAPROXY"
echo

python3 - "$TARGET_COMPOSE" "$REF_COMPOSE" <<'PY'
import re, sys, pathlib

target_file, ref_file = sys.argv[1], sys.argv[2]

def env_for(path, svc):
    text = pathlib.Path(path).read_text()
    m = re.search(rf'^  {re.escape(svc)}:\n(.*?)(?=^  [a-z][a-z0-9_-]*:\n|\Z)', text, re.M | re.S)
    if not m: return None
    block = m.group(1)
    envs = []
    for line in block.splitlines():
        s = line.strip()
        m1 = re.match(r'-\s*"?([A-Z][A-Z0-9_]*)\s*=\s*(.*?)"?$', s)
        if m1: envs.append((m1.group(1), m1.group(2))); continue
        m2 = re.match(r"([A-Z][A-Z0-9_]*)\s*:\s*'?([^']*)'?$", s)
        if m2 and not s.startswith('- '): envs.append((m2.group(1), m2.group(2)))
    return dict(envs)

def auth_filter(d):
    if d is None: return None
    return {k: v for k, v in d.items() if any(p in k for p in ('AUTH_', 'KEYCLOAK', 'OAUTH', 'CAS_', 'PARTC_', 'GDB_CLIENT_AUTH'))}

SERVICES = ['camunda', 'bpa-backend', 'bpa-frontend', 'ds-backend', 'ds-frontend',
            'mule', 'gdb', 'statistics-backend', 'statistics-frontend']

found_any = False
for svc in SERVICES:
    t = auth_filter(env_for(target_file, svc))
    r = auth_filter(env_for(ref_file, svc))
    if t is None and r is None:
        continue
    if t is None:
        print(f"  ⚠  {svc}: present in reference but missing in target")
        found_any = True
        continue
    if r is None:
        # service exists in target but not reference — informational
        continue
    only_ref = sorted(set(r) - set(t))
    if only_ref:
        print(f"\n  ⚠  {svc}: reference has, target lacks → {only_ref}")
        found_any = True

if not found_any:
    print("  No missing env vars per-service.")
PY

echo
echo "=== HAProxy use_backend ordering check ==="
# Flag path-only rules that appear after the host-only display_system catch-all.
python3 - "$TARGET_HAPROXY" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
# Capture use_backend rules in order (line, rule)
rules = []
in_frontend = False
for i, line in enumerate(text.splitlines(), 1):
    if re.match(r'^frontend\s+www-https', line):
        in_frontend = True; continue
    if in_frontend and re.match(r'^(frontend|backend)\b', line):
        break
    m = re.match(r'^\s*use_backend\s+(\S+)\s+if\s+(.*?)$', line)
    if m and in_frontend:
        rules.append((i, m.group(1), m.group(2)))

# Find the line where display_system catch-all appears
ds_idx = next((idx for idx, (_, b, _) in enumerate(rules) if b == 'display_system'), None)
if ds_idx is None:
    print("  (no display_system catch-all — skipping order check)")
else:
    issues = []
    for j in range(ds_idx + 1, len(rules)):
        ln, backend, cond = rules[j]
        # path-based conditions reference ACL names ending in _path or starting with is_*
        # but are host-independent (don't reference is_display_system or hdr(Host))
        if 'is_display_system' in cond: continue
        if 'hdr(Host)' in cond: continue
        if 'is_gdbs' in cond or 'is_stats' in cond or 'is_ds_frontend' in cond: continue
        # likely path-based
        if '_path' in cond or cond.startswith('is_') or 'if is_' in cond:
            issues.append((ln, backend, cond))
    if issues:
        print(f"  ⚠  {len(issues)} path-based rule(s) AFTER the display_system catch-all (likely unreachable):")
        for ln, b, c in issues:
            print(f"    line {ln}: use_backend {b} if {c}")
    else:
        print("  use_backend ordering looks fine.")
PY
