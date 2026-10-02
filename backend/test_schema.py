"""Proves the schema does what the comments in it claim.

Runs against a real MySQL server through the `mysql` client, so there is
nothing to pip install. Point it at your database with the usual flags:

    python3 test_schema.py --socket=/var/run/mysqld/mysqld.sock -u root
    python3 test_schema.py -h 127.0.0.1 -P 3306 -u root -pSECRET

Anything you pass is handed straight to `mysql`. The database name is
appended for you.

The three claims worth testing are the three that are expensive to get
wrong: that the money on an order is frozen, that the 10-hour cap and
the blocked-day calendar actually exclude a worker, and that the
constraints reject the rows the screens cannot render.
"""
import json, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).parent
DB   = "sparrow"
ARGS = sys.argv[1:] or ["--socket=/var/run/mysqld/mysqld.sock", "-u", "root"]

fails = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(label)


def sql(query, expect_error=False):
    """Run one statement. Returns a list of dict rows, or the error text."""
    p = subprocess.run(["mysql", *ARGS, DB, "--batch", "--raw", "-e", query],
                       capture_output=True, text=True)
    if p.returncode != 0:
        if expect_error:
            return p.stderr.strip()
        raise RuntimeError(f"{query[:70]} -> {p.stderr.strip()}")
    if expect_error:
        return None                       # it was supposed to fail and did not
    lines = p.stdout.rstrip("\n").split("\n")
    if len(lines) < 2:
        return []
    # information_schema hands column names back in upper case, so they are
    # lowered here and every assertion below can use one spelling.
    head = [h.lower() for h in lines[0].split("\t")]
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:]]


def one(query):
    rows = sql(query)
    return list(rows[0].values())[0] if rows else None


print("1. The schema loaded, and every table is InnoDB/utf8mb4")
tables = sql("SELECT table_name, engine, table_collation FROM information_schema.tables "
             f"WHERE table_schema='{DB}' AND table_type='BASE TABLE' ORDER BY table_name")
check("tables", len(tables), 19)
check("all InnoDB", {t["engine"] for t in tables}, {"InnoDB"})
check("all utf8mb4", {t["table_collation"].split("_")[0] for t in tables}, {"utf8mb4"})
views = sql(f"SELECT table_name FROM information_schema.views WHERE table_schema='{DB}'")
check("views", len(views), 2)

print("\n2. Money is DECIMAL, never a float")
floaty = sql("SELECT table_name, column_name, data_type FROM information_schema.columns "
             f"WHERE table_schema='{DB}' AND data_type IN ('float','double')")
check("no float/double columns anywhere", floaty, [])
money = sql("SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_schema='{DB}' AND table_name='orders' "
            "AND column_name IN ('flat_rate','hourly_rate','labour_total','extras_total',"
            "'service_fee','total')")
check("the six money columns on orders are decimal",
      {m["data_type"] for m in money}, {"decimal"})

print("\n3. Every order's own numbers add up")
bad = sql("SELECT reference, total, flat_rate + labour_total + extras_total + service_fee AS parts "
          "FROM orders WHERE ABS(total - (flat_rate + labour_total + extras_total + service_fee)) > 0.001")
check("total = flat + labour + extras + fee, on every row", bad, [])
bad = sql("SELECT reference FROM orders "
          "WHERE ABS(labour_total - hours_booked * hourly_rate) > 0.001")
check("labour = hours booked x the frozen hourly rate", bad, [])
bad = sql("SELECT o.reference FROM orders o LEFT JOIN ("
          "  SELECT order_id, SUM(price) s FROM order_extras GROUP BY order_id) e "
          "ON e.order_id = o.id WHERE ABS(o.extras_total - COALESCE(e.s,0)) > 0.001")
check("extras total matches the extras actually on the order", bad, [])

