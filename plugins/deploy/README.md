# deploy

Self-service deployment requests on the singlewindow Coolify server.

## Skills

| Skill | Description |
|-------|-------------|
| `request-deploy` | Open a well-formed deployment issue on `unctad-ai/deploy` from the current repo. Detects repo + framework, fills sensible defaults, swaps secret-shaped values to `<SET-IN-COOLIFY>`, and posts via `gh`. GitHub Actions on the deploy repo handles onboarding to Coolify. |

## How it works

1. You `cd` into the repo you want to deploy.
2. Ask Claude to "deploy this" (or invoke `request-deploy` directly).
3. The skill inspects your repo, proposes sensible defaults (slug, domain, build pack, port), asks only what's missing, and opens a GitHub issue on `unctad-ai/deploy`.
4. If your GitHub login is on the allowlist (`.github/deploy-authorized-users.yml` on the deploy repo), the deploy runs automatically — first build + Let's Encrypt cert takes ~3 minutes.
5. Otherwise, a maintainer reviews and applies the `approved` label.

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status`).
- The target repo's Coolify GitHub App access has been granted by a maintainer. (If not, the deploy onboarder fails with a clear error and you ask a maintainer to grant access.)

## Related

- [unctad-ai/deploy](https://github.com/unctad-ai/deploy) — the deploy-orchestration repo this skill targets.
- Allowlist edits go through `CODEOWNERS` on the deploy repo.
