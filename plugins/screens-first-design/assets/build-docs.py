#!/usr/bin/env python3
"""Assemble a project's screens-first UX documentation into ONE indexed, collapsible HTML (docs.html).

Copy this script into your project's DESIGN FOLDER (next to the NN-slug.md fiches and
NN-slug.html mockups), then edit the configuration block below.

The markdown files are the source of truth; docs.html is a generated mirror.
Regenerate after any edit:  python3 build-docs.py

Requires: pip install markdown
"""
import pathlib
import re
import markdown

HERE = pathlib.Path(__file__).parent
OUT = HERE / "docs.html"

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_TITLE = "Project — UX documentation"
PROJECT_SUBTITLE = "The invariant schema, the screens, the norms and the decisions — all in one document."
REPO_URL = ""  # optional, e.g. "https://github.com/org/project"; shown in the header when set

# (anchor id, display title, source path) — all paths RELATIVE to this design folder.
# List the schema first, then one line per screen fiche, then digests and the decisions journal.
DOCS = [
    ("schema",    "The invariant UX schema",   HERE / "ux-pattern.md"),
    ("screen0",   "Screen 0 — Home",           HERE / "00-home.md"),
    ("screen1",   "Screen 1 — Detail",         HERE / "01-detail.md"),
    # ("digest",  "Reference digest",          HERE / ".." / "reference" / "digest.md"),
    ("decisions", "Decisions journal",         HERE / ".." / "kb" / "decisions.md"),
]

# Clickable mockups, auto-discovered (NN-*.html files) so the nav never drifts.
# Desktop drafts (frozen, unverified) are excluded until the desktop work resumes.
MOCKUPS = sorted(p for p in HERE.glob("[0-9][0-9]-*.html") if "-desktop" not in p.name)

# Desktop mockups (NN-slug-desktop.html) are linked next to their mobile sibling
# once this flag is on — keep it False while the desktop derivation is still draft.
DESKTOP_READY = False

# Optional companion pages, linked from the nav only when the file exists.
TOUR = HERE / "tour.html"
TOUR_DESKTOP = HERE / "tour-desktop.html"
PRESENTATIONS = [HERE / "presentation.html"]  # add module presentations here
# ──────────────────────────────────────────────────────────────────────────────

def render(src: pathlib.Path) -> str:
    text = src.read_text(encoding="utf-8")
    # Drop the document's own H1 (the section summary carries the title).
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            del lines[i]
            break
    body = markdown.markdown("\n".join(lines),
                             extensions=["tables", "fenced_code", "sane_lists", "attr_list"])
    # Wrap each H2 block in a closed <details class="sub"> so subsections collapse too.
    parts = re.split(r"<h2>(.*?)</h2>", body)
    if len(parts) == 1:
        return body
    out = [parts[0]]
    for j in range(1, len(parts), 2):
        title, content = parts[j], parts[j + 1] if j + 1 < len(parts) else ""
        out.append(f'<details class="sub"><summary>{title}</summary><div class="subbody">{content}</div></details>')
    return "".join(out)

sections, index_items = [], []
for anchor, title, src in DOCS:
    if not src.exists():
        print(f"  skipped (missing): {src}")
        continue
    rel = src.resolve()
    try:
        rel = rel.relative_to(HERE.resolve().parent)
    except ValueError:
        rel = rel.name
    index_items.append(f'<a href="#{anchor}">{title}</a>')
    sections.append(
        f'<details class="doc" id="{anchor}" open><summary>{title}'
        f'<span class="src">{rel}</span></summary><div class="docbody">{render(src)}</div></details>'
    )

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:oklch(0.985 0.006 255); --fg:oklch(0.26 0.025 260); --muted:oklch(0.53 0.02 260);
  --accent:oklch(0.45 0.13 252); --border:oklch(0.9 0.011 255);
  --surface:#fff; --highlight:oklch(0.96 0.028 252);
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:"Poppins",-apple-system,BlinkMacSystemFont,sans-serif;
  line-height:1.65;margin:0;padding:3rem 1.25rem;font-size:15.5px;-webkit-font-smoothing:antialiased}
.wrap{max-width:880px;margin:0 auto}
header h1{font-size:1.9rem;font-weight:700;letter-spacing:-.02em;margin:0 0 .2rem;line-height:1.15}
header .sub{color:var(--muted);font-size:.92rem;margin:0 0 .3rem}
header .meta{color:var(--muted);font-size:.78rem}
nav{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1rem 1.25rem;margin:1.6rem 0 2rem}
nav b{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:.5rem}
nav a{display:block;color:var(--accent);text-decoration:none;font-weight:500;font-size:.94rem;padding:.22rem 0}
nav a:hover{text-decoration:underline}
nav .mock{margin-top:.8rem;padding-top:.8rem;border-top:1px solid var(--border);font-size:.85rem;color:var(--muted)}
nav .mock a{display:inline;padding:0}
nav .tour{display:flex;align-items:center;gap:.55rem;margin-top:.9rem;padding:.7rem .9rem;background:var(--highlight);
  border:1px solid var(--border);border-radius:11px;font-weight:600;font-size:.92rem}
