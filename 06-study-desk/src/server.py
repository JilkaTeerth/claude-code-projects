#!/usr/bin/env python3
"""Study Desk. A single page that answers 'what do I do now' and opens the guides.

Deliberately stdlib only and no build step, for the same reason the rest of this system
is boring: the previous piece of infrastructure died silently for nine days and nobody
noticed. Fewer moving parts, louder failures.

Reads Todoist live (it is the source of truth, kept current by ~/bin/canvas-sweep),
renders the study guides from ~/Desktop/F&M Notes/<course>/Study Guides/, and shows
sync health so a dead sweep is visible instead of invisible.
"""
import subprocess
import json, os, re, html, time, datetime, zoneinfo, urllib.request, urllib.error, urllib.parse, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT   = 7474
NOTES  = os.path.expanduser("~/Desktop/F&M Notes")
HB     = os.path.expanduser("~/.canvas-sweep-heartbeat")
TBASE  = "https://api.todoist.com/api/v1"
COURSES = ["MAT 230", "CPS 112", "DSC 215", "ANT 100"]
COLOR  = {"MAT 230": "#26532b", "CPS 112": "#5abcb9", "DSC 215": "#399e5a", "ANT 100": "#63e2c6"}


# Deadlines are Eastern (F&M), whatever timezone the laptop happens to be in. Todoist sends
# UTC stamps ("...Z") for exact-time tasks, so an 11:59pm deadline is 03:59Z the NEXT day;
# slicing [:10] off that put every late-night deadline one day late. Convert, then take the date.
CAMPUS_TZ = zoneinfo.ZoneInfo("America/New_York")

def due_date(due):
    if due.endswith("Z"):
        return datetime.datetime.fromisoformat(due.replace("Z", "+00:00")).astimezone(CAMPUS_TZ).date()
    return datetime.date.fromisoformat(due[:10])

def env(path):
    o = {}
    p = os.path.expanduser(path)
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); o[k.strip()] = v.strip()
    return o
TTOK = env("~/.todoist_env").get("TODOIST_TOKEN", "")

_cache = {"at": 0, "data": None, "err": None}
_lock = threading.Lock()

def td_list(path):
    out, c = [], None
    while True:
        p = path + (("&" if "?" in path else "?") + "cursor=" + c if c else "")
        r = urllib.request.Request(TBASE + p, headers={"Authorization": "Bearer " + TTOK})
        with urllib.request.urlopen(r, timeout=20) as z:
            d = json.loads(z.read().decode() or "{}")
        if isinstance(d, list): return d
        out.extend(d.get("results", [])); c = d.get("next_cursor")
        if not c: return out

def state(force=False):
    with _lock:
        if not force and _cache["data"] and time.time() - _cache["at"] < 45:
            return _cache["data"]
        try:
            projects = {p["id"]: p["name"] for p in td_list("/projects")}
            tasks = td_list("/tasks")
            _cache["err"] = None
        except Exception as e:
            _cache["err"] = str(e)
            return _cache["data"] or {"courses": {}, "undated": [], "guides": [], "review": [],
                                      "health": health(), "err": str(e)}
        today = datetime.date.today()
        bycourse, undated, guides, reviews, switch = {c: [] for c in COURSES}, [], [], [], None
        for t in tasks:
            pname = projects.get(t.get("project_id"), "")
            content = t.get("content", "")
            if content.startswith("Canvas sync alive"):
                switch = t; continue
            due = (t.get("due") or {}).get("date")
            d = None
            if due:
                try: d = due_date(due)
                except Exception: d = None
            desc = t.get("description") or ""
            gm = re.search(r"\[guide:([^\]]+)\]", desc)
            # Review items are made by `desk review`: things built for him that he still has
            # to go through. Same stateless trick as guides, the stamp lives in Todoist.
            rm = re.search(r"\[review:([^\]]*)\]", desc)
            note = re.sub(r"\[(canvas|cdue|guide|review):[^\]]*\]", "", desc).strip()
            cvm = re.search(r"\[canvas:(\d+)\]", desc)
            item = {"id": t["id"], "name": content, "course": pname, "canvas": cvm.group(1) if cvm else None,
                    "due": d.isoformat() if d else None,
                    "days": (d - today).days if d else None,
                    "guide": gm.group(1) if gm else None,
                    "note": note}
            if gm:
                item["total"] = guide_total(gm.group(1))
                item["trainer"] = bool(find_trainer(gm.group(1)))
                guides.append(item)
            if rm:
                bm = re.search(r"^Before:\s*(.+)$", note, re.M)
                item["path"] = rm.group(1).strip() if rm.group(1).strip() not in ("", "-") else None
                item["before"] = bm.group(1).strip() if bm else None
                item["why"] = note.splitlines()[0].strip() if note else ""
                item["name"] = re.sub(r"^Review:\s*", "", content)
                reviews.append(item)
            if gm or rm:
                continue  # listed under To review, not as deadlines
            if pname in bycourse:
                (bycourse[pname] if d else undated).append(item)
            elif d and pname != "Inbox":
                bycourse.setdefault(pname, []).append(item)
        for c in bycourse: bycourse[c].sort(key=lambda x: x["due"] or "9999")
        data = {"courses": bycourse, "undated": undated, "guides": sorted(guides, key=lambda g: g["due"] or "9999"),
                "review": sorted(reviews, key=lambda g: g["due"] or "9999"),
                "health": health(switch), "err": None,
                "today": today.isoformat()}
        _cache["at"], _cache["data"] = time.time(), data
        return data

def health(switch=None):
    out = {"sweep": "unknown", "detail": "", "ok": False}
    if os.path.exists(HB):
        try:
            h = json.load(open(HB))
            when = datetime.datetime.fromisoformat(h["at"])
            age = (datetime.datetime.now(datetime.timezone.utc) - when).total_seconds() / 3600.0
            out["ok"] = age < 26
            out["sweep"] = "healthy" if out["ok"] else "STALE"
            out["detail"] = "last sync %.1fh ago" % age
        except Exception as e:
            out["sweep"], out["detail"] = "unreadable", str(e)
    else:
        out["sweep"], out["detail"] = "never run", "no heartbeat file yet"
    return out

# ------------------------------------------------------------------ markdown

def md(text):
    """Small markdown renderer for what the guides actually use.

    Three things the naive line-by-line version got wrong and that matter here:
    tables rendered as raw pipes, HTML comments leaked into the page, and bold that
    wrapped across two source lines printed literal asterisks. All handled below.
    """
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    # Join wrapped continuation lines back onto their list item so inline markup that
    # spans a line break still closes.
    raw, lines = text.splitlines(), []
    for l in raw:
        if (lines and re.match(r"^\s{2,}\S", l) and lines[-1].strip()
                and re.match(r"^\s*[-*]\s", lines[-1])
                and not re.match(r"^\s*[-*]\s", l) and not l.lstrip().startswith("|")):
            lines[-1] = lines[-1].rstrip() + " " + l.strip()
        else:
            lines.append(l)

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"&lt;sub&gt;(.*?)&lt;/sub&gt;", r"<span class=sub>\1</span>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target=_blank>\1</a>', s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
        return s

    out, in_ul, i = [], False, 0
    def close_ul():
        nonlocal in_ul
        if in_ul: out.append("</ul>"); in_ul = False

    while i < len(lines):
        l = lines[i].rstrip()
        if not l.strip():
            close_ul(); i += 1; continue

        # table: header row, separator row, then body rows
        if l.lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i+1]):
            close_ul()
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            out.append("<table><thead><tr>" +
                       "".join("<th>%s</th>" % inline(c) for c in cells(l)) +
                       "</tr></thead><tbody>")
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                out.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in cells(lines[i])) + "</tr>")
                i += 1
            out.append("</tbody></table>"); continue

        m = re.match(r"^(#{1,4})\s+(.*)$", l)
        if m:
            close_ul()
            out.append("<h%d>%s</h%d>" % (len(m.group(1)), inline(m.group(2)), len(m.group(1))))
            i += 1; continue
        if l.startswith("> "):
            close_ul()
            buf = []
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(lines[i][2:].strip()); i += 1
            out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf))); continue
        m = re.match(r"^\s*[-*]\s+\[( |x)\]\s+(.*)$", l)
        if m:
            if not in_ul: out.append("<ul class=chk>"); in_ul = True
            ck = " checked" if m.group(1) == "x" else ""
            out.append("<li><label><input type=checkbox%s> <span>%s</span></label></li>"
                       % (ck, inline(m.group(2))))
            i += 1; continue
        m = re.match(r"^\s*[-*]\s+(.*)$", l)
        if m:
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append("<li>%s</li>" % inline(m.group(1))); i += 1; continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)$", l)
        if m:
            close_ul(); out.append("<p class=num><b>%s.</b> %s</p>" % (m.group(1), inline(m.group(2))))
            i += 1; continue
        close_ul()
        buf = []
        while i < len(lines):
            cur = lines[i].rstrip()
            if (not cur.strip() or re.match(r"^#{1,4}\s", cur) or cur.startswith("> ")
                    or re.match(r"^\s*[-*]\s", cur) or re.match(r"^\s*\d+\.\s", cur)
                    or cur.lstrip().startswith("|")):
                break
            buf.append(cur.strip()); i += 1
        out.append("<p>%s</p>" % inline(" ".join(buf)))
    close_ul()
    return "\n".join(out)

