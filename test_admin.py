"""Drives the admin dashboard: confirm-and-assign, approvals, search, worker upload.

The assertions are about behaviour that would break the business if wrong —
that an assignment actually moves the booking out of the queue, that the
cleaner shortlist is filtered by work type and city, and that an under-age
worker cannot be added.
"""
import pathlib, sys
from playwright.sync_api import sync_playwright

URL = "file://" + str(pathlib.Path(__file__).parent / "admin.html")
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
    pg.screenshot(path=OUT / "a1-overview.png")

    print("\n-- overview --")
    pending_badge = pg.inner_text('[data-nav="confirm"] .badge')
    check(pending_badge == "3", f"pending queue badge shows 3, got {pending_badge}")
    check(pg.locator('[data-nav="candidates"] .badge').inner_text() == "2",
          "candidate badge shows 2 new applications")

    # Done BEFORE the assign step below, which consumes the only pending
    # outdoor booking. Ordered this way so the check can never silently skip.
    print("\n-- shortlist is filtered by work type, not everyone --")
    pg.click('[data-nav="services"]'); pg.wait_for_timeout(300)
    pg.click("text=Outdoor cleaning >> nth=0"); pg.wait_for_timeout(400)
    n_out = pg.locator("text=Confirm & assign").count()
    check(n_out >= 1, f"there is a pending outdoor booking to test with ({n_out})")
    pg.click("text=Confirm & assign >> nth=0"); pg.wait_for_timeout(400)
    names = pg.locator("[data-cl] .w-n").all_inner_texts()
    check(len(names) >= 1, f"outdoor shortlist is not empty: {names}")
    check(all("Nomsa" not in n and "Grace" not in n for n in names),
          f"outdoor job offers only outdoor cleaners: {names}")
    pg.click(".modal-head [data-close]"); pg.wait_for_timeout(300)

    print("\n-- confirm & assign --")
    pg.click('[data-nav="confirm"]')
    pg.wait_for_timeout(400)
    before = pg.locator("table.tbl").first.locator("tbody tr").count()
    pg.screenshot(path=OUT / "a2-confirm-queue.png")
    pg.click("text=Confirm & assign >> nth=0")
    pg.wait_for_timeout(500)
    check(pg.locator(".veil.on").count() == 1, "assign modal opens")
    shortlist = pg.locator("[data-cl]").count()
    check(shortlist > 0, f"a shortlist of cleaners is offered ({shortlist})")
    check(pg.locator(".best").count() >= 1, "a best match / favourite is flagged")
    pg.screenshot(path=OUT / "a3-assign-modal.png")
    pg.click(".modal-foot .btn-primary")
    pg.wait_for_timeout(600)
    after = pg.locator("table.tbl").first.locator("tbody tr").count()
    check(after == before - 1, f"assigned booking leaves the queue ({before} -> {after})")
    check(pg.inner_text('[data-nav="confirm"] .badge') == "2", "queue badge drops to 2")

    print("\n-- candidates --")
    pg.click('[data-nav="candidates"]'); pg.wait_for_timeout(400)
    pg.screenshot(path=OUT / "a4-candidates.png")
    n_pending = pg.locator("text=New application").count()
    check(n_pending >= 1, f"indoor tab shows pending applications ({n_pending})")
    pg.click("text=Approve >> nth=0"); pg.wait_for_timeout(500)
    check(pg.locator("text=New application").count() == n_pending - 1,
          "approved candidate leaves the pending list")
    check(pg.inner_text('[data-nav="candidates"] .badge') == "1", "candidate badge drops to 1")

    print("\n-- customers --")
    pg.click('[data-nav="customers"]'); pg.wait_for_timeout(400)
    check(pg.locator("#custBody tr").count() == 4, "all 4 customers listed")
    pg.fill("#custQ", "aisha"); pg.wait_for_timeout(350)
    check(pg.locator("#custBody tr").count() == 1, "search narrows to 1 result")
    pg.fill("#custQ", "zzzz"); pg.wait_for_timeout(350)
    check(pg.locator("#custBody .empty").count() == 1, "no-match shows an empty state, not a blank table")
    pg.fill("#custQ", ""); pg.wait_for_timeout(350)
    check(pg.locator("#custBody tr").count() == 4, "clearing search restores the list")
    pg.locator("#custBody .btn").first.click(); pg.wait_for_timeout(400)
    check(pg.locator(".veil.on").count() == 1, "customer profile modal opens")
    pg.screenshot(path=OUT / "a5-customer.png")
    pg.click(".modal-head [data-close]"); pg.wait_for_timeout(300)

    print("\n-- upload new worker --")
    pg.click('[data-nav="upload"]'); pg.wait_for_timeout(400)
    n_city = pg.locator("#wCity option").count()
    check(n_city > 0, f"city dropdown is populated on first render ({n_city} options)")
    pg.click("text=Add indoor cleaner"); pg.wait_for_timeout(300)
    check(pg.locator(".field.bad").count() >= 4, "empty worker form is blocked")
    pg.fill("#wName", "Precious"); pg.fill("#wSur", "Sithole")
    pg.fill("#wAge", "15"); pg.fill("#wTel", "+27 82 771 3320")
    pg.click("#wDrop")
    pg.click("text=Add indoor cleaner"); pg.wait_for_timeout(300)
    check(pg.locator("#wAge").locator("xpath=ancestor::div[contains(@class,'field')]")
            .first.get_attribute("class").find("bad") >= 0, "a 15-year-old worker is rejected")
    pg.fill("#wAge", "34")
    pg.click("text=Add indoor cleaner"); pg.wait_for_timeout(600)
    check(pg.locator("text=Precious Sithole").count() >= 1, "valid worker is added and listed")
    pg.screenshot(path=OUT / "a6-upload.png")

    print("\n-- notifications --")
    pg.click('[data-nav="notifs"]'); pg.wait_for_timeout(350)
    check(pg.locator(".row-card").count() == 5, "notification list renders")

    # mobile
    m = b.new_page(viewport={"width": 412, "height": 860})
    m.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
    m.goto(URL); m.wait_for_timeout(1100)
    m.screenshot(path=OUT / "a7-mobile.png")
    m.click('[data-nav="confirm"]'); m.wait_for_timeout(400)
    m.screenshot(path=OUT / "a8-mobile-confirm.png")
    b.close()

print("\nJS errors:", errs or "none")
print("failures :", fails or "none")
sys.exit(1 if (errs or fails) else 0)
