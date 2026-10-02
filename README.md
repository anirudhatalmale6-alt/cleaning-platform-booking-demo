# Sparrow — cleaning services platform (prototype)

The customer website plus all three dashboards, built against the client's
written brief. **Live:** https://anirudhatalmale6-alt.github.io/cleaning-platform-booking-demo/

| Surface | File |
|---|---|
| Website, sign in / sign up / guest, booking flow | `index.html` |
| Customer dashboard | `dashboard.html` |
| Cleaner portal — registration, sign-in gate, dashboard | `cleaner.html` |
| Admin dashboard | `admin.html` |

Shared design system in `assets/app.css`; shared config, mock data and the
price engine in `assets/app.js`. All four surfaces read the same records, so
a rating left on the customer dashboard changes the average on that cleaner's
profile and in the admin employee list.

**The database and the API:** see [backend/README.md](backend/README.md).
MySQL 8 schema, seed data and a PHP API, with the four test suites that
prove it. [SCHEMA-NOTES.md](SCHEMA-NOTES.md) lists every field the screens
capture, in plain English.

The same four HTML files run two ways. Served from GitHub Pages there is no
PHP, so they run on the sample data in `assets/app.js` and the bar at the
top says so. Served from a host with PHP and MySQL, `assets/api.js` finds
the API on boot and every price, cleaner and booking comes out of the
database instead. One build, both modes, and the page always says which
one you are looking at.

**Opening it in VS Code:** see [RUN-IN-VSCODE.md](RUN-IN-VSCODE.md). There is
no build step — open the folder, right-click `index.html`, Open with Live
Server. `.vscode/` carries the extension recommendations and the tasks.

## Colours

Four palettes, switchable from the dot row in the prototype bar at the top of
every page:

| | |
|---|---|
| **Fresh** *(default)* | Bright emerald on white, with coral, amber and blue accents |
| **Electric** | The same shape, pushed harder — neon spring green and hot coral |
| **Forest** | Dark premium — the page inverts, the green stays bright |
| **Heritage** | The muted paper-and-moss palette the demo first shipped with |

Every colour on all four surfaces resolves from the variables at the top of
`assets/app.css`; there is no hardcoded green anywhere else, so a repaint is
one block of tokens.

Two tokens do different jobs and must not be collapsed into one:

- `--primary` is a **fill** — bright, with `--on-primary` (near-black green)
  as the text on it. A vivid green behind dark text is both louder and more
  legible than a vivid green behind white text.
- `--moss` is **text** — the same hue held dark enough to read on white.

The choice is remembered per browser and follows the visitor across all four
screens. The prototype bar, and the switcher with it, comes out before
launch — it is there so the palette can be chosen by looking rather than by
describing.

## Pricing — the client's numbers, used verbatim

    total  =  R155 flat rate
            + (service hours × R35)
            + extra tasks at their listed price
            + R35 service fee

| Unit size | Estimated hours |
|---|---|
| 1–2 bedroom | 4 |
| 3–4 bedroom | 6 |
| 5+ bedroom | 8 |

| Extra task | Adds | Costs |
|---|---|---|
| Oven clean | 30 min | R35 |
| Fridge clean | 30 min | R35 |
| Cupboard clean | 1 h | R35 |
| Basic wash, dry and fold | 1 h | R180 |
| Wash, dry and iron | 2 h | R250 |

Laundry is its own flow: hand wash (5 h) or machine wash (4 h), then dry &
fold (+2 h) or dry, iron & fold (+3.5 h).

**Window cleaning** is priced off the number of rooms in the house, and is
the one service on a different base fee:

| | |
|---|---|
| Base fee | **R110** (not R155) — confirmed 1 Oct as the base fee for *all* window jobs, and for window cleaning only |
| 4 rooms | 4 hours |
| Every room after that | +30 minutes |

It is stated on screen that this covers the windows **inside and out**.

