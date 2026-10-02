<?php
/**
 * Connection, JSON helpers, sessions, and the price engine.
 *
 * THE PRICE ENGINE IS THE IMPORTANT PART OF THIS FILE.
 *
 * The browser sends what the customer chose: a service, a band or a
 * vehicle, which extras are ticked, how many hours. It does NOT send a
 * total, and if it did, the total would be ignored. Everything is priced
 * again here from the `settings`, `services` and `service_extras` tables,
 * because anything the browser sends can be edited by whoever is using
 * the browser. A booking screen that posts "total: 1.00" must still be
 * charged R470.
 *
 * priceBooking() below mirrors priceBooking() in assets/app.js exactly.
 * Two implementations of one rule is a drift risk, so tests/test_parity.py
 * runs the same bookings through both and fails on any difference.
 */
declare(strict_types=1);

function cfg(): array
{
    static $c = null;
    if ($c === null) {
        $c = require __DIR__ . '/config.php';
    }
    return $c;
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }
    $c = cfg();
    $dsn = $c['db_socket']
        ? sprintf('mysql:unix_socket=%s;dbname=%s;charset=utf8mb4', $c['db_socket'], $c['db_name'])
        : sprintf('mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4', $c['db_host'], (int)$c['db_port'], $c['db_name']);
    $pdo = new PDO($dsn, $c['db_user'], $c['db_pass'], [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        // Real prepared statements, so a quote in a customer note can
        // never become part of the SQL.
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
    return $pdo;
}

function q(string $sql, array $params = []): array
{
    $st = db()->prepare($sql);
    $st->execute($params);
    return $st->fetchAll();
}

function q1(string $sql, array $params = []): ?array
{
    $rows = q($sql, $params);
    return $rows[0] ?? null;
}

function exec_sql(string $sql, array $params = []): int
{
    $st = db()->prepare($sql);
    $st->execute($params);
    return $st->rowCount();
}

/* ---------------------------------------------------------------- json */

function json_out($data, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('X-Sparrow-Api: 1');       // lets the front end tell a real API
                                      // from a web server quietly serving
                                      // an index page with a 200
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function fail(string $message, int $status = 400, array $extra = []): never
{
    json_out(['error' => $message] + $extra, $status);
}

function body(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === '' || $raw === false) {
        return [];
    }
    $d = json_decode($raw, true);
    return is_array($d) ? $d : [];
}

function need(array $src, string ...$keys): array
{
    $out = [];
    foreach ($keys as $k) {
        if (!isset($src[$k]) || $src[$k] === '') {
            fail("Missing field: $k", 422);
        }
        $out[] = $src[$k];
    }
    return $out;
}

/* ------------------------------------------------------------ sessions */

function session_start_once(): void
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_set_cookie_params([
            'httponly' => true,                 // JavaScript cannot read it
            'samesite' => 'Lax',
            'secure'   => !empty($_SERVER['HTTPS']),
        ]);
        session_start();
    }
}

function sign_in_as(string $role, int $id): void
{
    session_start_once();
    // A new session id on privilege change, so a session fixed before
    // login is not the session that ends up logged in.
    session_regenerate_id(true);
    $_SESSION['role'] = $role;
    $_SESSION['uid']  = $id;
}

function current_user(): ?array
{
    session_start_once();
    if (empty($_SESSION['role']) || empty($_SESSION['uid'])) {
        return null;
    }
    return ['role' => $_SESSION['role'], 'id' => (int)$_SESSION['uid']];
}

function require_role(string ...$roles): array
{
    $u = current_user();
    if (!$u || !in_array($u['role'], $roles, true)) {
        fail('Not signed in', 401);
    }
    return $u;
}

/* ------------------------------------------------------- price engine */

function settings_all(): array
{
    static $s = null;
    if ($s === null) {
        $s = [];
        foreach (q('SELECT setting_key, setting_value FROM settings') as $r) {
            $s[$r['setting_key']] = $r['setting_value'];
        }
    }
    return $s;
}

function setting(string $key, $default = null)
{
    $s = settings_all();
    return $s[$key] ?? $default;
}

function service_row(string $code): ?array
{
    return q1('SELECT * FROM services WHERE code = ? AND is_active = 1', [$code]);
}

