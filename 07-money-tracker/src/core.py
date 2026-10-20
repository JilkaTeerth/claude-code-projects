"""Money core: the database, Plaid sync, and every number the page and the CLI show.

Stdlib only, same reasoning as the Study Desk: fewer moving parts, louder failures.
The whole design is built around one fact about Teerth's spending: nothing big hurts,
the drip does. So every outflow is flagged, the budget is weekly (a leak shows after
three days, not twenty-five), and the page leads with "you're fine" when he is fine.
"""
import datetime, json, math, os, re, sqlite3, urllib.request, urllib.error, zoneinfo

HOME    = os.path.dirname(os.path.abspath(__file__))
DB      = os.environ.get("MONEY_DB", os.path.join(HOME, "money.db"))
ENVFILE = os.path.expanduser("~/.money_env")
TZ      = zoneinfo.ZoneInfo("America/New_York")


CATS = ["Dinners out", "Snacks", "Groceries", "Drinks", "Gummies", "Transport", "Essentials", "Subscriptions", "Events", "Stuff", "Minnesota", "Other"]

# ---------------------------------------------------------------- env / db

def env():
    o = {}
    if os.path.exists(ENVFILE):
        for line in open(ENVFILE):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                o[k.strip()] = v.strip().strip('"').strip("'")
    return o

def set_env(key, value):
    lines, found = [], False
    if os.path.exists(ENVFILE):
        for line in open(ENVFILE):
            if line.split("=", 1)[0].strip() == key:
                lines.append(f"{key}={value}\n"); found = True
            else:
                lines.append(line if line.endswith("\n") else line + "\n")
    if not found:
        lines.append(f"{key}={value}\n")
    with open(ENVFILE, "w") as f:
        f.writelines(lines)
    os.chmod(ENVFILE, 0o600)

SCHEMA = """
create table if not exists tx(
  id text primary key, date text, name text, merchant text, amount real,
  pfc text, pfc_detail text, pending int default 0, source text default 'plaid',
  kind text,              -- spend | transfer | income
  category text,
  verdict text,           -- null = in the inbox | worth | regret | big | wish
  bigone_id int, wish_id int, note text, seen_at text);
create table if not exists rules(merchant text primary key, category text);
create table if not exists bigones(id integer primary key, label text, amount real,
  created text, status text default 'open');
create table if not exists wish(id integer primary key, name text, price real,
  where_ text, created text, bought_tx text);
create table if not exists swipes(week text primary key, used int);
create table if not exists notes(month text primary key, text text);
create table if not exists state(k text primary key, v text);
"""

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    cols = lambda t: {r[1] for r in c.execute(f"pragma table_info({t})")}
    if "feel" not in cols("tx"):
        c.execute("alter table tx add column feel text")        # need | want | impulse
    if "per_week" not in cols("wish"):
        c.execute("alter table wish add column per_week real")  # what he puts aside for it each week
    if not get(c, "start"):
        put(c, "start", monday(today()).isoformat())
    return c

def get(c, k, default=None):
    r = c.execute("select v from state where k=?", (k,)).fetchone()
    return r["v"] if r else default

def put(c, k, v):
    c.execute("insert into state(k,v) values(?,?) on conflict(k) do update set v=excluded.v", (k, v))
    c.commit()


# ---------------------------------------------------------------- dates

def now():   return datetime.datetime.now(TZ)
def today(): return now().date()
def monday(d): return d - datetime.timedelta(days=d.weekday())
def D(s):    return datetime.date.fromisoformat(s)


# ---------------------------------------------------------------- classification

