#!/usr/bin/env python3
"""Generalised 'voice-guided leaflet' builder.

Injects a persistent, bottom-right Guide voice-guide into any leaflet HTML:
Guide narrates the whole page (guided tour: auto-scroll + highlight + live aura +
captions) and every subsection can be replayed. Guide is on by default and
dismissible (× → low-key "Ask Guide" re-open pill).

Audio: audio_mode="inline" (default) base64-inlines the mp3s into one self-contained
file; audio_mode="url" references audio/<file> on the server, lazy-loaded on play
(preload='none') — use this for the on-by-default page so it stays light. Her portrait
is always inlined.

Usage:
    python3 build-guide-leaflet.py <config.json>

The config is the ONLY per-company-type thing you edit. See guide-config.example.json.
The widget CSS/JS below is generic and should not need changing.
"""
import os, sys, json, base64

cfg_path = sys.argv[1] if len(sys.argv) > 1 else "guide-config.json"
cfg = json.load(open(cfg_path, encoding="utf-8"))
BASE = os.path.dirname(os.path.abspath(cfg_path))

def p(rel):
    return rel if os.path.isabs(rel) else os.path.normpath(os.path.join(BASE, rel))

def b64(path):
    return base64.b64encode(open(path, "rb").read()).decode()

audio_dir = cfg["audio_dir"]
# audio_mode: "inline" (default) base64-data-URIs the mp3s into one self-contained file;
# "url" references audio/<file> on the server (preload='none' → lazy, only fetched on play).
# Use "url" for the consolidated on-by-default page so it stays light (no ~2.5 MB inlined audio).
audio_mode = cfg.get("audio_mode", "inline")
audio_url_base = cfg.get("audio_url_base", "audio/")
segments = []
for s in cfg["segments"]:
    if audio_mode == "url":
        a_src = audio_url_base + s["file"]
    else:
        a_src = "data:audio/mpeg;base64," + b64(p(os.path.join(audio_dir, s["file"])))
    segments.append({
        "audio": a_src,
        "target": s.get("target"),
        "block": s.get("block", "start"),
        "text": s.get("text", ""),
    })
avatar_uri = "data:image/webp;base64," + b64(p(cfg["avatar"]))

CSS = """
  /* ===== Guide voice-guide (fixed, bottom-right) — generic ===== */
  #guide-widget { position: fixed; right: 28px; bottom: 28px; z-index: 9999; display: flex; flex-direction: column; align-items: flex-end; gap: 12px; }
  #guide-caption { max-width: 330px; background: #fff; border: 1px solid var(--brand-rule, #e5e7eb); border-radius: 14px; padding: 13px 16px; font-size: 14px; line-height: 1.5; color: var(--brand-ink, #111827); box-shadow: 0 10px 30px rgba(0,0,0,0.14); opacity: 0; transform: translateY(8px); transition: opacity .3s, transform .3s; pointer-events: none; }
  #guide-caption.show { opacity: 1; transform: none; }
  #guide-caption .gc-name { display: block; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--brand-accent, #15803d); margin-bottom: 5px; }
  #guide-dock { display: flex; align-items: center; gap: 12px; }
  #guide-cta { background: var(--brand-primary, #334155); color: #fff; border: none; border-radius: 100px; padding: 11px 18px; font: 600 14px 'Poppins', sans-serif; cursor: pointer; box-shadow: 0 6px 20px rgba(51,65,85,0.35); display: flex; align-items: center; gap: 9px; }
  #guide-cta:hover { filter: brightness(1.08); }
  #guide-cta .gc-ic { font-size: 12px; }
  #guide-bubble { position: relative; width: 96px; height: 96px; flex: none; cursor: pointer; }
  #guide-aura, #guide-ring, #guide-portrait { position: absolute; left: 50%; top: 50%; border-radius: 50%; }
  #guide-aura { width: 96px; height: 96px; transform: translate(-50%,-50%) scale(1); background: radial-gradient(circle, rgba(76,175,116,0.55) 0%, rgba(76,175,116,0) 70%); opacity: 0.2; }
  #guide-ring { width: 88px; height: 88px; transform: translate(-50%,-50%) scale(1); border: 3px solid rgba(76,175,116,0.7); }
  #guide-portrait { width: 74px; height: 74px; transform: translate(-50%,-50%); object-fit: cover; border: 3px solid #fff; box-shadow: 0 4px 16px rgba(0,0,0,0.3); background: #4CAF74; }
  #guide-nm { position: absolute; left: 50%; bottom: -19px; transform: translateX(-50%); font: 600 12px 'Poppins', sans-serif; color: #fff; background: rgba(51,65,85,0.9); padding: 2px 12px; border-radius: 100px; white-space: nowrap; }
  .guide-hl { animation: guideHl 2.4s ease; border-radius: 12px; }
  @keyframes guideHl { 0% { box-shadow: 0 0 0 0 rgba(76,175,116,0); } 22% { box-shadow: 0 0 0 5px rgba(76,175,116,0.4); } 100% { box-shadow: 0 0 0 0 rgba(76,175,116,0); } }
  .guide-replay { margin-left: 12px; border: 1px solid #cbd5e1; background: #fff; color: var(--brand-primary, #334155); border-radius: 100px; font: 600 11px 'Poppins', sans-serif; padding: 3px 11px; cursor: pointer; vertical-align: middle; }
  .guide-replay:hover { background: var(--brand-primary-wash, #eef0fb); }
  /* dismiss (×) on the bubble corner → collapses the widget to a low-key re-open pill */
  #guide-close { position: absolute; top: -7px; right: -7px; width: 24px; height: 24px; border-radius: 50%; border: none; background: #fff; color: var(--brand-ink-soft, #475569); box-shadow: 0 2px 8px rgba(0,0,0,0.22); cursor: pointer; font: 700 15px/1 'Poppins', sans-serif; display: flex; align-items: center; justify-content: center; z-index: 3; padding: 0; }
  #guide-close:hover { background: #f1f5f9; color: var(--brand-primary, #334155); }
  #guide-reopen { position: fixed; right: 28px; bottom: 28px; z-index: 9999; display: none; align-items: center; gap: 9px; background: #fff; border: 1px solid var(--brand-rule, #e5e7eb); border-radius: 100px; padding: 6px 17px 6px 6px; box-shadow: 0 8px 24px rgba(0,0,0,0.16); cursor: pointer; font: 600 13px 'Poppins', sans-serif; color: var(--brand-primary, #334155); }
  #guide-reopen:hover { box-shadow: 0 10px 28px rgba(0,0,0,0.2); }
  #guide-reopen img { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; background: #4CAF74; }
  #guide-reopen.show { display: flex; }
  @media print { #guide-widget, #guide-reopen, .guide-replay { display: none !important; } }
  @media (max-width: 600px) { #guide-caption { max-width: 210px; } #guide-cta .gc-tx { display: none; } #guide-cta { padding: 11px 14px; } }
"""

