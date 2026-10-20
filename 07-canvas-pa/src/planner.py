"""Planning logic for the PA: busy time, free slots, cost of delay, today's blocks."""
import json, os, datetime

HOME = os.path.expanduser("~")
BASE = os.path.join(HOME, ".canvas-pa")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Waking window we are willing to schedule inside
DAY_START, DAY_END = 8 * 60, 23 * 60
MIN_BLOCK, MAX_BLOCK = 30, 90      # minutes
GAP_AFTER_CLASS = 15               # don't schedule the instant a class ends


def mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def hhmm(m):
    return f"{m//60:02d}:{m%60:02d}"


def load_squash():
    p = os.path.join(BASE, "squash.json")
    if not os.path.exists(p):
        return []
    return json.load(open(p))


def busy(day, cfg, squash):
    """Merged busy intervals (minutes from midnight) for a given date."""
    out = []
    dayname = DAYS[day.weekday()]
    for cid, meta in cfg["courses"].items():
        for d, s, e in meta.get("meets", []):
            if d == dayname:
                out.append((mins(s), mins(e), meta["code"]))
    for ev in squash:
        if ev["date"] == day.isoformat():
            s, e = mins(ev["start"]), mins(ev["end"])
            if s == 0 and e >= 1439:
                return [(0, 1440, ev["title"])]       # all-day, whole day gone
            out.append((s, e, ev["title"]))
    out.sort()
    merged = []
    for s, e, label in out:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e),
                          merged[-1][2] + " + " + label)
        else:
            merged.append((s, e, label))
    return merged


def free_slots(day, cfg, squash, after=None):
    """Gaps in the waking window not taken by class or squash."""
    b = busy(day, cfg, squash)
    lo = DAY_START if after is None else max(DAY_START, after)
    slots, cur = [], lo
    for s, e, _ in b:
        if s > cur:
            slots.append((cur, min(s, DAY_END)))
        cur = max(cur, e + GAP_AFTER_CLASS)
    if cur < DAY_END:
        slots.append((cur, DAY_END))
    return [(s, e) for s, e in slots if e - s >= MIN_BLOCK and s < DAY_END]


def capacity(day, cfg, squash):
    """Free hours available on a day."""
    return round(sum(e - s for s, e in free_slots(day, cfg, squash)) / 60, 1)


def cost_of_delay(assignment, now, cfg, squash):
    """If you start on day N instead of today, how many hours per day does it become?
    This is the number that makes procrastination concrete."""
    due = datetime.datetime.fromisoformat(assignment["due"].replace("Z", "+00:00")).astimezone(now.tzinfo)
    need = assignment["hours"]
    rows = []
    d = now.date()
    while d < due.date() and len(rows) < 6:
        days_left = (due.date() - d).days
        if days_left <= 0:
            break
        # available capacity across remaining days
        cap = sum(capacity(d + datetime.timedelta(days=i), cfg, squash)
                  for i in range(days_left))
        per_day = round(need / days_left, 1)
        rows.append({"start_on": d.isoformat(),
                     "label": "today" if d == now.date() else
                              ("tomorrow" if (d - now.date()).days == 1 else d.strftime("%a %d %b")),
                     "hours_per_day": per_day,
                     "days_left": days_left,
                     "capacity": round(cap, 1),
                     "feasible": need <= cap})
        d += datetime.timedelta(days=1)
    return rows


def plan_today(assignments, now, cfg, squash, daily_cap_min=180):
    """Blocks for the rest of today.

    Schedules the *daily rate* needed to finish on time, not the whole task.
    A procrastinator ignores a 4 hour block; 70 minutes is a thing you can start.
    """
    slots = free_slots(now.date(), cfg, squash, after=now.hour * 60 + now.minute + 10)
    live = [a for a in assignments
            if not a.get("submitted") and not a.get("done") and a.get("due")]
    live.sort(key=lambda a: a["due"])

    # how much of each task belongs to today
    quota = []
    for a in live:
        due = datetime.datetime.fromisoformat(a["due"].replace("Z", "+00:00")).astimezone(now.tzinfo)
        days = max(1, (due.date() - now.date()).days)
        share = int(min(a["hours"] * 60, max(MIN_BLOCK, round(a["hours"] * 60 / days))))
        quota.append([a, share])

    blocks, budget = [], daily_cap_min
    for s, e in slots:
        cur = s
        while cur + MIN_BLOCK <= e and budget >= MIN_BLOCK:
            nxt = next((q for q in quota if q[1] >= MIN_BLOCK), None)
            if not nxt:
                break
            a, remaining = nxt
            length = int(min(MAX_BLOCK, remaining, e - cur, budget))
            if length < MIN_BLOCK:
                break
            already = any(b["task"] == a["name"] for b in blocks)
            blocks.append({"start": hhmm(cur), "end": hhmm(cur + length),
                           "minutes": length, "course": a["course"],
                           "task": a["name"], "aid": a.get("id"),
                           "continuation": already,
                           "first_step": ("Pick up where you stopped. Do not re-read what you already did."
                                          if already else first_step(a))})
            nxt[1] -= length
            budget -= length
            cur += length + 15
        if budget < MIN_BLOCK:
            break
    return blocks


def first_step(a):
    """The smallest possible opening move. Starting is the hard part, not finishing."""
    n = (a.get("name") or "").lower()
    c = a.get("course", "")
    if "lab" in n:
        return "Open the lab spec and create the project folder. Nothing else."
    if c == "MAT 211":
        return "Open the Overleaf template and paste in question 1. Don't solve it yet."
    if c == "MAT 230":
        return "Write out question 1 by hand. Just the question."
    if c == "DSC 215":
        return "Open RStudio and load the dataset."
    if c == "CPS 112":
        return "Open the starter file and get it compiling."
    return "Open the file and read the first question out loud."
