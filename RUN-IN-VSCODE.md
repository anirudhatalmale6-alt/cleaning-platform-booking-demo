# Running this in VS Code

Short answer: yes, and there is nothing to build. The site is plain HTML,
CSS and JavaScript — no npm, no node_modules, no compile step. Open the
folder and it runs.

---

## The 30-second version

1. **Code → Open Folder…** and pick this folder.
2. Right-click `index.html` in the file list → **Open with Live Server**.
3. The site opens at `http://127.0.0.1:5500/index.html`.

VS Code will offer to install Live Server the first time you open the
folder, because `.vscode/extensions.json` asks for it. Click **Install**.

Edit any file, hit save, and the browser reloads itself.

### If you would rather not install an extension

Press `Ctrl+Shift+P` (`Cmd+Shift+P` on a Mac) → **Tasks: Run Task** →
**Serve the site**, then open `http://localhost:5500`. That task runs a
one-line Python web server that is already on your machine.

### If you want the absolute quickest look

Double-click `index.html` in Finder/Explorer. It opens straight in the
browser off `file://` and works, including the palette switcher. Use one
of the two methods above for real work — a couple of browsers (Safari
especially) restrict what a page is allowed to do from `file://`, and
that is the sort of difference that wastes an afternoon.

---

## The four screens

| File | What it is |
| --- | --- |
| `index.html` | The public site, sign in / sign up / guest, and the whole booking flow |
| `dashboard.html` | The customer dashboard |
| `cleaner.html` | Cleaner registration, the sign-in gate, and the cleaner dashboard |
| `admin.html` | The admin dashboard |

The dark strip across the top of each one is a prototype aid, not part
of the product — it jumps between the four screens and holds the palette
switcher. It comes out before launch.

---

## Where the colours live

Every colour on all four screens comes from the variables at the top of
`assets/app.css`. Four palettes are defined there — Fresh, Electric,
Forest and Heritage — and the switcher just sets `data-theme` on the
`<html>` element.

To change a colour, change it in **one** place:

```css
:root,
[data-theme="fresh"]{
  --primary:#13C26A;     /* the bright green on buttons */
  --moss:#0A7D45;        /* green text, icons and borders */
  --clay:#D8451A;        /* the coral accent */
  ...
}
```

Save the file, refresh the browser, done. Nothing else needs touching —
there is no hardcoded green anywhere else in the project, which is what
makes a repaint a five-minute job rather than a day of find-and-replace.

Two tokens are easy to mix up and worth knowing apart:

- `--primary` is a **fill**. It is bright, and `--on-primary` (a
  near-black green) is the text that sits on it.
- `--moss` is **text**. It is darker on purpose so it reads on white.

If you make `--moss` as bright as `--primary`, green text on a white card
stops being readable. `test_theme.py` will tell you if that happens.

---

## Where the prices live

`assets/app.js`, the `CFG` object at the very top — the flat rate, the
R35/hour, the service fee, the unit-size estimates, every extra task and
its time, the window-cleaning rooms and the car-wash sizes. All of it is
data in one object, so changing a price never means changing logic.

Anything still marked `placeholder: true` is a number I invented because
it has not been priced yet. It is flagged on screen too.

---

## Running the tests (optional)

There are five suites. They drive a real Chromium browser through the
screens and recompute every price in Python from your price list, rather
than reading a number off the page and believing it.

One-time setup:

```
python3 -m pip install playwright
python3 -m playwright install chromium
```

Then `Ctrl+Shift+P` → **Tasks: Run Task** → **Run all tests**, or from a
terminal:

```
python3 run_tests.py
```

| Suite | Covers |
| --- | --- |
| `test_booking.py` | The booking flow and every total |
| `test_customer.py` | Customer dashboard, ratings and comments |
| `test_cleaner.py` | The application form, the sign-in gate, the calendar |
| `test_admin.py` | Approvals, declines, the order list |
| `test_theme.py` | The palettes, and a contrast check on every one |

On Windows use `py -3` instead of `python3`.

---

## What this is not, yet

There is no server and no database. The sample bookings, cleaners and
customers live in `assets/app.js`, and they reset when you refresh. That
is deliberate at this stage — it keeps the screens quick to change while
we are still agreeing what they should say.

The WhatsApp bot is the opposite: that one is a real Python service and
comes with its own `SETUP.md`.
