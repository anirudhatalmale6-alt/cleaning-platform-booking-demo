<?php
/**
 * The whole API, in one router.
 *
 * Every route is listed here so you can see the surface at a glance.
 * Nothing trusts a price, a role or an id that arrived from the browser.
 *
 *   GET  /api/health
 *   GET  /api/catalog                services, extras and the price levers
 *   POST /api/price                  quote a booking without saving it
 *   GET  /api/availability           who can take this job on this day
 *
 *   POST /api/customer/signup
 *   POST /api/customer/login
 *   POST /api/logout
 *   GET  /api/customer/me            profile, addresses, orders, favourites
 *   POST /api/customer/addresses
 *   POST /api/orders                 book and pay
 *   POST /api/orders/{ref}/cancel
 *   POST /api/orders/{ref}/rate
 *
 *   POST /api/employee/apply         returns a one-time upload token
 *   POST /api/employee/documents     multipart. Token for an applicant,
 *                                    session for an approved worker
 *   POST /api/employee/login         refuses pending and declined
 *   GET  /api/employee/me            jobs, calendar, profile, documents
 *   POST /api/employee/unavailability
 *
 *   POST /api/admin/login
 *   GET  /api/admin/overview
 *   GET  /api/admin/applications
 *   POST /api/admin/applications/{id}/decide
 *   GET  /api/admin/customers
 *   GET  /api/admin/messages
 *   GET  /api/admin/documents/{id}   streams an uploaded file
 */
declare(strict_types=1);

require __DIR__ . '/lib.php';
require __DIR__ . '/uploads.php';

$c = cfg();
if ($c['cors_origins'] && isset($_SERVER['HTTP_ORIGIN'])
    && in_array($_SERVER['HTTP_ORIGIN'], $c['cors_origins'], true)) {
    header('Access-Control-Allow-Origin: ' . $_SERVER['HTTP_ORIGIN']);
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Allow-Headers: Content-Type');
}
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

set_exception_handler(function (Throwable $e) {
    $c = cfg();
    error_log('[sparrow-api] ' . $e->getMessage() . ' @ ' . $e->getFile() . ':' . $e->getLine());
    // The real message goes to the log, never to the browser: a PDO error
    // quotes the SQL, and the SQL names your columns.
    json_out(['error' => $c['debug'] ? $e->getMessage() : 'Server error'], 500);
});

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

/**
 * Work out the route whichever way this file is being reached:
 *   /api/health                 Apache with the .htaccess rewrite
 *   /index.php/health           no rewrite, or PHP's built-in server
 *   /backend/api/index.php?...  a subfolder install
 * PATH_INFO is the server's own answer when it has one; otherwise the
 * script's own name is trimmed off the front of the request.
 */
$path = $_SERVER['PATH_INFO'] ?? '';
if ($path === '') {
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $script = $_SERVER['SCRIPT_NAME'] ?? '';
    if ($script !== '' && str_starts_with($path, $script)) {
        $path = substr($path, strlen($script));
    } else {
        $dir = rtrim(dirname($script), '/');
        if ($dir !== '' && str_starts_with($path, $dir)) {
            $path = substr($path, strlen($dir));
        }
    }
}
$path = preg_replace('#^/api(?=/|$)#', '', $path);
$path = '/' . trim($path, '/');
$seg    = $path === '/' ? [] : explode('/', trim($path, '/'));
$in     = body();

/* =====================================================================
   PUBLIC
   ===================================================================== */

if ($path === '/health') {
    /* storage_exposed warns when the upload folder is inside the folder the
       web server publishes. .htaccess covers Apache; nginx and PHP's own
       server ignore it, and then an ID document is one guessed URL away.
       Reported here so a deployment can be checked without taking anyone's
       word for it. */
    $docRoot = realpath($_SERVER['DOCUMENT_ROOT'] ?? '') ?: null;
    $store   = realpath(cfg()['storage_path'] ?? '') ?: null;
    $wanted = (float)setting('max_upload_mb', '5');
    json_out([
        'ok'      => true,
        'service' => 'sparrow-api',
        'time'    => gmdate('c'),
        'storage_exposed' => ($docRoot && $store && str_starts_with($store, $docRoot)),
        'upload_mb'        => effective_upload_mb(),
        // true when php.ini is the thing stopping a worker, not your setting
        'upload_capped_by_php' => php_limit_mb() < $wanted,
    ]);
}

