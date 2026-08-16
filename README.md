# Sparrow — Cleaning Platform booking flow (prototype)

Interactive prototype of the customer booking flow for the cleaning services
platform: service selection → space details → schedule → address → payment →
confirmation with automatic professional matching.

**Live demo:** https://anirudhatalmale6-alt.github.io/cleaning-platform-booking-demo/

## What is real in this prototype

- **Live pricing engine.** Base rate + per-bedroom/per-bathroom + extras +
  frequency discount + service fee, recalculated on every interaction.
  All rates live in one `CFG` object (`index.html`) — in production this is
  served by the API and edited from the admin dashboard, no redeploy.
- **Duration estimation** derived from the same rules, used to size the booking
  window and the professional's payout.
- **Promo codes** (`SPARROW20`, `WELCOME50`) applied against the post-discount
  subtotal, with the service fee recomputed on the net.
- **Availability-aware slots** — slots show how many professionals are free and
  disable when full.
- **Guest checkout** toggle, saved-address style fields, four payment rails
  (card / wallet / instant EFT / cash) and escrow-style capture-on-completion.
- **Responsive**: sticky summary panel on desktop, sticky price bar on mobile
  that drives the whole flow.

## What is mocked

Availability, the matched professional, and the confirmation reference are
generated client-side. There is no backend in this prototype — it exists so the
flow, the pricing rules and the visual direction can be agreed before the real
build starts.

## Testing

`shoot.py` drives the full flow with Playwright (desktop and mobile), asserts
the step gating and captures screenshots into `shots/`.

```
python3 shoot.py
```
