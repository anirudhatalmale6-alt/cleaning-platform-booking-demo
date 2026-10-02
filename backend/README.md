# The database and the API

MySQL 8 schema, seed data, and a PHP API that the four screens talk to.

Everything here was written against a real MySQL 8.0 and a real PHP 8.3,
not written and hoped at: `test_schema.py`, `test_api.py`, `test_parity.py`
and `test_live.py` are the proof, and all four pass.

---

## Getting it running

### 1. The database

```
mysql -u root -p < schema.sql
mysql -u root -p sparrow < seed.sql      # demo rows, optional but useful
```

`schema.sql` creates the database, 19 tables and 2 views. `seed.sql` fills
it with the same people and bookings the prototype shows, so the site
looks familiar the first time it comes up on your data.

The demo password for every seeded account is **demo1234**. Change it
before this goes anywhere real.

### 2. A database user that is not root

```sql
CREATE USER 'sparrow_app'@'localhost' IDENTIFIED BY 'a-long-random-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON sparrow.* TO 'sparrow_app'@'localhost';
FLUSH PRIVILEGES;
```

No DROP, no ALTER. If the website is ever compromised, the attacker gets
the rows, not the ability to delete the tables.

### 3. The API

```
cp api/config.local.example.php api/config.local.php
# edit it with the user and password from step 2
```

`config.local.php` is gitignored. Your database password does not belong
in a repository, not even a private one.

### 4. Run it

On your own machine, one command serves the website and the API together:

```
php -S localhost:8000 -t . backend/router.php
```

Then open <http://localhost:8000/index.html>. The dark bar at the top
should say **Live — reading and writing your MySQL database**. If it says
"sample data", the API is not answering and the page is telling you so
rather than pretending.

On real hosting you do not need `router.php`. Upload the folder, point
the domain at it, and the `.htaccess` in `api/` does the routing.

---

## How the site decides which mode it is in

The same four HTML files are served two ways: from GitHub Pages, where
there is no PHP, and from your host, where there is. On load the page
asks the API whether it exists. If it answers, every price, service,
cleaner and booking comes from MySQL. If it does not, the page runs on
the sample data in `assets/app.js`.

A 200 is not enough to decide that: a web server with no PHP will answer
`/api/health` with a styled 404 page, and `JSON.parse` on an HTML body
fails somewhere far from the cause. So every API response carries an
`X-Sparrow-Api` header, and that is what is checked.

---

## The two things worth knowing about the API

### Nothing the browser says about money is believed

The booking screen sends what the customer chose: a service, a band, which
extras are ticked, how many hours. It does **not** send a total, and if it
did, the total would be ignored. `price_booking()` in `api/lib.php` works
the price out again from the `settings`, `services` and `service_extras`
tables. A booking screen edited to post `total: 1.00` is still charged the
real amount, and `test_parity.py` proves it.

That does mean two price engines exist: one in JavaScript so the total
updates as the customer clicks, one in PHP that decides what is charged.
Two implementations of one rule drift apart. `test_parity.py` runs 218
bookings through both and fails on any difference down to the cent. It has
already earned its place twice: it caught the browser handing back an
estimate that broke the 10-hour cap, and the browser charging twice for an
extra listed twice.

### The money on an order is frozen

`orders` stores the flat rate, the hourly rate, the service fee and every
extra's price **as they were on the day**, not just a service code.

Raise the hourly rate from R35 to R40 with the rates stored on the order
and nothing happens to the orders you have already taken. Store only the
service code and recompute, and every order you have ever taken silently
changes price: refunds stop matching, reports stop matching, and the
customer's order history disagrees with their bank statement.

`test_schema.py` changes the rate and checks that not one historical
order moves.

---

## The files

| | |
| --- | --- |
| `schema.sql` | The whole database. Comments explain why, not just what. |
| `seed.sql` | Demo rows, generated from the prototype's own data so the two cannot disagree. |
| `api/index.php` | Every route, in one file, so the surface is visible at a glance. |
| `api/lib.php` | Connection, sessions, validation, and the price engine. |
| `api/config.php` | Reads `config.local.php`, or environment variables. |
| `api/.htaccess` | Apache routing, and denies serving the config as a file. |
| `router.php` | Only for PHP's built-in server while developing. |

## The tests

```
python3 test_schema.py --socket=/var/run/mysqld/mysqld.sock -u root
python3 tests/test_parity.py --base http://localhost:8000
python3 tests/test_api.py    --base http://localhost:8000
python3 tests/test_live.py   --base http://localhost:8000 --mysql "-u root -pSECRET"
```

Or all nine suites, front end and back, in one go:

```
python3 ../run_tests.py --with-backend --base http://localhost:8000 --mysql "-u root -pSECRET"
```

| Suite | What it proves |
| --- | --- |
| `test_schema.py` | The constraints reject what the screens cannot render; the money is frozen; the shortlist query excludes the right people |
| `test_parity.py` | The browser and the server price 218 bookings identically |
| `test_api.py` | The rules survive a client that lies: tampered totals, wrong roles, a full cleaner, a pending applicant |
| `test_live.py` | A real browser books a job, and the row is then read back out of MySQL with the right money on it |

`test_api.py` and `test_live.py` book, cancel and approve real rows, so
reload `seed.sql` before each run. `run_tests.py --with-backend` does that
for you.

---

## Still to do, and what it needs from you

- **Payments.** The order is marked paid and a `payments` row is written,
  but no gateway is called yet. Paystack and Peach both work in South
  Africa. Which one decides what goes in `api/index.php` at the `/orders`
  endpoint, and nothing else changes.
- **Email and SMS.** Every message the brief describes is composed and
  stored in `messages_sent`, and the admin dashboard reads them back.
  Sending them is one function, `record_message()` in `api/lib.php`.
  It needs an SMTP account, and an SMS provider for the worker alerts.
- **Google Places.** The address step runs against a stand-in geocoder.
  It needs an API key on your billing account, and then the latitude and
  longitude columns on `customer_addresses` and `orders` start being
  filled in for real.
- **File uploads.** `employee_documents` holds the paths. The upload
  handler is not written yet, and when it is, those files must sit
  **outside** the public web root: an ID document on a guessable URL is
  the worst kind of leak.
