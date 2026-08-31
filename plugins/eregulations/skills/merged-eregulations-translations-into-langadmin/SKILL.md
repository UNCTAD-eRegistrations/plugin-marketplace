---
name: merged-eregulations-translations-into-langadmin
description: >
  Use when asked to consolidate a per-instance MultilangCentralRepository's
  legacy label-family files (`Common.txt`, `e-RegulationsAdmin.txt`,
  `LayoutHomeAdmin.txt`, etc.) into `LangAdmin.txt`, so the Admin SPA —
  hardcoded to read only the LangAdmin family — can reach translations that
  already exist under other legacy module names. Symptoms: "copy the labels
  into LangAdmin.txt", "consolidate translations for <instance>", or the Admin
  SPA showing untranslated default text for a label that is clearly already
  translated somewhere in the legacy admin. This is the `translations` dispatch
  target of `ereg-router`. DO NOT TRIGGER for eRegistrations (2.x) translation
  work through the Global Translation Service — that is the `translations-mcp`
  plugin — or for reconciling a local snapshot directory against a server
  directory during an upgrade (a different script, see the gotcha below).
allowed-tools: Read, Bash, Grep, Glob
metadata:
  version: "0.1.0"
  version-date: "2026-08-26"
  argument-hint: "[instance]"
---

# Consolidating legacy Multilang families into LangAdmin.txt

## Why this exists

Background: the translation-engine initiative and legacy label-key reuse work —
the Admin SPA's `TranslationService.GetTranslationValue` is hardcoded to the
`LangAdmin` family only. The legacy ASP.NET admin spreads the same labels
across ~15 other family files (`Common.txt`, `e-RegulationsAdmin.txt`,
`LayoutHomeAdmin.txt`, ...), each with years of real human translations the
SPA has no path to reach. This skill merges the relevant families' rows into
`LangAdmin.txt` in place, on the shared `MultilangCentralRepository-<instance>`
folder, without ever regressing an existing LangAdmin translation.

## Which files to merge

Confirmed with the user for the pilot/comoros instances — **this exact list**,
in this priority order (earlier file wins when two source files disagree on a
key neither has yet been added under):

```
ActivityLog.txt
Common.txt
CountryParameters.txt
e-RegulationsAdmin.txt
e-RegulationsContact.txt
Feedback.txt
e-RegulationsMenuAdmin.txt
LayoutHomeAdmin.txt
ModificationHistory.txt
SiteAdmin.txt
Users.txt
```

Deliberately excluded: `e-RegulationsPublic.txt`, `SitePublic.txt` (public
site, not admin), `Maintenance.txt`, `MediaLibrary.txt`, `migratePages.txt`,
`PreDefinedLists.txt`, `Translator.txt` (not admin-label content). If a future
ask names a different file list, treat that as instance-specific guidance, not
a reason to silently deviate from this list for pilot/comoros-style requests —
confirm with the user first (see "Ask before assuming" below).

## Process

1. **Confirm the file list and destination folder with the user** if this is
   a new instance you haven't done before, or if it's been a while — don't
   silently reuse this skill's default list without at least naming it back
   to them, since a wrong file list on a live shared translation repo used by
   a real country instance is hard to fully undo. (Getting this wrong once is
   exactly why this skill exists — see "Ask before assuming" below.)
2. SSH to the host as `<user>@<host>`. **Neither the account nor the hostname is
   recorded in this skill — ask the operator for both**, and confirm the host
   again if this is a differently-hosted instance than the pilot/comoros-era
   ones. Then confirm the folder: `/data/eregulations/shared/MultilangCentralRepository-<instance>/`.
   `ls -la` it and check all 12 files (11 sources + `LangAdmin.txt`) exist and
   share the identical `id|en|es|fr|vn|pt|ru|sw|ar|dz|tj|ur`-style header —
   if headers differ across files, the merge script's simple column-index
   fill logic will misalign columns; handle that case manually instead of
   running the script blind.
3. Download all 12 files to a local scratch dir (`scp`, read-only — safe,
   no server writes yet):
   ```bash
   for f in LangAdmin.txt ActivityLog.txt Common.txt CountryParameters.txt \
            e-RegulationsAdmin.txt e-RegulationsContact.txt Feedback.txt \
            e-RegulationsMenuAdmin.txt LayoutHomeAdmin.txt ModificationHistory.txt \
            SiteAdmin.txt Users.txt; do
     scp -q <user>@<host>:/data/eregulations/shared/MultilangCentralRepository-<instance>/"$f" "$f"
   done
   ```