if ($path === '/catalog') {
    $services = q('SELECT code, name, description, service_group, pricing_model,
                          flat_rate_override, est_hours, add_hours, extra_set,
                          hours_are_estimated
                   FROM services WHERE is_active = 1 ORDER BY sort_order');
    $extras   = q('SELECT code, name, description, extra_set, minutes, price,
                          price_is_estimated
                   FROM service_extras WHERE is_active = 1 ORDER BY sort_order');
    $settings = settings_all();
    // The limit the screens enforce is the one that will actually work.
    $settings['max_upload_mb'] = (string)effective_upload_mb();
    json_out([
        'settings' => $settings,
        'services' => $services,
        'extras'   => $extras,
    ]);
}

if ($path === '/price' && $method === 'POST') {
    json_out(price_booking($in));
}

/**
 * Who can take this job. The 10-hour cap is checked against the hours of
 * the job being booked, not just against what the worker already has:
 * asking only "under 10?" offers a 6-hour clean to someone with 9 hours
 * on the day, and breaks the rule at the moment of booking.
 */
if ($path === '/availability') {
    $date    = $_GET['date']    ?? '';
    $city    = $_GET['city']    ?? '';
    $service = $_GET['service'] ?? '';
    $hours   = (float)($_GET['hours'] ?? 1);
    if (!$date || !$city || !$service) {
        fail('date, city and service are required', 422);
    }
    $svc = service_row($service);
    if (!$svc) {
        fail('Unknown service', 422);
    }
    $rows = q(
        'SELECT e.id, e.first_name, e.last_name, e.service_group, e.years_experience,
                e.profile_photo_path,
                COALESCE(r.rating_avg, 0)   AS rating,
                COALESCE(r.rating_count, 0) AS rating_count,
                COALESCE(r.jobs_completed, 0) AS jobs,
                COALESCE(l.hours_committed, 0) AS hours_committed
         FROM employees e
         JOIN employee_areas a      ON a.employee_id = e.id AND a.city = ?
         LEFT JOIN v_employee_ratings r ON r.employee_id = e.id
         LEFT JOIN v_employee_day_load l
                ON l.employee_id = e.id AND l.scheduled_date = ?
         WHERE e.account_status = "approved"
           AND e.service_group = ?
           AND NOT EXISTS (SELECT 1 FROM employee_unavailability u
                           WHERE u.employee_id = e.id AND u.unavailable_date = ?)
           AND COALESCE(l.hours_committed, 0) + ? <= ?
         ORDER BY rating DESC, jobs DESC',
        [$city, $date, $svc['service_group'], $date, $hours, (float)setting('max_hours', '10')]
    );
    $langs = [];
    if ($rows) {
        $ids = array_column($rows, 'id');
        $in2 = implode(',', array_fill(0, count($ids), '?'));
        foreach (q("SELECT employee_id, language FROM employee_languages
                    WHERE employee_id IN ($in2)", $ids) as $l) {
            $langs[$l['employee_id']][] = $l['language'];
        }
    }
    json_out(['cleaners' => array_map(fn($r) => array_merge($r, [
        'languages' => $langs[$r['id']] ?? [],
    ]), $rows)]);
}

/* =====================================================================
   CUSTOMER
   ===================================================================== */

if ($path === '/customer/signup' && $method === 'POST') {
    [$first, $last, $email, $pass] = need($in, 'first_name', 'last_name', 'email', 'password');
    if (!valid_email($email)) {
        fail('Enter a valid email address', 422);
    }
    if (strlen($pass) < 8) {
        fail('Password must be at least 8 characters', 422);
    }
    $phone = isset($in['phone']) ? normalise_sa_mobile((string)$in['phone']) : null;
    if (isset($in['phone']) && $in['phone'] !== '' && !$phone) {
        fail('Enter a valid South African mobile number', 422);
    }
    if (q1('SELECT 1 FROM customers WHERE email = ? AND is_guest = 0', [$email])) {
        fail('That email address already has an account', 409);
    }
    // A guest who comes back and signs up keeps their order history
    // instead of starting again with a second row.
    $guest = q1('SELECT id FROM customers WHERE email = ? AND is_guest = 1', [$email]);
    if ($guest) {
        exec_sql('UPDATE customers SET first_name=?, last_name=?, phone=?, password_hash=?,
                  is_guest=0 WHERE id=?',
                 [$first, $last, $phone, password_hash($pass, PASSWORD_DEFAULT), $guest['id']]);
        $id = (int)$guest['id'];
    } else {
        exec_sql('INSERT INTO customers (first_name,last_name,email,phone,password_hash,is_guest)
                  VALUES (?,?,?,?,?,0)',
                 [$first, $last, $email, $phone, password_hash($pass, PASSWORD_DEFAULT)]);
        $id = (int)db()->lastInsertId();
    }
    sign_in_as('customer', $id);
    json_out(['id' => $id, 'first_name' => $first, 'last_name' => $last, 'email' => $email]);
}

if ($path === '/customer/login' && $method === 'POST') {
    [$email, $pass] = need($in, 'email', 'password');
    $u = q1('SELECT * FROM customers WHERE email = ? AND is_guest = 0', [$email]);
    // One message for a wrong email and a wrong password, so this cannot
    // be used to find out which addresses have accounts.
    if (!$u || !$u['password_hash'] || !password_verify($pass, $u['password_hash'])) {
        fail('Those details do not match an account', 401);
    }
    exec_sql('UPDATE customers SET last_login_at = NOW() WHERE id = ?', [$u['id']]);
    sign_in_as('customer', (int)$u['id']);
    json_out(['id' => (int)$u['id'], 'first_name' => $u['first_name'],
              'last_name' => $u['last_name'], 'email' => $u['email']]);
}

if ($path === '/logout' && $method === 'POST') {
    session_start_once();
    $_SESSION = [];
    session_destroy();
    json_out(['ok' => true]);
}

if ($path === '/customer/me') {
    $u = require_role('customer');
    $me = q1('SELECT id, first_name, last_name, email, phone, created_at
              FROM customers WHERE id = ?', [$u['id']]);
    $addresses = q('SELECT * FROM customer_addresses WHERE customer_id = ?
                    ORDER BY is_primary DESC, id', [$u['id']]);
    $orders = q(
        'SELECT o.*, s.name AS service_name, s.pricing_model,
                e.first_name AS cleaner_first, e.last_name AS cleaner_last,
                r.stars AS rating_stars, r.comment AS rating_comment
         FROM orders o
         JOIN services s      ON s.code = o.service_code
         LEFT JOIN employees e ON e.id = o.employee_id
         LEFT JOIN order_ratings r ON r.order_id = o.id
         WHERE o.customer_id = ?
         ORDER BY o.scheduled_date DESC, o.scheduled_time DESC', [$u['id']]);
    $extras = [];
    if ($orders) {
        $ids = array_column($orders, 'id');
        $in2 = implode(',', array_fill(0, count($ids), '?'));
        foreach (q("SELECT * FROM order_extras WHERE order_id IN ($in2)", $ids) as $e) {
            $extras[$e['order_id']][] = $e;
        }
    }
    $favs = array_column(q('SELECT employee_id FROM customer_favourites WHERE customer_id = ?',
                           [$u['id']]), 'employee_id');
    json_out([
        'customer'  => $me,
        'addresses' => $addresses,
        'orders'    => array_map(fn($o) => array_merge($o, ['extras' => $extras[$o['id']] ?? []]), $orders),
        'favourites' => array_map('intval', $favs),
    ]);
}

if ($path === '/customer/addresses' && $method === 'POST') {
    $u = require_role('customer');
    [$line, $suburb, $city, $prov] = need($in, 'street_line', 'suburb', 'city', 'province');
    exec_sql('INSERT INTO customer_addresses
              (customer_id,label,property_type,street_line,unit_number,suburb,city,province,
               latitude,longitude,access_notes,is_primary)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
             [$u['id'], $in['label'] ?? 'Home', $in['property_type'] ?? 'House',
              $line, $in['unit_number'] ?? null, $suburb, $city, $prov,
              $in['latitude'] ?? null, $in['longitude'] ?? null,
              $in['access_notes'] ?? null, !empty($in['is_primary']) ? 1 : 0]);
    json_out(['id' => (int)db()->lastInsertId()], 201);
}

/**
 * Book and pay.
 *
 * The total is recomputed here and the browser's idea of it is ignored.
 * The whole thing runs in one transaction so a half-written order with
 * no extras on it cannot exist, and the chosen worker is re-checked
 * INSIDE that transaction: between the customer seeing the shortlist and
 * pressing pay, somebody else may have taken the last hours of that
 * worker's day.
 */
if ($path === '/orders' && $method === 'POST') {
    $user = current_user();
    [$service, $date, $time] = need($in, 'service', 'date', 'time');

    $p = price_booking($in);
    if ($p['capExceeded']) {
        fail('Those extras do not fit in a ' . setting('max_hours', '10')
             . '-hour day. Take one off, or book them as a second job.', 422);
    }
    $svc = service_row($service);

    // who is paying
    if ($user && $user['role'] === 'customer') {
        $customerId = $user['id'];
    } else {
        [$first, $last, $email] = need($in, 'first_name', 'last_name', 'email');
        if (!valid_email($email)) {
            fail('Enter a valid email address', 422);
        }
        $existing = q1('SELECT id FROM customers WHERE email = ?', [$email]);
        if ($existing) {
            $customerId = (int)$existing['id'];
        } else {
            exec_sql('INSERT INTO customers (first_name,last_name,email,phone,is_guest)
                      VALUES (?,?,?,?,1)',
                     [$first, $last, $email,
                      isset($in['phone']) ? normalise_sa_mobile((string)$in['phone']) : null]);
            $customerId = (int)db()->lastInsertId();
        }
    }

    $addr = $in['address'] ?? [];
    foreach (['street_line', 'suburb', 'city', 'province'] as $k) {
        if (empty($addr[$k])) {
            fail("Missing address field: $k", 422);
        }
    }

    $employeeId = isset($in['employee_id']) ? (int)$in['employee_id'] : 0;
    if (!$employeeId) {
        fail('Choose a cleaner', 422);
    }

    $pdo = db();
    $pdo->beginTransaction();
    try {
        // Re-check the worker under a row lock, inside the transaction.
        $emp = q1('SELECT * FROM employees WHERE id = ? AND account_status = "approved" FOR UPDATE',
                  [$employeeId]);
        if (!$emp) {
            throw new RuntimeException('That cleaner is not available');
        }
        if ($emp['service_group'] !== $svc['service_group']) {
            throw new RuntimeException('That cleaner does not do this kind of work');
        }
        if (q1('SELECT 1 FROM employee_unavailability WHERE employee_id = ? AND unavailable_date = ?',
               [$employeeId, $date])) {
            throw new RuntimeException('That cleaner is not working that day');
        }
        $committed = (float)(q1('SELECT COALESCE(hours_committed,0) h FROM v_employee_day_load
                                 WHERE employee_id = ? AND scheduled_date = ?',
                                [$employeeId, $date])['h'] ?? 0);
        if ($committed + $p['hours'] > (float)setting('max_hours', '10') + 1e-9) {
            throw new RuntimeException('That cleaner no longer has room on that day');
        }

        $ref = order_reference();
        exec_sql(
            'INSERT INTO orders
             (reference,customer_id,employee_id,service_code,scheduled_date,scheduled_time,
              hours_booked,bedroom_band,laundry_wash,laundry_finish,window_rooms,vehicle_size,
              address_id,address_line,address_unit,address_suburb,address_city,address_province,
              address_latitude,address_longitude,access_notes,note_for_worker,
              flat_rate,hourly_rate,labour_total,extras_total,service_fee,total,status)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"paid")',
            [$ref, $customerId, $employeeId, $service, $date, $time,
             $p['serviceHours'],
             $svc['pricing_model'] === 'bedrooms' ? ($in['band'] ?? null) : null,
             $svc['pricing_model'] === 'laundry'  ? ($in['wash'] ?? null) : null,
             $svc['pricing_model'] === 'laundry'  ? ($in['finish'] ?? null) : null,
             $svc['pricing_model'] === 'rooms'    ? (int)($in['rooms'] ?? 4) : null,
             $svc['pricing_model'] === 'vehicle'  ? ($in['vehicle'] ?? null) : null,
             $in['address_id'] ?? null,
             $addr['street_line'], $addr['unit_number'] ?? null, $addr['suburb'],
             $addr['city'], $addr['province'],
             $addr['latitude'] ?? null, $addr['longitude'] ?? null,
             $addr['access_notes'] ?? null, $in['note'] ?? null,
             $p['flat'], $p['hourlyRate'], $p['labour'], $p['extras'], $p['fee'], $p['total']]
        );
        $orderId = (int)$pdo->lastInsertId();

        foreach ($p['extraRows'] as $e) {
            exec_sql('INSERT INTO order_extras (order_id,extra_code,name,minutes,price)
                      VALUES (?,?,?,?,?)',
                     [$orderId, $e['code'], $e['name'], $e['minutes'], $e['price']]);
        }
        exec_sql('INSERT INTO payments (order_id,gateway,gateway_ref,amount,status,settled_at)
                  VALUES (?,?,?,?,"approved",NOW())',
                 [$orderId, 'demo', 'DEMO-' . $ref, $p['total']]);
        exec_sql('INSERT INTO order_status_history (order_id,status,note) VALUES (?,"paid",?)',
                 [$orderId, 'Payment approved']);

        $pdo->commit();
    } catch (RuntimeException $e) {
        $pdo->rollBack();
        fail($e->getMessage(), 409);
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }

    // The three automatic messages from the brief.
    $cust = q1('SELECT * FROM customers WHERE id = ?', [$customerId]);
    $money = fn($n) => 'R' . number_format((float)$n, ((float)$n == floor((float)$n)) ? 0 : 2);
    record_message('email', 'customer', $customerId, $cust['email'],
        "Your booking is confirmed — $ref",
        "Hi {$cust['first_name']},\n\nYour {$p['serviceName']} is booked for $date at $time.\n"
        . "Reference: $ref\nTotal paid: {$money($p['total'])}\n"
        . "Your cleaner is {$emp['first_name']} {$emp['last_name']}.", $orderId);
    record_message('sms', 'employee', $employeeId, $emp['phone'], null,
        "New job: {$p['serviceName']}, $date at $time, {$addr['suburb']}. Ref $ref.", $orderId);
    /* The new-order alert goes to the address in settings.orders_email,
       which is the one line to change to start receiving these. Any admin
       accounts on top of that get their own copy. */
    $ordersTo = trim((string)setting('orders_email', ''));
    $alertBody = "A new {$p['serviceName']} order came in.\n\n"
        . "Reference: $ref\nWhen: $date at $time\n"
        . "Customer: {$cust['first_name']} {$cust['last_name']} ({$cust['email']})\n"
        . "Cleaner: {$emp['first_name']} {$emp['last_name']}\n"
        . "Where: {$addr['suburb']}, {$addr['city']}\n"
        . "Total: {$money($p['total'])}";
    if ($ordersTo !== '') {
        record_message('email', 'admin', null, $ordersTo, "New order $ref", $alertBody, $orderId);
    }
    foreach (q('SELECT id, email FROM admins WHERE is_active = 1') as $a) {
        if (strcasecmp((string)$a['email'], $ordersTo) === 0) {
            continue;              // do not send the same person two copies
        }
        record_message('email', 'admin', (int)$a['id'], $a['email'],
            "New order $ref", $alertBody, $orderId);
    }

    json_out(['reference' => $ref, 'id' => $orderId, 'price' => $p], 201);
}

if (count($seg) === 3 && $seg[0] === 'orders' && $seg[2] === 'cancel' && $method === 'POST') {
    $u = require_role('customer');
    $o = q1('SELECT * FROM orders WHERE reference = ? AND customer_id = ?', [$seg[1], $u['id']]);
    if (!$o) {
        fail('No such order', 404);
    }
    if (in_array($o['status'], ['completed', 'cancelled'], true)) {
        fail('That order can no longer be cancelled', 409);
    }
    exec_sql('UPDATE orders SET status="cancelled", cancelled_reason=? WHERE id=?',
             [$in['reason'] ?? null, $o['id']]);
    exec_sql('INSERT INTO order_status_history (order_id,status,note) VALUES (?,"cancelled",?)',
             [$o['id'], $in['reason'] ?? null]);
    json_out(['ok' => true]);
}

if (count($seg) === 3 && $seg[0] === 'orders' && $seg[2] === 'rate' && $method === 'POST') {
    $u = require_role('customer');
    $o = q1('SELECT * FROM orders WHERE reference = ? AND customer_id = ?', [$seg[1], $u['id']]);
    if (!$o) {
        fail('No such order', 404);
    }
    if ($o['status'] !== 'completed') {
        fail('You can only rate a job once it is done', 409);
    }
    $stars = (int)($in['stars'] ?? 0);
    if ($stars < 1 || $stars > 5) {
        fail('Choose between one and five stars', 422);
    }
    // One rating per order: a second submission edits the first rather
    // than inflating the worker's average.
    exec_sql('INSERT INTO order_ratings (order_id,stars,comment) VALUES (?,?,?)
              ON DUPLICATE KEY UPDATE stars=VALUES(stars), comment=VALUES(comment)',
             [$o['id'], $stars, $in['comment'] ?? null]);
    json_out(['ok' => true]);
}

/* =====================================================================
   EMPLOYEE
   ===================================================================== */

if ($path === '/employee/apply' && $method === 'POST') {
    [$first, $last, $email, $phone, $dob, $idNum, $group] =
        need($in, 'first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'id_number', 'service_group');
    if (!valid_email($email)) {
        fail('Enter a valid email address', 422);
    }
    $mobile = normalise_sa_mobile((string)$phone);
    if (!$mobile) {
        fail('Enter a valid South African mobile number', 422);
    }
    // 18+ measured against today, not against a year number.
    $age = (new DateTime($dob))->diff(new DateTime('today'))->y;
    if ($age < 18) {
        fail('You must be at least 18 to apply', 422);
    }
    if (($in['id_type'] ?? 'sa_id') === 'sa_id') {
        $err = check_sa_id((string)$idNum, (string)$dob);
        if ($err) {
            fail($err, 422);
        }
    }
    if (q1('SELECT 1 FROM employees WHERE email = ?', [$email])) {
        fail('There is already an application with that email address', 409);
    }
    if (q1('SELECT 1 FROM employees WHERE id_number = ?', [preg_replace('/\D+/', '', (string)$idNum)])) {
        fail('There is already an application with that ID number', 409);
    }
    exec_sql('INSERT INTO employees (first_name,last_name,email,phone,date_of_birth,id_type,
              id_number,service_group,years_experience,has_own_transport,account_status)
              VALUES (?,?,?,?,?,?,?,?,?,?,"pending")',
             [$first, $last, $email, $mobile, $dob, $in['id_type'] ?? 'sa_id',
              preg_replace('/\D+/', '', (string)$idNum), $group,
              (int)($in['years_experience'] ?? 0), !empty($in['has_own_transport']) ? 1 : 0]);
    $id = (int)db()->lastInsertId();
    foreach ((array)($in['languages'] ?? []) as $l) {
        exec_sql('INSERT IGNORE INTO employee_languages (employee_id,language) VALUES (?,?)', [$id, $l]);
    }
    foreach ((array)($in['areas'] ?? []) as $a) {
        if (!empty($a['city'])) {
            exec_sql('INSERT IGNORE INTO employee_areas (employee_id,province,city) VALUES (?,?,?)',
                     [$id, $a['province'] ?? '', $a['city']]);
        }
    }
    /* The applicant has no account, and will not have one unless an admin
       approves them, so the uploads that follow are authorised by this
       one-time token rather than by a session. */
    json_out([
        'id'             => $id,
        'account_status' => 'pending',
        'upload_token'   => issue_upload_token($id),
        'required_documents' => $in['id_type'] === 'passport'
            ? ['id', 'photo', 'criminal_check', 'work_permit']
            : ['id', 'photo', 'criminal_check'],
    ], 201);
}

/**
 * Upload one document or photo.
 *
 * multipart/form-data with: file, doc_type, and either employee_id +
 * upload_token (an applicant) or nothing (an approved worker already
 * signed in, changing their profile photo).
 */
if ($path === '/employee/documents' && $method === 'POST') {
    $docType = $_POST['doc_type'] ?? '';
    $user    = current_user();

    if ($user && $user['role'] === 'employee') {
        $employeeId = $user['id'];
    } else {
        $employeeId = (int)($_POST['employee_id'] ?? 0);
        $token      = (string)($_POST['upload_token'] ?? '');
        if (!$employeeId || !check_upload_token($employeeId, $token)) {
            // One message whether the id is wrong, the token is wrong or
            // the token has expired: a different answer for each would let
            // someone probe which application ids exist.
            fail('That upload link is not valid any more. Apply again, or '
                 . 'contact the office.', 403);
        }
    }

    $row = accept_upload($_FILES['file'] ?? [], $employeeId, $docType);
    $id  = save_document($row);

    json_out([
        'id'        => $id,
        'doc_type'  => $row['doc_type'],
        'name'      => $row['original_name'],
        'size'      => $row['size_bytes'],
        'mime'      => $row['mime_type'],
    ], 201);
}

if ($path === '/employee/login' && $method === 'POST') {
    [$email, $pass] = need($in, 'email', 'password');
    $e = q1('SELECT * FROM employees WHERE email = ?', [$email]);
    if (!$e) {
        fail('Those details do not match an application', 401);
    }
    // The gate. An application is not an account: pending and declined
    // are refused here, in the API, so turning the button back on in the
    // browser achieves nothing.
    if ($e['account_status'] !== 'approved') {
        json_out([
            'error'          => 'Your account is not open yet',
            'account_status' => $e['account_status'],
            'decline_reason' => $e['decline_reason'],
            'first_name'     => $e['first_name'],
        ], 403);
    }
    if (!$e['password_hash'] || !password_verify($pass, $e['password_hash'])) {
        fail('Those details do not match an application', 401);
    }
    exec_sql('UPDATE employees SET last_login_at = NOW() WHERE id = ?', [$e['id']]);
    sign_in_as('employee', (int)$e['id']);
    json_out(['id' => (int)$e['id'], 'first_name' => $e['first_name'],
              'last_name' => $e['last_name'], 'service_group' => $e['service_group']]);
}

if ($path === '/employee/me') {
    $u = require_role('employee');
    $me = q1('SELECT id, first_name, last_name, email, phone, service_group, years_experience,
                     has_own_transport, profile_photo_path, account_status, date_of_birth,
                     id_number
              FROM employees WHERE id = ?', [$u['id']]);
    $me['id_number'] = mask_id($me['id_number']);     // masked wherever it is echoed back
    $jobs = q('SELECT o.*, s.name AS service_name, c.first_name AS customer_first,
                      c.last_name AS customer_last, c.phone AS customer_phone
               FROM orders o
               JOIN services s  ON s.code = o.service_code
               JOIN customers c ON c.id = o.customer_id
               WHERE o.employee_id = ? AND o.status <> "cancelled"
               ORDER BY o.scheduled_date DESC, o.scheduled_time DESC', [$u['id']]);
    json_out([
        'employee'      => $me,
        'rating'        => q1('SELECT * FROM v_employee_ratings WHERE employee_id = ?', [$u['id']]),
        'jobs'          => $jobs,
        'unavailable'   => array_column(
            q('SELECT unavailable_date FROM employee_unavailability WHERE employee_id = ?
               ORDER BY unavailable_date', [$u['id']]), 'unavailable_date'),
        'languages'     => array_column(
            q('SELECT language FROM employee_languages WHERE employee_id = ?', [$u['id']]), 'language'),
        'areas'         => q('SELECT province, city FROM employee_areas WHERE employee_id = ?', [$u['id']]),
        'documents'     => q('SELECT id, doc_type, original_name, mime_type, size_bytes,
                                     width_px, height_px, uploaded_at
                              FROM employee_documents WHERE employee_id = ?
                              ORDER BY doc_type', [$u['id']]),
    ]);
}

if ($path === '/employee/unavailability' && $method === 'POST') {
    $u = require_role('employee');
    [$date] = need($in, 'date');
    if (!empty($in['remove'])) {
        exec_sql('DELETE FROM employee_unavailability WHERE employee_id = ? AND unavailable_date = ?',
                 [$u['id'], $date]);
        json_out(['ok' => true, 'blocked' => false]);
    }
    // A worker cannot block a day they have already been booked for; the
    // customer has paid and the job exists.
    if (q1('SELECT 1 FROM orders WHERE employee_id = ? AND scheduled_date = ?
            AND status IN ("paid","upcoming","inprogress")', [$u['id'], $date])) {
        fail('You already have a job booked that day. Contact the office to move it.', 409);
    }
    exec_sql('INSERT IGNORE INTO employee_unavailability (employee_id,unavailable_date,reason)
              VALUES (?,?,?)', [$u['id'], $date, $in['reason'] ?? null]);
    json_out(['ok' => true, 'blocked' => true]);
}

/* =====================================================================
   ADMIN
   ===================================================================== */

if ($path === '/admin/login' && $method === 'POST') {
    [$email, $pass] = need($in, 'email', 'password');
    $a = q1('SELECT * FROM admins WHERE email = ? AND is_active = 1', [$email]);
    if (!$a || !password_verify($pass, $a['password_hash'])) {
        fail('Those details do not match an account', 401);
    }
    exec_sql('UPDATE admins SET last_login_at = NOW() WHERE id = ?', [$a['id']]);
    sign_in_as('admin', (int)$a['id']);
    json_out(['id' => (int)$a['id'], 'first_name' => $a['first_name'], 'role' => $a['role']]);
}

if ($path === '/admin/overview') {
    require_role('admin');
    json_out([
        'orders_total'     => (int)q1('SELECT COUNT(*) n FROM orders')['n'],
        'orders_upcoming'  => (int)q1('SELECT COUNT(*) n FROM orders
                                       WHERE status IN ("paid","upcoming")')['n'],
        'revenue'          => (float)q1('SELECT COALESCE(SUM(total),0) n FROM orders
                                         WHERE status <> "cancelled"')['n'],
        'employees_active' => (int)q1('SELECT COUNT(*) n FROM employees
                                       WHERE account_status = "approved"')['n'],
        'applications_new' => (int)q1('SELECT COUNT(*) n FROM employees
                                       WHERE account_status = "pending"')['n'],
        'orders' => array_map(function ($o) {
                        // the extras belong on the row: the admin order
                        // screen prints what was actually booked
                        $o['extras'] = q('SELECT extra_code, name, minutes, price
                                          FROM order_extras WHERE order_id = ?', [$o['id']]);
                        return $o;
                    }, q('SELECT o.*, s.name AS service_name,
                                 c.first_name AS customer_first, c.last_name AS customer_last,
                                 e.first_name AS cleaner_first, e.last_name AS cleaner_last,
                                 r.stars AS rating_stars, r.comment AS rating_comment
                          FROM orders o
                          JOIN services s   ON s.code = o.service_code
                          JOIN customers c  ON c.id = o.customer_id
                          LEFT JOIN employees e ON e.id = o.employee_id
                          LEFT JOIN order_ratings r ON r.order_id = o.id
                          ORDER BY o.scheduled_date DESC LIMIT 50')),
        'employees' => q('SELECT e.id, e.first_name, e.last_name, e.service_group, e.account_status,
                                 e.years_experience, COALESCE(r.rating_avg,0) rating,
                                 COALESCE(r.jobs_completed,0) jobs,
                                 GROUP_CONCAT(DISTINCT a.city) cities
                          FROM employees e
                          LEFT JOIN v_employee_ratings r ON r.employee_id = e.id
                          LEFT JOIN employee_areas a ON a.employee_id = e.id
                          GROUP BY e.id ORDER BY e.service_group, e.last_name'),
    ]);
}

if ($path === '/admin/applications') {
    require_role('admin');
    $rows = q('SELECT id, first_name, last_name, email, phone, date_of_birth, id_type,
                      id_number, service_group, years_experience, has_own_transport,
                      account_status, decline_reason, applied_at
               FROM employees WHERE account_status = "pending" ORDER BY applied_at');
    $docs = [];
    foreach (q('SELECT * FROM employee_documents') as $d) {
        $docs[$d['employee_id']][] = $d;
    }
    // array_merge, not `+`. The union operator keeps the LEFT side's value
    // for a duplicate key, so `$r + ['id_number' => mask_id(...)]` left the
    // ID number unmasked and read as though it masked it.
    json_out(['applications' => array_map(fn($r) => array_merge($r, [
        'id_number' => mask_id($r['id_number']),
        'documents' => $docs[$r['id']] ?? [],
    ]), $rows)]);
}

if (count($seg) === 4 && $seg[0] === 'admin' && $seg[1] === 'applications'
    && $seg[3] === 'decide' && $method === 'POST') {
    $admin = require_role('admin');
    $id = (int)$seg[2];
    $decision = $in['decision'] ?? '';
    if (!in_array($decision, ['approve', 'decline'], true)) {
        fail('decision must be approve or decline', 422);
    }
    $e = q1('SELECT * FROM employees WHERE id = ?', [$id]);
    if (!$e) {
        fail('No such application', 404);
    }
    if ($e['account_status'] !== 'pending') {
        fail('That application has already been decided', 409);
    }

    if ($decision === 'approve') {
        // A one-time password they are told to change. The alternative is
        // mailing a reset link, which needs the mail server we do not have.
        $temp = bin2hex(random_bytes(4));
        exec_sql('UPDATE employees SET account_status="approved", password_hash=?,
                  decided_by_admin_id=?, decided_at=NOW() WHERE id=?',
                 [password_hash($temp, PASSWORD_DEFAULT), $admin['id'], $id]);
        record_message('email', 'employee', $id, $e['email'], 'Welcome to Sparrow',
            "Congratulations {$e['first_name']}, your application has been approved.\n"
            . "You can sign in at the cleaner portal.\nTemporary password: $temp\n"
            . "Please change it the first time you sign in.");
        json_out(['ok' => true, 'account_status' => 'approved', 'temp_password' => $temp]);
    }

    $reason = trim((string)($in['reason'] ?? ''));
    if ($reason === '') {
        // The database refuses this too, but failing here gives the admin
        // a sentence instead of a constraint name.
        fail('Give a reason. It is what the applicant is told.', 422);
    }
    exec_sql('UPDATE employees SET account_status="declined", decline_reason=?,
              decided_by_admin_id=?, decided_at=NOW() WHERE id=?',
             [$reason, $admin['id'], $id]);
    record_message('email', 'employee', $id, $e['email'], 'About your application',
        "Hello {$e['first_name']},\n\nWe are not able to take your application further.\n\n$reason");
    json_out(['ok' => true, 'account_status' => 'declined']);
}

if ($path === '/admin/customers') {
    require_role('admin');
    json_out(['customers' => q(
        'SELECT c.id, c.first_name, c.last_name, c.email, c.phone, c.is_guest, c.created_at,
                COUNT(o.id) AS order_count, COALESCE(SUM(o.total),0) AS spent
         FROM customers c
         LEFT JOIN orders o ON o.customer_id = c.id AND o.status <> "cancelled"
         GROUP BY c.id ORDER BY c.created_at DESC')]);
}

if (count($seg) === 3 && $seg[0] === 'admin' && $seg[1] === 'documents' && $method === 'GET') {
    // Only an admin, and the file is read off disk rather than linked to,
    // so there is no URL anyone could share or guess.
    require_role('admin');
    stream_document((int)$seg[2]);
}

if ($path === '/admin/messages') {
    require_role('admin');
    json_out(['messages' => q('SELECT * FROM messages_sent ORDER BY created_at DESC LIMIT 100')]);
}

fail('No such endpoint: ' . $path, 404);