**Car wash** asks which vehicle it is — small car, medium car, big car,
SUV, bakkie, truck — but **every size is estimated at 1 h 30 m** on the
standard R155 flat rate, so the size does not change the price. It is asked
because the cleaner needs to know what is in the driveway, and the customer
can still push the hours up from the stepper. Client's figure, 1 Oct 2026:
"each car is estimated to take about 1hour 30 minutes and cleaning rates
apply there". Every car wash therefore comes to R242.50 before extras.

**Pool service** is an extra task on the outdoor jobs, not a service of its
own.

**Time rules.** The customer may take at most 30 minutes off the estimate and
add as much as they like, in 30-minute steps. A cleaner may not be booked
past 10 hours in a day — that cap is what greys extras out on a 5+ bedroom
job, and it also drops a cleaner off the shortlist once their day is full.

**One assumption, flagged to the client:** an extra task is charged at its
listed price and its time is added to the job, but that time is *not* billed
again at R35/hr — otherwise the customer pays for it twice.

Every rate lives in `CFG` at the top of `assets/app.js`. `priceBooking()` is
the only place a price is computed; the booking flow, both dashboards and the
admin order screen all call it, so they cannot disagree.

## Booking flow — the client's step order

Service → extras → address (property type, street, unit number, confirmed on
the map, then access notes) → **the customer picks their own cleaner** from
everyone free in that area on that day → checkout with a note for the cleaner
→ payment.

Nothing is shown on the cleaner step until the address has been found on the
map. The shortlist is filtered by service type, city, the days that cleaner
has blocked off, and how much of their 10 hours is already spoken for.

## Automatic messages

Every email and SMS in the brief is rendered exactly as it would be sent —
order confirmation to the customer, job details to the cleaner, new-order
alert to the admins, approval congratulations, and the decline with the
admin's own written reason. They collect in the admin *Sent messages* screen.
There is no mail server yet; this is the wording, for sign-off.

## Placeholders — mine, not the client's

Two of these closed on 1 Oct 2026: the car wash hours (1 h 30 m for every
size) and the scope of the R110 base fee (window cleaning only). Both are
now the client's numbers and are no longer flagged on screen.

- Office cleaning, outdoor cleaning and gardening have **estimated hours I
  made up**. The price list covers indoor house cleaning, laundry, window
  cleaning and the car wash. These are marked on screen wherever they
  appear.
- **Pool service** costs R70, which is its 2 hours at the client's own
  R35/hr, because he has not priced it. Both the time and the price are
  labelled "my estimate" on the task itself.
- Deep clean and move-in/move-out add 2 h and 3 h to the band estimate. Also
  mine.
- Geocoding runs against a stand-in. It swaps to Google Places once there is
  an API key on the client's billing account.
- Cleaner photos are drawn illustrations, not stock faces — the real card
  shows the head-and-shoulders photo uploaded with the application.

## Tests

```
python3 run_tests.py          # all five suites
python3 test_booking.py       # pricing, the hours stepper, the 10-hour cap, availability
python3 test_customer.py      # ratings with comments, addresses, cancelling
python3 test_cleaner.py       # the sign-in gate, the application form, the calendar
python3 test_admin.py         # approve, decline-with-reason, employees by role, search
python3 test_theme.py         # the palettes, and a contrast audit of every one

python3 run_tests.py --with-backend \
    --base http://localhost:8000 --mysql "-u root -pSECRET"   # all ten
```

Playwright drives the real pages, desktop and mobile. Prices are recomputed
in Python from the client's list and compared against what the page renders —
in cents, because half-hours land on 50c and comparing whole rands would hide
a real drift. The availability checks prove *why* a cleaner was excluded, not
just that the list was short.

`test_theme.py` measures WCAG contrast on real rendered text in all four
palettes — compositing semi-transparent colours over whatever is actually
behind them — so a palette cannot be made prettier at the cost of being
readable. It has to freeze CSS transitions before measuring: the tiles are
declared `transition:.22s` with no property list, so `all` animates, and a
style read straight after the palette changes returns a value part-way
through the fade. That is how the first run "found" a 2.93:1 service tile
that is really 17:1.
