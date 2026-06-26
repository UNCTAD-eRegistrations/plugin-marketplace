#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
echo "== plugin frontmatter (no NEW errors in bpa-mcp) =="
# validate-plugins.py exits non-zero on ~10 pre-existing errors in OTHER plugins;
# that is the clean baseline. We only fail on errors mentioning our plugin.
if python3 scripts/validate-plugins.py 2>&1 | grep -E "bpa-mcp|ereg-issue"; then
  echo "FAIL: new frontmatter errors in bpa-mcp/ereg-issue"; exit 1
fi
echo "no new errors in bpa-mcp ✓"
echo "(note: CI runs .github/scripts/validate-frontmatter.ts via bun; not runnable locally)"
echo "== ticket conformance =="
python3 plugins/bpa-mcp/skills/ereg-issue/tests/validate_ticket.py \
  plugins/bpa-mcp/skills/ereg-issue/samples/qualified-ticket.example.json
echo "== routing table coverage =="
python3 plugins/bpa-mcp/skills/ereg-issue/tests/test_routing_table.py
echo "== pytest (routing + autopilot conformance) =="
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
"$PYTEST_PY" -m pytest plugins/bpa-mcp/skills/ereg-issue/tests/ -q
echo "ALL GATES PASSED"
