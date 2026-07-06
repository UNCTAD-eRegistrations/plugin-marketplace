#!/bin/bash
# Pre-migration identity-reconciliation audit for a CAS -> Keycloak cutover.
#
# The migrator keys EVERYTHING on a single `cas_user_id`: a user's KC login,
# their attributes, roles, and (critically) their institution/unit group
# memberships all join on that one id. That is silently wrong when the same
# human exists under more than one legacy id — the classic case being a PARTC
# officer identity attached to an OLD cas account while the person's live login
# is a NEWER cas account with the same email. The migration carries the login
# (new id) and leaves the officer rights (old id) behind: the user signs in
# fine and sees no Part B desks, with nothing in any log.
#
# This audit surfaces those cases for a human decision BEFORE cutover. It never
# mutates anything (read-only psql). Same "surface, don't auto-fix" philosophy
# as the FK-orphan and username-collision handling elsewhere in this skill.
#
# Anomaly classes reported:
#   A. PARTC officer identity whose email maps to a DIFFERENT cas id than the
#      one PARTC stored  -> rights will land on the wrong (or no) KC user.
#   B. PARTC officer identity whose cas_id has no email/login in CAS at all
#      -> dangling; rights have no KC account to attach to.
#   C. Two CAS logins sharing one email  -> ambiguous identity at migration.
#
# "Officer identity" = a PARTC user carrying at least one institution or unit
# business-role assignment (an applicant-only PARTC user with no rights is not
# interesting — nothing is lost).
#
# Usage:
#   ./reconcile-identities.sh <ssh-host> [cas-db] [partc-db]
# Defaults: cas-db=cas, partc-db=partc (the historical two-DB layout).

set -euo pipefail

if [[ $# -lt 1 || $# -gt 3 ]]; then
    echo "usage: $0 <ssh-host> [cas-db] [partc-db]" >&2
    exit 2
fi
SSH_HOST="$1"
CAS_DB="${2:-cas}"
PARTC_DB="${3:-partc}"

# All queries run as the postgres superuser on the source host; the email
# property id is resolved from each schema's own catalog so the audit is not
# hardcoded to one instance's property numbering.
run_psql() { ssh "$SSH_HOST" "sudo -u postgres psql -d '$1' -tAF'|' -c \"$2\""; }

echo "== Reconciliation audit: $SSH_HOST  (cas=$CAS_DB partc=$PARTC_DB) =="

# CAS: email -> set of cas user ids  (lowercased email)
CAS_EMAILS=$(run_psql "$CAS_DB" "
  SELECT lower(up.value), up.user_id
  FROM cas.user_property up
  WHERE up.property_id = (SELECT id FROM cas.property WHERE name='primary_email')
    AND coalesce(up.value,'') <> ''")

# PARTC: officer identities = partc users with >=1 institution or unit role.
# Emit: partc_user_id | cas_id | email
PARTC_OFFICERS=$(run_psql "$PARTC_DB" "
  SELECT u.id, u.cas_id, lower(up.value)
  FROM partc.\\\"user\\\" u
  JOIN partc.user_property up
    ON up.user_id = u.id
   AND up.property_id = (SELECT id FROM partc.property WHERE name='primary_email')
  WHERE EXISTS (SELECT 1 FROM partc.user_bus_role_institution ri WHERE ri.user_id = u.id)
     OR EXISTS (SELECT 1 FROM partc.user_bus_role_institution_unit ru WHERE ru.user_id = u.id)")

export CAS_EMAILS PARTC_OFFICERS
python3 <<'PY'
import os
cas = {}   # email -> set(cas_user_id)
for line in os.environ["CAS_EMAILS"].splitlines():
    if not line.strip():
        continue
    email, uid = line.split("|", 1)
    cas.setdefault(email, set()).add(uid.strip())

A, B = [], []
for line in os.environ["PARTC_OFFICERS"].splitlines():
    if not line.strip():
        continue
    puid, cas_id, email = (line.split("|") + ["", "", ""])[:3]
    cas_id = cas_id.strip()
    login_ids = cas.get(email, set())
    if not login_ids:
        B.append((puid, cas_id, email))                       # dangling
    elif cas_id not in login_ids:
        A.append((puid, cas_id, email, sorted(login_ids)))     # split id

# Class C: emails under more than one CAS login.
C = {e: sorted(ids) for e, ids in cas.items() if len(ids) > 1}

def hdr(t): print(f"\n--- {t} ---")

hdr(f"A. PARTC officer identity whose email maps to a DIFFERENT cas id ({len(A)})")
if A:
    print("   partc_user | partc.cas_id | email | actual CAS login id(s) by email")
    for puid, cid, em, logins in A:
        print(f"   {puid:>6} | {cid:>6} | {em} | {','.join(logins)}")
    print("   -> officer rights are attached to partc.cas_id but the migration keyed the")
    print("      KC account on the login id. Re-attach the corresponding KC institution/unit")
    print("      groups to the login-id account, or merge, per operator decision.")
else:
    print("   none")

hdr(f"B. PARTC officer identity whose cas_id has no CAS login/email ({len(B)})")
if B:
    print("   partc_user | partc.cas_id | email")
    for puid, cid, em in B:
        print(f"   {puid:>6} | {cid:>6} | {em}")
else:
    print("   none")

hdr(f"C. One email under multiple CAS logins ({len(C)})")
if C:
    for em, ids in C.items():
        print(f"   {em}: cas ids {','.join(ids)}")
else:
    print("   none")

print(f"\n== {len(A)+len(B)+len(C)} identity anomalies for human review before cutover ==")
PY
