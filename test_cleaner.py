"""Drives the cleaner application form and the approved-cleaner dashboard.

Asserts the validation actually blocks — the point of a required field is that
an empty form cannot get past it.
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

URL = "file://" + str(pathlib.Path(__file__).parent / "cleaner.html")
OUT = pathlib.Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
errs, fails = [], []


def check(cond, msg):
    if not cond:
        fails.append(msg)
    print(("  ok  " if cond else "  FAIL") + "  " + msg)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_timeout(1200)
    pg.screenshot(path=OUT / "c1-apply.png")

    print("\n-- validation gates --")
    # empty form must not advance
    pg.click('.pane.on .btn-primary')
    pg.wait_for_timeout(300)
    check(pg.get_attribute('.pane.on', 'data-p') == "0", "empty step 1 is blocked")
    check(pg.locator('.field.bad').count() >= 6, "empty required fields are marked bad")

    # under-18 must be rejected even with everything else filled
    pg.fill("#fFull", "Nomsa Thandeka"); pg.fill("#fSur", "Mabaso")
    pg.fill("#fDocNo", "9203145800083"); pg.fill("#fPhone", "+27 83 114 9928")
    pg.fill("#fEmail", "nomsa.m@example.co.za")
    pg.fill("#fHome", "24 Sixth Avenue, Kensington, Cape Town")
    pg.click('#fCrim [data-c="no"]')
    pg.fill("#fDob", "2012-05-04")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(300)
    check(pg.get_attribute('.pane.on', 'data-p') == "0", "a 14-year-old is blocked")

    # bad email must be rejected
    pg.fill("#fDob", "1992-03-14")
    pg.fill("#fEmail", "nomsa.m@nowhere")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(300)
    check(pg.get_attribute('.pane.on', 'data-p') == "0", "malformed email is blocked")

    pg.fill("#fEmail", "nomsa.m@example.co.za")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(400)
    check(pg.get_attribute('.pane.on', 'data-p') == "1", "valid step 1 advances")

    print("\n-- areas --")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(250)
    check(pg.get_attribute('.pane.on', 'data-p') == "1", "no province selected is blocked")
    pg.select_option("#fProv", "Western Cape"); pg.wait_for_timeout(250)
    check(pg.locator('#fCities [data-city]').count() == 5, "province populates its cities")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(250)
    check(pg.get_attribute('.pane.on', 'data-p') == "1", "province without a city is blocked")
    pg.click('[data-city="Cape Town"]'); pg.click('[data-city="Somerset West"]')
    pg.click('#fGroup [data-g="indoor"]')
    pg.wait_for_timeout(200)
    pg.screenshot(path=OUT / "c2-areas.png")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(400)
    check(pg.get_attribute('.pane.on', 'data-p') == "2", "step 2 advances once complete")

    print("\n-- references --")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(250)
    check(pg.get_attribute('.pane.on', 'data-p') == "2", "empty references are blocked")
    check(pg.locator('.pane.on .field.bad').count() == 8, "all 8 reference fields flagged")
    for n in (1, 2):
        pg.fill(f"#r{n}Name", "Sarah"); pg.fill(f"#r{n}Sur", "Adams")
        pg.fill(f"#r{n}Tel", "+27 21 555 010" + str(n))
        pg.fill(f"#r{n}Addr", "Claremont, Cape Town")
    pg.click('.pane.on .btn-primary'); pg.wait_for_timeout(400)
    check(pg.get_attribute('.pane.on', 'data-p') == "3", "step 3 advances once complete")

    print("\n-- documents --")
    pg.click("text=Submit application"); pg.wait_for_timeout(250)
    check(pg.get_attribute('.pane.on', 'data-p') == "3", "submit without documents is blocked")
    pg.click("#dropId"); pg.click("#dropPic"); pg.wait_for_timeout(200)
    pg.click("text=Submit application"); pg.wait_for_timeout(250)
    check(pg.get_attribute('.pane.on', 'data-p') == "3", "submit without consent is blocked")
    pg.screenshot(path=OUT / "c3-documents.png")
    pg.click("#consent")
    pg.click("text=Submit application"); pg.wait_for_timeout(600)
    check(pg.get_attribute('.pane.on', 'data-p') == "4", "complete application submits")
    ref = pg.inner_text("#appRef")
    check(ref.startswith("APP-") and len(ref) == 10, f"reference generated: {ref}")
    pg.screenshot(path=OUT / "c4-submitted.png")

    print("\n-- approved cleaner dashboard --")
    pg.click('[data-mode="dash"]'); pg.wait_for_timeout(700)
    pg.screenshot(path=OUT / "c5-today.png")
    n_items = pg.locator(".checkitem").count()
    check(n_items == 3, f"checklist built from the booking extras ({n_items} items)")
    check(pg.is_disabled(".card .btn-primary"), "complete button disabled until every item ticked")
    for i in range(n_items):
        pg.locator(".checkitem").nth(i).click()
        pg.wait_for_timeout(120)
    check(not pg.is_disabled(".card .btn-primary"), "complete button enables when all ticked")
    pg.screenshot(path=OUT / "c6-checklist.png")

    for nav, title in [("offers", "Job offers"), ("schedule", "My schedule"),
                       ("earnings", "Earnings"), ("ratings", "Ratings"), ("cprofile", "My profile")]:
        pg.click(f'[data-nav="{nav}"]'); pg.wait_for_timeout(300)
        h = pg.inner_text(".page-head h1")
        check(title.lower() in h.lower(), f"{nav} renders -> {h}")
        if nav in ("earnings", "offers"):
            pg.screenshot(path=OUT / f"c7-{nav}.png")

    # accepting an offer must move it out of offers and into the schedule
    pg.click('[data-nav="schedule"]'); pg.wait_for_timeout(300)
    sched_before = pg.locator("table.tbl tbody tr").count()
    pg.click('[data-nav="offers"]'); pg.wait_for_timeout(300)
    before = pg.locator(".job").count()
    pg.click("text=Accept job"); pg.wait_for_timeout(500)
    after = pg.locator(".job").count()
    check(after == before - 1, f"accepted offer leaves the offer list ({before} -> {after})")
    pg.click('[data-nav="schedule"]'); pg.wait_for_timeout(300)
    sched_after = pg.locator("table.tbl tbody tr").count()
    check(sched_after == sched_before + 1,
          f"accepted job appears in the schedule ({sched_before} -> {sched_after})")

    # mobile
    m = b.new_page(viewport={"width": 412, "height": 860})
    m.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
    m.goto(URL); m.wait_for_timeout(1100)
    m.screenshot(path=OUT / "c8-mobile-apply.png")
    m.click('[data-mode="dash"]'); m.wait_for_timeout(700)
    m.screenshot(path=OUT / "c9-mobile-today.png")
    b.close()

print("\nJS errors:", errs or "none")
print("failures :", fails or "none")
sys.exit(1 if (errs or fails) else 0)
