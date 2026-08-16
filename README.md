# Sparrow — cleaning services platform (prototype)

Interactive prototype of the customer website plus all three dashboards, built
against the client's three specification documents.

**Live:** https://anirudhatalmale6-alt.github.io/cleaning-platform-booking-demo/

| Surface | File | Built from |
|---|---|---|
| Website + booking flow | `index.html` | *Customer Dashboards.docx* (booking, checkout, confirmation) |
| Customer dashboard | `dashboard.html` | *Customer Dashboards.docx* |
| Cleaner application + dashboard | `cleaner.html` | *Cleaner dashboard.docx* (+ additions, see below) |
| Admin dashboard | `admin.html` | *Admin Dashboards.pdf* |

Shared design system in `assets/app.css`, shared config/data/price-engine in
`assets/app.js`. All four surfaces read the same booking records, so a booking
confirmed in the admin dashboard is the same object the customer and the
cleaner see.

## Pricing — structure from the spec, numbers still open

The spec fixes the *structure*; the client has not yet given the rates. Every
number lives in `CFG` at the top of `assets/app.js`, so real rates drop in
without touching a single screen.

- **Room-based services** — `rooms × 40 min → hours × hourly rate`, floored at a
  2 hour minimum. 40 minutes per room is taken verbatim from the spec.
- **Office cleaning** — unit size band × number of units.
- **Flat-rate services** — gardening, windows, pool, laundry.
- **Checklist items** add both money and time, so the duration estimate stays
  honest and the cleaner is paid for a real window.
- **Checkout lines** follow the spec exactly: Service fee, Extras, Discount,
  VAT, Total. VAT is 15% added on top, configurable and switchable.

`priceBooking()` is the single price engine. The booking flow, the customer
dashboard, the cleaner payout screen and the admin quote all call it, so they
cannot disagree about what a job costs.

## Assignment model

The admin spec says the admin confirms bookings and assigns workers, so that is
what is built: checkout leaves a booking as **awaiting confirmation** with no
cleaner attached. The admin confirm-and-assign screen shortlists only cleaners
who do that kind of work *and* cover that city, flags the best match and the
customer's favourite, but never forces the choice.

The cleaner dashboard also carries a **Job offers** screen showing the
accept/decline model, so both approaches can be compared before deciding.

## Named additions — not in the client's documents

These were built because the product does not work without them. They are
flagged here rather than presented as if they were specified:

- **Everything a cleaner sees after approval** — the cleaner document covers
  only the application form. Job list, checklist, availability, earnings,
  payouts and ratings are my design.
- **Ratings and reviews** — favourite professionals and cleaner ratings both
  depend on a review loop that no document describes.
- The admin document lists "Indoor cleaner" twice under *Upload new worker*;
  the second is read as **Outdoor**.

## What is mocked

No backend. Availability, the professional shortlist and reference numbers are
generated client-side and deterministically — no `Math.random()`, so the demo
behaves identically on every run. Maps are drawn, not embedded.

## Tests

```
python3 run_tests.py          # all three suites
python3 test_booking.py       # booking flow + pricing maths
python3 test_cleaner.py       # application validation + cleaner dashboard
python3 test_admin.py         # confirm/assign, approvals, search, worker upload
```

Playwright drives the real pages in desktop and mobile viewports. The pricing
assertions recompute every total independently in Python from the spec rules
and compare against what the page renders, so a drift in either direction
fails. Screenshots land in `shots/`.
