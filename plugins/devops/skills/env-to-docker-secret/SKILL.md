---
name: env-to-docker-secret
description: >
  Generate `env-to-secrets.sh`, a self-contained converter that reads a `.env`
  file (`KEY=VALUE` lines) and emits a `.secrets` file containing one
  `printf '%s' 'VALUE' | docker secret create KEY -` line per entry. Skips
  comments and blank lines, strips surrounding single/double quotes from values
  (standard `.env` convention), and escapes embedded single quotes so the
  resulting `printf '...'` blocks are safe to feed back into bash. Supports
  dry-run (preview to stdout, no file written), custom input/output paths, and
  filter/exclude patterns. Use when standing up a Docker Swarm stack from an
  existing `.env` and you need every variable mirrored as a Docker secret
  without hand-typing the commands.
license: UNCTAD-Internal
compatibility: >
  Requires bash 4+ on the deployment host (for the generated script). The skill
  itself runs anywhere — generation needs no `.env` access; the converter
  validates input at run time on the host where Docker is reachable.
allowed-tools: Read, Write, Edit, Glob, Bash(test *), Bash(ls *), Bash(chmod +x *), AskUserQuestion
metadata:
  version: "1.0.0"
  version-date: "2026-05-05"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "[output-directory]"
---

You are an expert eRegistrations DevOps engineer. Your task is to drop a self-contained `env-to-secrets.sh` converter into the operator's chosen directory. The converter, when run on a deployment host, transforms a `.env` file into a `.secrets` file of `docker secret create` commands.

## Why this skill exists

Standing up a Docker Swarm stack often requires every value in a `.env` to exist as a Docker secret. Hand-converting `KEY=VALUE` to `printf '%s' 'VALUE' | docker secret create KEY -` for dozens of variables is tedious and error-prone — values containing single quotes, `%` characters, or surrounding quotes are easy to mis-escape. This skill emits one well-tested converter once; the operator runs it against every `.env` they need to seed.

## Core capabilities

1. Generate `env-to-secrets.sh` — a single bash file with no external dependencies beyond `bash 4+`
2. The converter parses `KEY=VALUE` lines, skipping `#` comments and blank lines
3. Strips matching surrounding single or double quotes from values (`KEY="value"` → `value`)
4. Escapes embedded single quotes so the emitted `printf '%s' '...'` block is shell-safe
5. Uses `printf '%s' 'VALUE'` (not `echo`, not `printf 'VALUE'`) so `%` and trailing newlines stay literal — the secret content is exactly the bytes between the quotes
6. Modes: write to `.secrets` (default), `--dry-run` to stdout, `--apply` to pipe directly into Docker
7. Filter / exclude by glob patterns when only a subset of `.env` should become secrets

## Out of scope

- Reading existing Docker secrets, rotating them, or comparing against `.env`
- Creating Docker networks, volumes, or stacks (use `docker stack deploy`)
- Bootstrapping the Swarm itself (`docker swarm init`)
- Mapping secret names → service `secrets:` blocks (that lives in `docker-stack.yml`)
- Multi-line values (eRegistrations `.env` values are single-line by convention)

## Workflow

### Phase 1: Input gathering

If `$ARGUMENTS[0]` is provided, treat it as the target directory. Otherwise default to the current working directory. Skip Question 1 when an arg is supplied.

**Question 1 — Output directory** (only when no arg):
```
question: "Where should env-to-secrets.sh be written?"
options:
  - label: "Current directory (Recommended)"
    description: "Write env-to-secrets.sh in $PWD"
  - label: "Custom path"
    description: "Specify a different directory"
default: "Current directory"
```

If the directory does not exist, abort with `mkdir -p <dir>` guidance — never auto-create.

### Phase 2: Generation

Use **Write** to emit `env-to-secrets.sh` from the template in *Generated script* (verbatim — no substitutions needed; the script is fully self-contained).

Then `chmod +x env-to-secrets.sh`.

### Phase 3: Validation

1. **Smoke test** — confirm the file exists and is executable:
   ```bash
   test -x env-to-secrets.sh
   ```

2. **Round-trip** — run `./env-to-secrets.sh --help` and confirm exit 0.

3. **Final summary**:
   ```
   === env-to-secrets converter ready ===

   Output:   <relative path>/env-to-secrets.sh

   Usage on the deployment host (where .env lives):
     ./env-to-secrets.sh                    # write .env → .secrets
     ./env-to-secrets.sh -n                 # dry-run, print to stdout
     ./env-to-secrets.sh -i custom.env      # custom input
     ./env-to-secrets.sh -o custom.secrets  # custom output
     ./env-to-secrets.sh --apply            # pipe straight to docker
     ./env-to-secrets.sh --include 'POSTGRES_*' --exclude '*_TEST'

   The .secrets file is itself a runnable bash script:
     bash .secrets
   ```