def find_trainer(slug):
    """Interactive trainers live next to their guide as <slug>-trainer.html."""
    for c in COURSES:
        f = os.path.join(NOTES, c, "Study Guides", slug + "-trainer.html")
        if os.path.exists(f):
            return f
    return None

def guide_total(slug):
    """How many checkboxes a guide has, so the dashboard can show real progress."""
    f = find_guide(slug)
    if not f:
        return 0
    return len(re.findall(r"^\s*[-*]\s+\[[ x]\]", open(f).read(), re.M))

def find_guide(slug):
    for c in COURSES:
        p = os.path.join(NOTES, c, "Study Guides", slug + ".md")
        if os.path.exists(p): return p
    return None

CSS = """
:root{
  /* palette: white + Dark Spruce, Shamrock, Tropical Teal, Turquoise, Cyan Glow */
  --spruce:#26532b; --shamrock:#399e5a; --teal:#5abcb9; --turq:#63e2c6; --cyan:#6ef9f5;
  --azure:var(--spruce); --cerulean:#2E7F7B; --alice:#FFFFFF; --sage:var(--shamrock);
  --room:#FFFFFF; --surface:#F6FBFA; --line:#DCECE8; --line2:#E6F2EF;
  --ink:#163019; --muted:#3F6450; --faint:#7A958A;
  --sage-ink:#2E8249; --soon:var(--spruce); --late:#B8433A;
  --serif:'Bricolage Grotesque',-apple-system,'Segoe UI',sans-serif; --sans:'Bricolage Grotesque',-apple-system,'Segoe UI',sans-serif;
}
*{box-sizing:border-box}
html{background:var(--room);overflow-x:clip}
body{margin:0;background:var(--room);color:var(--ink);font:17px/1.6 var(--sans);-webkit-font-smoothing:antialiased;min-height:100vh}
a{color:var(--azure)}
:focus-visible{outline:2px solid var(--azure);outline-offset:2px;border-radius:4px}
.wrap{max-width:1280px;margin:0 auto;padding:44px 40px 120px}

/* cover: full-bleed photo like a Notion page banner */
.cover{position:relative;height:380px;overflow:hidden;margin:-44px calc(50% - 50vw) 0;
  background:#CFE9E3}
.cover::before{content:"";position:absolute;inset:0;background:url(/static/yosemite.jpg) center 52%/cover no-repeat;
  animation:coverin 1.6s cubic-bezier(.2,.7,.2,1) both}
@keyframes coverin{from{opacity:0;transform:scale(1.04)}to{opacity:1;transform:none}}
.cover::after{content:"";position:absolute;inset:0;
  background:linear-gradient(to bottom,rgba(22,48,25,.26) 0%,rgba(22,48,25,0) 22%,rgba(255,255,255,0) 48%,
    rgba(255,255,255,.18) 62%,rgba(255,255,255,.5) 76%,rgba(255,255,255,.84) 90%,var(--alice) 100%)}
.brandchip{position:absolute;top:22px;left:max(40px,calc(50vw - 600px));z-index:1;font-size:14px !important;
  font:600 13px/1 var(--sans);letter-spacing:.01em;color:var(--azure);padding:8px 12px;border-radius:999px;
  background:rgba(255,255,255,.82);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
.bar{position:relative;margin-top:14px;margin-bottom:44px;align-items:flex-end}
.summary{margin:12px 0 0;font-size:21px;color:var(--muted);max-width:40ch}
.credit{margin-top:88px;padding-top:18px;border-top:1px solid var(--line);font-size:13.5px;color:var(--faint)}
.credit a{color:var(--muted)}

/* header: the date is the headline */
.bar{display:flex;justify-content:space-between;align-items:flex-end;gap:18px;margin-bottom:30px;flex-wrap:wrap}
.brand{font-size:19px;font-weight:500;color:var(--cerulean);margin-bottom:10px}
h1{font:650 68px/1 var(--serif);font-variation-settings:'opsz' 96;letter-spacing:-.025em;margin:0;color:var(--azure)}
.sub{color:var(--faint);font-size:12px}
.pill{display:inline-flex;align-items:center;gap:9px;font-size:14.5px;color:var(--muted)}
.pill i{width:7px;height:7px;border-radius:50%;background:var(--faint)}
.pill.ok i{background:var(--sage);box-shadow:0 0 0 3px rgba(57,158,90,.18)}
.pill.bad{color:var(--late)}.pill.bad i{background:var(--late)}

/* Today: the one solid block on the page */
.card{padding:0}
.card h2{font:650 26px/1.2 var(--serif);font-variation-settings:'opsz' 48;letter-spacing:-.015em;margin:0 0 10px;color:var(--azure)}
.hero{background:var(--azure);color:#fff;border-radius:18px;padding:30px 36px 18px;margin-bottom:64px;
  box-shadow:0 22px 50px -30px rgba(38,83,43,.5)}
.hero h2{color:#fff;font-size:30px;margin-bottom:8px}
.todayrow{display:flex;gap:18px;align-items:center;padding:18px 0;border-top:1px solid rgba(255,255,255,.18)}
.todayrow:first-of-type{border-top:0}
.todayrow .nm{flex:1;min-width:0}
.heroname{font:550 23px/1.3 var(--serif);color:#fff}
.hero .cn{color:#A9E8DA;font-size:15.5px;margin-top:2px}
.hero .why{display:block;color:#A9E8DA}
.herowhen{font-size:16px;font-weight:600;color:#6ef9f5;white-space:nowrap}
.hero .empty{color:#A9E8DA}
.hero .dot{width:11px;height:11px;box-shadow:0 0 0 2px rgba(255,255,255,.85)}

/* the two columns sit on the page, not in boxes */
.grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:72px}
.grid > *{min-width:0}
@media(max-width:780px){.grid{grid-template-columns:minmax(0,1fr);gap:36px}.rv{flex-wrap:wrap}.todayrow{flex-wrap:wrap;row-gap:4px}.todayrow .nm{flex-basis:calc(100% - 40px)}.todayrow .herowhen{padding-left:29px}.wrap{padding:28px 16px 72px}h1{font-size:42px}.summary{font-size:18px}.cover{height:230px}.bar{margin-top:8px}.wrap{padding:28px 18px 80px}.hero{padding:22px 20px 10px}.heroname{font-size:19px}.hero{padding:18px 18px 8px}}
.grid .card h2,.wrap > .card h2{padding-bottom:14px;border-bottom:2px solid var(--azure);margin-bottom:2px}
.row,.rv{display:flex;gap:14px;align-items:baseline;padding:16px 0;border-bottom:1px solid var(--line)}
.row:last-child,.rv:last-child{border-bottom:0}
.row .nm,.rv .nm{flex:1;min-width:0}
.row .nm{font-size:18px}
.dot{width:10px;height:10px;border-radius:50%;flex:none;transform:translateY(-1px)}
.when{font-size:15px;color:var(--muted);white-space:nowrap;font-variant-numeric:tabular-nums}
.when.soon{color:var(--soon);font-weight:600}.when.over{color:var(--late);font-weight:600}
.cn{font-size:15px;color:var(--faint);margin-top:2px}
.empty{color:var(--faint);font-size:16px;padding:16px 0}

/* To review */
.rv{align-items:flex-start}
.rv .dot{transform:translateY(9px)}
.rv .nm b{font-weight:600;font-size:18px;color:var(--ink)}
.rv .cn{margin-top:2px;color:var(--muted)}
.rv .bef{display:block;color:var(--faint);margin-top:1px}
.rv .prog{color:var(--sage-ink)}
.rvr{display:flex;flex-direction:column;align-items:flex-end;gap:7px;padding-top:2px}
.rvbtn{display:flex;gap:6px}
.rvbtn a.open,.rvbtn button{font:500 14.5px/1 var(--sans);height:34px;padding:0 15px;border-radius:8px;cursor:pointer;
  display:inline-flex;align-items:center;text-decoration:none;border:1px solid var(--cerulean);background:#fff;color:var(--azure);
  transition:background .15s,border-color .15s,color .15s}
.rvbtn a.open:hover{background:var(--azure);border-color:var(--azure);color:#fff}
.rvbtn button.done{width:36px;padding:0;justify-content:center;border-color:var(--sage);background:#fff;color:var(--sage-ink)}
.rvbtn button.done:hover{background:var(--sage);color:#fff}
.rvbtn button:disabled{opacity:.5;cursor:wait}
.rv{transition:opacity .3s}
details.more summary{cursor:pointer;color:var(--azure);font-size:16px;font-weight:500;padding:12px 0 4px;list-style:none}
details.more summary::-webkit-details-marker{display:none}
details.more summary::before{content:"Show ";}
details.more[open] summary{color:var(--faint)}

/* lower sections: quieter */
.wrap > .card.hero{margin-top:0}
.wrap > .card.hero h2{border-bottom:0;padding-bottom:0}
.wrap > .card{margin-top:64px}
.wrap > .card .empty:first-of-type{font-style:normal;font-family:var(--sans);font-size:15px;padding:8px 0 4px}

/* guide pages */
article{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:16px 48px 48px;max-width:880px;font-size:17.5px}
article h1{font:650 40px/1.1 var(--serif);margin:24px 0 8px;color:var(--azure)}
article h2{font:650 24px/1.25 var(--serif);color:var(--azure);margin:30px 0 10px;border-top:1px solid var(--line);padding-top:22px}
article h3,article h4{font:600 15.5px/1.3 var(--serif);margin:20px 0 6px;color:var(--ink)}
article p,article li{line-height:1.65}
article blockquote{margin:16px 0;padding:12px 16px;background:#EEF8F6;border-left:3px solid var(--cerulean);
  color:var(--ink);font-size:14px;border-radius:0 8px 8px 0}
ul.chk{list-style:none;padding:0;margin:10px 0}
ul.chk li{padding:5px 0}
ul.chk label{display:flex;gap:10px;align-items:flex-start;cursor:pointer}
ul.chk input{margin-top:5px;accent-color:var(--sage);flex:none}
ul.chk input:checked + span{opacity:.45;text-decoration:line-through}
code{background:#E6F4F1;color:var(--ink);padding:1px 6px;border-radius:5px;font-size:12.5px}
article table{border-collapse:collapse;width:100%;margin:18px 0;font-size:15.5px;display:block;overflow-x:auto}
article th{text-align:left;padding:8px 12px;border-bottom:2px solid var(--cerulean);color:var(--muted);font-weight:600;font-size:12.5px;white-space:nowrap}
article td{padding:8px 12px;border-bottom:1px solid var(--line2);vertical-align:top}
article tr:last-child td{border-bottom:0}
p.num{margin:7px 0}
p.num b{color:var(--muted);margin-right:4px}
.back{display:inline-block;margin:0 0 20px;color:var(--muted);text-decoration:none;font-size:16px}
.back:hover{color:var(--azure)}
a.back.tr{float:right;color:var(--azure)}
.trainerbadge{background:#DDF3EE;color:var(--azure);border-radius:5px;padding:1px 7px;font-size:11px;margin-left:6px}
.bar2{height:3px;background:var(--line);border-radius:3px;margin:9px 0 5px;overflow:hidden}
.bar2 i{display:block;height:100%;width:0;background:var(--sage);border-radius:3px;transition:width .3s}
@media(max-width:780px){.rvr{flex-direction:row;align-items:center;width:100%;justify-content:space-between;padding:4px 0 0 20px}}
@media (prefers-reduced-motion: reduce){*{transition:none!important;animation:none!important}}
"""

