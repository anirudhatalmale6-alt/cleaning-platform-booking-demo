"""The browser and the server must price a booking identically.

There are two price engines now: priceBooking() in assets/app.js, which
runs in the customer's browser so the total updates as they click, and
price_booking() in backend/api/lib.php, which runs on the server and is
the only one that decides what gets charged.

Two implementations of one rule drift. This runs the same matrix of
bookings through both and fails on any difference, down to the cent.

    python3 test_parity.py --base http://127.0.0.1:8080

Everything that moves a price is in the matrix: each unit-size band,
every extra and combination that fits under the cap, both laundry washes
against both finishes, the window-cleaning room ladder including the
rooms where the 10-hour cap bites, all six vehicle sizes, the stepper
pushed below the floor and above the ceiling, and the services whose
hours are still estimates.
"""
import itertools, json, subprocess, sys, urllib.request, pathlib

HERE = pathlib.Path(__file__).resolve().parent
DEMO = HERE.parent.parent                       # .../demo
BASE = "http://127.0.0.1:8080"
for i, a in enumerate(sys.argv):
    if a == "--base":
        BASE = sys.argv[i + 1]

def _resolve(base):
    """Accept either the API root or the site root.

    test_live.py is pointed at the website; these two were pointed at the
    API directly, and passing one to the other gave a 404 that read like a
    broken endpoint rather than a wrong address. Both are tried instead.
    """
    import urllib.request as _u
    for cand in (base.rstrip("/"), base.rstrip("/") + "/api"):
        try:
            with _u.urlopen(cand + "/health", timeout=5) as r:
                if r.headers.get("X-Sparrow-Api"):
                    return cand
        except Exception:
            pass
    return base.rstrip("/")


BASE = _resolve(BASE)

fails = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(label)


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


# ---------------------------------------------------------------- matrix
BOOKINGS = []
HOME_EXTRAS = ["oven", "fridge", "cupboard", "washfold", "washiron"]

for band in ("b12", "b34", "b5"):
    for svc in ("standard", "deep", "move"):
        BOOKINGS.append({"service": svc, "band": band, "extras": []})
        for n in (1, 2):
            for combo in itertools.combinations(HOME_EXTRAS, n):
                BOOKINGS.append({"service": svc, "band": band, "extras": list(combo)})

for wash in ("hand", "machine"):
    for finish in ("dryfold", "dryiron"):
        BOOKINGS.append({"service": "laundry", "wash": wash, "finish": finish, "extras": []})

# the room ladder, including past the point where the cap bites
for rooms in list(range(2, 19)):
    BOOKINGS.append({"service": "windows", "rooms": rooms, "extras": []})
    BOOKINGS.append({"service": "windows", "rooms": rooms, "extras": ["pool"]})

for v in ("small", "medium", "big", "suv", "bakkie", "truck"):
    BOOKINGS.append({"service": "carwash", "vehicle": v, "extras": []})

for svc in ("office", "outdoor", "garden"):
    BOOKINGS.append({"service": svc, "extras": []})
    BOOKINGS.append({"service": svc, "extras": ["pool"]})

# the stepper: below the floor, on it, above it, and past the cap
for hours in (0, 0.5, 3.5, 4, 4.5, 6, 9.5, 10, 12, 99):
    BOOKINGS.append({"service": "standard", "band": "b34", "extras": [], "hours": hours})
    BOOKINGS.append({"service": "standard", "band": "b5", "extras": ["oven"], "hours": hours})

# an extra that belongs to the other service's set must be ignored by both
BOOKINGS.append({"service": "standard", "band": "b12", "extras": ["pool"]})
BOOKINGS.append({"service": "windows", "rooms": 4, "extras": ["oven", "washiron"]})
BOOKINGS.append({"service": "carwash", "vehicle": "suv", "extras": ["oven"]})
# a duplicate id must not be billed twice
BOOKINGS.append({"service": "standard", "band": "b12", "extras": ["oven", "oven"]})

print(f"1. Pricing {len(BOOKINGS)} bookings through both engines")

# ------------------------------------------------- the browser's engine
runner = HERE / "_parity_runner.js"
runner.write_text("""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
global.document = { querySelector: () => null, querySelectorAll: () => [] };
global.window = {}; global.localStorage = { getItem: () => null, setItem: () => {} };
const bookings = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const out = eval(src + `
;(bookings.map(b => { const p = priceBooking(b);
    return p && { total: p.total, flat: p.flat, labour: p.labour,
                  extras: p.extras, fee: p.fee, serviceHours: p.serviceHours }; }))`);
console.log(JSON.stringify(out));
""")
payload = HERE / "_parity_bookings.json"
payload.write_text(json.dumps(BOOKINGS))
js = json.loads(subprocess.run(
    ["node", str(runner), str(DEMO / "assets" / "app.js"), str(payload)],
    capture_output=True, text=True, check=True).stdout)
runner.unlink(); payload.unlink()

# -------------------------------------------------- the server's engine
mismatches = []
for b, j in zip(BOOKINGS, js):
    p = post("/price", b)
    srv = {"total": p["total"], "flat": p["flat"], "labour": p["labour"],
           "extras": p["extras"], "fee": p["fee"], "serviceHours": p["serviceHours"]}
    # compare in cents: half an hour at R35 is R17.50, and comparing
    # whole rands would hide a 50c drift
    def cents(d):
        return {k: int(round(v * 100)) for k, v in d.items()}
    if cents(srv) != cents(j):
        mismatches.append((b, j, srv))

check("every booking prices the same in the browser and on the server",
      len(mismatches), 0)
for b, j, s in mismatches[:8]:
    print("      ", json.dumps(b))
    print("        browser:", j)
    print("        server :", s)

print("\n2. The server ignores a total sent by the browser")
# This is the whole reason the server prices it again. A booking screen
# that posts total: 1.00 must still be charged the real amount.
honest = post("/price", {"service": "standard", "band": "b34", "extras": ["oven", "fridge"]})
tampered = post("/price", {"service": "standard", "band": "b34", "extras": ["oven", "fridge"],
                           "total": 1, "flat": 0, "labour": 0, "fee": 0, "hourlyRate": 0})
check("a posted total changes nothing", tampered["total"], honest["total"])
check("and it is the real number", honest["total"], 470.0)

print("\n3. An extra from another service's set cannot be billed")
plain = post("/price", {"service": "standard", "band": "b12", "extras": []})
leak  = post("/price", {"service": "standard", "band": "b12", "extras": ["pool"]})
check("pool is an outdoor task, so it adds nothing to a house clean",
      leak["total"], plain["total"])

print("\n4. A duplicated extra is charged once")
once  = post("/price", {"service": "standard", "band": "b12", "extras": ["oven"]})
twice = post("/price", {"service": "standard", "band": "b12", "extras": ["oven", "oven"]})
check("same total", twice["total"], once["total"])

print("\n5. The hour rules hold on the server too")
below = post("/price", {"service": "standard", "band": "b34", "hours": 0})
check("cannot go more than 30 min under the estimate", below["serviceHours"], 5.5)
over = post("/price", {"service": "standard", "band": "b34", "hours": 99})
check("cannot pass the 10-hour cap", over["serviceHours"], 10.0)
capped = post("/price", {"service": "standard", "band": "b5", "extras": ["washiron"], "hours": 99})
check("and the extras' own time counts against the cap", capped["serviceHours"], 8.0)

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all parity checks passed")
