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

- Office cleaning and all four outdoor services have **estimated hours I made
  up**. The price list covers indoor house cleaning and laundry only. These
  are marked on screen wherever they appear.
- Deep clean and move-in/move-out add 2 h and 3 h to the band estimate. Also
  mine.
- Geocoding runs against a stand-in. It swaps to Google Places once there is
  an API key on the client's billing account.
- Cleaner photos are drawn illustrations, not stock faces — the real card
  shows the head-and-shoulders photo uploaded with the application.

## Tests

```
python3 run_tests.py          # all four suites
python3 test_booking.py       # pricing, the hours stepper, the 10-hour cap, availability
python3 test_customer.py      # ratings with comments, addresses, cancelling
python3 test_cleaner.py       # the sign-in gate, the application form, the calendar
python3 test_admin.py         # approve, decline-with-reason, employees by role, search
```

Playwright drives the real pages, desktop and mobile. Prices are recomputed
in Python from the client's list and compared against what the page renders —
in cents, because half-hours land on 50c and comparing whole rands would hide
a real drift. The availability checks prove *why* a cleaner was excluded, not
just that the list was short.
