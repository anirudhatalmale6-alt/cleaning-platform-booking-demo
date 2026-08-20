"""Booking flow + pricing.

Every total below is recomputed here, in Python, straight from the
client's price list — flat R155, R35 an hour, R35 service fee, extras
at their listed price. Nothing is read off the page and trusted.

    python3 test_booking.py
"""
import pathlib, sys
from playwright.sync_api import sync_playwright, expect

HERE  = pathlib.Path(__file__).parent
URL   = (HERE / "index.html").as_uri()
SHOTS = HERE / "shots"; SHOTS.mkdir(exist_ok=True)

FLAT, RATE, FEE, MAX_H = 155, 35, 35, 10
FLAT_WINDOWS = 110          # his 22 Aug instruction: window cleaning has its own base fee
BAND_H = {"b12": 4, "b34": 6, "b5": 8}
EXTRA  = {  # id: (minutes, price)
    "oven": (30, 35), "fridge": (30, 35), "cupboard": (60, 35),
    "washfold": (60, 180), "washiron": (120, 250),
}
POOL   = (120, 70)          # the outdoor extra — time and price are my placeholders
VEHICLE_H = {"small": 1, "medium": 1.5, "big": 2, "suv": 2.5, "bakkie": 2.5, "truck": 3}

def window_hours(rooms):
    """4 rooms is 4 hours; every room after that adds 30 minutes."""
    return 4 + max(0, rooms - 4) * 0.5

fails = []
def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(f"{label}: got {got}, expected {want}")

def amt(txt):
    """Amount in cents. Half an hour at R35 is R17.50, so totals land on 50c
    and comparing whole rands would hide a real 50c drift."""
    t = "".join(ch for ch in txt if ch.isdigit() or ch == ".")
    return int(round(float(t) * 100)) if t else None

def cents(x):
    return int(round(x * 100))

def hlabel(h):
    """The same '4h 30m' string the page prints."""
    m = int(round(h * 60))
    return f"{m // 60}h" + (f" {m % 60}m" if m % 60 else "") if m >= 60 else f"{m}m"

def zar(x):
    """The same string the page renders, for 'is this in the email' checks."""
    c = cents(x)
    return f"R{c // 100}" + (f".{c % 100:02d}" if c % 100 else "")

def total_for(service_hours, extras=(), flat=FLAT):
    return flat + service_hours * RATE + sum(EXTRA[e][1] for e in extras) + FEE


def sign_in(pg):
    pg.goto(URL)
    pg.click("#hcIn")
    pg.click("#siGo")
    pg.wait_for_selector("[data-svc='standard']")


def pick(pg, service):
    pg.click(f"[data-svc='{service}']")
    pg.click("#nextBtn")
    pg.wait_for_selector(".pane h2")


