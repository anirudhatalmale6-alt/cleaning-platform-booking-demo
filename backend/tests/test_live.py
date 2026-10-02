"""The whole stack: a real browser, the real pages, the real database.

The other suites each prove one layer. This one books a job in the browser
and then goes and looks in MySQL to see whether the row is there, with the
right money on it. Nothing is taken on trust from the screen.

    python3 test_live.py --base http://127.0.0.1:8000 \
                         --mysql "--socket=/var/run/mysqld/mysqld.sock -u root"

Reload seed.sql first: this books, approves and blocks real rows.
"""
import json, re, shlex, subprocess, sys
from playwright.sync_api import sync_playwright

BASE  = "http://127.0.0.1:8000"
MYSQL = ["--socket=/var/run/mysqld/mysqld.sock", "-u", "root"]
for i, a in enumerate(sys.argv):
    if a == "--base":
        BASE = sys.argv[i + 1]
    if a == "--mysql":
        MYSQL = shlex.split(sys.argv[i + 1])

# A date well clear of the seeded bookings, so the shortlist is about this
# test and not about who happens to be busy in the sample data.
BOOK_DATE = "2026-09-09"

fails = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(label)


def sql(query):
    p = subprocess.run(["mysql", *MYSQL, "sparrow", "--batch", "--raw", "-e", query],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    lines = p.stdout.rstrip("\n").split("\n")
    if len(lines) < 2:
        return []
    head = [h.lower() for h in lines[0].split("\t")]
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:]]