/** Minutes a window job of N rooms takes: 4 rooms is 4 hours, +30 min each. */
function window_hours(int $rooms): float
{
    $rooms = max(4, min(16, $rooms));
    return 4.0 + ($rooms - 4) * 0.5;
}

/** The estimate before the customer touches the stepper. */
function base_hours(array $svc, array $b): float
{
    switch ($svc['pricing_model']) {
        case 'bedrooms':
            $bands = ['b12' => 4.0, 'b34' => 6.0, 'b5' => 8.0];
            $h = $bands[$b['band'] ?? ''] ?? null;
            if ($h === null) {
                fail('Choose a unit size', 422);
            }
            return $h + (float)$svc['add_hours'];
        case 'laundry':
            $wash   = ['hand' => 5.0, 'machine' => 4.0];
            $finish = ['dryfold' => 2.0, 'dryiron' => 3.5];
            if (!isset($wash[$b['wash'] ?? ''], $finish[$b['finish'] ?? ''])) {
                fail('Choose a wash and a finish', 422);
            }
            return $wash[$b['wash']] + $finish[$b['finish']];
        case 'rooms':
            return window_hours((int)($b['rooms'] ?? 4));
        case 'vehicle':
            $sizes = ['small','medium','big','suv','bakkie','truck'];
            if (!in_array($b['vehicle'] ?? '', $sizes, true)) {
                fail('Choose a vehicle', 422);
            }
            // His figure, 1 Oct: every size is 1 h 30 m.
            return (float)setting('car_wash_hours', '1.5');
        default:
            return (float)($svc['est_hours'] ?? 0);
    }
}

/** The extras this service offers, filtered to the ones actually ticked. */
function chosen_extras(array $svc, array $b): array
{
    if (empty($svc['extra_set']) || empty($b['extras']) || !is_array($b['extras'])) {
        return [];
    }
    $ids  = array_values(array_unique(array_map('strval', $b['extras'])));
    $in   = implode(',', array_fill(0, count($ids), '?'));
    // extra_set is matched here, which is what stops an id left over from
    // a previous service quietly billing on this one.
    return q("SELECT * FROM service_extras
              WHERE code IN ($in) AND extra_set = ? AND is_active = 1",
             array_merge($ids, [$svc['extra_set']]));
}

/**
 * The whole price, recomputed from the database.
 * Returns the same shape the front end's priceBooking() returns.
 */
function price_booking(array $b): array
{
    $svc = service_row((string)($b['service'] ?? ''));
    if (!$svc) {
        fail('Unknown service', 422);
    }

    $rate     = (float)setting('hourly_rate', '35');
    $fee      = (float)setting('service_fee', '35');
    $maxHours = (float)setting('max_hours', '10');
    $stepMins = (float)setting('step_minutes', '30');
    $reduce   = (float)setting('reduce_minutes', '30');

    $flat = $svc['flat_rate_override'] !== null
        ? (float)$svc['flat_rate_override']
        : (float)setting('flat_rate', '155');

    $est     = base_hours($svc, $b);
    $extras  = chosen_extras($svc, $b);
    $exMins  = array_sum(array_column($extras, 'minutes'));
    $exMoney = array_sum(array_map('floatval', array_column($extras, 'price')));

    // The customer may take at most 30 minutes off the estimate, and add
    // as much as fits under the 10-hour cap once the extras' time is
    // accounted for.
    $min = max(0.5, $est - $reduce / 60);
    $max = max($min, $maxHours - $exMins / 60);

    $hours = isset($b['hours']) && $b['hours'] !== null ? (float)$b['hours'] : $est;
    $hours = min(max($hours, $min), $max);

    // Hours only move in 30-minute steps.
    $step  = $stepMins / 60;
    $hours = round($hours / $step) * $step;
    $hours = min(max($hours, $min), $max);

    // The estimate itself can be impossible: a deep clean of a 3-4 bedroom
    // is 8 hours, and an oven plus a wash-dry-iron is another 2.5, which is
    // 10.5 in a 10-hour day. The booking screen will not let a customer tick
    // their way into that, but a request that arrives here anyway is refused
    // at /orders rather than quietly booked 30 minutes short.
    $capExceeded = $est > $max + 1e-9;

    $labour = $hours * $rate;
    $total  = $flat + $labour + $exMoney + $fee;

    return [
        'service'      => $svc['code'],
        'serviceName'  => $svc['name'],
        'model'        => $svc['pricing_model'],
        'flat'         => round($flat, 2),
        'hourlyRate'   => round($rate, 2),
        'labour'       => round($labour, 2),
        'extras'       => round($exMoney, 2),
        'fee'          => round($fee, 2),
        'total'        => round($total, 2),
        'serviceHours' => $hours,
        'hours'        => $hours + $exMins / 60,
        'estHours'     => $est,
        'minHours'     => $min,
        'maxHours'     => $max,
        'capExceeded'  => $capExceeded,
        'extraRows'    => array_map(fn($e) => [
            'code'    => $e['code'],
            'name'    => $e['name'],
            'minutes' => (int)$e['minutes'],
            'price'   => round((float)$e['price'], 2),
        ], $extras),
    ];
}

