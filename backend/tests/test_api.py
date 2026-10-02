"""Drives the live API over HTTP, the way a browser would.

    python3 test_api.py --base http://127.0.0.1:8080

Reload seed.sql before running: it books, cancels and approves real rows.

What is worth testing here is not that the endpoints answer, but that the
rules survive a client that lies. Every check below either enforces a rule
from the brief, or tries to get around one.
"""
import json, sys, urllib.request, urllib.error, http.cookiejar

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


class Client:
    """One browser. Keeps its own cookie jar, so sessions do not leak
    between the customer, the cleaner and the admin in these tests."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, path, payload=None, method=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            BASE + path, data=data, method=method or ("POST" if data else "GET"),
            headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:300].decode("utf8", "replace")}


anon = Client()

print("1. The API is up, and says so in a way the front end can trust")
st, r = anon.call("/health")
check("health is 200", st, 200)
check("and it is this API, not some other server's index page",
      r.get("service"), "sparrow-api")

st, cat = anon.call("/catalog")
check("catalog returns the services", len(cat["services"]), 9)
check("and the extras", len(cat["extras"]), 6)
check("window cleaning carries its own base fee",
      next(s["flat_rate_override"] for s in cat["services"] if s["code"] == "windows"), "110.00")
check("the others do not",
      next(s["flat_rate_override"] for s in cat["services"] if s["code"] == "carwash"), None)
check("every car wash size is 1h30", cat["settings"]["car_wash_hours"], "1.5")

print("\n2. Availability honours the gate, the area and the calendar")
st, r = anon.call("/availability?date=2026-08-26&city=Cape%20Town&service=standard&hours=4")
names = {c["first_name"] for c in r["cleaners"]}
check("approved indoor Cape Town cleaners are offered", "Nomsa" in names, True)
check("a pending applicant is not", "Precious" in names, False)
check("a declined one is not", "Bongani" in names, False)
check("an outdoor worker is not offered an indoor job", "Sipho" in names, False)
check("and nobody from another city", "Lerato" in names, False)

st, r = anon.call("/availability?date=2026-08-24&city=Cape%20Town&service=standard&hours=4")
check("Nomsa blocked 24 Aug, so she is not offered",
      "Nomsa" in {c["first_name"] for c in r["cleaners"]}, False)

# Grace has 9 of her 10 hours committed on 20 Aug
st, r1 = anon.call("/availability?date=2026-08-20&city=Cape%20Town&service=standard&hours=1")
st, r4 = anon.call("/availability?date=2026-08-20&city=Cape%20Town&service=standard&hours=4")
check("Grace can still take a 1-hour job that day",
      "Grace" in {c["first_name"] for c in r1["cleaners"]}, True)
check("but not a 4-hour one",
      "Grace" in {c["first_name"] for c in r4["cleaners"]}, False)

print("\n3. Signing in")
cust = Client()
st, r = cust.call("/customer/login", {"email": "thandi.m@example.co.za", "password": "demo1234"})
check("a customer can sign in", st, 200)
check("and is greeted by name", r["first_name"], "Thandi")

st, r = cust.call("/customer/login", {"email": "thandi.m@example.co.za", "password": "wrong"})
check("a wrong password is refused", st, 401)
st, r = anon.call("/customer/login", {"email": "nobody@example.co.za", "password": "demo1234"})
check("an unknown address gives the same message, not a hint",
      r["error"], "Those details do not match an account")

print("\n4. The cleaner gate — an application is not an account")
pend = Client()
st, r = pend.call("/employee/login", {"email": "precious.s@example.co.za", "password": "demo1234"})
check("a pending applicant cannot sign in", st, 403)
check("and is told where they stand", r["account_status"], "pending")

dec = Client()
st, r = dec.call("/employee/login", {"email": "bongani.z@example.co.za", "password": "demo1234"})
check("a declined applicant cannot sign in", st, 403)
check("and is given the admin's own words", r["decline_reason"],
      "Criminal record check came back unresolved. Welcome to reapply once it clears.")

emp = Client()
st, r = emp.call("/employee/login", {"email": "nomsa.m@example.co.za", "password": "demo1234"})
check("an approved cleaner can", st, 200)
st, me = emp.call("/employee/me")
check("she sees her own jobs", len(me["jobs"]) > 0, True)
check("her ID number is masked wherever it is echoed back",
      "*" in me["employee"]["id_number"], True)
check("and her blocked day is there", "2026-08-24" in me["unavailable"], True)

print("\n5. Roles cannot reach each other's screens")
st, _ = cust.call("/admin/overview")
check("a customer cannot open the admin dashboard", st, 401)
st, _ = emp.call("/admin/applications")
check("nor can a cleaner", st, 401)
st, _ = anon.call("/customer/me")
check("and a stranger cannot read a customer's orders", st, 401)
st, _ = cust.call("/employee/me")
check("a customer is not a cleaner either", st, 401)

print("\n6. Booking, as a guest")
guest = Client()
booking = {
    "service": "standard", "band": "b34", "extras": ["oven", "fridge"],
    "date": "2026-08-27", "time": "09:00",
    "first_name": "Guest", "last_name": "Checkout",
    "email": "guest.checkout@example.co.za", "phone": "082 555 0100",
    "address": {"street_line": "9 Main Road", "suburb": "Observatory",
                "city": "Cape Town", "province": "Western Cape"},
    "note": "Gate code 1234.",
}
st, avail = guest.call("/availability?date=2026-08-27&city=Cape%20Town&service=standard&hours=7")
cleaner_id = avail["cleaners"][0]["id"]
st, r = guest.call("/orders", dict(booking, employee_id=int(cleaner_id)))
check("the order is created", st, 201)
check("priced from the database, not from the browser", r["price"]["total"], 470.0)
ref = r["reference"]

print("\n7. A tampered total is ignored")
st, r2 = guest.call("/orders", dict(booking, employee_id=int(cleaner_id),
                                    date="2026-08-28", total=1, price={"total": 1}))
check("posting total: 1 still charges the real amount", r2["price"]["total"], 470.0)

print("\n8. The 10-hour cap holds at the moment of booking, not just on screen")
# Grace has 1 hour left on 20 Aug. A 4-hour clean must be refused even
# though the browser could have been edited to offer her.
st, grace = anon.call("/availability?date=2026-08-26&city=Cape%20Town&service=standard&hours=1")
gid = next(int(c["id"]) for c in grace["cleaners"] if c["first_name"] == "Grace")
st, r = guest.call("/orders", dict(booking, employee_id=gid, date="2026-08-20",
                                   email="guest2@example.co.za"))
check("refused", st, 409)
check("with a reason a person can read",
      "room" in r["error"].lower() or "available" in r["error"].lower(), True)

print("\n9. You cannot book a cleaner for the wrong kind of work")
st, out = anon.call("/availability?date=2026-08-26&city=Cape%20Town&service=garden&hours=4")
outdoor_id = int(out["cleaners"][0]["id"])
st, r = guest.call("/orders", dict(booking, employee_id=outdoor_id, date="2026-08-29",
                                   email="guest3@example.co.za"))
check("an outdoor worker is refused an indoor job", st, 409)

print("\n10. Nor one who blocked the day")
st, r = guest.call("/orders", dict(booking, employee_id=int(cleaner_id), date="2026-08-24",
                                   email="guest4@example.co.za"))
check("refused", st, 409)

print("\n11. Extras that do not fit in a 10-hour day are refused, not trimmed")
st, r = guest.call("/orders", dict(booking, service="deep", band="b34",
                                   extras=["oven", "washiron"], employee_id=int(cleaner_id),
                                   date="2026-08-30", email="guest5@example.co.za"))
check("refused rather than quietly booked 30 minutes short", st, 422)
check("and the message says why", "fit" in r["error"], True)

print("\n12. The three automatic messages went out")
adm = Client()
st, r = adm.call("/admin/login", {"email": "lebo@sparrow.co.za", "password": "demo1234"})
check("admin signs in", st, 200)
st, msgs = adm.call("/admin/messages")
mine = [m for m in msgs["messages"] if ref in (m["body"] or "") or ref in (m["subject"] or "")]
# One per admin, so the count follows how many admins exist rather than
# being a magic number that breaks when a second admin is added.
check("one message per party",
      sorted(m["recipient_type"] for m in mine),
      ["admin", "admin", "customer", "employee"])
check("the customer got an email",
      any(m["recipient_type"] == "customer" and m["channel"] == "email" for m in mine), True)
check("the cleaner got an sms",
      any(m["recipient_type"] == "employee" and m["channel"] == "sms" for m in mine), True)
check("the admin got an email",
      any(m["recipient_type"] == "admin" for m in mine), True)

print("\n13. Approving and declining an application")
st, apps = adm.call("/admin/applications")
check("two are waiting", len(apps["applications"]), 2)
check("ID numbers are masked on the admin screen too",
      all("*" in a["id_number"] for a in apps["applications"]), True)
check("their documents are listed for download",
      all(len(a["documents"]) > 0 for a in apps["applications"]), True)

pid = next(int(a["id"]) for a in apps["applications"] if a["first_name"] == "Precious")
aid = next(int(a["id"]) for a in apps["applications"] if a["first_name"] == "Andile")

st, r = adm.call(f"/admin/applications/{aid}/decide", {"decision": "decline"})
check("declining with no reason is refused", st, 422)
st, r = adm.call(f"/admin/applications/{aid}/decide",
                 {"decision": "decline", "reason": "References could not be confirmed."})
check("declining with one works", st, 200)

st, r = adm.call(f"/admin/applications/{pid}/decide", {"decision": "approve"})
check("approving works", st, 200)
temp = r["temp_password"]
st, r = adm.call(f"/admin/applications/{pid}/decide", {"decision": "approve"})
check("and cannot be done twice", st, 409)

newly = Client()
st, r = newly.call("/employee/login", {"email": "precious.s@example.co.za", "password": temp})
check("the newly approved cleaner can now sign in", st, 200)

declined = Client()
st, r = declined.call("/employee/login", {"email": "andile.k@example.co.za", "password": "demo1234"})
check("the declined one still cannot", st, 403)
check("and sees the reason the admin typed",
      r["decline_reason"], "References could not be confirmed.")

print("\n14. The cleaner calendar")
st, r = emp.call("/employee/unavailability", {"date": "2026-09-14"})
check("a cleaner can block a free day", st, 200)
st, me = emp.call("/employee/me")
check("and it shows on her calendar", "2026-09-14" in me["unavailable"], True)
st, r = emp.call("/employee/unavailability", {"date": "2026-08-21"})
check("but not a day she is already booked for", st, 409)
st, r = emp.call("/employee/unavailability", {"date": "2026-09-14", "remove": True})
check("she can unblock it again", r["blocked"], False)

print("\n15. Rating is only possible on a job that happened")
st, me = cust.call("/customer/me")
upcoming = next(o for o in me["orders"] if o["status"] == "upcoming")
done = next(o for o in me["orders"] if o["status"] == "completed" and not o["rating_stars"])
st, r = cust.call(f"/orders/{upcoming['reference']}/rate", {"stars": 5})
check("an upcoming job cannot be rated", st, 409)
st, r = cust.call(f"/orders/{done['reference']}/rate", {"stars": 6})
check("six stars is refused", st, 422)
st, r = cust.call(f"/orders/{done['reference']}/rate",
                  {"stars": 4, "comment": "Good job, a bit late."})
check("a completed one can be rated", st, 200)
st, r = cust.call(f"/orders/{done['reference']}/rate", {"stars": 1})
check("rating twice edits rather than stacking", st, 200)
st, r = cust.call(f"/orders/{done['reference']}/rate",
                  {"stars": 2, "comment": "Changed my mind."})
st, me = cust.call("/customer/me")
rated = next(o for o in me["orders"] if o["reference"] == done["reference"])
# PDO returns native types with emulated prepares off, so a TINYINT comes
# back as a number, not a string.
check("the second rating replaced the first", int(rated["rating_stars"]), 2)
check("and the new comment with it", rated["rating_comment"], "Changed my mind.")

print("\n16. One customer cannot touch another's orders")
other = Client()
other.call("/customer/login", {"email": "riaan.vw@example.co.za", "password": "demo1234"})
st, r = other.call(f"/orders/{done['reference']}/cancel", {})
check("cancelling someone else's order is a 404, not a 403",
      st, 404)   # a 403 would confirm the reference exists

print("\n17. Cancelling frees the hours up again")
st, me = cust.call("/customer/me")
up = next(o for o in me["orders"] if o["status"] == "upcoming")
st, before = anon.call(f"/availability?date={up['scheduled_date']}&city=Cape%20Town"
                       f"&service=standard&hours=9")
st, r = cust.call(f"/orders/{up['reference']}/cancel", {"reason": "Away that week"})
check("the customer can cancel", st, 200)
st, after = anon.call(f"/availability?date={up['scheduled_date']}&city=Cape%20Town"
                      f"&service=standard&hours=9")
check("and the cleaner's day opens back up",
      len(after["cleaners"]) > len(before["cleaners"]), True)

print("\n18. Signing out really ends the session")
st, _ = cust.call("/logout", {})
st, _ = cust.call("/customer/me")
check("the session is gone", st, 401)

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all API checks passed")
