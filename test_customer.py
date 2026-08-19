"""Customer dashboard — rating with a comment, addresses, cancelling.

    python3 test_customer.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

HERE  = pathlib.Path(__file__).parent
URL   = (HERE / "dashboard.html").as_uri()
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

    print("\n1. The overview counts match the orders behind them")
    check("greeted", pg.locator(".page-head h1").inner_text(), "Welcome back, Thandi")
    for label, expr in (
        ("Upcoming", "DB.bookings.filter(b => b.cust === 'cu1' && b.status === 'upcoming' && b.date >= TODAY).length"),
        ("Orders",   "DB.bookings.filter(b => b.cust === 'cu1').length"),
        ("To rate",  "DB.bookings.filter(b => b.cust === 'cu1' && b.status === 'completed' && !b.rating).length"),
    ):
        check(f"'{label}' tile", pg.locator(".stat", has_text=label).locator(".s-v").inner_text(),
              str(pg.evaluate(f"() => {expr}")))

    print("\n2. Rating needs a star before it will save")
    nav(pg, "past")
    unrated = pg.evaluate("""() => DB.bookings.find(b => b.cust === 'cu1' && b.status === 'completed' && !b.rating).id""")
    pg.locator(f"[data-rate='{unrated}']").click()
    pg.wait_for_selector("#rComment")
    pg.fill("#rComment", "Spotless, and she was lovely with the dog.")
    pg.locator(".modal-foot .btn-primary").click()
    pg.wait_for_timeout(200)
    check("dialog stayed open", pg.locator("#rComment").count(), 1)
    check("and asked for a star", pg.locator("#rErr").is_visible(), True)
    check("nothing saved yet", pg.evaluate(f"() => !!DB.bookings.find(b => b.id === '{unrated}').rating"), False)

    print("\n3. With a star, the rating and the comment both save")
    pg.locator("[data-star='4']").click()
    pg.locator(".modal-foot .btn-primary").click()
    pg.wait_for_timeout(300)
    saved = pg.evaluate(f"() => DB.bookings.find(b => b.id === '{unrated}').rating")
    check("stars saved", saved["stars"], 4)
    check("comment saved", saved["comment"], "Spotless, and she was lovely with the dog.")
    check("and it is shown back on the order card",
          "lovely with the dog" in pg.locator("#body").inner_text(), True)
    check("that order left the 'to rate' pile",
          pg.evaluate(f"""() => DB.bookings.filter(b => b.cust === 'cu1' && b.status === 'completed' && !b.rating)
                                 .some(b => b.id === '{unrated}')"""), False)

    print("\n4. The rating changes what the cleaner's profile averages")
    cl = pg.evaluate(f"() => DB.bookings.find(b => b.id === '{unrated}').cleaner")
    avg = pg.evaluate(f"() => ratingOf('{cl}')")
    manual = pg.evaluate(f"""() => {{
        const r = DB.bookings.filter(b => b.cleaner === '{cl}' && b.rating).map(b => b.rating.stars);
        return Math.round(r.reduce((a, c) => a + c, 0) / r.length * 100) / 100;
    }}""")
    check("the average is computed from the ratings, not stored separately", avg, manual)

    print("\n5. A rating can be changed afterwards")
    pg.locator(f"[data-rate='{unrated}']").click()
    pg.wait_for_selector("#rComment")
    check("the old comment is loaded for editing",
          pg.input_value("#rComment"), "Spotless, and she was lovely with the dog.")
    check("the old stars are pre-lit", pg.locator(".rate-stars button.on").count(), 4)
    pg.locator("[data-star='5']").click()
    pg.locator(".modal-foot .btn-primary").click()
    pg.wait_for_timeout(250)
    check("updated", pg.evaluate(f"() => DB.bookings.find(b => b.id === '{unrated}').rating.stars"), 5)

    print("\n6. Cancelling an order asks first, then cancels")
    nav(pg, "upcoming")
    before = pg.locator(".card.panel").count()
    oid = pg.locator("[data-cancel]").first.get_attribute("data-cancel")
    pg.locator("[data-cancel]").first.click()
    pg.wait_for_selector(".modal")
    check("it warns before doing anything", "Cancel this order?" in pg.locator(".modal-head h3").inner_text(), True)
    pg.locator(".modal-foot .btn-outline").click()      # "Keep it"
    pg.wait_for_timeout(200)
    check("keeping it changed nothing", pg.evaluate(f"() => DB.bookings.find(b => b.id === '{oid}').status"), "upcoming")
    pg.locator("[data-cancel]").first.click()
    pg.wait_for_selector(".modal")
    pg.locator(".modal-foot .btn-danger").click()
    pg.wait_for_timeout(250)
    check("now it is cancelled", pg.evaluate(f"() => DB.bookings.find(b => b.id === '{oid}').status"), "cancelled")
    check("and it dropped off the upcoming list", pg.locator(".card.panel").count(), before - 1)

    print("\n7. Saved addresses: add, validate, set default")
    nav(pg, "addresses")
    n0 = pg.locator(".row-card").count()
    pg.click("#addAddr")
    pg.wait_for_selector("#eLabel")
    pg.locator(".modal-foot .btn-primary").click()      # empty
    pg.wait_for_timeout(200)
    check("an empty address is refused", pg.locator("#eLabel").count(), 1)
    check("and the offending fields are marked",
          pg.locator(".modal .field.bad").count(), 3)
    pg.fill("#eLabel", "Beach flat")
    pg.fill("#eLine", "3 Beach Road")
    pg.fill("#eSub", "Muizenberg")
    pg.locator(".modal-foot .btn-primary").click()
    pg.wait_for_timeout(250)
    check("it saved", pg.locator(".row-card").count(), n0 + 1)
    check("with the details typed", "3 Beach Road" in pg.locator("#body").inner_text(), True)

    check("exactly one default before", pg.locator(".row-card .pill").count(), 1)
    pg.locator("[data-primary]").last.click()
    pg.wait_for_timeout(200)
    check("still exactly one default after switching", pg.locator(".row-card .pill").count(), 1)
    check("and it moved to the new one",
          pg.evaluate("() => DB.addresses.filter(a => a.primary).map(a => a.label)"), ["Beach flat"])
    pg.screenshot(path=str(SHOTS / "customer-addresses.png"))

    print("\n8. Payment methods keep at least one card")
    nav(pg, "cards")
    cards = pg.locator(".row-card").count()
    pg.locator("[data-delcard]").last.click()
    pg.wait_for_timeout(200)
    check("one removed", pg.locator(".row-card").count(), cards - 1)
    pg.locator("[data-delcard]").first.click()
    pg.wait_for_timeout(200)
    check("the last card cannot be removed", pg.locator(".row-card").count(), cards - 1)
    check("a default always survives",
          pg.evaluate("() => DB.cards.filter(c => c.primary).length"), 1)

    print("\n9. Account details validate before saving")
    nav(pg, "account")
    pg.fill("#acEmail", "not-an-email")
    pg.click("#acSave")
    pg.wait_for_timeout(200)
    check("bad email refused", pg.locator("#acEmail").evaluate("e => e.closest('.field').className"), "field bad")
    pg.fill("#acEmail", "thandi.new@example.co.za")
    pg.fill("#acFirst", "Thandiwe")
    pg.click("#acSave")
    pg.wait_for_timeout(250)
    check("saved", pg.evaluate("() => DB.customer.email"), "thandi.new@example.co.za")
    check("and the greeting follows the change",
          pg.locator(".page-head h1").inner_text(), "My account")
    nav(pg, "overview")
    check("greeting updated", pg.locator(".page-head h1").inner_text(), "Welcome back, Thandiwe")

    print("\n10. Mobile")
    m = b.new_page(viewport={"width": 412, "height": 860})
    m.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
    m.goto(URL)
    m.wait_for_selector("#sideNav")
    check("all seven sections reachable", m.locator("#sideNav .snav").count(), 7)
    m.screenshot(path=str(SHOTS / "customer-mobile.png"))

    print("\n11. No JavaScript errors")
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
print("all customer checks passed")
