"""Write paths for the PA. Things Teerth adds himself, from the browser."""
import json, os, re, datetime

BASE = os.path.expanduser("~/.canvas-pa")
NOTES_ROOT = os.path.expanduser("~/Desktop/F&M Notes")
TASKS = os.path.join(BASE, "tasks.json")
OVERRIDES = os.path.join(BASE, "squash_overrides.json")


def _load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def _save(p, d):
    json.dump(d, open(p, "w"), indent=1)


# ---------- manual tasks ----------
def tasks():
    return _load(TASKS, [])


def add_task(course, name, due, hours, now):
    t = {"id": "m" + now.strftime("%y%m%d%H%M%S"),
         "course": course or "General", "name": name.strip(),
         "due": due, "hours": float(hours or 1.0),
         "manual": True, "created": now.isoformat()}
    ts = tasks()
    ts.append(t)
    _save(TASKS, ts)
    return t


def delete_task(tid):
    ts = [t for t in tasks() if t["id"] != tid]
    _save(TASKS, ts)
    return len(ts)


# ---------- quick notes ----------
def add_note(course, text, now):
    """Append to today's quick-capture file for that course."""
    safe = re.sub(r"[^A-Za-z0-9 ]", "", course or "General").strip() or "General"
    d = os.path.join(NOTES_ROOT, safe)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{now.date().isoformat()} quick.md")
    new = not os.path.exists(path)
    with open(path, "a") as f:
        if new:
            f.write(f"# {safe} · {now.strftime('%A %d %B %Y')}\n\n")
        f.write(f"- {text.strip()}   _({now.strftime('%H:%M')})_\n")
    return {"path": path, "created": new}


def add_question(course, text, now):
    """Questions get their own heading so notes.open_questions() finds them."""
    safe = re.sub(r"[^A-Za-z0-9 ]", "", course or "General").strip() or "General"
    d = os.path.join(NOTES_ROOT, safe)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{now.date().isoformat()} quick.md")
    body = open(path).read() if os.path.exists(path) else f"# {safe}\n\n"
    if "## questions" not in body.lower():
        body += "\n## questions\n"
    lines = body.rstrip().split("\n")
    # insert under the questions heading
    for i, l in enumerate(lines):
        if l.strip().lower().startswith("## question"):
            lines.insert(i + 1, f"- {text.strip()}")
            break
    open(path, "w").write("\n".join(lines) + "\n")
    return {"path": path}


# ---------- squash edits ----------
def overrides():
    return _load(OVERRIDES, {"cancelled": [], "added": []})


def cancel_squash(date, start):
    o = overrides()
    key = f"{date}|{start}"
    if key not in o["cancelled"]:
        o["cancelled"].append(key)
    _save(OVERRIDES, o)
    return o


def uncancel_squash(date, start):
    o = overrides()
    o["cancelled"] = [k for k in o["cancelled"] if k != f"{date}|{start}"]
    _save(OVERRIDES, o)
    return o


def add_squash(date, start, end, title, location=""):
    o = overrides()
    o["added"].append({"date": date, "start": start, "end": end,
                       "title": title or "Squash Practice", "location": location})
    _save(OVERRIDES, o)
    return o


def apply_overrides(events):
    """Fold cancellations and additions into the scraped Teamworks schedule."""
    o = overrides()
    cancelled = set(o.get("cancelled", []))
    out = [e for e in events if f"{e['date']}|{e['start']}" not in cancelled]
    out += o.get("added", [])
    out.sort(key=lambda e: (e["date"], e["start"]))
    return out
