import pathlib, sys
from playwright.sync_api import sync_playwright

URL = "file://" + str(pathlib.Path(__file__).parent / "index.html")
OUT = pathlib.Path(__file__).parent / "shots"
OUT.mkdir(exist_ok=True)
errs = []

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 860})
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL)
    pg.wait_for_timeout(1400)
    pg.screenshot(path=OUT / "01-hero.png")

    # step 1: service
    pg.click('[data-svc="deep"]')
    pg.wait_for_timeout(300)
    pg.screenshot(path=OUT / "02-service.png")
    pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(700)

    # step 2: details
    pg.click('[data-key="beds"][data-inc="1"]')
    pg.click('[data-key="baths"][data-inc="1"]')
    pg.click('[data-ex="oven"]')
    pg.click('[data-ex="fridge"]')
    pg.click('[data-freq="biweek"]')
    pg.wait_for_timeout(400)
    pg.screenshot(path=OUT / "03-details.png")
    total_a = pg.inner_text("#grand")
    pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(700)

    # step 3: schedule
    pg.click('[data-date="3"]')
    pg.wait_for_timeout(200)
    pg.click('.slot:not([disabled])')
    pg.wait_for_timeout(400)
    pg.screenshot(path=OUT / "04-schedule.png")
    pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(700)

    # step 4: address
    pg.fill("#fName", "Thandi Mokoena")
    pg.fill("#fPhone", "+27 82 445 1190")
    pg.fill("#fAddr", "18 Ocean View Drive")
    pg.fill("#fSub", "Sea Point")
    pg.fill("#fUnit", "Flat 4B, buzzer 12")
    pg.fill("#fNotes", "Two cats, please keep the balcony door shut.")
    pg.wait_for_timeout(300)
    pg.screenshot(path=OUT / "05-address.png")

    # promo on the summary
    pg.fill("#promo", "SPARROW20")
    pg.click("#applyPromo")
    pg.wait_for_timeout(300)
    total_b = pg.inner_text("#grand")
    promo_msg = pg.inner_text("#promoMsg")

    pg.click('.pane.on [data-next]')
    pg.wait_for_timeout(700)
    pg.screenshot(path=OUT / "06-payment.png")

    pg.click("#payBtn")
    pg.wait_for_timeout(900)
    pg.screenshot(path=OUT / "07-confirmed.png")
    ref = pg.inner_text("#refNo")

    # mobile pass — drive the whole flow from the sticky price bar only
    m = b.new_page(viewport={"width": 412, "height": 860})
    merrs = []
    m.on("pageerror", lambda e: merrs.append(str(e)))
    m.goto(URL); m.wait_for_timeout(1200)
    m.screenshot(path=OUT / "08-mobile-hero.png")
    assert m.is_disabled("#mNext"), "mobile Continue should be disabled with no service"
    m.click('[data-svc="standard"]')
    m.click("#mNext"); m.wait_for_timeout(600)
    m.click('[data-ex="iron"]'); m.click('[data-freq="weekly"]')
    m.wait_for_timeout(400)
    m.screenshot(path=OUT / "09-mobile-details.png")
    m.click("#mNext"); m.wait_for_timeout(600)
    assert m.is_disabled("#mNext"), "mobile Continue should be disabled before a slot is picked"
    m.click(".slot:not([disabled])"); m.wait_for_timeout(300)
    m.screenshot(path=OUT / "10-mobile-schedule.png")
    m.click("#mNext"); m.wait_for_timeout(600)
    m.click("#mNext"); m.wait_for_timeout(600)   # address -> payment
    m.screenshot(path=OUT / "11-mobile-payment.png")
    m.click("#mNext"); m.wait_for_timeout(800)   # pay
    m_ref = m.inner_text("#refNo")
    m_bar_hidden = not m.is_visible("#mbar")
    m.screenshot(path=OUT / "12-mobile-confirmed.png")
    b.close()
print("mobile ref        :", m_ref)
print("mobile bar hidden on confirm:", m_bar_hidden)
print("mobile JS errors  :", merrs or "none")

print("total before promo:", total_a)
print("total after promo :", total_b)
print("promo msg         :", promo_msg)
print("reference         :", ref)
print("JS errors         :", errs or "none")
sys.exit(1 if errs else 0)