/* ----------------------------------------------------------- utilities */

function order_reference(): string
{
    // Short, human-readable, and unique because the column says so. The
    // retry loop exists because two customers can check out in the same
    // millisecond.
    for ($i = 0; $i < 20; $i++) {
        $ref = 'SPW-' . random_int(100000, 999999);
        if (!q1('SELECT 1 FROM orders WHERE reference = ?', [$ref])) {
            return $ref;
        }
    }
    fail('Could not allocate an order reference', 500);
}

/** Mask an ID number everywhere it is echoed back. */
function mask_id(?string $id): ?string
{
    if (!$id) {
        return $id;
    }
    return substr($id, 0, 6) . str_repeat('*', max(0, strlen($id) - 10)) . substr($id, -4);
}

function valid_email(string $e): bool
{
    return (bool)filter_var($e, FILTER_VALIDATE_EMAIL);
}

/** South African mobile number, in any of the formats people type. */
function normalise_sa_mobile(string $p): ?string
{
    $d = preg_replace('/\D+/', '', $p);
    if (str_starts_with($d, '27') && strlen($d) === 11) {
        $d = '0' . substr($d, 2);
    }
    if (strlen($d) === 9 && $d[0] !== '0') {
        $d = '0' . $d;
    }
    if (strlen($d) !== 10 || $d[0] !== '0' || !in_array($d[1], ['6','7','8'], true)) {
        return null;
    }
    return '+27 ' . substr($d, 1, 2) . ' ' . substr($d, 3, 3) . ' ' . substr($d, 6);
}

/** SA ID number: 13 digits, Luhn check digit, and the birth date inside it. */
function check_sa_id(string $id, ?string $dob = null): ?string
{
    $id = preg_replace('/\D+/', '', $id);
    if (strlen($id) !== 13) {
        return 'An SA ID number is 13 digits';
    }
    $sum = 0;
    $alt = false;
    for ($i = 12; $i >= 0; $i--) {
        $n = (int)$id[$i];
        if ($alt) {
            $n *= 2;
            if ($n > 9) {
                $n -= 9;
            }
        }
        $sum += $n;
        $alt = !$alt;
    }
    if ($sum % 10 !== 0) {
        return 'That ID number does not check out';
    }
    if ($dob) {
        // The first six digits are the birth date. A real ID with the
        // wrong date of birth typed next to it is caught here, before an
        // admin ever sees the application.
        $yy = substr($id, 0, 2);
        $inside = substr($dob, 2, 2) . substr($dob, 5, 2) . substr($dob, 8, 2);
        if ($inside !== substr($id, 0, 6)) {
            return 'The date of birth does not match the one inside the ID number';
        }
    }
    return null;
}

function record_message(string $channel, string $recipientType, ?int $recipientId,
                        string $to, ?string $subject, string $bodyText, ?int $orderId = null): void
{
    // There is no mail server yet, so messages are recorded rather than
    // sent, and the admin dashboard reads them back. Swapping in a real
    // mailer means changing this one function.
    exec_sql(
        'INSERT INTO messages_sent (channel, recipient_type, recipient_id, to_address,
                                    subject, body, order_id, status, sent_at)
         VALUES (?,?,?,?,?,?,?,"sent",NOW())',
        [$channel, $recipientType, $recipientId, $to, $subject, $bodyText, $orderId]
    );
}
