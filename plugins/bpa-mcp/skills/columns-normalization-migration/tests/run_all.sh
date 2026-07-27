#!/usr/bin/env bash
set -euo pipefail
# Anchor on this script's own location, not the git root: the skill ships
# inside a plugin and may be run from an installed copy that is not a git
# checkout at all (bare `git rev-parse` would abort the whole gate).
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "== scripts are runnable with bare python3 (no install step) =="
for m in columns_logic columns_split columns_apply columns_split_apply; do
  test -f "$SKILL/scripts/$m.py" || { echo "FAIL: missing $SKILL/scripts/$m.py"; exit 1; }
  python3 -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" \
    "$SKILL/scripts/$m.py" || { echo "FAIL: $m.py does not parse"; exit 1; }
done
echo "scripts present and parseable ✓"
echo "== columns_logic CLI roundtrip (stdin -> JSON plan) =="
echo '{"components":[{"key":"row1","type":"columns","columns":[{"width":4,"components":[]},{"width":4,"components":[]}]}]}' \
  | python3 "$SKILL/scripts/columns_logic.py" >/dev/null
echo "CLI emits a plan and exits 0 ✓"
echo "== pytest (logic + split + apply + split-apply + corpus + skill prose) =="
# Find a python that has pytest installed (python3 alias is login-shell only).
if python3 -m pytest --version >/dev/null 2>&1; then
  PYTEST_PY=python3
elif python3.12 -m pytest --version >/dev/null 2>&1; then
  PYTEST_PY=python3.12
elif python3.11 -m pytest --version >/dev/null 2>&1; then
  PYTEST_PY=python3.11
else
  echo "FAIL: pytest not found on python3 / python3.12 / python3.11"; exit 1
fi
"$PYTEST_PY" -m pytest "$SKILL/tests/" -q
echo "ALL GATES PASSED"