WIDGET = """
<div id="guide-widget">
  <div id="guide-caption"><span class="gc-name">__NAME__</span><span id="guide-cap-tx"></span></div>
  <div id="guide-dock">
    <button id="guide-cta" aria-label="__CTA__"><span class="gc-ic" id="guide-ic">&#9654;</span><span class="gc-tx" id="guide-lb">__CTA__</span></button>
    <div id="guide-bubble" title="__NAME__">
      <div id="guide-aura"></div><div id="guide-ring"></div>
      <img id="guide-portrait" src="__AVATAR__" alt="__NAME__">
      <div id="guide-nm">__NAME__</div>
      <button id="guide-close" type="button" aria-label="Dismiss __NAME__" title="Dismiss __NAME__">&times;</button>
    </div>
  </div>
</div>
<button id="guide-reopen" type="button" aria-label="Re-open __NAME__"><img src="__AVATAR__" alt=""><span>Ask __NAME__</span></button>
<script>
const GUIDE_SEGMENTS = __SEGMENTS__;
(function(){
  const aura=document.getElementById('guide-aura'), ring=document.getElementById('guide-ring');
  const cap=document.getElementById('guide-caption'), capTx=document.getElementById('guide-cap-tx');
  const cta=document.getElementById('guide-cta'), ic=document.getElementById('guide-ic'), lb=document.getElementById('guide-lb');
  const bubble=document.getElementById('guide-bubble');
  const NAME=__NAME_JS__, CTA=__CTA_JS__;
  const audios=GUIDE_SEGMENTS.map(s=>{ const a=new Audio(); a.preload=__PRELOAD__; a.src=s.audio; return a; });
  let ctx, analyser, freq, srcs={}, raf;
  let current=-1, playing=false, tour=false;

  function ensureCtx(){
    if(!ctx){ ctx=new (window.AudioContext||window.webkitAudioContext)(); analyser=ctx.createAnalyser(); analyser.fftSize=256; freq=new Uint8Array(analyser.frequencyBinCount); analyser.connect(ctx.destination); }
    if(ctx.state==='suspended') ctx.resume();
  }
  function connect(i){ if(!srcs[i]){ try{ const s=ctx.createMediaElementSource(audios[i]); s.connect(analyser); srcs[i]=s; }catch(e){} } }
  function idle(){ aura.style.transform='translate(-50%,-50%) scale(1)'; aura.style.opacity='0.2'; ring.style.transform='translate(-50%,-50%) scale(1)'; ring.style.opacity='0.7'; }
  function pulse(){
    if(!playing){ idle(); return; }
    analyser.getByteFrequencyData(freq);
    let s=0; for(let i=0;i<freq.length;i++) s+=freq[i];
    const a=Math.min(1,(s/freq.length)/85);
    aura.style.transform='translate(-50%,-50%) scale('+(1+a*0.85)+')';
    aura.style.opacity=(0.2+a*0.6).toFixed(3);
    ring.style.transform='translate(-50%,-50%) scale('+(1+a*0.55)+')';
    ring.style.opacity=(0.7-a*0.35).toFixed(3);
    raf=requestAnimationFrame(pulse);
  }
  function setIcon(pl){ ic.innerHTML=pl?'&#10074;&#10074;':'&#9654;'; lb.textContent=pl?'Pause':(tour&&current>=0?'Resume':CTA); }
  function highlight(el){ document.querySelectorAll('.guide-hl').forEach(e=>e.classList.remove('guide-hl')); if(el){ void el.offsetWidth; el.classList.add('guide-hl'); } }
  function targetEl(seg){ return seg.target?document.querySelector(seg.target):null; }

  function play(i, isTour){
    ensureCtx(); tour=!!isTour;
    if(current>=0){ audios[current].pause(); audios[current].onended=null; }
    current=i; const seg=GUIDE_SEGMENTS[i], a=audios[i]; connect(i);
    const el=targetEl(seg);
    if(el){ el.scrollIntoView({behavior:'smooth', block:seg.block||'start'});
            highlight(el.classList.contains('screen-caption') ? (el.nextElementSibling||el) : el); }
    else { window.scrollTo({top:0,behavior:'smooth'}); highlight(null); }
    capTx.textContent=seg.text; cap.classList.add('show');
    a.currentTime=0;
    a.play().then(()=>{ playing=true; setIcon(true); pulse(); }).catch(()=>{});
    a.onended=function(){ playing=false; setIcon(false);
      if(tour && current<GUIDE_SEGMENTS.length-1){ play(current+1,true); }
      else { tour=false; cap.classList.remove('show'); highlight(null); idle(); }
    };
  }
  function toggle(){
    if(playing){ audios[current].pause(); playing=false; setIcon(false); idle(); }
    else if(tour && current>=0){ ensureCtx(); audios[current].play(); playing=true; setIcon(true); pulse(); }
    else { play(0,true); }
  }
  cta.addEventListener('click', toggle);
  bubble.addEventListener('click', toggle);

  // dismiss / re-open — Guide is on by default; the × collapses her to a low-key pill
  const widget=document.getElementById('guide-widget'), closeBtn=document.getElementById('guide-close'), reopen=document.getElementById('guide-reopen');
  closeBtn.addEventListener('click', function(ev){ ev.stopPropagation();
    if(playing){ audios[current].pause(); playing=false; setIcon(false); idle(); }
    cap.classList.remove('show'); highlight(null);
    widget.style.display='none'; reopen.classList.add('show');
  });
  reopen.addEventListener('click', function(){ reopen.classList.remove('show'); widget.style.display='flex'; });

  GUIDE_SEGMENTS.forEach((seg,i)=>{
    if(!seg.target) return;
    const host=document.querySelector(seg.target);
    if(!host) return;
    const anchor = host.querySelector('.part-eyebrow') || host.querySelector('.factbox-head') || host;
    const b=document.createElement('button');
    b.className='guide-replay'; b.type='button'; b.innerHTML='&#128266; '+NAME;
    b.title='Hear '+NAME+' explain this';
    b.addEventListener('click', function(ev){ ev.preventDefault(); ev.stopPropagation(); play(i,false); });
    anchor.appendChild(b);
  });
  idle();
})();
</script>
"""

name = cfg.get("assistant_name", "Guide")
cta = cfg.get("cta_label", "Let Guide guide you")
preload = "none" if audio_mode == "url" else "auto"
WIDGET = (WIDGET
          .replace("__AVATAR__", avatar_uri)
          .replace("__SEGMENTS__", json.dumps(segments))
          .replace("__NAME_JS__", json.dumps(name))
          .replace("__CTA_JS__", json.dumps(cta))
          .replace("__PRELOAD__", json.dumps(preload))
          .replace("__NAME__", name)
          .replace("__CTA__", cta))

src = open(p(cfg["input_html"]), encoding="utf-8").read()
for find, repl in cfg.get("anchors", []):
    if find not in src:
        print("WARN anchor not found:", find[:70])
    src = src.replace(find, repl, 1)
src = src.replace("</style>", CSS + "\n</style>", 1)
src = src.replace("</body>", WIDGET + "\n</body>", 1)
if cfg.get("title_replace"):
    src = src.replace(cfg["title_replace"][0], cfg["title_replace"][1], 1)

out = p(cfg["output_html"])
open(out, "w", encoding="utf-8").write(src)
print("wrote %s  (%d KB, %d segments)" % (out, os.path.getsize(out)//1024, len(segments)))
