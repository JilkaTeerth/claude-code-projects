import json, sys, urllib.request
try:
    d = json.load(urllib.request.urlopen("http://localhost:7373/api/state", timeout=8))
except Exception:
    sys.exit("PA not responding. Try: pa restart")

f = d.get("focus")
print("\nTHE ONE THING")
if f:
    print(f"  {f['course']} · {f['name']}   due {f['due_local']} · about {f['hours']}h")
else:
    print("  nothing due")

if d.get("plan"):
    print("\nTODAY")
    for b in d["plan"]:
        print(f"  {b['start']}-{b['end']}  {b['course']:<9} {b['task'][:40]}")
        print(f"      -> {b['first_step']}")

if d.get("delay"):
    print("\nCOST OF DELAY")
    for r in d["delay"]:
        print(f"  start {r['label']:<14} {r['hours_per_day']}h per day")

if d.get("overdue"):
    print("\nOVERDUE")
    for a in d["overdue"]:
        print(f"  {a['course']}  {a['name']}   was due {a['due_local']}")

cb = d.get("class_brief")
if cb:
    print(f"\nNEXT CLASS  {cb['code']} · {cb['prof']}")
    if cb.get("posted"):
        print("  posted:", ", ".join(p["name"] for p in cb["posted"]))
    ns = cb.get("notes_state") or {}
    print(f"  your notes: {ns.get('count', 0)}"
          + ("" if ns.get("days_since") is None else f", last {ns['days_since']}d ago"))

ns = d.get("next_squash")
if ns:
    print(f"\nNEXT SQUASH  {ns['date']} {ns['start']}  {ns['title']}")

cal = d.get("calibration") or {}
if cal:
    print("\nESTIMATE CORRECTION")
    for c, v in cal.items():
        print(f"  {c}: {v['factor']}x  ({v['samples']} check-ins)")
print()