## Generated script

```bash
#!/usr/bin/env bash
# Convert a .env file into a .secrets file of docker secret create commands.
# Generated by /env-to-docker-secret
#
# Usage:
#   ./env-to-secrets.sh [OPTIONS]
#
# Options:
#   -i, --input FILE      Input .env file (default: .env)
#   -o, --output FILE     Output .secrets file (default: .secrets)
#   -n, --dry-run         Print to stdout, do not write a file
#       --apply           Pipe the generated commands directly to bash
#                         (creates the secrets in Docker right now)
#       --include GLOB    Only emit keys matching this glob (repeatable)
#       --exclude GLOB    Skip keys matching this glob (repeatable)
#   -h, --help            Show this help

set -eu
set -o pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

INPUT=".env"
OUTPUT=".secrets"
MODE="write"          # write | dry-run | apply
INCLUDES=()
EXCLUDES=()

show_help() {
    sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)   INPUT="${2:?--input requires an argument}"; shift 2 ;;
        -o|--output)  OUTPUT="${2:?--output requires an argument}"; shift 2 ;;
        -n|--dry-run) MODE="dry-run"; shift ;;
        --apply)      MODE="apply"; shift ;;
        --include)    INCLUDES+=("${2:?--include requires a glob}"); shift 2 ;;
        --exclude)    EXCLUDES+=("${2:?--exclude requires a glob}"); shift 2 ;;
        -h|--help)    show_help; exit 0 ;;
        -*) echo -e "${RED}Unknown option: $1${NC}" >&2; exit 1 ;;
        *)  echo -e "${RED}Unexpected positional arg: $1${NC}" >&2; exit 1 ;;
    esac
done

if [ ! -f "$INPUT" ]; then
    echo -e "${RED}Error: input file not found: $INPUT${NC}" >&2
    exit 1
fi

# Match KEY against include/exclude globs.
# Returns 0 (emit) or 1 (skip).
should_emit() {
    local key="$1" pat
    for pat in "${EXCLUDES[@]}"; do
        # shellcheck disable=SC2053
        [[ "$key" == $pat ]] && return 1
    done
    if [ "${#INCLUDES[@]}" -eq 0 ]; then
        return 0
    fi
    for pat in "${INCLUDES[@]}"; do
        # shellcheck disable=SC2053
        [[ "$key" == $pat ]] && return 0
    done
    return 1
}

emit() {
    local line key val esc lineno=0 emitted=0
    while IFS= read -r line || [ -n "$line" ]; do
        lineno=$((lineno + 1))
        # strip trailing CR (CRLF tolerance)
        line="${line%$'\r'}"
        # skip blank lines
        [[ -z "${line//[[:space:]]/}" ]] && continue
        # skip comments (leading whitespace + #)
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        # tolerate optional `export ` prefix
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line#export }"
        # parse KEY=VALUE
        if [[ ! "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            echo -e "${RED}Skipping malformed line $lineno: $line${NC}" >&2
            continue
        fi
        key="${BASH_REMATCH[1]}"
        val="${BASH_REMATCH[2]}"
        # strip matching surrounding quotes (single or double)
        if [[ "$val" =~ ^\"(.*)\"$ ]]; then
            val="${BASH_REMATCH[1]}"
        elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
            val="${BASH_REMATCH[1]}"
        fi
        # filter
        should_emit "$key" || continue
        # escape ' for single-quoted printf: '  →  '\''
        esc="${val//\'/\'\\\'\'}"
        printf "printf '%%s' '%s' | docker secret create %s -\n" "$esc" "$key"
        emitted=$((emitted + 1))
    done < "$INPUT"
    if [ "$emitted" = "0" ]; then
        echo -e "${RED}Warning: no entries matched (filters too narrow?)${NC}" >&2
    fi
}

case "$MODE" in
    dry-run)
        emit
        ;;
    write)
        out_dir="$(dirname "$OUTPUT")"
        tmp="$(mktemp "${out_dir}/.env-to-secrets.XXXXXX")"
        trap 'rm -f "$tmp"' EXIT
        {
            printf '#!/usr/bin/env bash\n'
            printf '# Generated from %s on %s\n' \
                "$INPUT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
            printf 'set -eu\n\n'
            emit
        } > "$tmp"
        chmod 600 "$tmp"
        mv "$tmp" "$OUTPUT"
        trap - EXIT
        echo -e "${GREEN}Wrote ${OUTPUT}${NC}"
        echo -e "${CYAN}Run:${NC} bash ${OUTPUT}"
        ;;
    apply)
        echo -e "${CYAN}Applying to Docker...${NC}"
        emit | bash
        echo -e "${GREEN}[OK] done${NC}"
        ;;
esac
```

