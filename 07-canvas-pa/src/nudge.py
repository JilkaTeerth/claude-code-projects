"""OS-level nudges. Fires the morning brief, block starts, prep warnings and check-ins."""
import subprocess, datetime, json, os

BASE = os.path.expanduser("~/.canvas-pa")
SENT_PATH = os.path.join(BASE, "sent.json")
NOTIFIER = "/opt/homebrew/bin/terminal-notifier"


def _sent():
    try:
        return json.load(open(SENT_PATH))
    except Exception:
        return {}


def _save(d):
    json.dump(d, open(SENT_PATH, "w"))


def send(key, title, subtitle, message, sound="Ping", once_per="day"):
    """Fire a notification at most once per key per day."""
    stamp = datetime.date.today().isoformat() if once_per == "day" else ""
    k = f"{key}|{stamp}"
    s = _sent()
    if k in s:
        return False
    if not os.path.exists(NOTIFIER):
        return False
    try:
        subprocess.run([NOTIFIER, "-title", title, "-subtitle", subtitle,
                        "-message", message, "-sound", sound,
                        "-group", "canvas-pa",
                        "-open", "http://localhost:7373"],
                       timeout=10, capture_output=True)
    except Exception:
        return False
    s[k] = datetime.datetime.now().isoformat()
    # keep the file from growing forever
    if len(s) > 400:
        s = dict(list(s.items())[-200:])
    _save(s)
    return True


def morning_brief(b):
    """One notification at the start of the day that says what today actually is."""
    plan = b.get("plan") or []
    total = sum(x["minutes"] for x in plan)
    od = len(b.get("overdue") or [])
    sq = b.get("today_squash") or []
    bits = []
    if plan:
        bits.append(f"{round(total/60,1)}h of work planned")
    if od:
        bits.append(f"{od} overdue")
    if sq:
        bits.append(f"squash {sq[0]['start']}")
    focus = b.get("focus")
    msg = ", ".join(bits) or "nothing due"
    sub = f"Start with {focus['course']}: {focus['name']}" if focus else "Clear day"
    return send("morning", "Today", sub, msg, sound="Glass")


def block_start(b):
    """At the start of each planned block, tell him the first step only."""
    now = datetime.datetime.now()
    hit = False
    for blk in b.get("plan") or []:
        h, m = map(int, blk["start"].split(":"))
        start = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta = (now - start).total_seconds()
        if 0 <= delta <= 300:            # within 5 min of the block opening
            hit |= send(f"blk-{blk['start']}-{blk['task']}",
                        f"{blk['course']} · {blk['minutes']} min",
                        blk["task"], blk["first_step"], once_per="day")
    return hit


def checkin(b):
    """After a block should have ended, ask whether it actually happened."""
    now = datetime.datetime.now()
    hit = False
    for blk in b.get("plan") or []:
        h, m = map(int, blk["end"].split(":"))
        end = now.replace(hour=h, minute=m, second=0, microsecond=0)
        delta = (now - end).total_seconds()
        if 300 <= delta <= 900:
            hit |= send(f"chk-{blk['end']}-{blk['task']}",
                        "Did that happen?", f"{blk['course']} · {blk['task']}",
                        "Open the PA and tick it, or bin it honestly.",
                        sound="Submarine", once_per="day")
    return hit


def prep_warning(b):
    """Half an hour before a class that has unread posted material."""
    nc = b.get("next_class")
    prep = b.get("prep") or []
    if not nc or not prep:
        return False
    if 20 <= (nc.get("in_minutes") or 999) <= 40:
        names = ", ".join(p["name"] for p in prep[:2])
        return send(f"prep-{nc['code']}-{nc['when'][:10]}",
                    f"{nc['code']} in {nc['in_minutes']} min",
                    "Material posted you may not have opened", names,
                    sound="Tink", once_per="day")
    return False


def deadline_warning(b):
    """Once when something crosses 24h, once when it crosses 4h."""
    hit = False
    for a in b.get("upcoming") or []:
        if a.get("submitted") or a.get("done"):
            continue
        hl = a.get("hours_left", 999)
        if 20 <= hl <= 24:
            hit |= send(f"d24-{a['id']}", "Due tomorrow", f"{a['course']} · {a['name']}",
                        f"About {a['hours']}h of work left. Starting now costs you less.",
                        once_per="day")
        elif 3 <= hl <= 4:
            hit |= send(f"d4-{a['id']}", "Due in about 4 hours",
                        f"{a['course']} · {a['name']}", "This is the last useful moment.",
                        sound="Sosumi", once_per="day")
    return hit


def run_all(b, hour_start=8, hour_end=23):
    now = datetime.datetime.now()
    if not (hour_start <= now.hour < hour_end):
        return
    if now.hour == hour_start:
        morning_brief(b)
    block_start(b)
    checkin(b)
    prep_warning(b)
    deadline_warning(b)
