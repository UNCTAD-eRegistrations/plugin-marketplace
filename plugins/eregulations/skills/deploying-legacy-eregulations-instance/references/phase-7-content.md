# Phase 7 — Content folders, media mount, repository ownership

Extract the content zip's four folders straight into
`/data/eregulations/<name>/{media,Multilang,PublicConfig,PublicContent}`
(check what convention sibling instances on that host actually use — it
has changed over time). **Don't use plain `unzip` for this — see the mangled-filenames section below.** `chown -R 1654:1654` —
that's the container runtime uid. **Confirm the `media` folder here is
actually bind-mounted into the admin-api container as `/app/media` in
the Coolify service definition — if it's missing, admin-api crashes on
startup instead of just breaking media links (see the `/app/media` section below).** Point
`MULTILANG_CENTRAL_REPOSITORY_HOST_PATH` at this instance's own
`/data/eregulations/shared/MultilangCentralRepository-<name>` (each
instance gets its own directory under the shared parent path — don't
confuse "lives under the shared host folder" with "shares file content
with sibling instances"); if it doesn't exist yet, create it (copy from
the country's own zip content, or seed from a sibling's structure — just
not by literally reusing another live instance's directory, which would
mix translations across countries. **Whichever way it's populated,
`chown -R 1654:1654` this directory too — it does not get this for free
from phase 7's blanket chown because it lives outside
`/data/eregulations/<name>/`, under the separate `shared/` path.** Missing
this step doesn't show up until someone actually tries to save a
translation — see the repository-ownership section below, confirmed missing on two independently-provisioned
instances (`comoros`, `experimental-pilot`) before this step existed.

## Mangled filenames in the media folder

The content zip usually comes from a French- (or other non-English-)
locale Windows server, and old Windows zip tools don't always set the
UTF-8 flag (general-purpose bit 11) on entries with accented filenames —
they fall back to a legacy DOS/OEM code page instead, almost always
**CP850** for a French-locale machine. `unzip` on macOS doesn't know this
and guesses some other single-byte encoding (observed: something that
renders like DOS/Mac Cyrillic) — producing filenames with *valid but
wrong* characters, e.g. `établissement` becomes `Вtablissement` (Cyrillic
В, not a `�` replacement character). This does **not** show up as an
obvious "corrupted filename" — it looks like a plausible, slightly odd
filename, and the file is silently unreachable under the name the DB/HTML
actually reference. `unzip -l` on the zip itself will print
`mismatching "local" filename` warnings for these entries; that's the
signal, not the mangled result of extracting.

Symptom: an individual media file 404s / "is missing" even though nothing
else about the deployment looks wrong, and it re-occurs one file at a time
as people notice each broken link (there were 55 such files in one
instance — assume there's more than one, don't fix them individually).

Don't extract the media folder with plain `unzip`. Use Python's `zipfile`,
which exposes the UTF-8 flag per entry and lets you fall back to CP850
(not CP437 — CP437 is close but wrong for a few accented characters)
explicitly instead of guessing:
```python
import zipfile, os

z = zipfile.ZipFile('content.zip')
for info in z.infolist():
    if info.is_dir():
        continue
    name = info.filename
    if not (info.flag_bits & 0x800):  # UTF-8 flag not set
        name = name.encode('cp437').decode('cp850')
    target = os.path.join(outdir, name[len('<zip-root-prefix>/'):])
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with z.open(info) as src, open(target, 'wb') as dst:
        dst.write(src.read())
```
If you already extracted with plain `unzip` and are finding these
reactively: don't just add the correctly-named file and leave the garbled
one sitting there. Confirm the exact garbled name generated for each
correct name (re-derive it — `raw.encode('cp437').decode(<whatever wrong
encoding was actually used, e.g. cp866>)` — verify against one known bad
filename first) and only delete a same-size candidate once its content
hash matches the correct file byte-for-byte. Same-size ≠ same-file: legit,
unrelated files can coincidentally share a byte count, so hash before you
delete anything.

## admin-api crashes on startup if `/app/media` isn't mounted

Different failure mode from the MultilangCentralRepository gotcha below —
that one is a permissions problem that breaks *one action* (saving a
translation). This one is the mount being *absent* entirely, and it takes
the whole container down, not just one feature.

`eRegulations-4.0-Admin/Project/WebAppCore/Program.cs` wires up `/media`
static file serving via `PhysicalFileProvider(Path.Combine(Directory.GetCurrentDirectory(),
"media"))` with **no existence check** — if `/app/media` doesn't exist in
the container, this throws `DirectoryNotFoundException` at startup and
crashes the app immediately (restart-loop, not a single broken link).
`eRegulations-4.0-Public`'s equivalent `/media` setup in its own
`Program.cs` correctly guards with `if (Directory.Exists("/app/media"))`
first — Admin is missing that guard. Pre-existing gap, not introduced by
this migration process; as of this writing it's not fixed in code, so the
only mitigation from this side is making sure the mount is actually there.

**Symptom:** the admin-api container exits immediately after starting —
`docker logs <admin-api-container>` shows a `DirectoryNotFoundException`
naming `/app/media` (or `media` under the working directory) in the stack
trace. Most likely after a fresh Coolify deploy where the `media` bind
mount got left out of the service definition — a quick test image
deployed without going through the full reference `docker-compose.yml`,
or a Coolify app whose volumes were set up by hand and missed one entry.

**Fix:** confirm the Coolify app's admin-api service has a
`${CONTENT_DIR}/media:/app/media` (or equivalent) volume mount — the same
folder phase 7 already extracts the content zip's `media/` into and
`chown`s to `1654:1654`. If the mount is present in the service definition
and it's still crashing, check that the extracted content actually landed in that host folder per phase 7, rather than assuming the mount config
itself is the problem (`docker exec <admin-api-container> ls /app/media`
to confirm from inside the container).

## MultilangCentralRepository not writable by the container user

Symptom: saving *any* translation (new label auto-registered by the Admin
SPA, or editing an existing one in the Labels screen) 500s with
`System.UnauthorizedAccessException: Access to the path
'/app/MultilangCentralRepository/temp_<timestamp>.txt' is denied. --->
System.IO.IOException: Permission denied` in the API error body. Looks
instance-specific the first time you see it — it isn't. Confirmed present
on two independently-provisioned instances (`comoros`, `experimental-pilot`)
before this gotcha was written down, which means it had likely never
actually worked on either: earlier verification only confirmed the SPA
didn't blank out or crash on a failed save (a separate, already-fixed bug —
see [[project_translation_engine_initiative]]), not that the save reached
the disk.