def run(pw):
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))

    print("\n1. The three unit-size bands price exactly as the client listed them")
    sign_in(pg); pick(pg, "standard")
    for band, hours in BAND_H.items():
        pg.click(f"[data-band='{band}']")
        check(f"{band} hours", pg.locator("#hVal").inner_text(), f"{hours}h")
        check(f"{band} total", amt(pg.locator("#sumTot").inner_text()), cents(total_for(hours)))

    print("\n2. Extras add their listed price and their listed time")
    pg.click("[data-band='b34']")
    for ex in ("oven", "fridge", "cupboard"):
        pg.click(f"[data-task='{ex}']")
    got_total = pg.locator("#sumTot").inner_text()
    check("3-4 bed + oven + fridge + cupboard",
          amt(got_total), cents(total_for(6, ("oven", "fridge", "cupboard"))))
    # 6h service + 2h of extras = 8h on site
    check("duration shown on the summary",
          pg.locator("#sum .mini").last.inner_text(), "Estimated 8h on site")

    print("\n3. Hours: down 30 minutes only, up in 30-minute steps")
    for ex in ("oven", "fridge", "cupboard"):
        pg.click(f"[data-task='{ex}']")          # clear them again
    check("back to the estimate", pg.locator("#hVal").inner_text(), "6h")
    pg.click("#hMinus")
    check("one step down", pg.locator("#hVal").inner_text(), "5h 30m")
    check("30 min off is the floor", pg.locator("#hMinus").is_disabled(), True)
    check("price follows the hours", amt(pg.locator("#sumTot").inner_text()), cents(total_for(5.5)))
    pg.click("#hPlus"); pg.click("#hPlus")
    check("two steps up", pg.locator("#hVal").inner_text(), "6h 30m")
    check("price follows up too", amt(pg.locator("#sumTot").inner_text()), cents(total_for(6.5)))

    print("\n4. The 10-hour cap stops the job growing")
    pg.click("[data-band='b5']")                  # 8h, resets the stepper
    check("5+ bedroom estimate", pg.locator("#hVal").inner_text(), "8h")
    for _ in range(6):
        if pg.locator("#hPlus").is_disabled():
            break
        pg.click("#hPlus")
    check("cannot pass the cap", pg.locator("#hVal").inner_text(), f"{MAX_H}h")
    check("plus is disabled at the cap", pg.locator("#hPlus").is_disabled(), True)
    check("every extra greyed out at the cap",
          pg.locator(".task[disabled]").count(), len(EXTRA))

    print("\n5. 5+ bedroom greys out what will not fit")
    pg.click("[data-band='b12']")                 # reset the stepper
    pg.click("[data-band='b5']")                  # 8h clean, 2h of head-room
    # washiron needs 2h -> fits exactly; nothing blocked yet
    check("nothing blocked at 8h", pg.locator(".task[disabled]").count(), 0)
    pg.click("[data-task='oven']")                # +30 min -> 8h30
    pg.click("[data-task='fridge']")              # +30 min -> 9h
    check("only 1h left, so the 2h task is blocked",
          pg.locator(".task[disabled]").count(), 1)
    check("the blocked one is 'wash, dry and iron'",
          pg.locator(".task[disabled] .tk-t").inner_text(), "Wash, dry and iron")
    check("and it says why",
          "past 10 hours" in pg.locator(".task[disabled] .tk-s").inner_text(), True)

    print("\n5b. Window cleaning is priced off the rooms, on its own R110 base fee")
    sign_in(pg); pick(pg, "windows")
    check("starts at his 4 rooms", pg.locator("[data-rooms].on").inner_text().startswith("4 room"), True)
    check("4 rooms is 4 hours", pg.locator("#hVal").inner_text(), "4h")
    check("the base fee is R110, not R155",
          amt(pg.locator("#sum .li").first.inner_text()), cents(FLAT_WINDOWS))
    check("4-room total", amt(pg.locator("#sumTot").inner_text()),
          cents(total_for(4, flat=FLAT_WINDOWS)))
    for rooms in (5, 6, 9):
        pg.click(f"[data-rooms='{rooms}']")
        h = window_hours(rooms)
        check(f"{rooms} rooms is {h}h", pg.locator("#hVal").inner_text(), hlabel(h))
        check(f"{rooms}-room total", amt(pg.locator("#sumTot").inner_text()),
              cents(total_for(h, flat=FLAT_WINDOWS)))
    check("it says the job is in and out",
          "inside and out" in pg.locator(".note").first.text_content(), True)
    check("the room choices stop where the 10-hour cap does",
          pg.locator("[data-rooms]").count(), 13)          # 4 .. 16 rooms

    print("\n5c. Pool service is now an extra task on the outdoor jobs")
    pg.click("[data-rooms='4']")
    check("it is offered here", pg.locator("[data-task='pool']").count(), 1)
    check("and the indoor extras are not",
          pg.locator("[data-task='oven']").count(), 0)
    pg.click("[data-task='pool']")
    check("pool adds its price", amt(pg.locator("#sumTot").inner_text()),
          cents(FLAT_WINDOWS + 4 * RATE + POOL[1] + FEE))
    check("and its 2 hours", pg.locator("#sum .mini").last.inner_text(), "Estimated 6h on site")
    check("it is labelled as my estimate, not his",
          "my estimate" in pg.locator("[data-task='pool'] .tk-t").text_content(), True)
    pg.screenshot(path=str(SHOTS / "book-windows.png"))
    sign_in(pg); pick(pg, "standard")
    check("pool is not offered on an indoor clean", pg.locator("[data-task='pool']").count(), 0)

    print("\n5d. Car wash asks for the vehicle first")
    sign_in(pg); pick(pg, "carwash")
    check("all six vehicle sizes are offered", pg.locator("[data-vehicle]").count(), 6)
    check("no hours until one is picked", pg.locator("#hVal").count(), 0)
    check("cannot continue yet", pg.locator("#nextBtn").is_disabled(), True)
    for veh in ("small", "suv", "truck"):
        pg.click(f"[data-vehicle='{veh}']")
        h = VEHICLE_H[veh]
        check(f"{veh} is {h}h", pg.locator("#hVal").inner_text(), hlabel(h))
        check(f"{veh} total", amt(pg.locator("#sumTot").inner_text()), cents(total_for(h)))
    check("can continue now", pg.locator("#nextBtn").is_disabled(), False)
    check("the vehicle shows on the summary",
          "Truck" in pg.locator("#sum .mini").first.inner_text(), True)
    check("the hours are declared as mine",
          "estimates above are mine" in pg.locator(".pane .note.warn").last.text_content(), True)
    pg.screenshot(path=str(SHOTS / "book-carwash.png"))

    print("\n6. Laundry is its own flow, with its own estimates")
    pg.goto(URL); pg.click("#hcIn"); pg.click("#siGo")
    pg.wait_for_selector("[data-svc='laundry']")
    pick(pg, "laundry")
    check("finish is locked until a wash is picked",
          pg.locator("[data-finish='dryfold']").is_disabled(), True)
    pg.click("[data-wash='hand']")                # 5h
    check("finish unlocks", pg.locator("[data-finish='dryfold']").is_disabled(), False)
    pg.click("[data-finish='dryiron']")           # +3.5h
    check("hand wash + dry, iron & fold", amt(pg.locator("#sumTot").inner_text()), cents(total_for(8.5)))
    pg.click("[data-wash='machine']")             # 4h
    pg.click("[data-finish='dryfold']")           # +2h
    check("machine wash + dry & fold", amt(pg.locator("#sumTot").inner_text()), cents(total_for(6)))

    print("\n7. A signed-in customer's saved address arrives already pinned")
    pg.click("#nextBtn")
    check("on the address step", pg.locator(".pane h2").inner_text(), "Where and when?")
    check("saved address is pre-pinned, so no re-confirming",
          pg.locator("#afterGeo").is_visible(), True)
    check("and the saved addresses are offered as chips",
          pg.locator("[data-saved]").count(), 3)

    print("\n7b. A guest has to find the address on the map before anyone is shown")
    pg.goto(URL)
    pg.click("#ctaGuest")
    pg.wait_for_selector("[data-svc='standard']")
    pick(pg, "standard")
    pg.click("[data-band='b34']")
    pg.click("#nextBtn")
    pg.wait_for_selector("#geoBtn")
    check("no saved addresses for a guest", pg.locator("[data-saved]").count(), 0)
    check("the when/notes block is hidden until the address is pinned",
          pg.locator("#afterGeo").is_visible(), False)
    check("cannot continue yet", pg.locator("#nextBtn").is_disabled(), True)
    pg.select_option("#aType", "House")
    pg.fill("#aLine", "18 Ocean View Drive")
    pg.fill("#aSub", "Sea Point")
    pg.click("#geoBtn")
    pg.wait_for_selector(".geo-bar")
    check("address is pinned", "pinned" in pg.locator(".geo-bar .gb-s").inner_text(), True)
    check("the when/notes block appears", pg.locator("#afterGeo").is_visible(), True)
    check("still cannot continue without a date and time",
          pg.locator("#nextBtn").is_disabled(), True)

    print("\n8. Only cleaners free in that city, that day, who fit the job")
    pg.fill("#aDate", "2026-08-24")
    pg.click("[data-slot='09:00']")
    pg.click("#nextBtn")
    pg.wait_for_selector(".pane h2")
    check("on the cleaner step", pg.locator(".pane h2").inner_text(), "Choose your cleaner")
    names = pg.locator(".pro .p-n").all_inner_texts()
    check("Nomsa marked 24 Aug unavailable, so she is not offered",
          "Nomsa Mabaso" in names, False)
    check("...and that really is the reason — she has no work booked that day",
          pg.evaluate("() => bookedHoursOn('cl1', '2026-08-24')"), 0)
    check("indoor cleaners only — no outdoor names",
          any(n in names for n in ("Sipho Dlamini", "Thabo Maseko")), False)
    check("Lerato is in Johannesburg, not Cape Town",
          "Lerato Molefe" in names, False)
    check("Precious is still pending approval",
          "Precious Sithole" in names, False)
    check("so Grace and Zanele are what is left", sorted(names), ["Grace Nkosi", "Zanele Ndlovu"])
    check("cannot continue without picking one", pg.locator("#nextBtn").is_disabled(), True)

    print("\n8b. A cleaner already near the 10-hour cap is dropped too")
    pg.click("[data-back]")
    pg.wait_for_selector("#aDate")
    pg.fill("#aDate", "2026-08-21")               # Nomsa works 7h that day
    pg.click("[data-slot='09:00']")
    pg.click("#nextBtn")
    pg.wait_for_selector(".pane h2")
    booked = pg.evaluate("() => bookedHoursOn('cl1', '2026-08-21')")
    check("she is free that day, but already working", booked > 0, True)
    check("and 6 more hours would break the cap", booked + 6 > 10, True)
    check("so she is not offered", "Nomsa Mabaso" in pg.locator(".pro .p-n").all_inner_texts(), False)
    pg.click("[data-back]")
    pg.wait_for_selector("#aDate")
    pg.fill("#aDate", "2026-08-24")
    pg.click("[data-slot='09:00']")
    pg.click("#nextBtn")
    pg.wait_for_selector(".pro")

    print("\n9. Checkout, payment and the three automatic messages")
    pg.locator(".pro", has_text="Grace Nkosi").click()
    pg.screenshot(path=str(SHOTS / "book-workers.png"))
    pg.click("#nextBtn")
    pg.wait_for_selector("#payBtn")
    check("cleaner carried into checkout",
          "Grace Nkosi" in pg.locator(".card.panel .t-strong").first.inner_text(), True)
    check("checkout total matches the summary",
          amt(pg.locator(".total .t-v").last.inner_text()), cents(total_for(6)))
    pg.fill("#cNote", "Please do the laundry first, the machine is in the garage.")
    pg.screenshot(path=str(SHOTS / "book-checkout.png"))
    pg.click("#payBtn")
    pg.wait_for_selector(".ref")
    check("confirmed", "is booked" in pg.locator(".conf h2").inner_text(), True)
    ref = pg.locator(".ref").inner_text()
    check("a reference was issued", ref.startswith("SPW-"), True)

    for btn, label in (("#mailC", "customer email"), ("#mailW", "cleaner SMS"), ("#mailA", "admin email")):
        pg.click(btn)
        pg.wait_for_selector(".mailer")
        body = pg.locator(".mail-bd").inner_text()
        check(f"{label} carries the reference", ref in body or ref in pg.locator(".mail-hd").inner_text(), True)
        if label != "cleaner SMS":
            check(f"{label} shows the amount paid", zar(total_for(6)) in body, True)
        pg.locator(".modal [data-close]").click()
    pg.click("#mailW"); pg.wait_for_selector(".mailer")
    check("the note is in the cleaner's message",
          "machine is in the garage" in pg.locator(".mail-bd").inner_text(), True)
    pg.locator(".modal [data-close]").click()

    print("\n10. Mobile — the price bar drives the same flow")
    m = b.new_page(viewport={"width": 412, "height": 860})
    m.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
    m.goto(URL)
    m.click("#ctaGuest")
    m.wait_for_selector("[data-svc='standard']")
    check("price bar is showing", m.locator("#mbar").is_visible(), True)
    m.click("[data-svc='standard']")
    m.click("#mbarB")
    m.wait_for_selector("#hVal")
    check("the bar advanced the flow", m.locator(".pane h2").inner_text(), "Standard house cleaning")
    check("the bar shows the live total", amt(m.locator("#mbarV").inner_text()), cents(total_for(4)))
    m.click("[data-task='washiron']")
    check("bar follows an extra", amt(m.locator("#mbarV").inner_text()), cents(total_for(4, ("washiron",))))
    m.screenshot(path=str(SHOTS / "book-mobile.png"))

    print("\n11. No JavaScript errors anywhere in that run")
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
print("all booking checks passed")
