"""Cleaner portal — the sign-in gate, the application form, the calendar.

The gate is the important one: the client's rule is that a cleaner whose
account is pending or declined must not be able to sign in. That is
tested for all three account states, not just the happy one.

    python3 test_cleaner.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

HERE  = pathlib.Path(__file__).parent
URL   = (HERE / "cleaner.html").as_uri()
SHOTS = HERE / "shots"; SHOTS.mkdir(exist_ok=True)

fails = []
def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(f"{label}: got {got}, expected {want}")


def to_signin(pg):
    pg.goto(URL)
    pg.click("#goSignin")
    pg.wait_for_selector("#ciGo")


def run(pw):
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    print("\n1. A pending account cannot get in")
    to_signin(pg)
    pg.click("[data-as='cl6']")                      # Precious — pending
    pg.wait_for_selector(".gate")
    check("blocked", pg.locator(".auth-head h1").inner_text(), "Not yet")
    check("told it is still with the admins",
          "still with the admins" in pg.locator(".gate .g-t").inner_text(), True)
    check("no dashboard behind it", pg.locator("#sideNav").count(), 0)
    pg.screenshot(path=str(SHOTS / "cleaner-gate-pending.png"))

    print("\n2. A declined account cannot get in, and is told why")
    to_signin(pg)
    pg.click("[data-as='cl9']")                      # Bongani — declined
    pg.wait_for_selector(".gate")
    check("blocked", pg.locator(".gate .g-t").inner_text(), "Your application was declined")
    check("the admin's reason is shown to them",
          "Criminal record check" in pg.locator(".gate").inner_text(), True)
    check("offered a way back in", pg.locator("#gReapply").count(), 1)
    check("no dashboard behind it", pg.locator("#sideNav").count(), 0)

    print("\n3. An approved account gets the dashboard")
    to_signin(pg)
    pg.click("[data-as='cl1']")                      # Nomsa — approved
    pg.wait_for_selector("#sideNav")
    check("greeted by name", pg.locator(".page-head h1").inner_text(), "Good morning, Nomsa")
    check("all five sections", pg.locator("#sideNav .snav").count(), 5)

    print("\n4. Upcoming and past bookings are hers, and split correctly")
    pg.click("[data-nav='upcoming']")
    pg.wait_for_selector(".jobcard, .empty")
    up = pg.locator(".jobcard").count()
    check("she has upcoming work", up >= 1, True)
    check("upcoming are all upcoming",
          set(pg.locator(".jobcard .pill").all_inner_texts()), {"Upcoming"})
    pg.click("[data-nav='past']")
    pg.wait_for_selector(".jobcard, .empty")
    past_pills = set(pg.locator(".jobcard .pill").all_inner_texts())
    check("past holds nothing upcoming", "Upcoming" in past_pills, False)
    check("a customer rating is shown on the job",
          pg.locator(".jobcard .review").count() >= 1, True)

    print("\n5. The calendar blocks days off — but not days already booked")
    pg.click("[data-nav='calendar']")
    pg.wait_for_selector(".cal-grid")
    check("August 2026", pg.locator(".ch-t").inner_text(), "August 2026")
    check("she already blocked 21 Aug", pg.locator(".cal-day.off").count(), 1)
    booked = pg.locator(".cal-day.booked")
    check("her booked days are marked", booked.count() >= 1, True)
    check("and cannot be blocked out from under a customer",
          booked.first.is_disabled(), True)
    free = pg.locator(".cal-day:not(.off):not(.booked):not([disabled])").first
    day = free.get_attribute("data-day")
    free.click()
    pg.wait_for_timeout(200)
    check("clicking a free day blocks it", pg.locator(".cal-day.off").count(), 2)
    check("it is the day that was clicked",
          pg.locator(f".cal-day[data-day='{day}']").get_attribute("class").find("off") >= 0, True)
    pg.locator(f".cal-day[data-day='{day}']").click()
    pg.wait_for_timeout(200)
    check("clicking again frees it up", pg.locator(".cal-day.off").count(), 1)
    pg.screenshot(path=str(SHOTS / "cleaner-calendar.png"))

    print("\n6. Her profile shows the ratings customers actually left")
    pg.click("[data-nav='profile']")
    pg.wait_for_selector(".portrait")
    check("photo upload is offered", pg.locator("#photoDrop").count(), 1)
    check("reviews are listed", pg.locator(".review").count() >= 1, True)
    check("each review names the customer",
          "Thandi" in pg.locator(".review .rv-h").first.inner_text(), True)

    print("\n7. The application form refuses an applicant under 18")
    pg.goto(URL)
    pg.click("#goApply")
    pg.wait_for_selector("#fFirst")
    pg.fill("#fFirst", "Lindiwe"); pg.fill("#fLast", "Mahlangu")
    pg.fill("#fDob", "2012-03-04")                   # 14 on the fixed "today"
    pg.fill("#fPhone", "0821234567"); pg.fill("#fEmail", "lindiwe@example.co.za")
    pg.click("#fGroup [data-g='indoor']")
    pg.fill("#fYears", "1")
    pg.click("#fNext")
    pg.wait_for_timeout(200)
    check("still on step 1", pg.locator(".step-t").text_content().startswith("Step 1"), True)
    check("and told the age, not just 'invalid'",
          pg.locator("#fDobErr").inner_text(), "You are 14. We cannot take on anyone under 18.")

    print("\n8. A valid date of birth lets her through")
    pg.fill("#fDob", "1994-03-04")
    pg.click("#fNext")
    pg.wait_for_selector("#fProv")
    check("on step 2", pg.locator(".step-t").text_content().startswith("Step 2"), True)

    print("\n9. Province, cities and languages are all required")
    pg.click("#fNext")
    pg.wait_for_timeout(150)
    check("cities blocked it", pg.locator("#fCityErr").is_visible(), True)
    check("languages blocked it too", pg.locator("#fLangErr").is_visible(), True)
    check("cities are populated on first render, before touching the province",
          pg.locator("#fCities .chip").count() > 0, True)
    pg.locator("#fCities .chip", has_text="Cape Town").click()
    pg.locator("#fLangs [data-lang='English']").click()
    pg.click("#fNext")
    pg.wait_for_selector("#fIdNum")
    check("on step 3", pg.locator(".step-t").text_content().startswith("Step 3"), True)

    print("\n10. Documents: a 13-digit ID, and all three uploads")
    pg.fill("#fIdNum", "94030")                      # too short
    pg.click("#fNext")
    pg.wait_for_timeout(150)
    check("short ID rejected", pg.locator("#fIdNum").evaluate("e => e.closest('.field').className"), "field bad")
    check("missing uploads called out", pg.locator("#fUpIdErr").is_visible(), True)
    pg.fill("#fIdNum", "9403045800083")
    for k in ("upId", "upPhoto", "upCrim"):
        pg.click(f"[data-up='{k}']")
        pg.wait_for_timeout(120)
    check("all three attached", pg.locator(".drop.filled").count(), 3)
    pg.click("#fNext")
    pg.wait_for_selector("#fR1Name")

    print("\n11. Two references, and the declaration must be ticked")
    for n in (1, 2):
        pg.fill(f"#fR{n}Name", f"Reference {n}")
        pg.fill(f"#fR{n}Phone", "0821112222")
        pg.fill(f"#fR{n}Rel", "Cleaned their home weekly for three years")
    pg.click("#fNext")
    pg.wait_for_timeout(150)
    check("cannot submit without agreeing", pg.locator("#fAgreeErr").is_visible(), True)
    pg.click("#fAgree")
    pg.wait_for_timeout(150)
    pg.click("#fNext")
    pg.wait_for_selector("#readAck")
    check("submitted", "Application sent" in pg.locator(".form-wrap h2").inner_text(), True)
    check("told they cannot sign in yet",
          "cannot sign in until you are approved" in pg.locator(".form-wrap p").inner_text(), True)
    pg.screenshot(path=str(SHOTS / "cleaner-applied.png"))

    print("\n12. The new applicant lands in the pending queue, not the approved list")
    state = pg.evaluate("""() => {
      const c = DB.cleaners.find(x => x.name === 'Lindiwe');
      return { found: !!c, account: c && c.account,
               inQueue: DB.applications.some(a => c && a.id === c.id) };
    }""")
    check("the application was recorded", state["found"], True)
    check("as pending, never approved", state["account"], "pending")
    check("and it is in the admin queue", state["inQueue"], True)

    print("\n13. And that new applicant still cannot sign in")
    newid = pg.evaluate("() => DB.cleaners.find(x => x.name === 'Lindiwe').id")
    pg.evaluate(f"() => signIn('{newid}')")
    pg.wait_for_selector(".gate")
    check("gated", pg.locator("#sideNav").count(), 0)

    print("\n14. No JavaScript errors")
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
print("all cleaner checks passed")
