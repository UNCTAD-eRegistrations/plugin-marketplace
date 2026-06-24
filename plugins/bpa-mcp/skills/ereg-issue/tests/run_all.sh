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
echo "ALL GATES PASSED"