print("\n4. The totals agree with the website's own price engine")
# These are the numbers priceBooking() in assets/app.js produced, carried
# across by the seed generator. If the database and the site ever disagree
# about what a booking costs, it shows up here and nowhere else.
data = json.loads((HERE / "expected_totals.json").read_text())
rows = {r["reference"]: r["total"] for r in sql("SELECT reference, total FROM orders")}
check("same number of orders", len(rows), len(data))
mismatch = {ref: (rows.get(ref), f"{want:.2f}") for ref, want in data.items()
            if rows.get(ref) != f"{want:.2f}"}
check("every order matches the site to the cent", mismatch, {})

print("\n5. The money is frozen — raising the rate must not reprice history")
before = {r["reference"]: r["total"] for r in sql("SELECT reference, total FROM orders")}
sql("UPDATE settings SET setting_value='40.00' WHERE setting_key='hourly_rate'")
after = {r["reference"]: r["total"] for r in sql("SELECT reference, total FROM orders")}
check("R35/hr -> R40/hr changes no existing order", after, before)
check("and the setting really did change",
      one("SELECT setting_value FROM settings WHERE setting_key='hourly_rate'"), "40.00")
sql("UPDATE settings SET setting_value='35.00' WHERE setting_key='hourly_rate'")

print("\n6. The shortlist query excludes who it should")
# Look the ids up by name. The first version of this file hardcoded them
# and had them wrong — the seed inserts the workers in the order they
# appear in the prototype, which is not cl1..cl9 — so three assertions
# passed for the wrong reason. A test that is right by accident is worse
# than no test.
WHO = {r["first_name"]: r["id"]
       for r in sql("SELECT id, first_name FROM employees")}
print("   ids:", {k: WHO[k] for k in sorted(WHO)})


def shortlist(date, group, city, job_hours=1):
    """Who can take a `job_hours` job of this type, in this city, that day.

    The 10-hour cap has to be checked against the hours of the job being
    booked, not just against what the worker already has. Asking only
    `hours_committed < 10` offers a 6-hour clean to someone with 9 hours
    already on the day, and the cap is breached at the moment of booking.
    """
    return [r["id"] for r in sql(f"""
        SELECT e.id FROM employees e
        JOIN employee_areas a ON a.employee_id = e.id AND a.city = '{city}'
        WHERE e.account_status = 'approved'
          AND e.service_group = '{group}'
          AND NOT EXISTS (SELECT 1 FROM employee_unavailability u
                          WHERE u.employee_id = e.id AND u.unavailable_date = '{date}')
          AND COALESCE((SELECT l.hours_committed FROM v_employee_day_load l
                        WHERE l.employee_id = e.id AND l.scheduled_date = '{date}'), 0)
              + {job_hours}
              <= (SELECT setting_value FROM settings WHERE setting_key = 'max_hours')
        ORDER BY e.id""")]


nomsa, grace, zanele = WHO["Nomsa"], WHO["Grace"], WHO["Zanele"]
lerato, precious, bongani = WHO["Lerato"], WHO["Precious"], WHO["Bongani"]

check("Nomsa blocked 24 Aug, so she is not offered that day",
      nomsa in shortlist("2026-08-24", "indoor", "Cape Town"), False)
check("but she is offered on a day she did not block",
      nomsa in shortlist("2026-08-26", "indoor", "Cape Town"), True)
check("an outdoor job never shortlists an indoor cleaner",
      set(shortlist("2026-08-26", "outdoor", "Cape Town")) &
      set(shortlist("2026-08-26", "indoor", "Cape Town")), set())
check("Precious is still pending, so she is never shortlisted",
      precious in shortlist("2026-08-26", "indoor", "Cape Town"), False)
check("Bongani was declined, so neither is he",
      bongani in shortlist("2026-08-26", "outdoor", "Cape Town"), False)
check("Lerato works Johannesburg, so not in a Cape Town list",
      lerato in shortlist("2026-08-26", "indoor", "Cape Town"), False)
check("and she IS in a Johannesburg list",
      lerato in shortlist("2026-08-26", "indoor", "Johannesburg"), True)