## Encoding rules

| Slot | Form | Meaning |
|---|---|---|
| KEY | `[A-Za-z_][A-Za-z0-9_]*` | POSIX env var identifier; anything else is rejected. |
| VALUE | bare | Used as-is. |
| VALUE | `"…"` | Surrounding double quotes stripped (one pair). |
| VALUE | `'…'` | Surrounding single quotes stripped (one pair). |
| VALUE | contains `'` | Escaped to `'\''` inside the emitted single-quoted block. |

**Why `printf '%s' 'VALUE'` and not `printf 'VALUE'`** — the `%s` form is immune to `%` characters in the value (otherwise `%n` would crash, `%s` would consume more args, etc.). This is the standard safe idiom; the user-visible behavior is identical for normal values.

**Why no trailing newline** — `docker secret create` reads stdin verbatim. A trailing `\n` from `echo` would become part of the secret. `printf '%s' …` emits exactly the bytes between the quotes — nothing more.

## Examples

### Example 1 — basic conversion

`.env`:
```
# eRegistrations
POSTGRES_USER=bpa
POSTGRES_PASSWORD=s3cret
SERVICE_HOST=10.0.0.5
EMPTY_VAR=
```

`./env-to-secrets.sh -n`:
```
printf '%s' 'bpa' | docker secret create POSTGRES_USER -
printf '%s' 's3cret' | docker secret create POSTGRES_PASSWORD -
printf '%s' '10.0.0.5' | docker secret create SERVICE_HOST -
printf '%s' '' | docker secret create EMPTY_VAR -
```

### Example 2 — values with quotes and special chars

`.env`:
```
QUOTED_DOUBLE="hello world"
QUOTED_SINGLE='it works'
HAS_APOSTROPHE=don't panic
HAS_PERCENT=50% off
HAS_DOLLAR=$PATH-like
```

Output:
```
printf '%s' 'hello world' | docker secret create QUOTED_DOUBLE -
printf '%s' 'it works' | docker secret create QUOTED_SINGLE -
printf '%s' 'don'\''t panic' | docker secret create HAS_APOSTROPHE -
printf '%s' '50% off' | docker secret create HAS_PERCENT -
printf '%s' '$PATH-like' | docker secret create HAS_DOLLAR -
```

The single-quote escape (`'\''`) closes the current quoted block, inserts a literal `'`, then reopens the block — the canonical bash idiom.

### Example 3 — filtering

`./env-to-secrets.sh -n --include 'POSTGRES_*' --exclude '*_USER'` against the Example 1 `.env`:
```
printf '%s' 's3cret' | docker secret create POSTGRES_PASSWORD -
```

### Example 4 — apply mode

`./env-to-secrets.sh --apply` runs the generated commands inline:
```
Applying to Docker...
qx9ab1...  (docker secret ID)
4nzwk2...
...
[OK] done
```

## CRITICAL RULES

- NEVER alter `.env` — read-only input.
- NEVER add `\n` to secret values. `printf '%s' …` is mandatory; `echo` and `printf 'literal'` are both wrong.
- NEVER quote-strip a value that has only a leading or trailing quote — only matched pairs.
- NEVER accept malformed lines silently. Log to stderr, continue with remaining lines, and warn at the end if zero entries were emitted.
- NEVER ship a converter that depends on Python, Node, or any non-bash interpreter. Bash 4+ only.
- ALWAYS write atomically (`tmp` + `mv`) so a crash mid-write doesn't leave a half-written `.secrets` that a later pipeline mistakes for valid.
- ALWAYS chmod 600 the output (it contains plaintext sensitive values).

## Companion to docker-swarm-migration

| Concern | Where it lives |
|---|---|
| Build the swarm-shape stack file | `/devops:docker-swarm-migration` |
| Push `.env` values into Docker secrets so apps can read them | `init-swarm.sh` (output of `/devops:docker-swarm-migration`) **or** `.secrets` (output of this skill) |
| Align Postgres / Mongo server-side passwords with `.env` | `/devops:correct-db-passwords` |

`init-swarm.sh` and `.secrets` are alternative ways to seed the same set of values. Use this skill when:
- You don't need the rest of `init-swarm.sh`'s logic (anomaly checks, secret-name remapping)
- You're seeding ad hoc outside a full migration
- You want a one-file artefact you can version-control alongside the stack

## Dependencies

- Tools (skill): Read, Write, Edit, Glob, Bash, AskUserQuestion
- Tools (generated script, on the operator's host): bash 4+, `docker` CLI with Swarm initialized (`--apply` mode only)
- Prerequisites: a `.env` file at script-runtime; nothing at skill-generation time.