Root cause: the API writes new/updated translations via a
write-temp-then-atomic-rename pattern inside
`ApplicationSettings__CentralRepositoryPath` (`/app/MultilangCentralRepository`
in-container, bind-mounted from
`/data/eregulations/shared/MultilangCentralRepository-<name>` on the host).
The container runs as a non-root uid (`1654`, baked into the
`mcr.microsoft.com/dotnet/aspnet:8.0-jammy-amd64` base image via `$APP_UID`
— not set explicitly anywhere in this repo's `Dockerfile`, confirmed
identical across two independently-deployed containers so it's stable for
any instance built from the current Dockerfile/base image, but would need
re-checking if the base image ever changes). If the host directory is
`root:root` mode `755` (the default for a directory nobody has explicitly
fixed), uid 1654 gets read+traverse only — no write, so it can't create the
temp file for *any* save, not just new-key inserts.

**Diagnose:** confirm with a live write test from inside the container
rather than just eyeballing `ls -la` permissions:
```bash
docker exec <admin-api-container> sh -c 'touch /app/MultilangCentralRepository/.write-test && echo WRITABLE || echo DENIED'
```
**Fix**, on the host (needs `sudo` — the directory being root-owned is
exactly why):
```bash
sudo chown -R 1654:1654 /data/eregulations/shared/MultilangCentralRepository-<name>
```
Safe to run any time, including on a live instance — it only changes
ownership, not content, and there's no evidence anything else (a backup job,
a different-uid process) needs root ownership specifically; nothing broke
when this was applied to `comoros`.

This is now folded into phase 7 so it happens at provisioning time for
new instances instead of surfacing as a live 500 later — but it was missed
for every instance provisioned before this was written down, so **check any
existing instance you're troubleshooting, not just newly-provisioned ones.**