4. Run `scripts/consolidate_into_langadmin.py` against the local copies:
   ```bash
   python3 scripts/consolidate_into_langadmin.py \
     <src-dir> \
     <src-dir>/LangAdmin.merged.txt \
     <conflicts-output>.txt \
     ActivityLog.txt Common.txt CountryParameters.txt e-RegulationsAdmin.txt \
     e-RegulationsContact.txt Feedback.txt e-RegulationsMenuAdmin.txt \
     LayoutHomeAdmin.txt ModificationHistory.txt SiteAdmin.txt Users.txt
   ```
   It prints a per-file table of new keys / cells filled / conflicts, plus the
   final row count. Sanity-check the numbers look plausible for the instance's
   size before going further (a near-empty result usually means the source
   files downloaded empty or truncated — check file sizes first).
5. **Server files are owned by `root`; the operator account can't write directly but is in `sudo`.** `scp` the merged file + conflicts report to `/tmp` on the server,
   then over SSH: `sudo cp` the *original* `LangAdmin.txt` to
   `LangAdmin.txt.pre-merge-backup-<timestamp>` first (this is the actual
   undo path if anything looks wrong after), `sudo cp` the merged file into
   place as `LangAdmin.txt`, `sudo chown root:root` + `sudo chmod 644` both,
   drop the conflicts report next to the instance folder as
   `MultilangCentralRepository-<instance>-merge-conflicts-<timestamp>.txt`
   (sibling of the folder, not inside it — matches where it was found on
   pilot/comoros), then clean up the `/tmp` staging files.
6. Report back: new-keys total, cells-filled total, conflicts total (all
   conflicts default to **keeping the LangAdmin/destination value** — nothing
   from a source file ever silently overwrites an existing LangAdmin
   translation), and the backup filename so the user has the exact undo path
   without having to ask.

## The merge algorithm (`scripts/consolidate_into_langadmin.py`)

- `LangAdmin.txt` is the destination; its existing rows/cells are never
  regressed.
- Source files process in the fixed priority order given on the command line.
  A key not yet in the accumulated destination gets added whole from the
  first source file that has it.
- For a key already present in the destination: per language cell, if the
  destination's cell is blank *or equal to the destination's own English
  anchor text* (i.e. "untranslated" — the legacy convention for "no real
  translation yet"), and the source has a real, distinct value, fill it in
  from source. If the destination already has a real value that differs from
  source's, keep the destination and log a conflict.
- English (`en`) is never overwritten — differences are logged as conflicts
  only, since English is the SPA's default/fallback text and corrupting it
  would change what every untranslated user sees.
- The destination's header row is what names the languages, so the script
  **refuses** (exit 1, nothing written) a `LangAdmin.txt` that is empty or
  whose header carries no language column. Merging into one would write every
  source row as a bare id with no cells — every translation discarded, while
  the counts still looked healthy. A header-only `LangAdmin.txt` is fine and
  merges normally; only a destination that names no languages is refused.
- All 12 files must share an identical header for the script's plain
  column-index cell lookups to be correct — it does not attempt to union
  differing language columns across files (unlike the unrelated
  local-vs-server upgrade-merge script this was adapted from).

## Gotcha: don't confuse this with the other Multilang merge script

There's a second, structurally different script (`merge_multilang.py`, seen
in an unrelated "comoros-upgrade" session) that merges ONE local snapshot
directory against ONE server directory, file-by-file (same filename on both
sides), for reconciling an upgrade package into a live server. That's a
different shape of problem (1 source dir → 1 dest dir, matched by filename)
from this skill's (N source *files* → 1 destination *file*, matched by row
key within a single family). Don't reach for one when the task calls for the
other — check which shape the user is actually describing before picking a
script.

## Ask before assuming

The very first time this task came up, the exact file list wasn't written
down anywhere retrievable — a prior session's merge evidence (a
`LangAdmin.txt.pre-merge-backup` file with no accompanying script) existed on
the pilot server, but the actual script that produced it was gone. The user
had to re-state the file list from memory. If you ever find yourself in the
same spot (evidence of a past merge, no retrievable script/list), don't guess
the file list from filename patterns alone (e.g. "everything with 'Admin' in
the name") — the real list mixes admin-named and non-admin-named files
(`Common.txt`, `Feedback.txt`, `Users.txt`, `CountryParameters.txt`,
`ModificationHistory.txt` are all included; `e-RegulationsContact.txt` is
included despite not being admin-specific) and excludes some admin-adjacent
ones you might expect (none excluded in practice among the "Admin"-named
files, but public-facing and non-label files are excluded even though they
live in the same folder). Ask the user to confirm or restate the list rather
than pattern-matching on filenames.