PAGE = """<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>%(title)s</title><link rel=preconnect href=https://fonts.googleapis.com><link rel=preconnect href=https://fonts.gstatic.com crossorigin><link href='https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..700&display=swap' rel=stylesheet><link rel=icon href=/favicon.ico type=image/svg+xml><style>%(css)s</style><div class=wrap>%(body)s</div>
<script>
(function(){document.querySelectorAll('[data-slug]').forEach(function(a){
  var tot=+a.dataset.total||0,n=0;
  try{for(var i=0;i<tot;i++){if(localStorage.getItem('sd:/guide/'+a.dataset.slug+':'+i))n++;}}catch(e){}
  var bar=a.querySelector('.bar2 i'),lab=a.querySelector('.prog');
  if(tot&&lab){if(bar)bar.style.width=(100*n/tot)+'%%';lab.textContent=n+' of '+tot+' checked';}
  else if(lab){lab.textContent='';}
});})();
document.addEventListener('click',e=>{const b=e.target.closest('button.done');if(!b)return;
 b.disabled=true;b.textContent='...';
 fetch('/api/done/'+b.dataset.id,{method:'POST'}).then(r=>{if(r.ok){b.closest('.rv').style.opacity=.3;setTimeout(()=>location.reload(),350);}
  else{b.disabled=false;b.textContent='failed, retry';}}).catch(()=>{b.disabled=false;b.textContent='failed, retry';});});
document.addEventListener('change',e=>{if(e.target.type!=='checkbox')return;
 const k='sd:'+location.pathname+':'+[...document.querySelectorAll('input[type=checkbox]')].indexOf(e.target);
 try{localStorage.setItem(k,e.target.checked?'1':'')}catch(_){}});
try{document.querySelectorAll('input[type=checkbox]').forEach((b,i)=>{
 if(localStorage.getItem('sd:'+location.pathname+':'+i))b.checked=true;
 b.dispatchEvent(new Event('change',{bubbles:false}))})}catch(_){}
</script>"""

# ------------------------------------------------------------------ live Canvas feed
# Second sync: Canvas straight to this page, every 2 minutes, in a background thread.
# (The first sync, canvas-sweep, still runs 4x a day and feeds Todoist and the phone.)
# It loads canvas-sweep itself so both syncs use the same Canvas client and the same rules
# about what counts as a task. It never writes to Todoist; it only changes what the page shows.
import importlib.machinery, importlib.util

LIVE_EVERY = 120
_live = {"at": 0, "data": {}, "err": None}

