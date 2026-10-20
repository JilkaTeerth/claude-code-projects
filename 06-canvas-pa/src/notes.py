"""Reads Teerth's own course notes so the PA can brief him from them."""
import os, re, datetime

NOTES_ROOT = os.path.expanduser("~/Desktop/F&M Notes")
EXT = (".md", ".txt", ".markdown")


def course_dir(code):
    return os.path.join(NOTES_ROOT, code)


def list_notes(code):
    d = course_dir(code)
    if not os.path.isdir(d):
        return []
    out = []
    for fn in os.listdir(d):
        if fn.startswith("_") or not fn.lower().endswith(EXT):
            continue
        p = os.path.join(d, fn)
        try:
            st = os.stat(p)
        except OSError:
            continue
        out.append({"file": fn, "path": p, "mtime": st.st_mtime,
                    "size": st.st_size,
                    "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat()})
    out.sort(key=lambda x: x["mtime"], reverse=True)
    return out


def read_note(path, limit=4000):
    try:
        return open(path, errors="replace").read()[:limit]
    except OSError:
        return ""


def open_questions(code):
    """Anything under a '## questions' heading in your notes, for office hours."""
    qs = []
    for n in list_notes(code):
        txt = read_note(n["path"])
        for m in re.finditer(r'^##+\s*questions?\s*$(.*?)(?=^##\s|\Z)',
                             txt, re.I | re.M | re.S):
            for line in m.group(1).split("\n"):
                line = line.strip().lstrip("-*• ").strip()
                if len(line) > 3:
                    qs.append({"q": line, "from": n["file"], "course": code})
    return qs


def latest_summary(code, chars=600):
    ns = list_notes(code)
    if not ns:
        return None
    txt = read_note(ns[0]["path"], chars * 2)
    body = re.sub(r'\n{3,}', '\n\n', txt).strip()
    return {"file": ns[0]["file"], "modified": ns[0]["modified"],
            "excerpt": body[:chars]}


def coverage(code, days=14):
    """Have you actually written anything lately for this course?"""
    ns = list_notes(code)
    if not ns:
        return {"count": 0, "days_since": None, "stale": True}
    newest = max(n["mtime"] for n in ns)
    since = (datetime.datetime.now() - datetime.datetime.fromtimestamp(newest)).days
    return {"count": len(ns), "days_since": since, "stale": since > 7}
