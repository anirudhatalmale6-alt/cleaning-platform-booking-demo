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

### 3b. Where the uploads go, and your email address

Two settings decide whether this is safe and whether you hear about
orders.

**storage_path**, in `config.local.php`. Point it somewhere **outside**
your `public_html`. Worker ID copies and police clearances are written
there, and nothing should be able to reach them except the admin download.
`/api/health` reports `storage_exposed: true` if you have left it inside
the public folder, so you can check rather than hope.

**Your email addresses**, in the `settings` table. These are the lines to
change:

```sql
UPDATE settings SET setting_value = 'you@yourcompany.co.za'  WHERE setting_key = 'orders_email';
UPDATE settings SET setting_value = 'noreply@yourcompany.co.za' WHERE setting_key = 'from_email';
UPDATE settings SET setting_value = 'Your Company'            WHERE setting_key = 'from_name';
UPDATE settings SET setting_value = 'help@yourcompany.co.za'  WHERE setting_key = 'support_email';
```

`orders_email` is the one that matters most: every new order writes an
alert addressed to it. If one of your admin accounts already uses that
address it is not sent twice.

### 3c. Upload size

`settings.max_upload_mb` is what you want. PHP's `upload_max_filesize` and
`post_max_size` are what the server will physically accept, and on a
default install both are **2 MB**. The smaller of the two wins, and it is
the number the application form shows the worker, so they are never told
5 MB and stopped at 2.

`/api/health` returns `upload_mb` (the real limit) and
`upload_capped_by_php` (true when php.ini is the thing in the way). If it
is true, raise both values in `php.ini` or `.htaccess`:

```
php_value upload_max_filesize 10M
php_value post_max_size 12M
```

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
| `migrations/` | Run these only if you loaded `schema.sql` before the change they describe. |
| `api/uploads.php` | Document and photo uploads, and everything they refuse. |
| `api/gateway_ozow.php` | Ozow, written out but not switched on. See below. |
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
| `test_uploads.py` | A PHP script renamed to .pdf is refused, a filename cannot escape the folder, the files are not reachable by URL, and only an admin can download one |
| `test_live.py` | A real browser books a job, and the row is then read back out of MySQL with the right money on it |

`test_api.py` and `test_live.py` book, cancel and approve real rows, so
reload `seed.sql` before each run. `run_tests.py --with-backend` does that
for you.

---

## Uploads

Workers attach their ID copy, a head-and-shoulders photo and a police
clearance on the application form, and an approved worker can replace
their photo from their dashboard afterwards.

An applicant has no account yet, so the application is written first and
hands back a **one-time upload token**, valid for two hours and stored
hashed exactly as a password would be. The files are uploaded against
that. Doing it the other way round would mean holding people's ID copies
for applications that were never finished.

What the server refuses, and why:

| | |
| --- | --- |
| A PHP file renamed `.pdf` | The type is read out of the bytes with `finfo`, not taken from the request or the extension |
| A file that only *starts* like a PNG | `getimagesize()` has to decode it |
| A filename like `../../index.php` | The stored name is generated here; theirs is kept for display only, with any path stripped |
| A PDF as a profile photo | That picture is what customers see |
| Anything over the limit | And it says which limit, and how to raise it |

The files are served only by `GET /api/admin/documents/{id}`, which checks
for an admin session, sends `Content-Disposition: attachment` and
`X-Content-Type-Options: nosniff`, so a stored file can never be rendered
in place by a browser.

## Ozow

`api/gateway_ozow.php` has the whole integration written out with the live
calls commented. Nothing calls it yet. To switch it on you need a SiteCode
and a PrivateKey from Ozow Merchant Admin, both of which go in
`config.local.php`.

**One thing to check before trusting it.** Ozow's documentation and the
community examples disagree about whether the private key is appended
before or after the string is lowercased. If your key has uppercase
letters in it the two produce different hashes, and the only symptom is
"hash check failed". Both forms are in the file, one line apart. Confirm
which against the documentation on your own merchant account.

**The rule that matters once it is live:** the order is marked paid by the
server-to-server notification, never by the customer arriving back at the
success URL. Anyone can open a success URL without paying.

## Still to do, and what it needs from you

- **Payments.** `gateway_ozow.php` is written but not switched on, and the
  order is marked paid directly so the demo can be clicked through. It
  needs your Ozow credentials.
- **Email and SMS.** Every message the brief describes is composed and
  stored in `messages_sent`, and the admin dashboard reads them back.
  Sending them is one function, `record_message()` in `api/lib.php`.
  It needs an SMTP account, and an SMS provider for the worker alerts.
- **Google Places.** The address step runs against a stand-in geocoder.
  It needs an API key on your billing account, and then the latitude and
  longitude columns on `customer_addresses` and `orders` start being
  filled in for real.
- **Virus scanning.** The uploads are type-checked but not scanned. If you
  want ClamAV in front of them, it is one call in `accept_upload()`.
