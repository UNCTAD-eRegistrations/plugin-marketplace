---
description: Route an eRegulations request — bugfix, deploy, upgrade, dev, translations — through classification, context resolution and safety gates.
argument-hint: "[request] or --dry-run [request]"
effort: medium
allowed-tools: Read, Bash, Grep, Glob
---

Invoke the `ereg-router` skill with the request below. It classifies the request
into a primary kind plus any secondary kinds, resolves which instance and version
it concerns, detects whether this environment can plan, build or execute, and
evaluates the safety gates before any work starts.

If the first argument is `--dry-run`, run steps 1–4 only and print the decision —
classification, resolved context (including any drift and any unresolved fields),
the detected lane, and every gate decision with its reason — then **stop before
dispatch**. Nothing is executed, nothing is written, no override is recorded.

This command is the explicit entry point. The primary one is plain English:
describing an eRegulations problem reaches the same router with nothing typed.
It resolves as `/eregulations:ereg` — plugin commands are namespaced
`plugin:command`, so a bare `/ereg` is not available from a plugin.

$ARGUMENTS
