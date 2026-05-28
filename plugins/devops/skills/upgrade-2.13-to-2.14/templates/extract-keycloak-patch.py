"""Generate Keycloak realm-patch artifacts for an upgraded eRegistrations instance.

Reads the starter-conf realm template (authoritative canonical realm shape),
substitutes placeholders from this country's docker-stack.yml, extracts the
three resources that upgraded realms are missing (display-system-frontend
client, eregistrations client scope, declarative user profile), and writes
them + an apply.sh into <OUT_DIR>.

The starter-conf path is NOT baked in — pass it as STARTER_CONF_PATH env var
or first positional arg. The starter template evolves independently; this
script must read the current copy at run-time, not a frozen snapshot.

Usage:
  python3 extract-keycloak-patch.py <stack-file> <out-dir> [<starter-conf-path>]

env:
  STARTER_CONF_PATH  fallback if positional 3 not given

The script:
  - Parses docker-stack.yml to learn the realm name (KEYCLOAK_REALM=...) and
    primary domain (KC_HOSTNAME=login.<domain>).
  - Substitutes placeholders in the starter realm template.
  - Generates fresh uuid.uuid4() per confidential-client secret.
  - strip_ids() recursively on the extracted client-scope so Keycloak
    generates fresh entity IDs on POST.
  - Writes partial-import.json, client-scope.json, user-profile.json,
    apply.sh (the latter copied from apply.sh.tpl in the same templates/ dir).
  - Prints generated UUIDs to stdout so the operator can mirror them into .env.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import stat
import sys
import uuid
from pathlib import Path

# ---------- argument parsing -----------------------------------------------

if len(sys.argv) < 3:
    sys.exit(f"usage: {sys.argv[0]} <stack-file> <out-dir> [<starter-conf-path>]")

STACK = Path(sys.argv[1])
OUT = Path(sys.argv[2])
STARTER = Path(sys.argv[3] if len(sys.argv) >= 4 else os.environ.get("STARTER_CONF_PATH", ""))

if not STACK.is_file():
    sys.exit(f"stack file not found: {STACK}")
if not STARTER.is_dir():
    sys.exit(f"starter-conf path not a directory: {STARTER}")
TEMPLATE = STARTER / "scripts" / "keycloak-realm.template.json"
if not TEMPLATE.is_file():
    sys.exit(f"realm template not at {TEMPLATE}")

OUT.mkdir(parents=True, exist_ok=True)

# ---------- read stack -----------------------------------------------------

stack_text = STACK.read_text()


def extract_env(var: str) -> str | None:
    """Find an env-list item like `- "VAR=value"` or `- VAR=value` and return value."""
    m = re.search(rf'-\s*"?{re.escape(var)}=([^"\n]+?)"?\s*$', stack_text, flags=re.MULTILINE)
    return m.group(1) if m else None


REALM = extract_env("KEYCLOAK_REALM") or extract_env("AUTH_SERVICE_REALM") or extract_env("SYSTEM_CODE")
if not REALM:
    sys.exit("could not find KEYCLOAK_REALM / SYSTEM_CODE in stack file")

m = re.search(r"KC_HOSTNAME=login\.([^\s\"]+)", stack_text)
if not m:
    sys.exit("could not find KC_HOSTNAME=login.<domain> on keycloak service")
DOMAIN = m.group(1)


# Canonical client IDs — these may be overridden by what's actually in the
# docker-stack.yml if a non-canonical name was used (rare).
def env_or_default(stack_var: str, default: str) -> str:
    return extract_env(stack_var) or default


CLIENT_IDS = {
    "BPA_BE_OAUTH_CLIENT_ID_PLACEHOLDER": env_or_default("KEYCLOAK_RESOURCE", "bpa-backend"),  # bpa-backend block
    "BPA_FE_OAUTH_CLIENT_ID_PLACEHOLDER": env_or_default("OAUTH_CLIENT_ID", "bpa-frontend"),  # bpa-frontend
    "CAMUNDA_OAUTH_CLIENT_ID_PLACEHOLDER": "camunda-client",
    "DS_OAUTH_CLIENT_ID_PLACEHOLDER": "ds-client",
    "DS_FE_OAUTH_CLIENT_ID_PLACEHOLDER": "display-system-frontend",
    "GDB_OAUTH_CLIENT_ID_PLACEHOLDER": "gdb-client",
    "STATISTICS_BE_OAUTH_CLIENT_ID_PLACEHOLDER": "statistics-backend",
    "STATISTICS_FE_OAUTH_CLIENT_ID_PLACEHOLDER": "statistics-frontend",
}

UUIDS = {k: str(uuid.uuid4()) for k in [
    "BPA_BE_OAUTH_CLIENT_SECRET",
    "CAMUNDA_OAUTH_CLIENT_SECRET",
    "DS_OAUTH_CLIENT_SECRET",
    "GDB_OAUTH_CLIENT_SECRET",
    "STATISTICS_BE_OAUTH_CLIENT_SECRET",
]}

SUBS = {
    "REALM_LOWERCASE_PLACEHOLDER": REALM.lower(),
    "REALM_PLACEHOLDER": REALM,
    "YOUR_DOMAIN_NAME_PLACEHOLDER": DOMAIN,
    "MAIL_HOST_PLACEHOLDER": "email-smtp.us-east-1.amazonaws.com",
    "MAIL_PORT_PLACEHOLDER": "587",
    "MAIL_FROM_PLACEHOLDER": "noreply@eregistrations.org",
    "MAIL_REPLY_TO_PLACEHOLDER": "noreply@eregistrations.org",
    "MAIL_USERNAME_PLACEHOLDER": "DUMMY_SMTP_USER",
    "MAIL_PASSWORD_PLACEHOLDER": "dummy-smtp-password",
    **CLIENT_IDS,
    **{f"{k}_PLACEHOLDER": v for k, v in UUIDS.items()},
}

# ---------- substitute + parse ---------------------------------------------

template_text = TEMPLATE.read_text()
for key in sorted(SUBS, key=len, reverse=True):
    template_text = template_text.replace(key, SUBS[key])

remaining = re.findall(r"[A-Z_]+_PLACEHOLDER", template_text)
if remaining:
    sys.exit(f"unresolved placeholders: {sorted(set(remaining))}")

realm = json.loads(template_text)  # also validates JSON

# ---------- extract --------------------------------------------------------


def strip_ids(obj):
    if isinstance(obj, dict):
        obj.pop("id", None)
        for v in obj.values():
            strip_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            strip_ids(v)
    return obj


ds_fe = next((c for c in realm["clients"] if c["clientId"] == CLIENT_IDS["DS_FE_OAUTH_CLIENT_ID_PLACEHOLDER"]), None)
if not ds_fe:
    sys.exit(f"client {CLIENT_IDS['DS_FE_OAUTH_CLIENT_ID_PLACEHOLDER']!r} not in template")

ereg_scope = next((s for s in realm["clientScopes"] if s["name"] == "eregistrations"), None)
if not ereg_scope:
    sys.exit("eregistrations client scope not in template")
ereg_scope_clean = strip_ids(copy.deepcopy(ereg_scope))

up = next(
    (e for e in realm.get("components", {}).get("org.keycloak.userprofile.UserProfileProvider", [])
     if e.get("providerId") == "declarative-user-profile"),
    None,
)
if not up:
    sys.exit("declarative-user-profile component not in template")
up_config = json.loads(up["config"]["kc.user.profile.config"][0])

# ---------- write ----------------------------------------------------------

(OUT / "partial-import.json").write_text(
    json.dumps({"ifResourceExists": "SKIP", "clients": [ds_fe]}, indent=2)
)
(OUT / "client-scope.json").write_text(json.dumps(ereg_scope_clean, indent=2))
(OUT / "user-profile.json").write_text(json.dumps(up_config, indent=2))

apply_tpl = Path(__file__).parent / "apply.sh.tpl"
if not apply_tpl.is_file():
    sys.exit(f"apply.sh template missing: {apply_tpl}")
apply_dst = OUT / "apply.sh"
shutil.copy(apply_tpl, apply_dst)
apply_dst.chmod(apply_dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

# ---------- report ---------------------------------------------------------

print(f"wrote {OUT}/ ({len(list(OUT.iterdir()))} files)")
print(f"  realm: {REALM}  (lowercase: {REALM.lower()})")
print(f"  domain: {DOMAIN}")
print()
print("Generated client secrets — mirror into .env so init-swarm.sh seeds them:")
for k, v in UUIDS.items():
    print(f"  {k}={v}")
print()
print("Next:")
print(f"  cd {OUT}")
print(f"  KC_URL=https://login.{DOMAIN} KC_REALM={REALM} \\")
print(f"    KC_ADMIN_USER=<master-admin> KC_ADMIN_PASS=<master-admin-pass> \\")
print(f"    ./apply.sh")