nav .tour svg{width:1.05rem;height:1.05rem;color:var(--accent);flex:none}
nav .tour a{display:inline;padding:0}
nav .tour span{font-weight:500;font-size:.8rem;color:var(--muted)}
details.doc{background:var(--surface);border:1px solid var(--border);border-radius:14px;margin-bottom:14px;padding:0 1.4rem}
details.doc>summary{cursor:pointer;list-style:none;font-size:1.28rem;font-weight:700;letter-spacing:-.015em;
  padding:1.05rem 0;display:flex;align-items:baseline;gap:.7rem;position:relative;padding-left:1.2rem}
details.doc>summary .src{font-size:.7rem;font-weight:500;color:var(--muted);font-family:ui-monospace,Menlo,monospace;margin-left:auto}
details.doc>summary::before,details.sub>summary::before{content:"";position:absolute;left:0;top:50%;
  width:.42rem;height:.42rem;border-right:1.5px solid var(--muted);border-bottom:1.5px solid var(--muted);
  transform:translateY(-70%) rotate(-45deg);transition:transform .15s}
details[open]>summary::before{transform:translateY(-70%) rotate(45deg)}
details.doc>.docbody{padding:0 0 1.3rem;border-top:1px solid var(--border)}
details.sub{margin:.7rem 0;border:0;padding:0}
details.sub>summary{cursor:pointer;list-style:none;font-size:1.02rem;font-weight:600;padding:.35rem 0 .35rem 1.1rem;position:relative}
details.sub .subbody{padding-left:1.1rem}
summary::-webkit-details-marker{display:none}
p{margin:.6rem 0}
a{color:var(--accent)}
code{background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:.05em .35em;
  font-size:.85em;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
table{border-collapse:collapse;width:100%;margin:1rem 0;font-size:.9rem}
th,td{text-align:left;padding:.45rem .65rem;border-bottom:1px solid var(--border);vertical-align:top}
th{background:var(--bg);font-weight:600}
tr:last-child td{border-bottom:0}
ul,ol{padding-left:1.3rem;margin:.6rem 0}
li{margin:.25rem 0}
blockquote{margin:1rem 0;padding-left:1rem;color:var(--muted);border-left:2px solid var(--border)}
hr{border:0;border-top:1px solid var(--border);margin:1.6rem 0}
strong{font-weight:600}
em{color:var(--muted);font-style:normal}
footer{margin-top:2.5rem;color:var(--muted);font-size:.82rem;border-top:1px solid var(--border);padding-top:1rem}
@media (max-width:640px){body{padding:1.5rem .9rem}details.doc{padding:0 1rem}details.doc>summary .src{display:none}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>__TITLE__</h1>
  <p class="sub">__SUBTITLE__</p>
  <p class="meta">Generated from the markdown files (source of truth)__REPO__</p>
</header>
<nav>
  <b>Index</b>
  __INDEX__
  __MOCKS__
  __COMPANIONS__
</nav>
__SECTIONS__
<footer>Regenerate after any change to the .md files: <code>python3 build-docs.py</code></footer>
</div>
<script>
function openTarget(){const h=location.hash.slice(1);if(!h)return;const d=document.getElementById(h);
  if(d&&d.tagName==='DETAILS'){d.open=true;d.scrollIntoView({behavior:'smooth'});}}
window.addEventListener('hashchange',openTarget);openTarget();
</script>
</body>
</html>
"""

def mock_link(m: pathlib.Path) -> str:
    label = f'screen {int(m.name[:2])} · {m.stem[3:].replace("-", " ")}'
    desktop = m.with_name(f"{m.stem}-desktop.html")
    link = f'<a href="{m.name}">{label}</a>'
    if DESKTOP_READY and desktop.exists():
        link += f' (<a href="{desktop.name}">desktop</a>)'
    return link

mock_links = " · ".join(mock_link(m) for m in MOCKUPS)
mocks_html = f'<div class="mock">Clickable mockups: {mock_links}</div>' if MOCKUPS else ""

companions = []
if TOUR.exists():
    tour_extra = (f' · <a href="{TOUR_DESKTOP.name}">desktop tour</a>'
                  if DESKTOP_READY and TOUR_DESKTOP.exists() else "")
    companions.append(
        '<div class="tour"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/>'
        '<path d="M8 21h8M12 17v4"/></svg>'
        f'<a href="{TOUR.name}">All the system\'s screens, chained</a>{tour_extra} '
        '<span>— overview + screen-by-screen guided visit, live mockups</span></div>'
    )
pres_links = " · ".join(f'<a href="{p.name}">{p.stem}</a>' for p in PRESENTATIONS if p.exists())
if pres_links:
    companions.append(
        '<div class="tour"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h20v14H2zM8 21h8"/><path d="M6 7h6M6 10h9"/></svg>'
        '<span style="font-weight:600;color:var(--fg)">Team presentations:</span> ' + pres_links + '</div>'
    )

repo_html = f' · repo <a href="{REPO_URL}">{REPO_URL.split("://")[-1]}</a>' if REPO_URL else ""

out_html = (HTML.replace("__TITLE__", PROJECT_TITLE)
                .replace("__SUBTITLE__", PROJECT_SUBTITLE)
                .replace("__REPO__", repo_html)
                .replace("__INDEX__", "\n  ".join(index_items))
                .replace("__MOCKS__", mocks_html)
                .replace("__COMPANIONS__", "\n  ".join(companions))
                .replace("__SECTIONS__", "\n".join(sections)))
OUT.write_text(out_html, encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
