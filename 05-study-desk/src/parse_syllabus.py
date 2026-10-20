#!/usr/bin/env python3
"""Parse the course schedule tables into structured JSON the guide builder can use.

MAT 230's syllabus PDF and CPS 112's Canvas page both carry a class-by-class table
(date, topic, readings/problems). That table is what makes a real study guide possible:
it says exactly which sections a given test covers and which problems the professor assigned.
"""
import json, os, re, html, urllib.request, datetime

YEAR = 2026
MONTHS = {"aug":8,"sept":9,"sep":9,"oct":10,"nov":11,"dec":12,"jan":1,"feb":2,"mar":3,"apr":4,"may":5}
OUT = os.path.expanduser("~/.study-desk/syllabus.json")

def canvas_env():
    o={}
    for line in open(os.path.expanduser("~/.canvas_env")):
        line=line.strip()
        if line and not line.startswith("#") and "=" in line:
            k,v=line.split("=",1); o[k.strip()]=v.strip()
    return o

def clean(b):
    t = html.unescape(re.sub("<[^>]+>", " ", b or ""))
    return re.sub(r"\s+", " ", t).strip()

def parse_mat230(txt):
    """Rows look like:  'Sept 9' / '3.4 Eigenvalues and Diagonalization' / '3.2: 1(b), (d), 4(b)' / '1 hour'"""
    lines = [l.strip() for l in txt.splitlines()]
    start = next((i for i,l in enumerate(lines) if l.startswith("Schedule for MAT 230")), 0)
    lines = lines[start:]
    datepat = re.compile(r"^(Aug|Sept|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2})(\s*[-–]\s*\d{1,2})?$", re.I)
    rows, cur = [], None
    for l in lines:
        if not l:
            continue
        m = datepat.match(l)
        if m:
            if cur: rows.append(cur)
            mo = MONTHS[m.group(1).lower().rstrip(".")]
            cur = {"date": "%d-%02d-%02d" % (YEAR, mo, int(m.group(2))), "lines": []}
        elif cur is not None:
            cur["lines"].append(l)
    if cur: rows.append(cur)

    out = []
    for r in rows:
        ls = r["lines"]
        topic = ls[0] if ls else ""
        hw, hours = "", ""
        for l in ls[1:]:
            if re.match(r"^[\d.]+\s*hours?$|^\.\d+\s*hours?$", l, re.I):
                hours = l
            elif re.match(r"^\d+\.\d+\s*:", l) or re.search(r"\d+\.\d+\s*:", l):
                hw = (hw + " " + l).strip()
        sections = re.findall(r"\b(\d+\.\d+)\b", topic)
        out.append({"date": r["date"], "topic": topic, "daily_hw": hw,
                    "time": hours, "sections": sections,
                    "is_test": bool(re.search(r"\btest\s*\d", topic, re.I)),
                    "is_review": bool(re.search(r"review", topic, re.I)),
                    "is_lab": bool(re.search(r"\blab\b", topic, re.I))})
    return out

def parse_cps112(txt):
    """'(8/25) Java Overview Reading: 1.1, 1.7 Slides: 01-Introducing Java.pdf ...'"""
    out = []
    parts = re.split(r"\((\d{1,2})/(\d{1,2})\)", txt)
    for i in range(1, len(parts)-2, 3):
        mo, day, body = int(parts[i]), int(parts[i+1]), parts[i+2].strip()
        topic = re.sub(r"\s+", " ", body.split("Reading")[0].split("Slides")[0]).strip(" :.-")
        rd = re.search(r"Readings?:\s*([^A-Z]*?)(?:Slides|Code|$)", body)
        sl = re.search(r"Slides:\s*(.*?)(?:Code:|Editor:|Java Install|$)", body)
        norm = lambda x: re.sub(r"\s+", " ", x).strip(" ,.")
        out.append({"date": "%d-%02d-%02d" % (YEAR, mo, day), "topic": topic,
                    "readings": norm(rd.group(1)) if rd else "",
                    "slides": norm(sl.group(1)) if sl else ""})
    return out

def main():
    syl = os.path.expanduser("~/.study-desk/syl/")
    data = {"generated": datetime.datetime.now().isoformat(), "courses": {}}

    p = syl + "MAT230_Syll_MAT_230_F26.txt"
    if os.path.exists(p):
        data["courses"]["MAT 230"] = {
            "canvas_id": "25929", "prof": "Prof. A",
            "ai_policy": "Per the professor, see the syllabus.",
            "textbook": "Andrilli & Hecker, Elementary Linear Algebra 4th ed",
            "pdf_page_offset": 30,
            "assessments": [{"name":"Test 1","date":"2026-09-16","covers":"Chapters 2 and 3"},
                            {"name":"Test 2","date":"2026-10-23","covers":"Chapters 4 and 5"},
                            {"name":"Test 3","date":"2026-11-13","covers":"Ch 6 and 8.10-8.11"}],
            "schedule": parse_mat230(open(p).read())}

    cfg = canvas_env()
    H, T = cfg["CANVAS_HOST"].rstrip("/"), cfg["CANVAS_TOKEN"]
    try:
        r = urllib.request.Request(H + "/api/v1/courses/25520/pages/readings-and-slides-mod-1-2",
                                   headers={"Authorization": "Bearer " + T})
        body = clean(json.load(urllib.request.urlopen(r, timeout=40)).get("body"))
        data["courses"]["CPS 112"] = {
            "canvas_id": "25520", "prof": "Brad McDanel",
            "ai_policy": "Not stated on the Canvas pages. Treat conservatively: guides "
                         "may explain concepts, never produce submittable code.",
            "textbook": "Goodrich, Data Structures and Algorithms in Java",
            "schedule": parse_cps112(body)}
    except Exception as e:
        print("cps112 fetch failed:", e)

    data["courses"]["DSC 215"] = {
        "canvas_id": "25857", "prof": "Prof. B",
        "ai_policy": "Permitted as a reference for understanding topics. NOT permitted "
                     "during in-class evaluations. Guides are fine.",
        "quiz_rule": "Every second Thursday, 20% of grade. A quiz never covers material "
                     "from the Tuesday class immediately before it. Lowest quiz dropped.",
        "schedule": []}
    data["courses"]["ANT 100"] = {
        "canvas_id": "25561", "prof": "Prof. C",
        "ai_policy": "May be used to get started. Never to generate content that is "
                     "turned in. Guides are fine, drafted prose for submission is not.",
        "grading_note": "Engagement 20-25% is a conduct grade earned in class on paper. "
                        "Research proposal 35%. Exam only 10%.",
        "schedule": []}

    json.dump(data, open(OUT, "w"), indent=1)
    for c, v in data["courses"].items():
        print("%-9s %3d schedule rows" % (c, len(v.get("schedule", []))))
    print("->", OUT)

if __name__ == "__main__":
    main()
