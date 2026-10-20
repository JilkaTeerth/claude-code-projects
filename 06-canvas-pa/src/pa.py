#!/usr/bin/env python3
"""Canvas PA. Background poller + local server. Always on, never needs a manual refresh."""
import json, os, re, sys, time, threading, urllib.request, urllib.error, datetime, html
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import planner, notes, nudge, capture

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".canvas-pa")
CFG = json.load(open(os.path.join(BASE, "config.json")))
STATE_PATH = os.path.join(BASE, "state.json")
TZ = ZoneInfo(CFG.get("timezone", "America/New_York"))
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

env = {}
for line in open(os.path.join(HOME, ".canvas_env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k] = v
HOST, TOK = env["CANVAS_HOST"].rstrip("/"), env["CANVAS_TOKEN"]

# extensions granted off-Canvas (email, in person): assignment id -> ISO8601 UTC
DUE_OVERRIDES = CFG.get("due_overrides", {})

STORE_PATH = os.path.join(BASE, "store.json")
def load_store():
    try: return json.load(open(STORE_PATH))
    except Exception: return {}
def save_store(d):
    json.dump(d, open(STORE_PATH, "w"), indent=1)

STATE = {"updated": None, "error": None, "courses": [], "assignments": [],
         "announcements": [], "files": [], "seen_files": {}}
LOCK = threading.Lock()


def api(path):
    out, url = [], HOST + path
    while url:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOK})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
            link = r.headers.get("Link", "")
        if isinstance(data, dict):
            return data
        out.extend(data)
        m = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = m.group(1) if m else None
    return out


def now():
    return datetime.datetime.now(TZ)


def parse(s):
    if not s:
        return None
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TZ)


def strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = re.sub(r"</p>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def calibration():
    """Ratio of actual to estimated minutes, per course, from your own check-ins."""
    st = load_store()
    agg = {}
    for aid, rec in st.items():
        for entry in rec.get("log", []):
            c, est, act = entry.get("course"), entry.get("estimated"), entry.get("minutes")
            if c and est and act:
                a = agg.setdefault(c, {"actual": 0, "est": 0, "n": 0})
                a["actual"] += act; a["est"] += est; a["n"] += 1
    return {c: {"factor": round(v["actual"] / v["est"], 2), "samples": v["n"]}
            for c, v in agg.items() if v["est"] > 0 and v["n"] >= 2}


PREP_VERBS = re.compile(
    r'\b(read|re-?read|watch|listen|bring|install|download|print|complete|review|'
    r'sign up|register|create an account|make an account|set up|come to class with)\b', re.I)


def buried_work(desc):
    """Things hidden inside an assignment description that are not the submission itself.

    Readings, videos, software to install, things to bring to class. These never appear
    as their own deadline anywhere, so they are exactly what gets missed. This is the
    slack the dashboard is supposed to pick up.
    """
    if not desc:
        return []
    txt = strip_markup(desc)
    out, seen = [], set()
    for line in re.split(r'[\n\r]+|(?<=[.!?])\s{2,}', txt):
        line = re.sub(r'\s+', ' ', line).strip(' -*\u2022')
        if len(line) < 8 or len(line) > 260:
            continue
        has_link = bool(re.search(r'<https?://', line))
        has_file = bool(re.search(r'\b[\w-]+\.(java|py|r|rmd|csv|pdf|nb|xlsx|zip)\b', line, re.I))
        if not (PREP_VERBS.search(line) or has_link or has_file):
            continue
        if re.search(r'\b(upload|submit|hand in|turn in|due)\b', line, re.I) and \
           not PREP_VERBS.search(line.split('upload')[0] or ' '):
            continue
        url = re.search(r'<(https?://[^>]+)>', line)
        clean = re.sub(r'\s*<https?://[^>]+>', '', line).strip()
        key = clean.lower()[:70]
        if key in seen:
            continue
        seen.add(key)
        out.append({"text": clean, "url": url.group(1) if url else None})
    return out[:6]


FILE_CACHE = {}
COURSE_PREP = {}


def readable_file_text(f):
    """Fetch small text-ish course files (.Rmd, .txt, .md) so we can mine them for
    instructions. Some professors put the entire assignment, readings included, inside
    a template file and leave the Canvas assignment description empty. the professor does
    exactly this, which is how a whole set of readings can be invisible."""
    name = (f.get("display_name") or "").lower()
    if not name.endswith((".rmd", ".txt", ".md", ".markdown")):
        return ""
    if (f.get("size") or 0) > 120_000:
        return ""
    key = f"{f.get('id')}|{f.get('updated_at')}"
    if key in FILE_CACHE:
        return FILE_CACHE[key]
    try:
        req = urllib.request.Request(f["url"], headers={"Authorization": "Bearer " + TOK})
        body = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    except Exception:
        body = ""
    if len(FILE_CACHE) > 60:
        FILE_CACHE.clear()
    FILE_CACHE[key] = body
    return body


def strip_markup(t):
    t = re.sub(r'\\href\{([^}]*)\}\{\\underline\{\{?([^}]*)\}?\}\}', r'\2 <\1>', t)
    t = re.sub(r'\\href\{([^}]*)\}\{([^}]*)\}', r'\2 <\1>', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\1 <\2>', t)
    t = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'\2 <\1>', t, flags=re.S | re.I)
    t = re.sub(r'<br\s*/?>|</p>|</li>|</div>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'```.*?```', ' ', t, flags=re.S)
    return t.replace('&nbsp;', ' ').replace('&amp;', '&').replace('\\underline', '')


def estimate_hours(a, course):
    """Rough study estimate: scales with points and the course's difficulty rating."""
    pts = a.get("points_possible") or 0
    diff = course.get("difficulty", 3)
    if pts >= 50:
        base = 6.0            # exam-sized
    elif pts >= 20:
        base = 3.0            # written homework set
    elif pts >= 5:
        base = 2.0
    else:
        base = 1.5            # small weekly check-in
    return round(base * (0.6 + 0.2 * diff), 1)   # base only; calibrated at read time


def promote_pending():
    """Courses Teerth has registered for but Canvas has not synced yet live under
    config['pending'], keyed by course code. As soon as the enrolment appears in
    Canvas we move it into config['courses'] against its real Canvas id. This is
    why he never has to run a script after adding a class."""
    cfg = json.load(open(os.path.join(BASE, "config.json")))
    pending = cfg.get("pending") or {}
    if not pending:
        return False
    try:
        live = api("/api/v1/courses?enrollment_state=active&per_page=100")
    except Exception:
        return False
    moved = []
    for code, meta in list(pending.items()):
        loose = code.replace(" ", r"[\s-]?")
        for c in live:
            hay = f"{c.get('name','')} {c.get('course_code','')}"
            if re.search(loose, hay, re.I):
                cid = str(c["id"])
                if cid not in cfg["courses"]:
                    cfg["courses"][cid] = meta
                    moved.append(f"{code} -> {cid}")
                pending.pop(code, None)
                break
    if moved:
        cfg["pending"] = pending
        json.dump(cfg, open(os.path.join(BASE, "config.json"), "w"), indent=2)
        CFG.clear(); CFG.update(cfg)
        with LOCK:
            STATE["promoted"] = moved
        return True
    return False


def poll():
    """Pull everything from Canvas into STATE. Runs forever on a background thread."""
    while True:
        try:
            promote_pending()
            courses, assignments, anns, files = [], [], [], []
            for cid, meta in CFG["courses"].items():
                c = api(f"/api/v1/courses/{cid}?include[]=total_scores")
                en = (c.get("enrollments") or [{}])[0]
                courses.append({"prep": [], "id": cid, "code": meta["code"], "short": meta["short"],
                                "color": meta.get("color", "#8A8A8A"),
                                "glow": meta.get("glow", "#64748B"),
                                "tint": meta.get("tint", "#141922"),
                                "name": c.get("name"), "prof": meta["prof"],
                                "note": meta.get("note", ""),
                                "difficulty": meta.get("difficulty", 3),
                                "baseline": meta.get("baseline_hours", 5),
                                "score": en.get("computed_current_score")})
                for a in api(f"/api/v1/courses/{cid}/assignments?per_page=100&include[]=submission"):
                    sub = a.get("submission") or {}
                    assignments.append({
                        "color": meta.get("color", "#8A8A8A"),
                        "tint": meta.get("tint", "#EEF1F4"),
                        "id": str(a.get("id")), "course": meta["code"], "cid": cid, "name": a.get("name"),
                        "due": DUE_OVERRIDES.get(str(a.get("id")), a.get("due_at")),
                        "due_override": str(a.get("id")) in DUE_OVERRIDES,
                        "points": a.get("points_possible"),
                        "url": a.get("html_url"),
                        "submitted": bool(sub.get("submitted_at")),
                        "score": sub.get("score"),
                        "missing": bool(sub.get("missing")),
                        "hours_base": estimate_hours(a, meta), "hours": estimate_hours(a, meta),
                        "prep": buried_work(a.get("description")),
                    })
                course_prep = []
                try:
                    for f in api(f"/api/v1/courses/{cid}/files?per_page=25&sort=created_at&order=desc")[:12]:
                        body = readable_file_text(f)
                        if body:
                            for item in buried_work(body):
                                item["from"] = f.get("display_name")
                                course_prep.append(item)
                        files.append({"course": meta["code"], "cid": cid,
                                      "name": f.get("display_name"),
                                      "created": f.get("created_at"),
                                      "url": f.get("url", "").split("?")[0],
                                      "id": str(f.get("id"))})
                except Exception:
                    pass   # some courses lock the files tab
                COURSE_PREP[cid] = course_prep[:8]
            for c in courses:
                c["prep"] = COURSE_PREP.get(c["id"], [])
            ctx = "&".join(f"context_codes[]=course_{c}" for c in CFG["courses"])
            start = (now() - datetime.timedelta(days=21)).date()
            for a in api(f"/api/v1/announcements?{ctx}&start_date={start}&per_page=40"):
                cid = str(a.get("context_code", "")).replace("course_", "")
                anns.append({"course": CFG["courses"].get(cid, {}).get("code", cid),
                             "title": a.get("title"), "posted": a.get("posted_at"),
                             "body": strip_html(a.get("message"))[:900],
                             "url": a.get("html_url")})
            anns.sort(key=lambda x: x.get("posted") or "", reverse=True)
            files.sort(key=lambda x: x.get("created") or "", reverse=True)
            with LOCK:
                STATE.update({"updated": now().isoformat(), "error": None,
                              "courses": courses, "assignments": assignments,
                              "announcements": anns, "files": files})
                json.dump(STATE, open(STATE_PATH, "w"), indent=1)
        except Exception as e:
            with LOCK:
                STATE["error"] = f"{type(e).__name__}: {e}"
        time.sleep(CFG.get("poll_seconds", 300))


def schedule_blocks():
    out = []
    for cid, m in CFG["courses"].items():
        for day, s, e in m.get("meets", []):
            out.append({"cid": cid, "code": m["code"], "short": m["short"],
                        "prof": m["prof"], "day": day, "start": s, "end": e,
                        "lab": (int(e.split(":")[0]) - int(s.split(":")[0])) >= 2})
    return out


def next_class(ref=None):
    """The next scheduled meeting from `ref`, searching forward up to a week."""
    ref = ref or now()
    blocks = schedule_blocks()
    best = None
    for delta in range(0, 8):
        d = ref + datetime.timedelta(days=delta)
        dayname = DAYS[d.weekday()]
        for b in blocks:
            if b["day"] != dayname:
                continue
            h, mi = map(int, b["start"].split(":"))
            when = d.replace(hour=h, minute=mi, second=0, microsecond=0)
            if when <= ref:
                continue
            if best is None or when < best[0]:
                best = (when, b)
        if best:
            break
    if not best:
        return None
    when, b = best
    return {**b, "when": when.isoformat(),
            "in_minutes": int((when - ref).total_seconds() // 60)}


def brief():
    """Everything the UI needs, computed fresh on each request."""
    with LOCK:
        s = json.loads(json.dumps(STATE))
    n = now()
    nc = next_class(n)

    manual = []
    for t in capture.tasks():
        manual.append({"id": t["id"], "course": t["course"], "cid": None,
                       "name": t["name"], "due": t["due"],
                       "points": None, "url": None, "submitted": False,
                       "score": None, "missing": False, "manual": True,
                       "hours_base": t["hours"], "hours": t["hours"]})
    live = []
    for a in s["assignments"] + manual:
        d = parse(a["due"])
        if not d:
            continue
        a = dict(a)
        a["due_local"] = d.strftime("%a %d %b, %H:%M")
        a["overdue"] = d < n and not a["submitted"]
        a["hours_left"] = (d - n).total_seconds() / 3600
        if d > n or a["overdue"]:
            live.append(a)
    live.sort(key=lambda x: x["due"])

    upcoming = [a for a in live if not a["overdue"]][:12]
    overdue = [a for a in live if a["overdue"]]

    # study load for the next 7 days, per course
    horizon = n + datetime.timedelta(days=7)
    load = {}
    for a in upcoming:
        d = parse(a["due"])
        if d and d <= horizon and not a["submitted"]:
            load[a["course"]] = round(load.get(a["course"], 0) + a["hours"], 1)
    total = round(sum(load.values()), 1)

    # material posted since the last class in that course, i.e. "is there something to read"
    prep = []
    if nc:
        cutoff = n - datetime.timedelta(days=7)
        for f in s["files"]:
            if f["cid"] == nc["cid"]:
                c = parse(f["created"])
                if c and c >= cutoff:
                    prep.append({**f, "ago": human_ago(c, n)})
    fresh_ann = []
    for a in s["announcements"][:6]:
        p = parse(a["posted"])
        if p and (n - p).days <= 5:
            fresh_ann.append({**a, "ago": human_ago(p, n)})

    # today's remaining classes
    todays = []
    for b in schedule_blocks():
        if b["day"] == DAYS[n.weekday()]:
            h, mi = map(int, b["start"].split(":"))
            when = n.replace(hour=h, minute=mi, second=0, microsecond=0)
            todays.append({**b, "past": when < n})
    todays.sort(key=lambda x: x["start"])

    # office hours worth going to right now or next
    oh = []
    for o in CFG.get("office_hours", []):
        idx = DAYS.index(o["day"])
        delta = (idx - n.weekday()) % 7
        d = (n + datetime.timedelta(days=delta))
        h, mi = map(int, o["start"].split(":"))
        eh, emi = map(int, o["end"].split(":"))
        st = d.replace(hour=h, minute=mi, second=0, microsecond=0)
        en_ = d.replace(hour=eh, minute=emi, second=0, microsecond=0)
        if en_ < n:
            st += datetime.timedelta(days=7); en_ += datetime.timedelta(days=7)
        oh.append({**o, "start_iso": st.isoformat(),
                   "live": st <= n <= en_,
                   "in_minutes": int((st - n).total_seconds() // 60),
                   "when": st.strftime("%a %H:%M")})
    oh.sort(key=lambda x: x["start_iso"])

    store = load_store()
    cal = calibration()
    for a in live:
        f = (cal.get(a["course"]) or {}).get("factor")
        if f:
            a["hours"] = round(a.get("hours_base", a["hours"]) * f, 1)
        st = store.get(a["id"], {})
        a["done"] = bool(st.get("done"))
        a["dismissed"] = bool(st.get("dismissed"))
    upcoming = [a for a in live if not a["overdue"] and not a["dismissed"]][:12]
    overdue = [a for a in live if a["overdue"] and not a["done"] and not a["dismissed"]]

    squash = capture.apply_overrides(planner.load_squash())
    plan = planner.plan_today([dict(a) for a in upcoming], n, CFG, squash)
    focus = next((a for a in upcoming if not a["submitted"] and not a["done"]), None)
    delay = planner.cost_of_delay(focus, n, CFG, squash) if focus else []
    week = []
    for i in range(7):
        d = (n + datetime.timedelta(days=i)).date()
        sq_h = sum(1 for e in squash if e["date"] == d.isoformat())
        week.append({"date": d.isoformat(), "label": d.strftime("%a %d"),
                     "free": planner.capacity(d, CFG, squash), "squash": sq_h})

    today_sq = [e for e in squash if e["date"] == n.date().isoformat()]
    next_sq = next((e for e in squash if e["date"] >= n.date().isoformat()), None)

    note_state, questions = {}, []
    for c in s["courses"]:
        note_state[c["code"]] = notes.coverage(c["code"])
        questions += notes.open_questions(c["code"])

    class_brief = None
    if nc:
        code = CFG["courses"][nc["cid"]]["code"]
        due_in = [a for a in upcoming if a["course"] == code][:3]
        class_brief = {
            "code": code,
            "prof": nc["prof"],
            "posted": prep,
            "your_notes": notes.latest_summary(code),
            "notes_state": note_state.get(code),
            "questions": [q for q in questions if q["course"] == code],
            "due": [{"name": a["name"], "due_local": a["due_local"]} for a in due_in],
            "announcement": next((a for a in s["announcements"]
                                  if a["course"] == code), None),
        }

    # ---- semester terrain: squash load + deadline density, week by week
    sem_start = datetime.date(2026, 8, 24)
    sem_end = datetime.date(2026, 12, 18)
    weeks, wk = [], sem_start
    all_due = [a["due"][:10] for a in s["assignments"] if a.get("due")]
    while wk <= sem_end:
        wend = wk + datetime.timedelta(days=6)
        sq = 0.0
        for e in squash:
            if wk.isoformat() <= e["date"] <= wend.isoformat():
                if e["start"] == "00:00" and e["end"] >= "23:59":
                    sq += 8
                else:
                    sh, sm = map(int, e["start"].split(":"))
                    eh, em = map(int, e["end"].split(":"))
                    sq += ((eh * 60 + em) - (sh * 60 + sm)) / 60
        weeks.append({
            "start": wk.isoformat(),
            "label": wk.strftime("%d %b"),
            "month": wk.strftime("%b"),
            "month_start": wk.day <= 7 or wk == sem_start,
            "squash": round(sq, 1),
            "deadlines": sum(1 for d in all_due if wk.isoformat() <= d <= wend.isoformat()),
            "current": wk <= n.date() <= wend,
            "past": wend < n.date(),
        })
        wk += datetime.timedelta(days=7)
    peak = max([w["squash"] for w in weeks] + [1])
    milestones = [
        {"date": "2026-09-28", "label": "Season starts", "note": "squash jumps to 11h a week"},
        {"date": "2026-11-20", "label": "Maine trip", "note": "you miss MAT 211 and MAT 230"},
        {"date": "2026-12-11", "label": "Classes end", "note": "assumed, unconfirmed"},
    ]
    for m in milestones:
        md = datetime.date.fromisoformat(m["date"])
        m["week_index"] = max(0, (md - sem_start).days // 7)
        m["days_away"] = (md - n.date()).days

    # ---- momentum: what you actually did this week
    store_all = load_store()
    monday = n.date() - datetime.timedelta(days=n.weekday())
    done_min = plan_min = sessions = skipped = 0
    for rec in store_all.values():
        for entry in rec.get("log", []):
            at = entry.get("at", "")[:10]
            if at >= monday.isoformat():
                plan_min += entry.get("estimated") or 0
                done_min += entry.get("minutes") or 0
                sessions += 1
                if not entry.get("did"):
                    skipped += 1
    momentum = {"done_min": done_min, "planned_min": plan_min,
                "sessions": sessions, "skipped": skipped,
                "ratio": round(done_min / plan_min, 2) if plan_min else None,
                "week_of": monday.isoformat()}

    for c in s["courses"]:
        c["notes"] = note_state.get(c["code"], {})
        c["office"] = [o for o in CFG.get("office_hours", []) if o["course"] == c["code"]]
        c["calibration"] = calibration().get(c["code"])

    upcoming_squash = [e for e in squash if e["date"] >= n.date().isoformat()][:6]
    return {"squash_soon": upcoming_squash, "semester": weeks, "peak_squash": peak, "milestones": milestones,
            "momentum": momentum,
            "class_brief": class_brief, "notes": note_state,
            "questions": questions, "calibration": calibration(),
            "plan": plan, "delay": delay, "focus": focus, "week": week,
            "today_squash": today_sq, "next_squash": next_sq,
            "now": n.isoformat(), "updated": s["updated"], "error": s["error"],
            "courses": s["courses"], "next_class": nc, "today": todays,
            "upcoming": upcoming, "overdue": overdue, "load": load,
            "total_hours": total, "prep": prep, "announcements": fresh_ann,
            "office_hours": oh}


def human_ago(then, ref):
    secs = (ref - then).total_seconds()
    if secs < 3600:
        return f"{int(secs//60)}m ago"
    if secs < 86400:
        return f"{int(secs//3600)}h ago"
    return f"{int(secs//86400)}d ago"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            body = {}
        aid, action = str(body.get("id", "")), body.get("action", "")
        st = load_store()
        cur = st.setdefault(aid, {})
        if action == "done":
            cur["done"] = not cur.get("done")
        elif action == "dismiss":
            cur["dismissed"] = True
        elif action == "restore":
            cur["dismissed"] = False; cur["done"] = False
        elif action == "log":
            cur.setdefault("log", []).append({"at": now().isoformat(),
                                              "minutes": body.get("minutes"),
                                              "estimated": body.get("estimated"),
                                              "course": body.get("course"),
                                              "did": body.get("did")})
        save_store(st)
        out = json.dumps({"ok": True, "state": cur}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_PUT(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            b = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            b = {}
        kind = b.get("kind")
        now_ = now()
        try:
            if kind == "task":
                r = capture.add_task(b.get("course"), b.get("name"),
                                     b.get("due"), b.get("hours"), now_)
            elif kind == "untask":
                r = {"remaining": capture.delete_task(b.get("id"))}
            elif kind == "note":
                r = capture.add_note(b.get("course"), b.get("text"), now_)
            elif kind == "question":
                r = capture.add_question(b.get("course"), b.get("text"), now_)
            elif kind == "squash_cancel":
                r = capture.cancel_squash(b.get("date"), b.get("start"))
            elif kind == "squash_add":
                r = capture.add_squash(b.get("date"), b.get("start"), b.get("end"),
                                       b.get("title"), b.get("location", ""))
            else:
                r = {"error": f"unknown kind {kind!r}"}
            ok = "error" not in r
        except Exception as e:
            r, ok = {"error": f"{type(e).__name__}: {e}"}, False
        out = json.dumps({"ok": ok, "result": r}).encode()
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(brief()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/api/refresh"):
            threading.Thread(target=lambda: None).start()
            self.send_response(204); self.end_headers(); return
        page = open(os.path.join(BASE, "index.html"), "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)


def nudge_loop():
    while True:
        try:
            if STATE.get("updated"):
                nudge.run_all(brief())
        except Exception as e:
            with LOCK:
                STATE["nudge_error"] = str(e)
        time.sleep(60)


if __name__ == "__main__":
    threading.Thread(target=poll, daemon=True).start()
    threading.Thread(target=nudge_loop, daemon=True).start()
    port = CFG.get("port", 7373)
    print(f"Canvas PA on http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