def _load_sweep():
    path = os.path.expanduser("~/bin/canvas-sweep")
    loader = importlib.machinery.SourceFileLoader("canvas_sweep", path)
    spec = importlib.util.spec_from_loader("canvas_sweep", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

def live_refresh():
    sw = _load_sweep()
    out = {}
    for cid, (project, diff) in sw.COURSES.items():
        items = sw.canvas("/api/v1/courses/%s/assignments?include[]=submission&per_page=100" % cid)
        best = {}
        for a in items:                      # same duplicate-column collapse as the sweep
            k = sw.norm(a["name"])
            cur = best.get(k)
            if cur is None or (a.get("due_at") and not cur.get("due_at")):
                best[k] = a
        for a in best.values():
            sub = a.get("submission") or {}
            due = a.get("due_at")
            dd = None
            if due:
                dd = datetime.datetime.strptime(due, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            est = sw.estimate(a.get("points_possible"), diff)
            out[str(a["id"])] = {
                "name": a["name"], "course": project, "due_iso": due, "due_dt": dd,
                "due": dd.astimezone(CAMPUS_TZ).date().isoformat() if dd else None,
                "submitted": bool(sub.get("submitted_at")) or sub.get("score") is not None,
                "submittable": bool(set(a.get("submission_types") or []) & sw.SUBMITTABLE),
                "url": a.get("html_url", ""), "est": est}
    return out

_kick = threading.Event()

def live_loop():
    # Paced by the wall clock, not time.sleep(120): sleep's clock stops while the Mac is
    # asleep, so after opening the lid the page sat on pre-sleep data ("updated 99m ago").
    while True:
        tried = time.time()
        try:
            data = live_refresh()
            with _lock:
                _live["data"], _live["at"], _live["err"] = data, time.time(), None
        except Exception as e:
            with _lock:
                _live["err"] = str(e)[:120]
        _kick.clear()
        while time.time() - tried < LIVE_EVERY and not _kick.wait(5):
            pass

def ensure_fresh(wait=15):
    """A page load with stale Canvas data pulls fresh data first, so it never renders old."""
    if _live["at"] and time.time() - _live["at"] < LIVE_EVERY:
        return
    before = _live["at"]
    _kick.set()
    end = time.time() + wait
    while time.time() < end and _live["at"] == before:
        time.sleep(0.25)

def apply_live(items, unsched, today):
    """Overlay live Canvas on the Todoist view: hide what is already submitted, use Canvas's
    current due date, and add assignments Canvas has that the 4x-daily sync hasn't made yet."""
    live = _live["data"]
    if not live:
        return items, unsched
    done_cv = set()
    for t in recent_done():
        m = re.search(r"\[canvas:(\d+)\]", t.get("description") or "")
        if m: done_cv.add(m.group(1))
    known, keep_items, keep_uns = set(), [], []
    for bucket, keep in ((items, keep_items), (unsched, keep_uns)):
        for i in bucket:
            cv = i.get("canvas")
            if cv: known.add(cv)
            L = live.get(cv) if cv else None
            if L:
                if L["submitted"]:
                    continue
                if L["due"] and L["due"] != i.get("due"):
                    i["due"] = L["due"]
                    i["days"] = (datetime.date.fromisoformat(L["due"]) - today).days
            keep.append(i)
    now = datetime.datetime.now(datetime.timezone.utc)
    for cv, L in live.items():
        if cv in known or cv in done_cv or L["submitted"]:
            continue
        if not L["due"] and not L["submittable"]:
            continue
        if L["due_dt"] and L["due_dt"] < now - datetime.timedelta(days=3):
            continue
        note = L["url"] + (("\nRough estimate: %sh" % L["est"]) if L["est"] else "")
        it = {"id": "cv" + cv, "name": L["name"], "course": L["course"], "canvas": cv,
              "due": L["due"], "guide": None, "note": note, "kind": "deadline",
              "days": (datetime.date.fromisoformat(L["due"]) - today).days if L["due"] else None}
        (keep_items if L["due"] else keep_uns).append(it)
    return keep_items, keep_uns

def close_live_only(aid):
    """Ticking an assignment the 4x-daily sync hasn't copied to Todoist yet: create it the
    way canvas-sweep would, stamped with its Canvas id, then close it. The sweep then sees
    it as done and never recreates it."""
    L = _live["data"].get(aid)
    if not L:
        raise ValueError("unknown Canvas assignment %s" % aid)
    projects = {p["name"]: p["id"] for p in td_list("/projects")}
    body = {"content": L["name"], "project_id": projects.get(L["course"]),
            "description": "[canvas:%s][cdue:%s]\n%s" % (aid, L["due_iso"] or "", L["url"]), "priority": 3}
    if L["due_iso"]: body["due_datetime"] = L["due_iso"]
    r = urllib.request.Request(TBASE + "/tasks", data=json.dumps(body).encode(), method="POST",
                               headers={"Authorization": "Bearer " + TTOK, "Content-Type": "application/json"})
    tid = json.loads(urllib.request.urlopen(r, timeout=20).read())["id"]
    r = urllib.request.Request(TBASE + "/tasks/%s/close" % tid, data=b"", method="POST",
                               headers={"Authorization": "Bearer " + TTOK})
    urllib.request.urlopen(r, timeout=20).read()


# ------------------------------------------------------------------ dashboard v3
# Presentation only. Reads the same state() the rest of the desk uses; the only extra data
# is a read-only lookup of recently completed Todoist tasks for the weekly progress bar and
# the streak. Nothing here writes to Todoist except the existing /api/done route.

_done_cache = {"at": 0, "data": []}

def recent_done():
    """Completed tasks over the last 35 days (read-only), cached for 45s like state()."""
    with _lock:
        if time.time() - _done_cache["at"] < 45:
            return _done_cache["data"]
    now = datetime.datetime.now(datetime.timezone.utc)
    since = (now - datetime.timedelta(days=35)).strftime("%Y-%m-%dT%H:%M:%SZ")
    until = (now + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out, cur = [], None
    try:
        while True:
            url = TBASE + "/tasks/completed/by_completion_date?since=%s&until=%s&limit=200" % (since, until)
            if cur: url += "&cursor=" + cur
            r = urllib.request.Request(url, headers={"Authorization": "Bearer " + TTOK})
            d = json.loads(urllib.request.urlopen(r, timeout=20).read().decode() or "{}")
            out.extend(d.get("items", []))
            cur = d.get("next_cursor")
            if not cur: break
    except Exception:
        return _done_cache["data"]
    out = [t for t in out if not (t.get("content") or "").startswith("Canvas sync alive")]
    with _lock:
        _done_cache["at"], _done_cache["data"] = time.time(), out
    return out


def est_min(name, note, kind):
    """Minutes of work. The Canvas sweep writes 'Rough estimate: 1.5h' where it can; otherwise
    guess by kind. Guesses are shown with a ~ like every estimate."""
    m = re.search(r"Rough estimate:\s*([\d.]+)\s*h", note or "")
    if m: return int(round(float(m.group(1)) * 60))
    m = re.search(r"~\s*(\d+)\s*min", note or "")
    if m: return int(m.group(1))
    n = (name or "").lower()
    if kind == "review": return 25
    if kind == "guide": return 30
    if n.startswith("daily hw"): return 35
    if "office hours" in n: return 30
    if any(w in n for w in ("quiz", "exam", "test")): return 60
    return 45


def fmt_min(m):
    if m <= 0: return "0m"
    h, mm = divmod(int(m), 60)
    return ("%dh %02dm" % (h, mm)) if h and mm else (("%dh" % h) if h else "%dm" % mm)


def hw_template(i):
    """DSC 215 homework (H6, H7...) opens the Rmd template in HW<n>/, if one exists."""
    m = re.match(r"^H(\d+)$", (i.get("name") or "").strip())
    if i.get("course") != "DSC 215" or not m: return None
    rel = "DSC 215/HW%s/m215hwk%s.Rmd" % (m.group(1), m.group(1))
    return rel if os.path.isfile(os.path.join(NOTES, rel)) else ""


def open_url(i):
    """"" means no Open button at all."""
    if i.get("guide"): return "/guide/%s" % i["guide"]
    hw = hw_template(i)
    if hw is not None: return ("/open/" + urllib.parse.quote(hw)) if hw else ""
    if i.get("path"): return "/open/" + urllib.parse.quote(i["path"])
    note = i.get("note") or ""
    m = re.search(r"F&M Notes/([^\n]+?\.(?:pdf|md|html))", note)
    if m: return "/open/" + urllib.parse.quote(m.group(1).strip())
    m = re.search(r"https?://[^\s)\]]+", note)
    if m and "localhost:7474" not in m.group(0): return m.group(0)
    return "https://app.todoist.com/app/task/%s" % i["id"]


def due_words(d):
    if d is None: return "No date"
    if d < 0: return "%d day%s late" % (-d, "" if d == -1 else "s")
    if d == 0: return "Due today"
    if d == 1: return "Due tomorrow"
    return "Due in %d days" % d


def dash():
    ensure_fresh()
    s = state()
    h = s["health"]
    today = datetime.date.fromisoformat(s["today"])
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)

    # ---- gather every open item once, tagged with a kind
    items = []
    for c, lst in s["courses"].items():
        for i in lst: items.append(dict(i, kind="deadline"))
    items, unsched_live = apply_live(items, [dict(i) for i in s["undated"]], today)
    for g in s.get("review", []): items.append(dict(g, kind="review"))
    for g in s["guides"]:
        if g.get("guide"): items.append(dict(g, kind="guide"))
    for i in items:
        i["est"] = est_min(i["name"], i.get("note"), i["kind"])
        i["url"] = open_url(i)
        i["title"] = i["name"].replace("Study guide ready: ", "")
        dd = datetime.date.fromisoformat(i["due"]) if i["due"] else None
        i["thisweek"] = bool(dd and monday <= dd <= sunday)

    deadlines = sorted([i for i in items if i["kind"] == "deadline"], key=lambda x: x["due"] or "9999")
    overdue = [i for i in deadlines if i["days"] is not None and i["days"] < 0]
    todays = [i for i in deadlines if i["days"] is not None and 0 <= i["days"] <= 1]
    rev = sorted([i for i in items if i["kind"] != "deadline"], key=lambda x: x["due"] or "9999")
    todays += [i for i in rev if i["days"] is not None and i["days"] <= 1]
    todays = todays[:3]
    tids = {i["id"] for i in todays}
    nextup = [i for i in deadlines if i["days"] is not None and i["days"] >= 2][:6]
    unsched = unsched_live
    for i in unsched:
        i.update(kind="deadline", est=est_min(i["name"], i.get("note"), "deadline"),
                 url=open_url(i), title=i["name"], thisweek=False)

    # the next task: a recent overdue first, then the top of Today, then the next deadline
    recent_over = [i for i in overdue if i["days"] >= -7]
    nxt = (recent_over or todays or nextup or [None])[0]

    # ---- week numbers
    done = recent_done()
    def done_day(t):
        try:
            return datetime.datetime.fromisoformat(t["completed_at"].replace("Z", "+00:00")).astimezone().date()
        except Exception:
            return None
    done_week = [t for t in done if (done_day(t) or monday) >= monday]
    open_week = [i for i in items if i["thisweek"]]
    total = len(done_week) + len(open_week)
    pct = int(round(100.0 * len(done_week) / total)) if total else 0
    min_done = sum(est_min(t.get("content"), t.get("description"),
                           "review" if (t.get("content") or "").startswith("Review:") else "deadline")
                   for t in done_week)
    min_left = sum(i["est"] for i in open_week)
    min_today = sum(i["est"] for i in todays)
    days_done = {done_day(t) for t in done}
    streak, cur = 0, today if today in days_done else today - datetime.timedelta(days=1)
    while cur in days_done:
        streak += 1; cur -= datetime.timedelta(days=1)
    n_week_left = len([i for i in open_week if i["days"] is None or i["days"] >= 0])

    # ---- render helpers
    def when_cls(d):
        return "over" if d is not None and d < 0 else ("soon" if d is not None and d <= 1 else "")

    def task(i, bucket, big=False):
        d = i["days"]
        meta = [html.escape(i["course"])] if i.get("course") else []
        meta.append("~" + fmt_min(i["est"]))
        if i["kind"] != "deadline": meta.append("Review")
        why = ('<div class=twhy>%s</div>' % html.escape(i["why"])) if i.get("why") else ""
        return ('<div class="task%s" data-id="%s" data-bucket="%s" data-est="%d" data-week="%d">'
                '<button class=check aria-label="Mark done" data-id="%s"><svg viewBox="0 0 24 24"><path d="M6 12.5l4 4 8-9"/></svg></button>'
                '<span class=cdot style="background:%s"></span>'
                '<div class=tbody><div class=ttitle>%s</div><div class=tmeta>%s</div>%s</div>'
                '<div class=tside><span class="tdue %s">%s</span>'
                '%s</div></div>'
                % (" big" if big else "", html.escape(i["id"]), bucket, i["est"], 1 if i["thisweek"] else 0,
                   html.escape(i["id"]), COLOR.get(i.get("course"), "#9AA8B8"),
                   html.escape(i["title"]), " &middot; ".join(meta), why,
                   when_cls(d), due_words(d),
                   ('<a class=openbtn href="%s" target=_blank rel=noopener>Open <span aria-hidden=true>&rarr;</span></a>'
                    % html.escape(i["url"], quote=True)) if i["url"] else ""))

    hr = datetime.datetime.now().hour
    greet = "Good morning" if hr < 12 else ("Good afternoon" if hr < 18 else "Good evening")
    num = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]
    say = lambda n: num[n] if n < len(num) else str(n)
    summary = "%s thing%s today, %s more this week. About %s of work today." % (
        say(len(todays)), "" if len(todays) == 1 else "s", say(max(n_week_left - len(todays), 0)).lower(),
        fmt_min(min_today))

    age = time.time() - _live["at"] if _live["at"] else None
    live_ok = age is not None and age < 3 * LIVE_EVERY and not _live["err"]
    if age is None:
        lw = "starting up" if not _live["err"] else "unreachable"
    else:
        lw = ("updated %ds ago" % age) if age < 90 else ("updated %dm ago" % (age // 60))
    hp = ('<span class="pill %s"><i></i>Canvas to this page: live, %s</span>'
          '<span class="pill %s"><i></i>Canvas to Todoist: %s, %s</span>'
          % ("ok" if live_ok else "bad", lw, "ok" if h["ok"] else "bad", h["sweep"], h["detail"]))
    if s.get("err"):
        hp += ' <span class="pill bad"><i></i>Todoist unreachable: %s</span>' % html.escape(s["err"][:60])

    b = []
    b.append('<div class=cover role=img aria-label="Tunnel View, Yosemite Valley"><span class=brandchip>Study Desk</span></div>')
    b.append('<header class=hdr><div class=greet>%s, Teerth</div><h1>%s</h1><p class=summary>%s</p>%s</header>'
             % (greet, today.strftime("%A, ") + str(today.day) + today.strftime(" %B"), html.escape(summary), hp))

    # stats row
    b.append('<section class=stats>'
             '<div class=stat><div class=snum id=s-today>%d</div><div class=slab>Today</div></div>'
             '<div class=stat><div class=snum id=s-week>%d</div><div class=slab>This week</div></div>'
             '<div class="stat%s"><div class=snum id=s-over>%d</div><div class=slab>Overdue</div></div>'
             '<div class="stat prog"><div class=pnum><span id=s-pct>%d</span>%%</div><div class=slab>Weekly progress</div>'
             '<div class=pbar><i id=s-bar style="width:%d%%"></i></div>'
             '<div class=psub><span id=s-done>%d</span> of <span id=s-total>%d</span> done this week</div></div>'
             '</section>'
             % (len(todays), n_week_left, " alarm" if overdue else "", len(overdue), pct, pct, len(done_week), total))

    # next task
    if nxt:
        b.append('<section class=focus><div class=flabel>Your next task</div>%s</section>' % task(nxt, "next", big=True))

    # today
    b.append('<section class=sec><h2>Today <span class=hsub>~%s</span></h2>' % fmt_min(min_today))
    if not todays: b.append('<p class=empty>Nothing due today or tomorrow. Pick something from To review.</p>')
    for i in todays:
        if nxt and i["id"] == nxt["id"] and len(todays) > 1: continue
        b.append(task(i, "today"))
    b.append('</section>')

    # next up + next 7 days strip
    b.append('<div class=two><section class=sec><h2>Next up</h2>')
    if not nextup: b.append('<p class=empty>Nothing else dated in the next two weeks.</p>')
    for i in nextup: b.append(task(i, "next2"))
    b.append('</section><section class=sec><h2>Next 7 days</h2><div class=week>')
    loads = []
    for k in range(7):
        day = today + datetime.timedelta(days=k)
        di = [i for i in items if i["due"] == day.isoformat()]
        loads.append((day, di, sum(i["est"] for i in di)))
    mx = max([m for _, _, m in loads] + [60])
    for day, di, m in loads:
        lab = "Today" if day == today else ("Tomorrow" if day == today + datetime.timedelta(days=1) else day.strftime("%a %-d"))
        b.append('<div class="wday%s"><div class=wlab>%s</div><div class=wtrack><i style="width:%d%%"></i></div>'
                 '<div class=wnum>%s</div></div>'
                 % (" heavy" if m >= 120 else "", lab, int(100 * m / mx),
                    ("%d task%s, ~%s" % (len(di), "" if len(di) == 1 else "s", fmt_min(m))) if di else "Free"))
    b.append('</div><div class=wtot>%d open this week, about %s left</div></section></div>'
             % (len(open_week), fmt_min(min_left)))

    # overdue
    if overdue:
        b.append('<section class="sec overdue"><h2>Overdue <span class=hsub>%d</span></h2>' % len(overdue))
        for i in overdue:
            if nxt and i["id"] == nxt["id"]: continue
            b.append(task(i, "over"))
        b.append('</section>')

    # to review
    b.append('<section class="sec review"><h2>To review</h2><p class=secnote>Things built for you to learn from, not deadlines.</p>')
    if not rev: b.append('<p class=empty>Nothing waiting.</p>')
    for i in rev:
        if i["id"] in tids: continue
        b.append(task(i, "review"))
    b.append('</section>')

    # unscheduled
    if unsched:
        b.append('<section class="sec quiet"><h2>Unscheduled</h2><p class=secnote>No date on Canvas yet. Confirm in class.</p><div class=chips>')
        for i in unsched:
            b.append('<a class=chip href="%s" target=_blank rel=noopener><span class=cdot style="background:%s"></span>%s <span>%s</span></a>'
                     % (html.escape(i["url"], quote=True), COLOR.get(i["course"], "#9AA8B8"),
                        html.escape(i["name"]), html.escape(i["course"])))
        b.append('</div></section>')

    # your week
    b.append('<section class="sec yourweek"><h2>Your week</h2><div class=yw>'
             '<div><div class=ybig><span id=y-done>%d</span> / <span id=y-total>%d</span></div><div class=slab>tasks done</div></div>'
             '<div><div class=ybig id=y-min>%s</div><div class=slab>of work done</div></div>'
             '<div><div class=ybig id=y-left>%s</div><div class=slab>still to go</div></div>'
             '<div><div class=ybig>%d day%s</div><div class=slab>streak</div></div></div>'
             '<div class="pbar wide"><i id=y-bar style="width:%d%%"></i></div></section>'
             % (len(done_week), total, fmt_min(min_done), fmt_min(min_left), streak, "" if streak == 1 else "s", pct))

    b.append('<footer class=credit>Cover: Tunnel View, Yosemite Valley. Photo by '
             '<a href="https://commons.wikimedia.org/wiki/File:Tunnel_View,_Yosemite_Valley,_Yosemite_NP_-_Diliff.jpg" '
             'target=_blank>Diliff</a>, CC BY-SA 3.0.</footer>')
    b.append('<div id=toast role=status aria-live=polite></div><canvas id=fx></canvas>')
    b.append('<script>window.SD=%s;</script><script>%s</script>'
             % (json.dumps({"done": len(done_week), "total": total, "minDone": min_done, "minLeft": min_left}), DASH_JS))
    return PAGE % {"title": "Study Desk", "css": CSS + DASH_CSS, "body": "\n".join(b)}


DASH_JS = r"""
(function(){
const $=id=>document.getElementById(id);
const fmt=m=>{m=Math.max(0,Math.round(m));const h=Math.floor(m/60),r=m%60;return h&&r?h+'h '+String(r).padStart(2,'0')+'m':h?h+'h':r+'m';};
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
function tween(el,from,to,ms,f){if(!el)return;if(reduce){el.textContent=f?f(to):to;return;}
  const t0=performance.now();(function step(t){const k=Math.min(1,(t-t0)/ms),e=1-Math.pow(1-k,3);
  const v=from+(to-from)*e;el.textContent=f?f(v):Math.round(v);if(k<1)requestAnimationFrame(step);})(t0);}
function bump(id,delta){const el=$(id);if(!el)return;const v=+el.textContent||0;tween(el,v,Math.max(0,v+delta),500);}
let toastT;function toast(msg,big){const t=$('toast');t.textContent=msg;t.className=big?'show big':'show';
  clearTimeout(toastT);toastT=setTimeout(()=>t.className='',big?3200:1800);}
// confetti, drawn in the page palette
const cv=$('fx'),cx=cv.getContext('2d');let parts=[],running=false;
const COLS=['#26532b','#399e5a','#5abcb9','#63e2c6','#6ef9f5'];
function size(){cv.width=innerWidth*devicePixelRatio;cv.height=innerHeight*devicePixelRatio;}size();addEventListener('resize',size);
function burst(x,y,n,spread){if(reduce)return;for(let i=0;i<n;i++){const a=-Math.PI/2+(Math.random()-.5)*spread,v=4+Math.random()*7;
  parts.push({x,y,vx:Math.cos(a)*v,vy:Math.sin(a)*v,r:3+Math.random()*4,c:COLS[i%COLS.length],rot:Math.random()*6,vr:(Math.random()-.5)*.3,life:0,max:55+Math.random()*35});}
  if(!running){running=true;requestAnimationFrame(tick);}}
function tick(){const d=devicePixelRatio;cx.clearRect(0,0,cv.width,cv.height);
  parts=parts.filter(p=>p.life<p.max);for(const p of parts){p.life++;p.vy+=.22;p.vx*=.985;p.x+=p.vx;p.y+=p.vy;p.rot+=p.vr;
  cx.save();cx.globalAlpha=1-p.life/p.max;cx.translate(p.x*d,p.y*d);cx.rotate(p.rot);cx.fillStyle=p.c;cx.fillRect(-p.r*d,-p.r*d/2,p.r*2*d,p.r*d);cx.restore();}
  if(parts.length)requestAnimationFrame(tick);else{running=false;cx.clearRect(0,0,cv.width,cv.height);}}
function rain(){if(reduce)return;for(let k=0;k<6;k++)setTimeout(()=>burst(innerWidth*(.1+.16*k),innerHeight*.35,60,1.6),k*120);}

document.addEventListener('click',e=>{
  const b=e.target.closest('button.check');if(!b||b.disabled)return;
  const card=b.closest('.task');b.disabled=true;card.classList.add('doing');
  fetch('/api/done/'+b.dataset.id,{method:'POST'}).then(r=>{if(!r.ok)throw 0;
    const before=SD.total?Math.round(100*SD.done/SD.total):0;
    card.classList.remove('doing');card.classList.add('done');
    const rc=b.getBoundingClientRect();burst(rc.left+rc.width/2,rc.top+rc.height/2,34,2.4);
    const est=+card.dataset.est||0,wk=card.dataset.week==='1',bk=card.dataset.bucket;
    SD.done+=1;if(!wk)SD.total+=1;SD.minDone+=est;if(wk)SD.minLeft-=est;
    const pct=SD.total?Math.round(100*SD.done/SD.total):0;
    tween($('s-pct'),before,pct,700);tween($('y-min'),SD.minDone-est,SD.minDone,700,fmt);tween($('y-left'),SD.minLeft+(wk?est:0),SD.minLeft,700,fmt);
    ['s-done','y-done'].forEach(id=>bump(id,1));if(!wk)['s-total','y-total'].forEach(id=>bump(id,1));
    $('s-bar').style.width=pct+'%';$('y-bar').style.width=pct+'%';
    if(bk==='today'||bk==='next')bump('s-today',-1);
    if(bk==='over')bump('s-over',-1);
    if(wk&&bk!=='over')bump('s-week',-1);
    const hit=m=>before<m&&pct>=m;
    if(hit(100)){rain();toast('Week complete. '+SD.done+' of '+SD.total+' done.',true);}
    else if(hit(75)){burst(innerWidth/2,innerHeight*.3,90,2.8);toast("Almost done. You're past 75%.");}
    else if(hit(50)){burst(innerWidth/2,innerHeight*.3,70,2.6);toast('Halfway there.');}
    else if(hit(25)){burst(innerWidth/2,innerHeight*.3,50,2.4);toast('A quarter of the week, done.');}
    else toast(['Nice. One down.','Done.','Good. Next one.','Crossed off.'][SD.done%4]);
    setTimeout(()=>{card.classList.add('gone');},900);
    setTimeout(()=>{card.remove();if(bk==='next')location.reload();},1400);
  }).catch(()=>{b.disabled=false;card.classList.remove('doing');toast('Could not reach Todoist. Try again.');});
});
// keep a tab that's left open current: refresh quietly every 10 minutes, and when you come
// back to the tab after 5+ minutes away. Never mid-celebration.
let loaded=Date.now(),hidAt=0;
const fresh=()=>{if(document.querySelector('.task.doing,.task.done')||document.getElementById('toast').className)return;location.reload();};
setInterval(()=>{if(document.visibilityState==='visible')fresh();},180000);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')hidAt=Date.now();
  else if(hidAt&&Date.now()-hidAt>300000)fresh();});
})();
"""

DASH_CSS = """
.hdr{margin:18px 0 40px}
.greet{font-size:24px;font-weight:500;color:var(--cerulean);margin-bottom:6px}
.hdr h1{font:700 84px/0.98 var(--serif);font-variation-settings:'opsz' 96;letter-spacing:-.035em;color:var(--azure);margin:0}
.hdr .pill{margin-right:22px}
.hdr .summary{font-size:22px;color:var(--muted);margin:16px 0 14px;max-width:none}

.stats{display:grid;grid-template-columns:1fr 1fr 1fr 1.9fr;gap:18px;margin-bottom:56px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:22px 24px 20px}
.snum,.pnum{font:700 64px/1 var(--serif);font-variation-settings:'opsz' 96;letter-spacing:-.03em;color:var(--azure);font-variant-numeric:tabular-nums}
.slab{font-size:17px;font-weight:600;color:var(--muted);margin-top:8px}
.stat.alarm{background:#FBEFEE;border-color:#EDCBC7}.stat.alarm .snum{color:var(--late)}
.stat.prog .pnum{color:var(--sage-ink)}
.pbar{height:14px;background:#E3F3EF;border-radius:99px;overflow:hidden;margin:14px 0 8px}
.pbar i{display:block;height:100%;background:linear-gradient(90deg,var(--shamrock),var(--turq));border-radius:99px;transition:width .8s cubic-bezier(.2,.7,.2,1)}
.pbar.wide{height:18px;margin-top:22px}
.psub{font-size:15px;color:var(--faint)}

.focus{background:var(--azure);border-radius:22px;padding:30px 34px;margin-bottom:64px;color:#fff;
  box-shadow:0 26px 60px -34px rgba(38,83,43,.55)}
.flabel{font-size:18px;font-weight:600;color:#A9E8DA;margin-bottom:10px}
.focus .task{border:0;padding:6px 0 0;background:none}
.focus .ttitle{color:#fff;font-size:34px;line-height:1.15;letter-spacing:-.015em}
.focus .tmeta{color:#A9E8DA;font-size:18px}
.focus .tdue,.focus .tdue.soon,.focus .tdue.over{color:var(--cyan);font-size:19px;font-weight:700}
.focus .openbtn{background:#fff;color:var(--azure);border-color:#fff;font-size:19px;height:52px;padding:0 26px}
.focus .openbtn:hover{background:var(--alice)}
.focus .check{border-color:rgba(255,255,255,.7)}
.focus .check svg path{stroke:#fff}
.focus .cdot{box-shadow:0 0 0 2px rgba(255,255,255,.85)}

.sec{margin-bottom:64px}
.sec h2{font:700 36px/1.1 var(--serif);font-variation-settings:'opsz' 72;letter-spacing:-.02em;color:var(--azure);
  margin:0 0 8px;padding:0 0 14px;border-bottom:2px solid var(--azure);display:flex;align-items:baseline;gap:14px}
.hsub{font-size:20px;font-weight:600;color:var(--cerulean);letter-spacing:0}
.secnote{font-size:17px;color:var(--faint);margin:10px 0 4px}
.empty{font-size:18px;color:var(--faint);padding:18px 0}
.two{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:64px}
.two .sec{margin-bottom:64px}

.task{display:flex;align-items:center;gap:18px;padding:20px 0;border-bottom:1px solid var(--line);
  transition:opacity .45s,transform .45s,max-height .5s,padding .5s;max-height:400px}
.task.big{align-items:center}
.check{flex:none;width:34px;height:34px;border-radius:50%;border:2px solid var(--cerulean);background:transparent;
  cursor:pointer;display:grid;place-items:center;padding:0;transition:background .2s,border-color .2s,transform .2s}
.check:hover{border-color:var(--sage);background:rgba(57,158,90,.08)}
.check svg{width:20px;height:20px;fill:none}
.check svg path{stroke:var(--sage);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:24;stroke-dashoffset:24;transition:stroke-dashoffset .35s .05s}
.task.doing .check{opacity:.6}
.task.done .check{background:var(--sage);border-color:var(--sage);animation:pop .45s cubic-bezier(.3,1.6,.5,1)}
.task.done .check svg path{stroke:#fff;stroke-dashoffset:0}
.task.done .ttitle{text-decoration:line-through;text-decoration-thickness:2px;opacity:.55}
.task.gone{opacity:0;transform:scale(.97);max-height:0;padding-top:0;padding-bottom:0;overflow:hidden}
@keyframes pop{0%{transform:scale(.8)}60%{transform:scale(1.18)}100%{transform:scale(1)}}
.cdot{width:12px;height:12px;border-radius:50%;flex:none}
.tbody{flex:1;min-width:0}
.ttitle{font-size:23px;font-weight:600;line-height:1.3;color:var(--ink);letter-spacing:-.005em}
.tmeta{font-size:16.5px;color:var(--muted);margin-top:4px}
.twhy{font-size:16px;color:var(--faint);margin-top:3px}
.tside{display:flex;align-items:center;gap:22px;flex:none}
.tdue{font-size:17px;font-weight:600;color:var(--muted);white-space:nowrap}
.tdue.soon{color:var(--spruce);font-weight:700}.tdue.over{color:var(--late);font-size:19px}
.openbtn{display:inline-flex;align-items:center;gap:8px;height:44px;padding:0 20px;border-radius:12px;
  background:var(--azure);color:#fff;border:1px solid var(--azure);font-size:17px;font-weight:600;text-decoration:none;
  transition:background .15s,transform .15s}
.openbtn:hover{background:#1C4121}
.openbtn:active{transform:translateY(1px)}

.two .task .tside{flex-direction:column;align-items:flex-end;gap:10px}
.two .ttitle{font-size:21px}

.week{display:flex;flex-direction:column;gap:14px;margin-top:14px}
.wday{display:grid;grid-template-columns:110px 1fr;grid-template-rows:auto auto;column-gap:16px;align-items:center}
.wlab{font-size:18px;font-weight:600;color:var(--ink);grid-row:span 2}
.wtrack{height:14px;background:#E3F3EF;border-radius:99px;overflow:hidden}
.wtrack i{display:block;height:100%;background:var(--teal);border-radius:99px}
.wday.heavy .wtrack i{background:var(--azure)}
.wnum{font-size:15px;color:var(--faint);margin-top:4px}
.wtot{margin-top:22px;font-size:18px;font-weight:600;color:var(--muted)}

.overdue h2{color:var(--late);border-bottom-color:var(--late)}
.overdue .hsub{color:var(--late)}
.overdue .task{background:#FBEFEE;border:1px solid #EDCBC7;border-radius:16px;padding:18px 22px;margin-top:14px}

.review .check{border-color:var(--sage)}
.review .openbtn{background:#fff;color:var(--azure);border-color:var(--cerulean)}
.review .openbtn:hover{background:var(--azure);color:#fff}

.quiet h2{font-size:26px;color:var(--cerulean);border-bottom:1px solid var(--line)}
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
.chip{display:inline-flex;align-items:center;gap:9px;padding:9px 14px;border:1px solid var(--line);border-radius:12px;
  background:var(--surface);color:var(--ink);font-size:16px;font-weight:600;text-decoration:none}
.chip span:last-child{font-weight:400;color:var(--faint)}
.chip:hover{border-color:var(--cerulean)}

.yourweek{background:var(--surface);border:1px solid var(--line);border-radius:22px;padding:30px 34px}
.yourweek h2{border-bottom:0;padding-bottom:0}
.yw{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;margin-top:18px}
.ybig{font:700 48px/1 var(--serif);font-variation-settings:'opsz' 96;letter-spacing:-.03em;color:var(--azure);font-variant-numeric:tabular-nums}

#toast{position:fixed;left:50%;bottom:36px;transform:translate(-50%,20px);opacity:0;pointer-events:none;
  background:var(--ink);color:#fff;font-size:18px;font-weight:600;padding:14px 22px;border-radius:14px;
  box-shadow:0 18px 40px -18px rgba(22,48,25,.55);transition:opacity .25s,transform .25s;z-index:20}
#toast.show{opacity:1;transform:translate(-50%,0)}
#toast.big{font-size:26px;padding:22px 34px;background:var(--azure)}
#fx{position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:19}
@media (prefers-reduced-motion: reduce){.pbar i,.task,.check svg path{transition:none!important}}
"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype="text/html; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        p = self.path.split("?")[0]
        try:
            if p == "/": return self.send(200, dash())
            m = re.match(r"^/static/([A-Za-z0-9_-]+\.(jpg|png|webp))$", p)
            if m:
                f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", m.group(1))
                if not os.path.isfile(f): return self.send(404, "no such file", "text/plain")
                return self.send(200, open(f, "rb").read(), "image/jpeg" if m.group(2) == "jpg" else "image/" + m.group(2))
            if p == "/favicon.ico":
                # inline SVG book, avoids a 404 on every page load
                svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
                       "<rect width='32' height='32' rx='7' fill='#7B5EA7'/>"
                       "<path d='M8 9h7a3 3 0 0 1 3 3v12a2 2 0 0 0-2-2H8z' fill='#fff' opacity='.92'/>"
                       "<path d='M24 9h-7a3 3 0 0 0-3 3v12a2 2 0 0 1 2-2h8z' fill='#fff' opacity='.62'/></svg>")
                return self.send(200, svg, "image/svg+xml")
            if p == "/api/state": return self.send(200, json.dumps(state(), indent=1), "application/json")
            if p.startswith("/open/"):
                return self.open_file(urllib.parse.unquote(p[len("/open/"):]))
            if p.startswith("/trainer/"):
                f = find_trainer(p[len("/trainer/"):].strip("/"))
                if not f:
                    return self.send(404, "no trainer", "text/plain")
                return self.send(200, open(f, "rb").read(), "text/html; charset=utf-8")
            if p.startswith("/guide/"):
                slug = p[len("/guide/"):].strip("/")
                for c in COURSES:   # a hand-built HTML guide beats the generated markdown
                    h = os.path.join(NOTES, c, "Study Guides", slug + ".html")
                    if os.path.isfile(h):
                        return self.send(200, open(h, "rb").read(), "text/html; charset=utf-8")
                f = find_guide(slug)
                if not f: return self.send(404, PAGE % {"title": "not found", "css": CSS,
                    "body": "<a class=back href='/'>back</a><article><h1>No such guide</h1>"
                            "<p>Nothing at <code>%s</code>. Run <code>study-guide</code>.</p></article>" % html.escape(slug)})
                tr = ('<a class="back tr" href="/trainer/%s">Open the interactive trainer &rarr;</a>'
                      % slug) if find_trainer(slug) else ""
                body = ("<a class=back href='/'>&larr; Study Desk</a>%s<article>%s</article>"
                        % (tr, md(open(f).read())))
                return self.send(200, PAGE % {"title": slug, "css": CSS, "body": body})
            self.send(404, "not found", "text/plain")
        except Exception as e:
            self.send(500, "error: %s" % e, "text/plain")

    OPEN_TYPES = {".pdf": "application/pdf", ".html": "text/html; charset=utf-8",
                  ".png": "image/png", ".jpg": "image/jpeg", ".txt": "text/plain; charset=utf-8"}

    def open_file(self, rel):
        """Serve a file for an Open button. Browsers refuse file:// links from an http
        page, so the desk serves them itself, but ONLY from inside F&M Notes."""
        root = os.path.realpath(NOTES)
        full = os.path.realpath(os.path.join(root, rel))
        if not full.startswith(root + os.sep):
            return self.send(403, "outside F&M Notes", "text/plain")
        if not os.path.isfile(full):
            return self.send(404, "no such file: %s" % rel, "text/plain")
        ext = os.path.splitext(full)[1].lower()
        if ext == ".rmd":
            subprocess.Popen(["open", full])   # hand it to RStudio, close the blank tab
            return self.send(200, "<script>window.close()</script>Opened %s in RStudio." % html.escape(os.path.basename(full)))
        if ext == ".md":
            body = "<a class=back href='/'>&larr; Study Desk</a><article>%s</article>" % md(open(full).read())
            return self.send(200, PAGE % {"title": os.path.basename(full), "css": CSS, "body": body})
        return self.send(200, open(full, "rb").read(), self.OPEN_TYPES.get(ext, "application/octet-stream"))

    def do_POST(self):
        """/api/done/<task_id> closes a Todoist task, which is what "Reviewed" means."""
        p = self.path.split("?")[0]
        origin = self.headers.get("Origin", "")
        if origin and origin not in ("http://localhost:%d" % PORT, "http://127.0.0.1:%d" % PORT):
            return self.send(403, "bad origin", "text/plain")   # no other site may close tasks
        m = re.match(r"^/api/done/([A-Za-z0-9]+)$", p)
        if not m:
            return self.send(404, "not found", "text/plain")
        lm = re.match(r"^cv(\d+)$", m.group(1))
        if lm:
            try:
                close_live_only(lm.group(1))
            except Exception as e:
                return self.send(502, "todoist: %s" % e, "text/plain")
            with _lock:
                _cache["at"] = 0; _done_cache["at"] = 0
            return self.send(200, '{"ok":true}', "application/json")
        try:
            r = urllib.request.Request(TBASE + "/tasks/%s/close" % m.group(1), data=b"", method="POST",
                                       headers={"Authorization": "Bearer " + TTOK})
            urllib.request.urlopen(r, timeout=20).read()
        except Exception as e:
            return self.send(502, "todoist: %s" % e, "text/plain")
        with _lock:
            _cache["at"] = 0; _done_cache["at"] = 0
        return self.send(200, '{"ok":true}', "application/json")

if __name__ == "__main__":
    threading.Thread(target=live_loop, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
