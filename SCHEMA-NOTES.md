# What the screens actually capture

You are writing the SQL for customers, admins and workers. This is the list
of every field the four screens collect or display, pulled out of the code
rather than from memory, so your tables cover them first time and we do not
have to migrate afterwards.

It is a checklist, not a schema. Name things however you like. If it is
easier, say the word and I will send a reference `schema.sql` you can take
or ignore.

Three things below are easy to miss and expensive to add later. They are
marked **WATCH**.

---

## Customers

| Field | Notes |
| --- | --- |
| id | |
| first name, surname | shown as "Welcome back, Thandi" |
| email | sign-in identity, and where the order confirmation goes |
| mobile | |
| password hash | |
| joined date | shown on the admin customer screen |
| guest flag | guests check out without an account; you still need the row to send them a confirmation |

### Customer addresses — a separate table, one customer has many

| Field | Notes |
| --- | --- |
| label | "Home", "Mom's place", "Office" |
| property type | House / Flat / Townhouse / Cottage / Bachelor unit |
| street line | |
| unit / flat number | |
| suburb | |
| city, province | |
| latitude, longitude | from the geocode step, so the worker gets a pin not a paragraph |
| access notes | "Buzzer 12. Two cats, keep the balcony door shut." |
| is primary | |

### Saved payment methods

Card brand, last four digits, expiry, and the token from whichever gateway
you end up using. **Never the full card number** — your gateway holds that,
not you.

---

## Workers

Everything the application form asks, in the order it asks it:

| Field | Notes |
| --- | --- |
| first name, surname | |
| email, mobile | |
| date of birth | 18+ is enforced at this field |
| SA ID or passport number | the form checks the ID's own check digit, and that the birth date inside the ID matches the one typed |
| indoor or outdoor | this is what the admin lists them by |
| years of experience | |
| languages | several per worker |
| provinces and cities they cover | several per worker, so its own table |
| own transport | yes / no |
| account status | pending / approved / declined — a worker cannot sign in until approved |
| decline reason | the admin types it, and it is what the declined worker sees and gets emailed |
| profile photo | they can change this after approval |

### Worker documents — a separate table, one worker has many

ID document, head-and-shoulders photo, criminal record check, work permit.
Store the file path or object key, the original filename, the size and the
upload date. The admin screen downloads these from the application.

### Worker unavailability — **WATCH**

The cleaner calendar lets a worker block individual days so they are not
booked. That is its own table: worker id + date. It is easy to leave out
because nothing on the customer side shows it, but the booking screen will
not shortlist a worker whose day is blocked, so without it the calendar does
nothing.

### Worker ratings

Rating and comment are left by the customer against a completed order, so
they belong to the order, not the worker. The worker's average is derived.

---

## Admins

| Field | Notes |
| --- | --- |
| id, name, email, password hash | |
| role | if you ever want more than one level of admin, this is the cheapest time to add it |

---

## Orders

| Field | Notes |
| --- | --- |
| reference | the SPW-104312 the customer sees |
| customer id | |
| worker id | set at checkout, since the customer picks their own |
| address id, or a copy of the address | see the WATCH below |
| service | standard / deep / move / laundry / office / outdoor / garden / windows / carwash |
| date, start time | |
| hours booked | after the customer has moved the stepper |
| note for the worker | |
| status | paid, upcoming, in progress, completed, cancelled |
| created at, paid at | |

### Service-specific answers — **WATCH**

Each service asks a different question, and the answer has to be stored or
the worker arrives not knowing the job:

| Service | What is stored |
| --- | --- |
| Standard / deep / move-in-out | bedroom band (1-2, 3-4, 5+) |
| Laundry | wash type, and finish type |
| Window cleaning | number of rooms |
| Car wash | vehicle size |
| Office / outdoor / gardening | nothing extra, just the hours |

Two normal ways to handle it: one nullable column per answer on the orders
table, or a small `order_details` table of order id / key / value. The first
is simpler to read, the second survives you adding services later. Either is
fine, but pick one now.

### Extra tasks on an order

A separate table: order id, task id, and **the price and minutes as charged
at the time**. See the next point.

### Freeze the money on the order — **WATCH**

Store the flat rate, the hourly rate, the service fee, each extra's price,
and the total **as numbers on the order row**, not just the service id.

If you store only the service and recompute the total from your current
price list, then the day you raise the hourly rate from R35 to R40, every
order you ever took silently changes price. Refunds stop matching, your
reports stop matching, and the customer's order history disagrees with their
bank statement. A past order is a record of what was charged, not a sum to
be recalculated.

---

## Messages sent

The brief has automatic emails and SMS going out on new orders, approvals
and declines. Worth one table: who it went to, which channel, the subject,
the body, when it was sent, and whether it went through. It is what you will
want the first time a worker says they were never told about a job.

---

## One question back

Nothing in the screens tracks whether a worker was paid, only whether the
customer paid you. If you want payouts, invoices or commission on the admin
dashboard, that is another table or two and better decided before the schema
is fixed than after.
