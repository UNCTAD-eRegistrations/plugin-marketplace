---
name: deploy-eregulations-instance
description: >
  Use when deploying a new eRegulations / TradePortal instance onto a server, or adding
  another instance to a server that already hosts one. Covers Ubuntu server preparation,
  the admin back-office deploy, the public front-end deploy, post-deploy cleanup, and
  running multiple instances that share databases. Triggers on "deploy tradeportal",
  "deploy eregulations", "admin.<x>.tradeportal.org", "public site for tradeportal",
  multiple instances on one host, or shared eRegulations databases. NOTE: this is the
  eRegulations procedure-documentation product, NOT the eRegistrations (BPA) platform.
license: UNCTAD-Internal
compatibility: Requires SSH access to the target Ubuntu server and the eRegulations / TradePortal deployment artifacts (images, compose/stack files, configuration). Fill in exact prerequisites below.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(ssh *), Bash(scp *), Bash(docker *), Bash(git *), Bash(ls *), Bash(cat *), AskUserQuestion, TodoWrite
metadata:
  version: "0.1.0"
  version-date: "2026-06-05"
  author: "UNCTAD Trade Facilitation Section"
  argument-hint: "<instance-name> [admin|public|all]"
  status: "DRAFT — capture in progress; phases marked FILL are not yet written"
---

<!--
═══════════════════════════════════════════════════════════════════════════════
✍️  FOR THE AUTHOR — read this, then delete this whole comment block when done.
═══════════════════════════════════════════════════════════════════════════════

This is a SCAFFOLD. Your job is to turn your deployment experience into a runbook
another engineer (or Claude) can follow without you in the room.

How to fill it in:
  • Replace every `<!-- FILL: ... -->` with the real thing: exact commands, file
    paths, env var names, DNS records, ports. Copy/paste from your shell history —
    do not paraphrase. A command that actually ran beats a description of it.
  • Where a value differs per instance (domain, DB name, secrets), write it as a
    placeholder like `<INSTANCE>` or `${DB_NAME}` and list it in "Inputs" below.
  • If you hit a trap and worked around it, write it in "Troubleshooting" — that is
    the most valuable part of any runbook.
  • Delete phases that don't exist yet rather than leaving them empty, OR leave the
    FILL marker so we can see what's outstanding (`grep -rc "FILL:" SKILL.md`).

Conventions (house style — see other devops skills):
  • Bump `metadata.version` on every meaningful change; keep `version-date` current.
  • Add a one-line entry to the Changelog at the bottom each time you bump.
  • When the skill is complete and tested, raise version to `1.0.0`, drop the
    `status: DRAFT` line, and delete this comment block.
  • Keep secrets OUT of this file — reference where they live, never the values.

Want to know if it reads well? Hand the finished draft to a colleague who has NOT
done this deploy and ask them to follow it on a throwaway server. Every place they
get stuck is a FILL you missed.
═══════════════════════════════════════════════════════════════════════════════
-->

# Deploy an eRegulations / TradePortal instance

## Overview

eRegulations / TradePortal is the UNCTAD procedure-**documentation** portal. A full
instance has two tiers:

- **admin** — the back-office where procedures are authored and managed.
- **public** — the citizen-facing front-end that publishes those procedures.

This skill is the deployment runbook for standing up an instance on a server,
and for hosting **multiple instances on one server** where some databases are shared.

> Reference deployment: `admin.pilot.tradeportal.org` on an Ubuntu server.

## When to use

- Deploying a brand-new instance (admin, public, or both).
- Adding a second/third instance to a host that already runs one.
- Re-deploying or recovering an existing instance.

Not for: eRegistrations / BPA deployments — use the `devops` plugin for those.

## Inputs

<!-- FILL: list every value the operator must supply before starting, e.g.: -->
<!-- FILL: | Input | Example | Where it comes from | -->
<!-- FILL: | instance name | pilot | chosen by you | -->
<!-- FILL: | admin domain | admin.pilot.tradeportal.org | DNS / ops | -->
<!-- FILL: | public domain | pilot.tradeportal.org | DNS / ops | -->
<!-- FILL: | server host/IP | xxx.xxx.xxx.xxx | provisioning ticket | -->

## Prerequisites

<!-- FILL: what must already exist/be installed before phase 1. e.g. Ubuntu version, -->
<!-- FILL: Docker / Docker Compose / Swarm, SSH key access, DNS records pointing at -->
<!-- FILL: the host, TLS/Let's Encrypt setup, access to the image registry, the -->
<!-- FILL: config/compose repo. List exact versions where they matter. -->

## Phase 1 — Server preparation

<!-- FILL: everything you did to a fresh Ubuntu box before deploying anything: -->
<!-- FILL: packages installed, Docker setup, firewall/ports opened, users created, -->
<!-- FILL: directory layout, reverse proxy. Exact commands. -->

## Phase 2 — Deploy admin (back-office)  ✅ done on pilot

<!-- FILL: the exact steps that got admin.pilot.tradeportal.org running. -->
<!-- FILL: - where the compose/stack file lives and what it contains -->
<!-- FILL: - the env vars / secrets it needs and where they're set -->
<!-- FILL: - the database(s) it uses and how they're created/migrated -->
<!-- FILL: - the up command(s) -->
<!-- FILL: - how you verified it was healthy (URL, health check, login) -->

## Phase 3 — Deploy public (front-end)  ⏳ in progress

<!-- FILL: same shape as Phase 2, for the public tier. -->
<!-- FILL: call out anything the public tier needs FROM the admin tier -->
<!-- FILL: (shared DB? API URL? generated/published content?). -->

## Phase 4 — Cleanup & hardening

<!-- FILL: the "cleanup" you flagged: removing throwaway artifacts, tightening -->
<!-- FILL: permissions, securing secrets, removing default credentials, log/backup -->
<!-- FILL: setup, anything you'd do before calling the instance production-ready. -->

## Phase 5 — Multiple instances on one server (shared databases)

This is the hard part — capture it carefully.

<!-- FILL: which databases are SHARED across instances vs. per-instance. A table: -->
<!-- FILL: | Database | Shared or per-instance? | Why / what it holds | -->
<!-- FILL: -->
<!-- FILL: then the procedure for adding instance N+1 without breaking instance N: -->
<!-- FILL: - naming/namespacing (containers, networks, volumes, DB schemas) -->
<!-- FILL: - port / domain routing for the second instance -->
<!-- FILL: - what must NOT be duplicated because it's shared -->
<!-- FILL: - migration ordering when a shared DB changes -->

## Verification

<!-- FILL: how to confirm a deploy is fully working end-to-end — URLs to hit, -->
<!-- FILL: expected responses, a smoke-test checklist. -->

## Troubleshooting

<!-- FILL: every trap you hit and how you got past it. Format: -->
<!-- FILL: **Symptom** → likely cause → fix. This section pays for itself. -->

## Rollback

<!-- FILL: how to back out a bad deploy (and what's safe to remove vs. shared). -->

## Changelog

- **0.1.0** (2026-06-05) — Scaffold created; phases awaiting capture from the pilot deploy.