print("\n7. The 10-hour cap is enforced against the job being booked")
# Grace has an 8-hour clean on 20 Aug with an oven and a fridge on it,
# which is another hour of her day: 9 committed, 1 left.
load = one("SELECT hours_committed FROM v_employee_day_load "
           f"WHERE employee_id = {grace} AND scheduled_date = '2026-08-20'")
check("her committed hours include the extras' time", float(load), 9.0)
check("a 1-hour job still fits",
      grace in shortlist("2026-08-20", "indoor", "Cape Town", job_hours=1), True)
check("a 2-hour job does not",
      grace in shortlist("2026-08-20", "indoor", "Cape Town", job_hours=2), False)
check("a 4-hour job certainly does not",
      grace in shortlist("2026-08-20", "indoor", "Cape Town", job_hours=4), False)
check("and she is free again the next day",
      grace in shortlist("2026-08-21", "indoor", "Cape Town", job_hours=8), True)
check("a cancelled job gives its hours back",
      one("SELECT hours_committed FROM v_employee_day_load "
          f"WHERE employee_id = {WHO['Thabo']} AND scheduled_date = '2026-06-30'"), None)

print("\n8. The constraints reject the rows the screens cannot render")
err = sql("INSERT INTO employees (first_name,last_name,email,phone,date_of_birth,id_number,"
          "service_group,account_status) VALUES ('Test','Case','t@c.co','0820000000',"
          "'1990-01-01','9001015800085','indoor','declined')", expect_error=True)
check("a decline with no reason is refused", "chk_emp_decline_reason" in (err or ""), True)

err = sql("INSERT INTO order_ratings (order_id,stars) VALUES (1,6)", expect_error=True)
check("six stars is refused", "chk_rating_stars" in (err or ""), True)

err = sql("INSERT INTO employee_unavailability (employee_id,unavailable_date) "
          "VALUES (1,'2026-08-24')", expect_error=True)
check("blocking the same day twice is refused", "Duplicate entry" in (err or ""), True)

err = sql("INSERT INTO customers (first_name,last_name,email) "
          "VALUES ('Dup','Licate','thandi.m@example.co.za')", expect_error=True)
check("two customers cannot share an email", "Duplicate entry" in (err or ""), True)

err = sql("INSERT INTO payments (order_id,gateway,gateway_ref,amount) "
          "VALUES (1,'payfast','PF-DEMO-00001',100)", expect_error=True)
check("a gateway resending its callback cannot double-charge",
      "Duplicate entry" in (err or ""), True)

err = sql("DELETE FROM customers WHERE id = 1", expect_error=True)
check("a customer with orders cannot be deleted out from under them",
      "foreign key constraint" in (err or "").lower(), True)

print("\n9. Deleting a customer does take their addresses with them")
sql("INSERT INTO customers (id,first_name,last_name,email) VALUES (99,'No','Orders','no@orders.co.za')")
sql("INSERT INTO customer_addresses (customer_id,street_line,suburb,city,province) "
    "VALUES (99,'1 Nowhere Street','Nowhere','Cape Town','Western Cape')")
check("address exists", one("SELECT COUNT(*) FROM customer_addresses WHERE customer_id=99"), "1")
sql("DELETE FROM customers WHERE id = 99")
check("and is gone with the customer",
      one("SELECT COUNT(*) FROM customer_addresses WHERE customer_id=99"), "0")

print("\n10. Ratings are derived, so they cannot drift from the reviews shown")
r = sql("SELECT employee_id, rating_count, rating_avg FROM v_employee_ratings "
        "WHERE rating_count > 0 ORDER BY employee_id")
check("some workers have ratings", len(r) > 0, True)
manual = one("SELECT ROUND(AVG(rt.stars),2) FROM order_ratings rt "
             "JOIN orders o ON o.id = rt.order_id WHERE o.employee_id = 1")
view = one("SELECT rating_avg FROM v_employee_ratings WHERE employee_id = 1")
check("the view agrees with the raw average", view, manual)

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all schema checks passed")
