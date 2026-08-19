"""Admin dashboard — approvals, declines, employees by role, customers.

The approve/decline pair is the one that matters: approving must open the
account AND send the congratulations message; declining must refuse to go
through without a written reason, and that reason must be what the
applicant is later shown.

    python3 test_admin.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

HERE  = pathlib.Path(__file__).parent
URL   = (HERE / "admin.html").as_uri()
SHOTS = HERE / "shots"; SHOTS.mkdir(exist_ok=True)

fails = []
def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(f"{label}: got {got}, expected {want}")


def nav(pg, section):
    pg.click(f"[data-nav='{section}']")
    pg.wait_for_timeout(150)


def run(pw):
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL)
    pg.wait_for_selector("#sideNav")

    print("\n1. The overview counts what is actually there")
    check("greeted", pg.locator(".page-head h1").inner_text(), "Welcome back, Lebo")
    queue_badge = int(pg.locator("[data-nav='apps'] .badge").inner_text())
    real_pending = pg.evaluate("() => DB.cleaners.filter(c => c.account === 'pending').length")
    check("the queue badge matches the data", queue_badge, real_pending)
    check("the tile agrees with the badge",
          pg.locator(".stat", has_text="Waiting on you").locator(".s-v").inner_text(), str(queue_badge))

    print("\n2. The submitted form opens, with downloadable documents")
    nav(pg, "apps")
    check("both applicants listed", pg.locator(".row-card").count(), real_pending)
    pg.locator("[data-form]").first.click()
    pg.wait_for_selector(".modal")
    check("references are on the form", "References" in pg.locator(".modal-body").inner_text(), True)
    check("all four documents offered", pg.locator(".doc-row").count(), 4)
    check("each has a download button", pg.locator("[data-dl]").count(), 4)
    check("the head-and-shoulders photo is one of them",
          "Head & shoulders photo" in pg.locator(".docs").inner_text(), True)
    pg.screenshot(path=str(SHOTS / "admin-application.png"))
    pg.locator(".modal [data-close]").click()

    print("\n3. Declining refuses to go through without a reason")
    target = pg.locator("[data-decline]").first.get_attribute("data-decline")
    before = pg.evaluate(f"() => cleaner('{target}').account")
    check("that applicant starts pending", before, "pending")
    pg.locator("[data-decline]").first.click()
    pg.wait_for_selector("#dcReason")
    pg.locator(".modal-foot .btn-danger").click()          # submit with an empty reason
    pg.wait_for_timeout(200)
    check("the dialog stayed open", pg.locator("#dcReason").count(), 1)
    check("and said why", pg.locator("#dcErr").is_visible(), True)
    check("nothing was changed", pg.evaluate(f"() => cleaner('{target}').account"), "pending")

    print("\n4. With a reason, it declines and sends that exact wording")
    REASON = "References could not be reached on the numbers given."
    pg.fill("#dcReason", REASON)
    pg.locator(".modal-foot .btn-danger").click()
    pg.wait_for_selector(".mailer")
    check("the account is declined", pg.evaluate(f"() => cleaner('{target}').account"), "declined")
    check("the reason is stored on the account",
          pg.evaluate(f"() => cleaner('{target}').declineReason"), REASON)
    check("and the message carries it word for word",
          REASON in pg.locator(".mail-bd").inner_text(), True)
    check("it is addressed to them, not to the admin",
          "admin" in pg.locator(".mail-hd").inner_text().lower(), False)
    pg.locator(".modal [data-close]").click()
    pg.wait_for_timeout(200)
    check("they left the queue", pg.evaluate(f"() => DB.applications.some(a => a.id === '{target}')"), False)

    print("\n5. Approving opens the account and congratulates them")
    nav(pg, "apps")
    target2 = pg.locator("[data-approve]").first.get_attribute("data-approve")
    pg.locator("[data-approve]").first.click()
    pg.wait_for_selector(".mailer")
    check("account approved", pg.evaluate(f"() => cleaner('{target2}').account"), "approved")
    body = pg.locator(".mail-bd").inner_text()
    check("the message congratulates them", "Welcome aboard" in body, True)
    check("and tells them to open their calendar", "calendar" in body, True)
    pg.locator(".modal [data-close]").click()
    pg.wait_for_timeout(200)
    check("queue is now empty", pg.locator("[data-nav='apps'] .badge").count(), 0)
    check("empty state shown", "Nothing waiting" in pg.locator("#body").inner_text(), True)

    print("\n6. Employees are listed by role, and the filter really filters")
    nav(pg, "staff")
    heads = pg.locator(".sect-head h2").all_inner_texts()
    check("both roles have their own block", heads, ["Indoor cleaners", "Outdoor cleaners"])
    everyone = pg.locator("tbody tr").count()
    pg.click("[data-role='indoor']")
    pg.wait_for_timeout(150)
    indoor = pg.locator("tbody tr").count()
    check("indoor only shows the indoor block", pg.locator(".sect-head h2").all_inner_texts(), ["Indoor cleaners"])
    pg.click("[data-role='outdoor']")
    pg.wait_for_timeout(150)
    outdoor = pg.locator("tbody tr").count()
    check("outdoor only shows the outdoor block", pg.locator(".sect-head h2").all_inner_texts(), ["Outdoor cleaners"])
    check("the two halves add up to everyone", indoor + outdoor, everyone)
    check("the filter is not just showing the same list twice", indoor == everyone, False)
    pg.click("[data-role='all']")
    pg.wait_for_timeout(150)
    pg.screenshot(path=str(SHOTS / "admin-staff.png"))

    print("\n7. Opening an employee shows their jobs and their ratings")
    pg.locator("[data-staff]").first.click()
    pg.wait_for_selector(".modal")
    check("their bookings are listed", pg.locator(".modal .tbl tbody tr").count() >= 1, True)
    pg.locator(".modal [data-close]").click()

    print("\n8. Customer search actually narrows the list")
    nav(pg, "custs")
    all_rows = pg.locator("#custBody tr").count()
    check("every customer is listed", all_rows,
          pg.evaluate("() => DB.customers.length"))
    pg.fill("#custSearch", "aisha")
    pg.wait_for_timeout(200)
    check("one match", pg.locator("#custBody tr").count(), 1)
    check("and it is the right one", "Aisha" in pg.locator("#custBody").inner_text(), True)
    pg.fill("#custSearch", "zzzz")
    pg.wait_for_timeout(200)
    check("no match says so", "Nobody matches" in pg.locator("#body").inner_text(), True)
    pg.fill("#custSearch", "")
    pg.wait_for_timeout(200)
    check("clearing it brings everyone back", pg.locator("#custBody tr").count(), all_rows)

    print("\n9. A customer's order history opens, and the money adds up")
    pg.locator("[data-cust]").first.click()
    pg.wait_for_selector(".modal")
    rows = pg.locator(".modal .tbl tbody tr").count()
    shown = pg.evaluate("() => DB.bookings.filter(b => b.cust === 'cu1').length")
    check("every order for that customer", rows, shown)
    spent = pg.evaluate("""() => DB.bookings
        .filter(b => b.cust === 'cu1' && b.status !== 'cancelled')
        .reduce((n, b) => n + priceBooking(b).total, 0)""")
    shown_spent = pg.locator(".modal .stat", has_text="Spent").locator(".s-v").inner_text()
    digits = "".join(c for c in shown_spent if c.isdigit() or c == ".")
    check("the spend tile matches the orders", round(float(digits), 2), round(spent, 2))
    pg.screenshot(path=str(SHOTS / "admin-customer.png"))
    pg.locator(".modal [data-close]").click()

    print("\n10. The outbox holds everything that was sent this session")
    nav(pg, "outbox")
    check("both the decline and the approval are there",
          pg.locator(".row-card").count(), 2)
    pg.locator("[data-sent]").first.click()
    pg.wait_for_selector(".mailer")
    check("it re-opens with its body intact", pg.locator(".mail-bd").inner_text() != "", True)
    pg.locator(".modal [data-close]").click()

    print("\n11. An order opens with the full price breakdown")
    nav(pg, "orders")
    pg.locator("[data-order]").first.click()
    pg.wait_for_selector(".modal")
    text = pg.locator(".modal-body").text_content()   # inner_text() returns CSS-uppercased labels
    for line in ("Flat rate", "Service fee", "Total"):
        check(f"'{line}' on the breakdown", line in text, True)
    pg.locator(".modal [data-close]").click()

    print("\n12. Mobile")
    m = b.new_page(viewport={"width": 412, "height": 860})
    m.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
    m.goto(URL)
    m.wait_for_selector("#sideNav")
    check("side nav collapses to a scroller", m.locator("#sideNav .snav").count(), 6)
    m.screenshot(path=str(SHOTS / "admin-mobile.png"))

    print("\n13. No JavaScript errors")
    check("errors", errs, [])
    b.close()


with sync_playwright() as pw:
    run(pw)

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all admin checks passed")
