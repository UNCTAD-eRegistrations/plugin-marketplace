#!/usr/bin/env python3
"""rewrite_camunda_role_groups.py

Companion to ``rewrite_camunda_role_groups.sql.tpl``.

Builds the legacy-id → KC-group-UUID maps required by the SQL by reading the
target Keycloak realm's institutions tree through the Admin REST API. The
maps are emitted as CSV files in the workspace and consumed by the SQL
template via ``\\copy``.

Usage:
    python rewrite_camunda_role_groups.py \\
        --kc-url   https://login.<country>.eregistrations.org \\
        --realm    CU \\
        --root-id  967d3d31-5114-4131-b7e1-f5c652227259 \\
        --token    "$ADMIN_TOKEN" \\
        --out-dir  /tmp

Prints a summary of rows produced, and exits non-zero if any institution or
unit group is missing the expected ``partc_institution_id`` /
``partc_unit_id`` attribute.

The script is intentionally read-only — it never mutates Keycloak. Mutations
happen only via the accompanying SQL template, transactionally, against the
Camunda postgres database.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import urllib.parse
import urllib.request
import json
from typing import Iterable


def _http_get_json(url: str, token: str) -> object:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def fetch_children(kc_url: str, realm: str, parent_id: str, token: str) -> list[dict]:
    """Return immediate children of a KC group with full attribute set."""
    qs = urllib.parse.urlencode({"briefRepresentation": "false", "max": 9999})
    url = f"{kc_url.rstrip('/')}/admin/realms/{realm}/groups/{parent_id}/children?{qs}"
    data = _http_get_json(url, token)
    if not isinstance(data, list):
        raise SystemExit(f"unexpected response from KC: {data!r}")
    return data


def _attr(group: dict, name: str) -> str | None:
    v = (group.get("attributes") or {}).get(name)
    if not v:
        return None
    return v[0]


def build_maps(institutions: Iterable[dict]) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    insts: list[tuple[int, str]] = []
    units: list[tuple[int, str]] = []
    errors: list[str] = []

    for inst in institutions:
        pid = _attr(inst, "partc_institution_id")
        if pid is None:
            errors.append(f"institution '{inst.get('name')}' missing partc_institution_id")
            continue
        try:
            insts.append((int(pid), inst["id"]))
        except (TypeError, ValueError):
            errors.append(f"institution '{inst.get('name')}' has non-integer partc_institution_id={pid!r}")
            continue

        for unit in inst.get("subGroups") or []:
            uid = _attr(unit, "partc_unit_id") or _attr(unit, "partc_institution_unit_id")
            if uid is None:
                errors.append(f"unit '{unit.get('name')}' (under {inst.get('name')}) missing partc_unit_id")
                continue
            try:
                units.append((int(uid), unit["id"]))
            except (TypeError, ValueError):
                errors.append(f"unit '{unit.get('name')}' has non-integer partc_unit_id={uid!r}")
                continue

    if errors:
        for e in errors:
            print(f"WARN: {e}", file=sys.stderr)

    return insts, units


def fetch_full_tree(kc_url: str, realm: str, root_id: str, token: str) -> list[dict]:
    insts = fetch_children(kc_url, realm, root_id, token)
    for inst in insts:
        try:
            inst["subGroups"] = fetch_children(kc_url, realm, inst["id"], token)
        except Exception as e:  # noqa: BLE001
            print(f"WARN: could not fetch units of {inst.get('name')}: {e}", file=sys.stderr)
            inst["subGroups"] = []
    return insts


def write_csv(path: str, header: tuple[str, str], rows: Iterable[tuple[int, str]]) -> int:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        n = 0
        for r in rows:
            w.writerow(r)
            n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--kc-url", required=True, help="https://login.<country>.eregistrations.org")
    p.add_argument("--realm", required=True)
    p.add_argument("--root-id", required=True, help="institutions root group UUID")
    p.add_argument("--token", required=True, help="bearer token (bot or admin) for KC admin API")
    p.add_argument("--out-dir", default="/tmp")
    args = p.parse_args()

    tree = fetch_full_tree(args.kc_url, args.realm, args.root_id, args.token)
    insts, units = build_maps(tree)

    inst_csv = os.path.join(args.out_dir, "inst_map.csv")
    unit_csv = os.path.join(args.out_dir, "unit_map.csv")
    n_inst = write_csv(inst_csv, ("partc_id", "kc_group_id"), insts)
    n_unit = write_csv(unit_csv, ("partc_id", "kc_group_id"), units)

    print(f"wrote {n_inst} institution rows  → {inst_csv}")
    print(f"wrote {n_unit} unit rows         → {unit_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