def mkey(name):
    """Merchant key for rules: 'SQ *CHIPOTLE 1234 LANCASTER' -> 'chipotle lancaster'."""
    s = re.sub(r"^(sq|tst|sp|pp|paypal|dd|uber)\s*\*\s*", "", (name or "").lower())
    s = re.sub(r"[#\d*]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:40]

# Transfers that stay his money (savings, own accounts, card payoff) never count.
# Venmo/Zelle/ATM cash DO count: for a student that is dinner, drinks and splitting.
OWN_MONEY = {"TRANSFER_OUT_SAVINGS", "TRANSFER_OUT_ACCOUNT_TRANSFER",
             "TRANSFER_OUT_INVESTMENT_AND_RETIREMENT_FUNDS", "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT"}

def kind_of(amount, pfc, detail):
    if amount <= 0:
        return "income"                  # refunds and money in: never counted as spending
    if detail in OWN_MONEY or pfc == "LOAN_PAYMENTS":
        return "transfer"
    return "spend"

def guess_category(pfc, detail, name):
    d, n = detail or "", (name or "").lower()
    if "BEER_WINE_AND_LIQUOR" in d or re.search(r"liquor|wine|spirits|brew|\bbar\b|pub|tavern", n):
        return "Drinks"
    if re.search(r"icloud|subscription|\bsub\b|spotify|netflix|hulu|youtube premium|rocket money|apple\.com|chatgpt|prime", n):
        return "Subscriptions"
    if re.search(r"dispens|cbd|delta|smoke|vape|thc|gumm|green|weed|edible|pre.?roll", n):
        return "Gummies"
    if re.search(r"uber|lyft|taxi|amtrak|bus|train|septa|rrta|gas\b|parking", n) and "eats" not in n:
        return "Transport"
    if re.search(r"grocer|giant|weis|aldi|trader joe|whole foods|target|walmart|costco|lidl|market", n):
        return "Groceries"
    if re.search(r"laundry|soap|shampoo|toilet|pharma|medic|haircut|barber|print|stationery|charger", n):
        return "Essentials"
    if re.search(r"starbucks|dunkin|coffee|cafe|vending|snack|chips|candy|cookie|insomnia|ice cream|boba|munch", n):
        return "Snacks"
    if re.search(r"chipotle|mcdonald|wendy|taco bell|chick-fil|subway|panera|domino|pizza|sweetgreen|five guys|"
                 r"shake shack|burger|sushi|thai|grill|kitchen|diner|restaurant|doordash|uber eats|grubhub", n):
        return "Dinners out"
    if pfc == "FOOD_AND_DRINK":
        if any(x in d for x in ("GROCER", "VENDING", "COFFEE")):
            return "Snacks"
        return "Dinners out"
    if "CONVENIENCE" in d or re.search(r"wawa|sheetz|cvs|rite aid|7-eleven|walgreens", n):
        return "Snacks"
    # Events = tickets and nights out. Streaming and app subscriptions are not events.
    if "SPORTING_EVENTS" in d or "CASINOS" in d or re.search(r"ticket|eventbrite|cinema|theat|bowling", n):
        return "Events"
    if pfc == "GENERAL_MERCHANDISE" or re.search(r"vinted|amazon|depop|ebay", n):
        return "Stuff"
    return "Other"


# ---------------------------------------------------------------- ingest

def upsert(c, t):
    """t: dict with id,date,name,merchant,amount,pfc,pfc_detail,pending,source[,replaces]."""
    old = c.execute("select * from tx where id=?", (t["id"],)).fetchone()
    # A posted charge replaces its pending twin: carry his tags across, don't re-flag it.
    twin = None
    if not old and t.get("replaces"):
        twin = c.execute("select * from tx where id=?", (t["replaces"],)).fetchone()
        c.execute("delete from tx where id=?", (t["replaces"],))
    keep = old or twin
    k = kind_of(t["amount"], t["pfc"], t["pfc_detail"])
    key = mkey(t["merchant"] or t["name"])
    rule = c.execute("select category from rules where merchant=?", (key,)).fetchone()
    cat = keep["category"] if keep else (rule["category"] if rule else
                                         guess_category(t["pfc"], t["pfc_detail"], t["merchant"] or t["name"]))
    verdict = keep["verdict"] if keep else None
    bigone = keep["bigone_id"] if keep else None
    wish = keep["wish_id"] if keep else None
    note = keep["note"] if keep else None
    if not keep and k == "spend":
        bigone = match_bigone(c, t)
        if bigone:
            verdict, cat = "big", ("Minnesota" if "minnesota" in label_of(c, bigone).lower() else cat)
    if k != "spend" and verdict is None:
        verdict = "n/a"                  # transfers and money in never hit the inbox
    # The first sync pulls ~6 months. History before he started tracking fills the charts,
    # it doesn't bury him in an inbox of 200 things to review.
    if verdict is None and t["date"] < get(c, "start"):
        verdict = "past"
    c.execute("""insert or replace into tx(id,date,name,merchant,amount,pfc,pfc_detail,pending,source,
                 kind,category,verdict,bigone_id,wish_id,note,seen_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (t["id"], t["date"], t["name"], t["merchant"], t["amount"], t["pfc"], t["pfc_detail"],
               int(bool(t.get("pending"))), t.get("source", "plaid"), k, cat, verdict, bigone, wish, note,
               keep["seen_at"] if keep else now().isoformat(timespec="seconds")))

def label_of(c, bid):
    r = c.execute("select label from bigones where id=?", (bid,)).fetchone()
    return r["label"] if r else ""

def match_bigone(c, t):
    """A charge within 20% of an open heads-up's amount, within 14 days of him announcing it."""
    for b in c.execute("select * from bigones where status='open'"):
        age = (D(t["date"]) - D(b["created"][:10])).days
        if -3 <= age <= 14 and abs(t["amount"] - b["amount"]) <= 0.2 * b["amount"]:
            c.execute("update bigones set status='matched' where id=?", (b["id"],))
            return b["id"]
    return None


# ---------------------------------------------------------------- plaid

def plaid(path, body):
    e = env()
    host = {"sandbox": "https://sandbox.plaid.com",
            "production": "https://production.plaid.com"}[e.get("PLAID_ENV", "sandbox")]
    body = {"client_id": e["PLAID_CLIENT_ID"], "secret": e["PLAID_SECRET"], **body}
    req = urllib.request.Request(host + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as err:
        detail = json.loads(err.read() or b"{}")
        raise RuntimeError(f"Plaid {path}: {detail.get('error_code')} {detail.get('error_message')}")

def plaid_ready():
    e = env()
    return bool(e.get("PLAID_CLIENT_ID") and e.get("PLAID_SECRET"))

def link_token():
    e = env()
    body = {"user": {"client_user_id": "teerth"}, "client_name": "Money",
            "products": ["transactions"], "country_codes": ["US"], "language": "en",
            "transactions": {"days_requested": 180}}
    if e.get("PLAID_REDIRECT_URI"):
        body["redirect_uri"] = e["PLAID_REDIRECT_URI"]
    return plaid("/link/token/create", body)["link_token"]

def exchange(public_token):
    r = plaid("/item/public_token/exchange", {"public_token": public_token})
    set_env("PLAID_ACCESS_TOKEN", r["access_token"])
    c = db(); put(c, "cursor", "")
    return sync()

def sync():
    """Pull everything new since the stored cursor. Safe to run any number of times."""
    e = env()
    if not e.get("PLAID_ACCESS_TOKEN"):
        return {"ok": False, "why": "no bank linked yet"}
    c = db()
    cursor, added, modified, removed = get(c, "cursor", ""), 0, 0, 0
    while True:
        body = {"access_token": e["PLAID_ACCESS_TOKEN"], "count": 500}
        if cursor:
            body["cursor"] = cursor
        r = plaid("/transactions/sync", body)
        for t in r["added"] + r["modified"]:
            pfc = t.get("personal_finance_category") or {}
            upsert(c, {"id": t["transaction_id"], "date": t.get("authorized_date") or t["date"],
                       "name": t["name"], "merchant": t.get("merchant_name"), "amount": t["amount"],
                       "pfc": pfc.get("primary"), "pfc_detail": pfc.get("detailed"),
                       "pending": t["pending"], "replaces": t.get("pending_transaction_id")})
        for t in r["removed"]:
            # A pending charge that posted is handled in upsert; don't delete the tagged twin.
            c.execute("delete from tx where id=?", (t["transaction_id"],))
        added += len(r["added"]); modified += len(r["modified"]); removed += len(r["removed"])
        cursor = r["next_cursor"]
        if not r["has_more"]:
            break
    c.commit()
    put(c, "cursor", cursor)
    put(c, "last_sync", now().isoformat(timespec="seconds"))
    return {"ok": True, "added": added, "modified": modified, "removed": removed}


# ---------------------------------------------------------------- apple pay taps
# An iPhone Shortcuts automation ("When I tap any card in Wallet") appends one line per tap:
#   2026-10-01T14:03:00-04:00|Chipotle|$13.40
# to iCloud Drive/Shortcuts/money-taps.txt, which syncs to this Mac. Reading it is idempotent:
# each line hashes to a stable id, so re-reading the whole file never duplicates anything.
TAPS = os.path.expanduser("~/Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/money-taps.txt")

def import_taps():
    try:
        lines = open(TAPS, encoding="utf-8", errors="replace").read().splitlines()
    except (FileNotFoundError, PermissionError):
        lines = []
    return ingest_tap_lines(lines)

def tap_date(raw):
    """ISO from Shortcuts, or whatever Notes kept ('1 Oct 2026 at 2:03 PM', 'Oct 1, 2026, 14:03')."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    head = re.split(r"\s+at\s+|,\s*\d{1,2}:\d{2}|\s+\d{1,2}:\d{2}", raw)[0].strip().rstrip(",")
    for fmt in ("%d %b %Y", "%b %d, %Y", "%d %B %Y", "%B %d, %Y", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(head, fmt).date().isoformat()
        except ValueError:
            pass
    return None

def ingest_tap_lines(lines):
    import hashlib
    c, n = db(), 0
    for line in lines:
        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 3:
            continue
        d = tap_date(parts[0])
        if not d:
            continue
        parts[0] = d + parts[0][10:] if parts[0][:10] == d else parts[0]
        tid = "tap-" + hashlib.sha1(line.strip().encode()).hexdigest()[:16]
        if c.execute("select 1 from tx where id=?", (tid,)).fetchone():
            continue
        try:
            amt = float(re.sub(r"[^\d.]", "", parts[2].replace(",", "")) or 0)
        except ValueError:
            continue
        if amt <= 0:
            continue
        upsert(c, {"id": tid, "date": d, "name": parts[1] or "Apple Pay", "merchant": parts[1] or None,
                   "amount": amt, "pfc": None, "pfc_detail": None, "pending": 0, "source": "applepay"})
        n += 1
    c.commit()
    if n:
        put(c, "last_tap", now().isoformat(timespec="seconds"))
    return n


# The iPhone automation appends taps to an Apple Note ("Money Taps"). The Mac can't read the
# Notes database without Full Disk Access, so instead it runs a tiny synced shortcut,
# "Money Export" (Find Notes named Money Taps), through the official `shortcuts` CLI.
EXPORT_SHORTCUT = "Money Export"

def import_note_taps():
    import subprocess, tempfile
    out = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name
    try:
        r = subprocess.run(["shortcuts", "run", EXPORT_SHORTCUT, "--output-path", out],
                           capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return {"ok": False, "why": (r.stderr or r.stdout).strip()[:200]}
        text = open(out, encoding="utf-8", errors="replace").read()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"ok": False, "why": str(e)}
    finally:
        try: os.remove(out)
        except OSError: pass
    text = re.sub(r"<br\s*/?>|</(div|p)>", "\n", text)      # in case the note comes back as HTML
    text = re.sub(r"<[^>]+>", "", text)
    return {"ok": True, "added": ingest_tap_lines(text.splitlines())}


# ---------------------------------------------------------------- csv fallback

def import_csv(path):
    """Bank CSV export. Finds date/description/amount columns by header name."""
    import csv, hashlib
    c, n = db(), 0
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0
    cols = {h.lower().strip(): h for h in rows[0]}
    pick = lambda *names: next((cols[x] for x in cols if any(nm in x for nm in names)), None)
    dcol, ncol = pick("date"), pick("description", "merchant", "payee", "name")
    acol, debit, credit = pick("amount"), pick("debit", "withdrawal"), pick("credit", "deposit")
    for r in rows:
        raw = r[dcol].strip()
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try: d = datetime.datetime.strptime(raw, fmt).date(); break
            except ValueError: d = None
        if not d:
            continue
        num = lambda v: float(re.sub(r"[^\d.\-]", "", v) or 0)
        if acol:
            amt = -num(r[acol])          # banks export spending as negative; Plaid uses positive
        else:
            amt = num(r.get(debit) or "0") - num(r.get(credit) or "0")
        name = r[ncol].strip()
        tid = "csv-" + hashlib.sha1(f"{d}|{name}|{amt}".encode()).hexdigest()[:16]
        upsert(c, {"id": tid, "date": d.isoformat(), "name": name, "merchant": None, "amount": amt,
                   "pfc": None, "pfc_detail": None, "pending": 0, "source": "csv"})
        n += 1
    c.commit()
    return n


# ---------------------------------------------------------------- the pot
# Rebuilt 2026-10-06. One pot (everything he has) and no end date: the goal is to make it last
# as long as he possibly can. So the score is the RUNWAY, the day the money runs out at the rate
# he actually spends. Every spend is priced in days of money. A good week pushes the date later.
# No allowances, no automatic funds: he adds what he spent, the page does the arithmetic.

POT_DEFAULT = 600.00  # demo value
FEELS = ("need", "want", "impulse")
# The rate leans on a prior worth two weeks of data: the $250/month ceiling he stated on
# 2026-09-30 (~$X/day). Without it, day one's $14 burrito says "broke by November" and a
# quiet day says "set till 2036".
PRIOR_DAY, PRIOR_DAYS = 250 * 12 / 365, 14
# The floor he set on 2026-10-06: "at least till Jan". The budget is built so the pot lasts
# through 31 Jan 2027; anything past that is the runway score. Each Monday the week's budget is
# what's left split over the weeks to the floor, so an over week quietly shrinks the rest.
FLOOR = datetime.date(2027, 1, 31)

def pot_cfg(c):
    if not get(c, "pot_start"):
        put(c, "pot_start", today().isoformat())
    return float(get(c, "pot", POT_DEFAULT)), D(get(c, "pot_start"))

def set_pot(amount):
    c = db(); put(c, "pot", str(float(amount)))

def counted(rows):
    """Everyday spending: what sets his rate. Wish buys leave the pot but aren't a habit."""
    return [r for r in rows if r["kind"] == "spend" and r["verdict"] not in ("big", "wish")]

def between(c, a, b):
    return c.execute("select * from tx where date>=? and date<? order by date desc, seen_at desc",
                     (a.isoformat(), b.isoformat())).fetchall()

def since_start(c):
    _, s = pot_cfg(c)
    return c.execute("select * from tx where date>=? order by date desc, seen_at desc", (s.isoformat(),)).fetchall()

def runway_at(c, d, rows=None):
    """Where the money runs out, judged at the end of day d."""
    pot, s = pot_cfg(c)
    rows = rows if rows is not None else since_start(c)
    upto = [r for r in rows if r["kind"] == "spend" and r["date"] <= d.isoformat()]
    habit = sum(r["amount"] for r in counted(upto))
    bal = pot - sum(r["amount"] for r in upto)
    days = max(0, (d - s).days + 1)
    rate = (habit + PRIOR_DAY * PRIOR_DAYS) / (days + PRIOR_DAYS)    # the prior is two weeks' weight, fading as days pile up
    left = bal / rate if rate > 0 else 3650
    return {"rate": rate, "balance": bal, "days": left, "date": d + datetime.timedelta(days=left)}

def days_of(c, amount, rate=None):
    return amount / (rate or runway_at(c, today())["rate"])

def ledger(c):
    pot, s = pot_cfg(c)
    rows = since_start(c)
    t = today()
    now = runway_at(c, t, rows)
    wk = monday(t)
    base = runway_at(c, max(wk, s) - datetime.timedelta(days=1), rows)      # before this week
    spends = counted(rows)
    wk_spent = round(sum(r["amount"] for r in spends if r["date"] >= wk.isoformat()), 2)
    # "Finish the week like this": project the rest of the week at this week's daily pace.
    elapsed = (t - max(wk, s)).days + 1
    hist, w = [], monday(s)
    while w < wk:
        a = runway_at(c, max(w, s) - datetime.timedelta(days=1), rows)
        b = runway_at(c, w + datetime.timedelta(days=6), rows)
        sp = round(sum(r["amount"] for r in spends if w.isoformat() <= r["date"] < (w + datetime.timedelta(days=7)).isoformat()), 2)
        hist.append({"week": w.isoformat(), "spent": sp, "moved": round((b["date"] - a["date"]).days, 0),
                     "before": a["date"].strftime("%-d %b"), "after": b["date"].strftime("%-d %b"),
                     "label": f"{w.strftime('%-d %b')} to {(w + datetime.timedelta(days=6)).strftime('%-d %b')}"})
        w += datetime.timedelta(days=7)
    # The daily line: the pot spread evenly from the start to the floor. Every day earns that much.
    # A quiet day's share STACKS (he asked for this 2026-10-06: "yo, u cud technically spend").
    # Spend more than the stack and the overdraft is spread over every day left to the floor.
    total_days = (FLOOR - s).days + 1
    base_day = pot / total_days
    elapsed = (t - s).days + 1
    spent_all = sum(r["amount"] for r in rows if r["kind"] == "spend")
    on_today = sum(r["amount"] for r in rows if r["kind"] == "spend" and r["date"] == t.isoformat())
    stack = base_day * elapsed - spent_all                       # what today can take
    remaining = max(1, (FLOOR - t).days)                         # days after today
    quiet, d = 0, t - datetime.timedelta(days=1)
    while d >= s and not any(r["kind"] == "spend" and r["date"] == d.isoformat() for r in rows):
        quiet += 1; d -= datetime.timedelta(days=1)
    budget = {"base_day": round(base_day, 2), "base_week": round(base_day * 7, 2),
              "today_left": round(stack, 2), "today_spent": round(on_today, 2),
              "stacked": round(stack + on_today - base_day, 2),   # carried in from earlier days
              "quiet": quiet, "remaining": remaining,
              "next_day": round(base_day + min(0.0, stack) / remaining, 2),
              "floor": FLOOR.isoformat(), "floor_label": FLOOR.strftime("%-d %b"),
              "on_track": now["date"] >= FLOOR}
    return {"pot": pot, "start": s.isoformat(), "balance": round(now["balance"], 2), "budget": budget,
            "spent_total": round(pot - now["balance"], 2),
            "rate_day": round(now["rate"], 2), "rate_week": round(now["rate"] * 7, 2),
            "runway_date": now["date"].date().isoformat() if hasattr(now["date"], "date") else now["date"].isoformat(),
            "runway_label": now["date"].strftime("%-d %b %Y"), "runway_days": int(now["days"]),
            "moved_week": int(round((now["date"] - base["date"]).days)), "base_label": base["date"].strftime("%-d %b"),
            "week": {"week": wk.isoformat(), "spent": wk_spent, "elapsed": elapsed,
                     "proj": round(wk_spent / elapsed * 7, 2) if elapsed else 0},
            "hist": hist}

def day_spend(c, d):
    return sum(r["amount"] for r in counted(between(c, d, d + datetime.timedelta(days=1))))

def month_bounds(d):
    a = d.replace(day=1)
    return a, (a + datetime.timedelta(days=32)).replace(day=1)


# ---------------------------------------------------------------- adding things
# One box. "chipotle 14" plus a tap on Need / Want / Impulse logs it, dated today.
# "beats pill 50-70" plus Wishlist adds a wish with a price range.

NUM = r"\$?(\d+(?:\.\d{1,2})?)"

def parse(text):
    """'chipotle 14.50' -> ('Chipotle', 14.5, None);  'beats pill 50-70' -> ('Beats pill', 70, 50)."""
    text = text or ""
    rng = re.search(NUM + r"\s*(?:-|–|to)\s*" + NUM, text)
    if rng:
        lo, hi = sorted((float(rng.group(1)), float(rng.group(2))))
        name = text[:rng.start()] + text[rng.end():]
    else:
        m = list(re.finditer(NUM, text))
        if not m:
            raise ValueError("no amount")
        hi, lo = float(m[-1].group(1)), None
        name = text[:m[-1].start()] + text[m[-1].end():]
    name = re.sub(r"\s+", " ", name.replace("$", " ")).strip(" -,.@") or "Something"
    return name[:1].upper() + name[1:], hi, lo

def add_expense(name, amount, feel="want", category=None, date=None):
    import uuid
    c = db()
    rule = c.execute("select category from rules where merchant=?", (mkey(name),)).fetchone()
    cat = category or (rule["category"] if rule else guess_category(None, None, name))
    tid = "m-" + uuid.uuid4().hex[:12]
    c.execute("""insert into tx(id,date,name,merchant,amount,pending,source,kind,category,verdict,feel,seen_at)
                 values(?,?,?,?,?,0,'manual','spend',?,'seen',?,?)""",
              (tid, (date or today().isoformat())[:10], name, name, float(amount), cat,
               feel if feel in FEELS else "want", now().isoformat(timespec="seconds")))
    c.commit()
    return tid

def delete_tx(tx_id):
    c = db()
    c.execute("update wish set bought_tx=null where bought_tx=?", (tx_id,))
    c.execute("delete from tx where id=?", (tx_id,)); c.commit()

def wish_cols(c):
    have = {r[1] for r in c.execute("pragma table_info(wish)")}
    for col, typ in (("price_lo", "real"), ("alt", "text"), ("base_runway", "text")):
        if col not in have:
            c.execute(f"alter table wish add column {col} {typ}")

def add_wish(name, price, lo=None, where=""):
    c = db(); wish_cols(c)
    cur = c.execute("insert into wish(name,price,price_lo,where_,created,base_runway) values(?,?,?,?,?,?)",
                    (name, float(price), lo, where, today().isoformat(), runway_at(c, today())["date"].isoformat()))
    c.commit()
    return cur.lastrowid

def set_alt(wish_id, alt):
    c = db(); wish_cols(c); c.execute("update wish set alt=? where id=?", (alt.strip() or None, wish_id)); c.commit()

def delete_wish(wish_id):
    c = db(); c.execute("delete from wish where id=? and bought_tx is null", (wish_id,)); c.commit()

def buy_wish(wish_id, price):
    """Bought it, at whatever it actually cost. Leaves the pot, doesn't count as a habit."""
    import uuid
    c = db()
    w = c.execute("select * from wish where id=?", (wish_id,)).fetchone()
    tid = "w-" + uuid.uuid4().hex[:12]
    c.execute("""insert into tx(id,date,name,merchant,amount,pending,source,kind,category,verdict,wish_id,feel,seen_at)
                 values(?,?,?,?,?,0,'manual','spend','Stuff','wish',?,'want',?)""",
              (tid, today().isoformat(), w["name"], w["name"], float(price), wish_id, now().isoformat(timespec="seconds")))
    c.execute("update wish set bought_tx=? where id=?", (tid, wish_id))
    c.commit()

def tag(tx_id, verdict=None, category=None, remember=True):
    c = db()
    t = c.execute("select * from tx where id=?", (tx_id,)).fetchone()
    if verdict:
        c.execute("update tx set verdict=? where id=?", (verdict, tx_id))
    if category:
        c.execute("update tx set category=? where id=?", (category, tx_id))
        if remember:
            c.execute("insert or replace into rules values(?,?)", (mkey(t["merchant"] or t["name"]), category))
    c.commit()


# ---------------------------------------------------------------- what the page says

def wishes(c, L):
    """Each wish priced in days of money, against the days he's earned by pushing the date out
    since he added it. Earned >= cost at the low price means he can have it and still be where
    he was the day he wanted it."""
    wish_cols(c)
    rate, out = L["rate_day"], []
    run = D(L["runway_date"])
    for w in c.execute("select * from wish order by bought_tx is not null, created, id"):
        d = dict(w)
        lo, hi = w["price_lo"] or w["price"], w["price"]
        steps = sorted({round(lo), round((lo + hi) / 2 / 5) * 5, round(hi)}) if hi > lo else [round(hi)]
        base = D((w["base_runway"] or L["runway_date"])[:10])
        earned = max(0, (run - base).days)
        cost = lambda p: max(1, math.ceil(p / rate)) if rate else 0
        d.update({"lo": lo, "hi": hi, "earned": earned,
                  "prices": [{"p": p, "days": cost(p), "ok": earned >= cost(p)} for p in steps],
                  "need_days": cost(lo), "ready": not w["bought_tx"] and earned >= cost(lo),
                  # shave this much a week and the cheapest price is earned in about 4 weeks
                  "shave": round(lo / 4, 0)})
        out.append(d)
    return out

def goal(c, L):
    return next((w for w in wishes(c, L) if not w["bought_tx"]), None)

def reaction(c, tx_id):
    t = c.execute("select * from tx where id=?", (tx_id,)).fetchone()
    L = ledger(c); g = goal(c, L); amt = t["amount"]
    days = amt / L["rate_day"] if L["rate_day"] else 0
    dtxt = f"{days:.1f} days of money" if days < 10 else f"{days:.0f} days of money"
    tail = f" Lasts till {L['runway_label']}."
    pct = f" {amt / g['lo'] * 100:.0f}% of the {g['name']}." if g else ""
    if t["feel"] == "need":
        return {"title": "Covered.", "line": f"That's {dtxt}, and it's what the money is for.{tail}"}
    if t["feel"] == "want":
        return {"title": "Fair, you wanted it.", "line": f"That's {dtxt}.{pct}{tail}"}
    a, b = month_bounds(today())
    imp = [r for r in counted(between(c, a, b)) if r["feel"] == "impulse"]
    return {"title": "Caught it. That's the hard part.",
            "line": f"That's {dtxt}. Impulse #{len(imp)} this month, ${sum(r['amount'] for r in imp):.2f} total.{tail}"}

def feel_split(rows):
    out = {f: {"n": 0, "amt": 0.0} for f in FEELS}
    for r in rows:
        x = out.get(r["feel"] or "want"); x["n"] += 1; x["amt"] = round(x["amt"] + r["amount"], 2)
    return out

def month_report(c, d=None):
    d = d or today()
    a, b = month_bounds(d)
    L = ledger(c)
    rows = counted([r for r in between(c, a, b) if r["date"] >= L["start"]])
    spent = round(sum(r["amount"] for r in rows), 2)
    f = feel_split(rows)
    cats = {}
    for r in rows:
        x = cats.setdefault(r["category"], {"n": 0, "amt": 0.0}); x["n"] += 1; x["amt"] = round(x["amt"] + r["amount"], 2)
    nxt = b.strftime("%B"); steps = []
    if f["impulse"]["amt"] and f["impulse"]["amt"] >= 0.15 * spent:
        steps.append(f"Impulses were ${f['impulse']['amt']:.0f} over {f['impulse']['n']} buy{'s' if f['impulse']['n'] != 1 else ''}, about {f['impulse']['amt'] / L['rate_day']:.0f} days of money. In {nxt}, anything unplanned waits ten minutes.")
    wants = {}
    for r in rows:
        if r["feel"] != "need":
            x = wants.setdefault(r["category"], {"n": 0, "amt": 0.0}); x["n"] += 1; x["amt"] += r["amount"]
    if wants:
        cat, x = max(wants.items(), key=lambda kv: kv[1]["amt"])
        if x["n"] >= 3:
            cap = max(1, math.floor(x["n"] * 0.7)); back = x["amt"] / x["n"] * (x["n"] - cap)
            steps.append(f"{cat} was the biggest want: {x['n']} times, ${x['amt']:.0f}. Cap it at {cap} in {nxt}, that's ${back:.0f} back, about {back / L['rate_day']:.0f} more days.")
    if L["rate_week"] > 0 and L["balance"] > 0:
        shave = max(5, round(L["rate_week"] * 0.15 / 5) * 5)
        later = D(L["runway_date"]) + datetime.timedelta(days=int(L["balance"] / max(0.01, L["rate_day"] - shave / 7) - L["runway_days"]))
        steps.append(f"You're running at ${L['rate_week']:.0f} a week, so the money lasts till {L['runway_label']}. ${shave:.0f} less a week and it's {later.strftime('%-d %b %Y')}.")
    if not steps:
        steps.append(f"Same again in {nxt}. Whatever you did, it worked.")
    return {"month": a.strftime("%Y-%m"), "label": a.strftime("%B"), "next": nxt, "spent": spent, "n": len(rows),
            "feels": f, "cats": sorted([{"cat": k, **v} for k, v in cats.items()], key=lambda x: -x["amt"]),
            "steps": steps[:3]}

def ceremony(c, L):
    """One moment at a time: a wish he's earned beats a week result."""
    for w in wishes(c, L):
        if w["ready"] and not get(c, f"cer:wish:{w['id']}"):
            return {"key": f"wish:{w['id']}", "kind": "wish", "name": w["name"], "lo": w["lo"], "hi": w["hi"],
                    "where": w["where_"], "earned": w["earned"], "need_days": w["need_days"], "wish_id": w["id"],
                    "alt": w.get("alt")}
    if L["hist"]:
        h = L["hist"][-1]
        wk_end = (D(h["week"]) + datetime.timedelta(days=6)).isoformat()
        logging = c.execute("select 1 from tx where kind='spend' and date<=?", (wk_end,)).fetchone()
        tracked = (D(wk_end) - D(L["start"])).days + 1
        # Only weeks he actually logged, with at least 4 tracked days and a real move in the date.
        if logging and tracked >= 4 and abs(h["moved"]) >= 2 and not get(c, f"cer:week:{h['week']}"):
            return {"key": f"week:{h['week']}", "kind": "win" if h["moved"] >= 0 else "fail", **h,
                    "runway_label": L["runway_label"], "rate_week": L["rate_week"]}
    return None

def ceremony_done(key):
    c = db(); put(c, "cer:" + key, now().isoformat(timespec="seconds"))

def summary():
    c = db()
    L = ledger(c)
    t = today()
    rows = [dict(r) for r in since_start(c) if r["kind"] == "spend"]
    days = []
    for i in range(7):
        d = monday(t) + datetime.timedelta(days=i)
        days.append({"d": d.isoformat(), "label": d.strftime("%a")[0], "future": d > t,
                     "before": d.isoformat() < L["start"], "spent": round(day_spend(c, d), 2) if d <= t else 0})
    lw = L["hist"][-1] if L["hist"] else None
    return {"today": t.isoformat(), "ledger": L, "tx": rows, "wishes": wishes(c, L), "goal": goal(c, L),
            "days": days, "last_week": lw,
            "last_week_feels": feel_split(counted(between(c, D(lw["week"]), D(lw["week"]) + datetime.timedelta(days=7)))) if lw else None,
            "report": month_report(c, t), "ceremony": ceremony(c, L), "insights": insights(c, L)}

def insights(c, L):
    """Cards about his own spending. Only ones the data can back: no insight from two receipts."""
    rows = counted(since_start(c))
    if not rows:
        return []
    rate = L["rate_day"] or 1
    dd = lambda amt: f"{amt / rate:.0f} day{'s' if round(amt / rate) != 1 else ''} of money"
    total = sum(r["amount"] for r in rows)
    out = []
    by_m = {}
    for r in rows:
        k = (r["merchant"] or r["name"]).strip().title()
        x = by_m.setdefault(k, {"n": 0, "amt": 0.0}); x["n"] += 1; x["amt"] += r["amount"]
    reg = max(by_m.items(), key=lambda kv: (kv[1]["n"], kv[1]["amt"]))
    if reg[1]["n"] >= 2:
        out.append({"k": "Your regular", "big": reg[0], "sub": f"{reg[1]['n']} times, ${reg[1]['amt']:.2f}. That's {dd(reg[1]['amt'])}."})
    big = max(rows, key=lambda r: r["amount"])
    out.append({"k": "Biggest single spend", "big": f"${big['amount']:.2f}", "sub": f"{big['name']}, {D(big['date']).strftime('%a %-d %b')}. {dd(big['amount']).capitalize()}."})
    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + r["amount"]
    named = {k: v for k, v in cats.items() if k != "Other"} or cats
    cat, amt = max(named.items(), key=lambda kv: kv[1])
    if len(rows) >= 3:
        out.append({"k": "Where most of it goes", "big": cat, "sub": f"{amt / total * 100:.0f}% of everything, ${amt:.2f}."})
    f = feel_split(rows)
    if len(rows) >= 3:
        wnt = f["want"]["amt"] + f["impulse"]["amt"]
        out.append({"k": "Wants vs needs", "big": f"{wnt / total * 100:.0f}% wants", "sub":
                    f"${wnt:.2f} on wants" + (f", ${f['impulse']['amt']:.2f} of it impulse" if f["impulse"]["n"] else "") + f". Needs ${f['need']['amt']:.2f}."})
    _, s = pot_cfg(c)
    span = (today() - s).days + 1
    if span >= 7:
        wd = [0.0] * 7
        for r in rows:
            wd[D(r["date"]).weekday()] += r["amount"]
        i = max(range(7), key=lambda j: wd[j])
        if wd[i] > 0.25 * total:
            out.append({"k": "Danger day", "big": ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"][i],
                        "sub": f"{wd[i] / total * 100:.0f}% of your spending lands on one day of the week."})
    spent_days = {r["date"] for r in rows}
    quiet = sum(1 for i in range(span) if (s + datetime.timedelta(days=i)).isoformat() not in spent_days)
    out.append({"k": "No-spend days", "big": f"{quiet} of {span}", "sub": "Each one pushes the date later on its own."})
    small = [r for r in rows if r["amount"] < 10]
    if len(small) >= 3:
        st = sum(r["amount"] for r in small)
        out.append({"k": "The drip", "big": f"{len(small)} small buys", "sub": f"Under $10 each, ${st:.2f} together. {dd(st).capitalize()}."})
    return out[:6]