with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--no-proxy-server"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    errors = []

    def new_page(name):
        p = ctx.new_page()
        p.on("pageerror", lambda e, n=name: errors.append(f"{n}: {e}"))
        return p

    print("1. The site knows it has a database behind it")
    pg = new_page("index")
    pg.goto(f"{BASE}/index.html")
    pg.wait_for_selector(".svc")
    mode = pg.locator("#pbMode").inner_text()
    check("the bar says so, rather than leaving you to guess",
          "Live" in mode, True)
    check("and names the database, not the sample set", "sample" in mode.lower(), False)

    print("\n2. The prices on screen came out of the settings table")
    db_rate = sql("SELECT setting_value v FROM settings WHERE setting_key='hourly_rate'")[0]["v"]
    page_rate = pg.evaluate("CFG.hourlyRate")
    check("hourly rate matches the row in MySQL", float(page_rate), float(db_rate))
    check("services came from the services table",
          pg.evaluate("CFG.services.length"),
          len(sql("SELECT code FROM services WHERE is_active=1")))
    check("window cleaning still carries its own base fee",
          pg.evaluate("CFG.services.find(s=>s.id==='windows').flatRate"), 110)

    # Change a price in the database and reload: the site must follow.
    sql("UPDATE settings SET setting_value='37.50' WHERE setting_key='hourly_rate'")
    pg.reload(); pg.wait_for_selector(".svc")
    check("editing the rate in SQL changes the site on the next load",
          pg.evaluate("CFG.hourlyRate"), 37.5)
    sql("UPDATE settings SET setting_value='35.00' WHERE setting_key='hourly_rate'")
    pg.reload(); pg.wait_for_selector(".svc")
    check("and back again", pg.evaluate("CFG.hourlyRate"), 35)

    print("\n3. Booking a job, in the browser, end to end")
    orders_before = int(sql("SELECT COUNT(*) n FROM orders")[0]["n"])

    pg.click("#hcGuest")                        # continue as guest
    pg.wait_for_selector("[data-svc='standard']")
    pg.click("[data-svc='standard']")
    pg.click("#nextBtn")
    pg.wait_for_selector(".pane h2")
    pg.click("[data-band='b34']")               # 6 hours
    pg.click("[data-task='oven']")              # +30 min, R35
    pg.click("#nextBtn")
    pg.wait_for_selector("#geoBtn")
    pg.select_option("#aType", "House")
    pg.fill("#aLine", "14 Kloof Street")
    pg.fill("#aSub", "Gardens")
    pg.click("#geoBtn")
    pg.wait_for_selector(".geo-bar")
    pg.fill("#aDate", BOOK_DATE)
    pg.click("[data-slot='09:00']")
    shown_total = pg.locator("#sumTot").inner_text()
    # The booking flow rebuilds its own chrome on every step, so the "Live"
    # label has to survive navigation, not just be right on the landing page.
    check("the live label survives moving through the flow",
          "Live" in pg.locator("#pbMode").inner_text(), True)
    pg.click("#nextBtn")                        # -> choose your cleaner
    pg.wait_for_selector(".pro", timeout=15000)

    listed = pg.locator(".pro").count()
    db_free = len(sql("""
        SELECT e.id FROM employees e
        JOIN employee_areas a ON a.employee_id=e.id AND a.city='Cape Town'
        WHERE e.account_status='approved' AND e.service_group='indoor'"""))
    check("the shortlist came from SQL, not from this browser", listed <= db_free, True)
    check("and it is not empty", listed > 0, True)

    pg.locator(".pro").first.click()
    pg.click("#nextBtn")
    pg.wait_for_selector("#payBtn")
    pg.fill("#coFirst", "Live")
    pg.fill("#coLast", "Test")
    pg.fill("#coEmail", "live.test@example.co.za")
    pg.fill("#coPhone", "082 555 0199")
    pg.click("#payBtn")
    pg.wait_for_selector(".ref", timeout=20000)
    check("and is still right on the confirmation",
          "Live" in pg.locator("#pbMode").inner_text(), True)
    ref = pg.locator(".ref").inner_text().strip()
    check("the confirmation shows a reference", bool(re.match(r"SPW-\d+", ref)), True)

    print("\n4. And the row is actually in MySQL")
    rows = sql(f"SELECT * FROM orders WHERE reference='{ref}'")
    check("exactly one order with that reference", len(rows), 1)
    o = rows[0]
    check("one more order than before",
          int(sql("SELECT COUNT(*) n FROM orders")[0]["n"]), orders_before + 1)
    check("the service is right", o["service_code"], "standard")
    check("the unit size was stored", o["bedroom_band"], "b34")
    check("the hours were stored", float(o["hours_booked"]), 6.0)
    check("the address the worker needs is on the row", o["address_line"], "14 Kloof Street")

    # R155 flat + 6h x R35 + R35 oven + R35 fee = R425
    check("the total in the database is the client's formula",
          float(o["total"]), 155 + 6 * 35 + 35 + 35)
    check("and it is the number the customer was shown",
          float(o["total"]), float(shown_total.replace("R", "").replace(",", "")))
    check("the rates were frozen onto the order", float(o["hourly_rate"]), 35.0)
    ex = sql(f"SELECT * FROM order_extras WHERE order_id={o['id']}")
    check("the oven clean is on the order", [e["extra_code"] for e in ex], ["oven"])
    check("with the price it had on the day", float(ex[0]["price"]), 35.0)
    check("a payment row was written",
          len(sql(f"SELECT * FROM payments WHERE order_id={o['id']}")), 1)

    print("\n5. The three automatic messages are in the database")
    msgs = sql(f"SELECT channel, recipient_type FROM messages_sent WHERE order_id={o['id']}")
    check("customer, cleaner and both admins were told",
          sorted(m["recipient_type"] for m in msgs),
          ["admin", "admin", "customer", "employee"])
    check("the cleaner got an sms",
          next(m["channel"] for m in msgs if m["recipient_type"] == "employee"), "sms")

    print("\n6. Raising the rate does not reprice that order")
    sql("UPDATE settings SET setting_value='50.00' WHERE setting_key='hourly_rate'")
    after = sql(f"SELECT total FROM orders WHERE reference='{ref}'")[0]["total"]
    check("the order the customer paid for is unchanged", float(after), 435.0)
    sql("UPDATE settings SET setting_value='35.00' WHERE setting_key='hourly_rate'")

    print("\n7. The cleaner portal gate, against the real accounts")
    cp = new_page("cleaner")
    cp.goto(f"{BASE}/cleaner.html")
    cp.wait_for_selector(".protobar")
    cp.evaluate("view = 'signin'; render()")
    cp.wait_for_selector("#ciGo")
    cp.fill("#ciEmail", "precious.s@example.co.za")
    cp.fill("#ciPass", "demo1234")
    cp.click("#ciGo")
    cp.wait_for_selector(".gate", timeout=15000)
    check("a pending applicant is stopped at the gate",
          "still with the admins" in cp.locator(".gate").inner_text(), True)

    cp.evaluate("view = 'signin'; render()")
    cp.wait_for_selector("#ciGo")
    cp.fill("#ciEmail", "bongani.z@example.co.za")
    cp.fill("#ciPass", "demo1234")
    cp.click("#ciGo")
    cp.wait_for_selector(".gate.bad", timeout=15000)
    check("a declined one is shown the admin's own words",
          "Criminal record check" in cp.locator(".gate").inner_text(), True)

    cp.evaluate("view = 'signin'; render()")
    cp.wait_for_selector("#ciGo")
    cp.fill("#ciEmail", "nomsa.m@example.co.za")
    cp.fill("#ciPass", "demo1234")
    cp.click("#ciGo")
    cp.wait_for_selector(".snav", timeout=15000)
    check("an approved cleaner gets her dashboard",
          "Nomsa" in cp.locator(".page-head h1").inner_text(), True)

    print("\n8. The cleaner's calendar writes to the database")
    blocked_before = int(sql("SELECT COUNT(*) n FROM employee_unavailability "
                             "WHERE employee_id=1")[0]["n"])
    cp.locator("[data-nav='calendar']").click()
    cp.wait_for_selector(".cal-day")
    free = cp.locator(".cal-day:not([disabled]):not(.off)").last
    day = free.get_attribute("data-day")
    free.click()
    cp.wait_for_timeout(1200)
    check("the blocked day is in MySQL",
          int(sql(f"SELECT COUNT(*) n FROM employee_unavailability "
                  f"WHERE employee_id=1 AND unavailable_date='{day}'")[0]["n"]), 1)
    check("one more than before",
          int(sql("SELECT COUNT(*) n FROM employee_unavailability "
                  "WHERE employee_id=1")[0]["n"]), blocked_before + 1)

    print("\n9. That blocked day disappears from the booking screen")
    pg2 = new_page("index2")
    pg2.goto(f"{BASE}/index.html")
    pg2.wait_for_selector(".svc")
    free_then = json.loads(pg2.evaluate(
        """async () => {
             const r = await fetch('api/availability?date=%s&city=Cape%%20Town'
                                   + '&service=standard&hours=4', {credentials:'include'});
             return JSON.stringify(await r.json()); }""" % day))
    check("Nomsa is not offered on the day she just blocked",
          any(c["first_name"] == "Nomsa" for c in free_then["cleaners"]), False)

    print("\n10. The admin dashboard reads the same database")
    ad = new_page("admin")
    ad.goto(f"{BASE}/admin.html")
    ad.wait_for_selector(".protobar")
    ad.evaluate("""async () => {
        await API.post('admin/login', {email:'lebo@sparrow.co.za', password:'demo1234'});
        await loadAdmin(); render(); }""")
    ad.wait_for_timeout(1500)
    check("the admin sees the order that was just booked",
          ad.evaluate("DB.bookings.some(b => b.id === %s)" % json.dumps(ref)), True)
    check("and the two applications still waiting",
          ad.evaluate("DB.applications.length"),
          int(sql("SELECT COUNT(*) n FROM employees WHERE account_status='pending'")[0]["n"]))

    print("\n11. Approving from the admin screen changes the database")
    # Measure the change, not a magic number: a hardcoded total is right
    # until the seed gains a row, and then it is wrong for no good reason.
    def counts():
        r = sql("SELECT account_status s, COUNT(*) n FROM employees GROUP BY account_status")
        return {x["s"]: int(x["n"]) for x in r}

    before_c = counts()
    ad.evaluate("""async () => {
        const id = DB.applications[0].id; await approve(id); }""")
    ad.wait_for_timeout(1500)
    after_c = counts()
    check("one fewer pending applicant",
          after_c.get("pending", 0), before_c.get("pending", 0) - 1)
    check("and one more approved",
          after_c.get("approved", 0), before_c.get("approved", 0) + 1)
    check("nobody was declined along the way",
          after_c.get("declined", 0), before_c.get("declined", 0))

    print("\n12. No JavaScript errors anywhere in that run")
    check("errors", errors, [])

    browser.close()

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all live-stack checks passed")
