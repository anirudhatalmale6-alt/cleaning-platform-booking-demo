"""Drives the customer booking flow and checks the money.

The pricing assertions are computed independently in Python from the rules in
the spec (rooms x 40 min -> hours x rate, extras, discount, fee, VAT) and
compared against what the page renders. If the JS engine and this file ever
disagree, one of them is wrong and the test says so.
"""
import pathlib, re, sys
from playwright.sync_api import sync_playwright

URL = "file://" + str(pathlib.Path(__file__).parent / "index.html")
OUT = pathlib.Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
errs, fails = [], []

RATE, MIN_PER_ROOM, MIN_HOURS = 120, 40, 2
FEE_PCT, VAT = 0.07, 0.15
EXTRA = {"oven": (120, 35), "fridge": (90, 25), "windows": (90, 30), "general": (0, 0)}
FREQ = {"once": 1.00, "weekly": 0.85, "biweek": 0.90}


def check(cond, msg):
    if not cond:
        fails.append(msg)
    print(("  ok  " if cond else "  FAIL") + "  " + msg)


def rands(text):
    """'R1 002' -> 1002"""
    return int(re.sub(r"[^\d]", "", text))


def expect_total(rooms, extras, freq, room_factor=1.0, promo=None):
    hours = max(MIN_HOURS, rooms * MIN_PER_ROOM / 60 * room_factor)
    base = hours * RATE
    ex = sum(EXTRA[e][0] for e in extras)
    sub = base + ex
    freq_disc = round(sub * (1 - FREQ[freq]))
    after = sub - freq_disc
    promo_disc = round(after * 0.20) if promo == "SPARROW20" else 0
    net = after - promo_disc
    fee = round(net * FEE_PCT)
    ex_vat = net + fee
    return round(ex_vat + round(ex_vat * VAT))


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_timeout(1300)
    pg.screenshot(path=OUT / "b1-hero.png")

    print("\n-- step gating --")
    check(pg.is_disabled('.pane.on [data-next]'), "cannot continue without picking a service")
    check(pg.locator('[data-svc]').count() == 9, "all 9 services offered, split indoor/outdoor")

    print("\n-- rooms model: 40 minutes per room --")
    pg.click('[data-svc="standard"]')
    check(not pg.is_disabled('.pane.on [data-next]'), "continue enables once a service is picked")
    pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(600)

    # default 3 rooms -> 2h (floor of 2h applies to 3 rooms at 40 min = 2h exactly)
    hours_shown = pg.inner_text(".row-lbl:has-text('Hours') .mono")
    check(hours_shown.strip() == "2h", f"3 rooms x 40 min renders as 2h, got {hours_shown!r}")

    pg.click('[data-key="rooms"][data-inc="1"]')   # 4 rooms
    pg.click('[data-key="rooms"][data-inc="1"]')   # 5 rooms
    pg.wait_for_timeout(300)
    hours_shown = pg.inner_text(".row-lbl:has-text('Hours') .mono").strip()
    check(hours_shown == "3h 20m", f"5 rooms x 40 min = 3h 20m, got {hours_shown!r}")

    got = rands(pg.inner_text("#grand"))
    want = expect_total(5, ["general"], "once")
    check(got == want, f"5-room standard total: page {got}, computed {want}")

    print("\n-- checklist adds money and time --")
    pg.click('[data-ex="oven"]'); pg.click('[data-ex="fridge"]')
    pg.wait_for_timeout(350)
    hours_shown = pg.inner_text(".row-lbl:has-text('Hours') .mono").strip()
    # 3h20 (200 min) + oven 35 + fridge 25 = 260 min
    check(hours_shown == "4h 20m", f"oven(35m)+fridge(25m) pushes 3h20 to 4h20, got {hours_shown!r}")
    got = rands(pg.inner_text("#grand"))
    want = expect_total(5, ["general", "oven", "fridge"], "once")
    check(got == want, f"with extras: page {got}, computed {want}")

    print("\n-- frequency discount --")
    pg.click('[data-freq="weekly"]')
    pg.wait_for_timeout(350)
    got = rands(pg.inner_text("#grand"))
    want = expect_total(5, ["general", "oven", "fridge"], "weekly")
    check(got == want, f"weekly -15%: page {got}, computed {want}")
    pg.screenshot(path=OUT / "b2-details.png")

    print("\n-- promo stacks on top of the frequency discount --")
    pg.fill("#promo", "SPARROW20"); pg.click("#applyPromo")
    pg.wait_for_timeout(350)
    got = rands(pg.inner_text("#grand"))
    want = expect_total(5, ["general", "oven", "fridge"], "weekly", promo="SPARROW20")
    check(got == want, f"weekly + SPARROW20: page {got}, computed {want}")
    check("applied" in pg.inner_text("#promoMsg"), "promo confirmation shown")
    pg.fill("#promo", "NOPE"); pg.click("#applyPromo")
    pg.wait_for_timeout(300)
    check("not valid" in pg.inner_text("#promoMsg"), "bad promo is rejected")
    got = rands(pg.inner_text("#grand"))
    check(got == expect_total(5, ["general", "oven", "fridge"], "weekly"),
          "rejected promo removes the discount rather than keeping it")

    print("\n-- VAT is its own line --")
    vat_line = pg.inner_text("#lines").lower()
    check("vat (15%)" in vat_line, "VAT appears as a separate summary line")

    print("\n-- schedule --")
    pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(600)
    check(pg.is_disabled('.pane.on [data-next]'), "cannot continue before choosing a slot")
    pg.click('[data-date="3"]'); pg.wait_for_timeout(250)
    pg.click(".slot:not([disabled])"); pg.wait_for_timeout(350)
    check(not pg.is_disabled('.pane.on [data-next]'), "continue enables once a slot is picked")
    pg.screenshot(path=OUT / "b3-schedule.png")

    print("\n-- address validation --")
    pg.click('.pane.on [data-next]'); pg.wait_for_timeout(600)
    pg.click('.pane.on [data-next]'); pg.wait_for_timeout(400)
    check(pg.get_attribute('.pane.on', 'data-pane') == "3", "empty address form is blocked")
    check(pg.locator('.field.bad').count() == 6, "all 6 required address fields flagged")
    pg.fill("#fName", "Thandi"); pg.fill("#fSur", "Mokoena")
    pg.fill("#fPhone", "+27 82 445 1190")
    pg.fill("#fEmail", "thandi.m@nowhere")          # malformed on purpose
    pg.fill("#fAddr", "18 Ocean View Drive"); pg.fill("#fSub", "Sea Point")
    pg.fill("#fUnit", "Flat 4B, buzzer 12")
    pg.click('.pane.on [data-next]'); pg.wait_for_timeout(400)
    check(pg.get_attribute('.pane.on', 'data-pane') == "3", "malformed email is blocked")
    pg.fill("#fEmail", "thandi.m@example.co.za")
    pg.screenshot(path=OUT / "b4-address.png")
    pg.click('.pane.on [data-next]'); pg.wait_for_timeout(700)
    check(pg.get_attribute('.pane.on', 'data-pane') == "4", "valid address advances to checkout")

    print("\n-- checkout breakdown matches the spec's line order --")
    labels = [l.strip() for l in pg.locator("#checkoutSummary .li span:first-child").all_inner_texts()]
    check(labels[:2] == ["Service fee", "Extras"], f"starts with Service fee, Extras — got {labels}")
    check("Discount" in labels and any("VAT" in l for l in labels),
          f"Discount and VAT both present — got {labels}")
    co_total = rands(pg.inner_text("#checkoutSummary .t-v"))
    side_total = rands(pg.inner_text("#grand"))
    check(co_total == side_total, f"checkout total {co_total} matches summary panel {side_total}")
    pg.screenshot(path=OUT / "b5-checkout.png")

    print("\n-- confirmation --")
    pg.click("#payBtn"); pg.wait_for_timeout(800)
    check(pg.get_attribute('.pane.on', 'data-pane') == "5", "payment advances to confirmation")
    ref = pg.inner_text("#refNo")
    check(ref.startswith("SPW-"), f"booking reference generated: {ref}")
    facts = pg.inner_text("#confirmFacts")
    check("Service date" in facts and "Service duration" in facts,
          "confirmation shows service date and duration, as the spec asks")
    body = pg.inner_text(".pane.on")
    check("Awaiting confirmation" in body,
          "confirmation says an admin still has to assign — not 'matched automatically'")
    check("automatically" not in body.lower(), "no auto-match claim remains on the page")
    pg.screenshot(path=OUT / "b6-confirmed.png")

    print("\n-- office model: size band x units --")
    pg.click("#restart"); pg.wait_for_timeout(600)
    pg.click('[data-svc="office"]'); pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(600)
    check(pg.locator("#band").count() == 1, "office shows a unit size range selector")
    check(pg.locator('[data-key="units"]').count() == 2, "office shows a number-of-units counter")
    check(pg.locator('[data-key="rooms"]').count() == 0, "office does NOT ask for bedrooms")
    band_total_1 = rands(pg.inner_text("#grand"))
    pg.click('[data-key="units"][data-inc="1"]'); pg.wait_for_timeout(350)
    band_total_2 = rands(pg.inner_text("#grand"))
    check(band_total_2 > band_total_1 * 1.8,
          f"a second unit roughly doubles the price ({band_total_1} -> {band_total_2})")
    pg.screenshot(path=OUT / "b7-office.png")

    print("\n-- flat-rate model --")
    pg.click('[data-back]'); pg.wait_for_timeout(500)
    pg.click('[data-svc="garden"]'); pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(600)
    check(pg.locator('[data-key="rooms"]').count() == 0 and pg.locator("#band").count() == 0,
          "gardening asks for neither rooms nor size bands")

    print("\n-- deep link from the dashboard --")
    d = b.new_page(viewport={"width": 1280, "height": 900})
    d.on("pageerror", lambda e: errs.append("deeplink: " + str(e)))
    d.goto(URL + "?service=deep"); d.wait_for_timeout(1100)
    check(d.locator('[data-svc="deep"].sel').count() == 1, "?service=deep preselects the deep clean")

    print("\n-- mobile --")
    m = b.new_page(viewport={"width": 412, "height": 860})
    m.on("pageerror", lambda e: errs.append("mobile: " + str(e)))
    m.goto(URL); m.wait_for_timeout(1100)
    check(m.is_disabled("#mNext"), "mobile bar disabled with no service")
    m.click('[data-svc="standard"]'); m.click("#mNext")
    m.wait_for_timeout(600)
    m.screenshot(path=OUT / "b8-mobile.png")
    check(m.get_attribute('.pane.on', 'data-pane') == "1", "mobile price bar drives the flow")
    b.close()

print("\nJS errors:", errs or "none")
print("failures :", fails or "none")
sys.exit(1 if (errs or fails) else 0)
