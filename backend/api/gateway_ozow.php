<?php
/**
 * OZOW — instant EFT. NOT LIVE YET. Nothing in this file is called.
 *
 * You said you will be using Ozow, so this is the shape the integration
 * takes, with the live calls commented out, ready to switch on once you
 * have your merchant credentials. Right now /orders marks the order paid
 * directly, which is what lets the demo be clicked through.
 *
 * ---------------------------------------------------------------------
 * WHAT I NEED FROM YOU TO FINISH IT
 * ---------------------------------------------------------------------
 *   SiteCode     from Ozow Merchant Admin, under the site you create
 *   PrivateKey   same screen. This one is a secret: it belongs in
 *                config.local.php, never in this file and never in git
 *   ApiKey       only needed if you want the server-to-server API as well
 *                as the redirect flow
 *
 * Then set IsTest to false and put the live URL in.
 *
 * ---------------------------------------------------------------------
 * ONE THING TO CHECK BEFORE YOU TRUST THE HASH BELOW
 * ---------------------------------------------------------------------
 * Ozow's own documentation and the community examples disagree about one
 * detail: whether the private key is appended BEFORE lowercasing the
 * whole string, or after the rest has already been lowercased. If your
 * key contains uppercase letters those two produce different hashes, and
 * you get "hash check failed" with nothing else to go on.
 *
 * I have written it the first way (concatenate everything including the
 * key, then lowercase, then SHA512), which is what Ozow's integration
 * page describes. Confirm it against the merchant documentation on your
 * own account before going live, and if it rejects the first request,
 * try HASH_KEY_OUTSIDE below. It is a one-line change and it is the first
 * thing to suspect.
 * ---------------------------------------------------------------------
 */
declare(strict_types=1);

const OZOW_POST_URL      = 'https://pay.ozow.com/';
const OZOW_POST_URL_TEST = 'https://staging.ozow.com/';

/**
 * The field order matters. Ozow concatenates the values in exactly this
 * order to check the hash, so changing the order here breaks it even
 * though every value is right.
 */
function ozow_request_fields(array $order, array $cfg): array
{
    return [
        'SiteCode'             => $cfg['ozow_site_code'],
        'CountryCode'          => 'ZA',
        'CurrencyCode'         => 'ZAR',
        'Amount'               => number_format((float)$order['total'], 2, '.', ''),
        'TransactionReference' => $order['reference'],   // ours
        'BankReference'        => substr($order['reference'], 0, 20), // shown on their statement
        'Optional1'            => '',
        'Optional2'            => '',
        'Optional3'            => '',
        'Optional4'            => '',
        'Optional5'            => '',
        'Customer'             => $order['customer_name'] ?? '',
        'CancelUrl'            => $cfg['site_url'] . '/pay/cancelled',
        'ErrorUrl'             => $cfg['site_url'] . '/pay/error',
        'SuccessUrl'           => $cfg['site_url'] . '/pay/done',
        'NotifyUrl'            => $cfg['site_url'] . '/api/payments/ozow/notify',
        'IsTest'               => $cfg['ozow_is_test'] ? 'true' : 'false',
    ];
}

/** SHA512 of the concatenated values with the private key on the end. */
function ozow_hash(array $fields, string $privateKey, bool $keyOutsideLowercase = false): string
{
    $joined = implode('', array_values($fields));
    // See the note at the top of this file. Both forms are here because
    // one of them is wrong and only your merchant docs say which.
    $s = $keyOutsideLowercase
        ? strtolower($joined) . $privateKey          // HASH_KEY_OUTSIDE
        : strtolower($joined . $privateKey);         // what is used below
    return hash('sha512', $s);
}

/**
 * Build the form the customer's browser posts to Ozow.
 *
 * Ozow's redirect flow is a POST, not a link, so the page renders a form
 * and submits it. The customer picks their bank on Ozow's side and comes
 * back to SuccessUrl.
 */
function ozow_redirect_form(array $order): string
{
    $c = cfg();
    $fields = ozow_request_fields($order, $c);
    $fields['HashCheck'] = ozow_hash($fields, $c['ozow_private_key']);

    $url = $c['ozow_is_test'] ? OZOW_POST_URL_TEST : OZOW_POST_URL;
    $html = '<form id="ozow" method="post" action="' . htmlspecialchars($url) . '">';
    foreach ($fields as $k => $v) {
        $html .= '<input type="hidden" name="' . htmlspecialchars($k)
               . '" value="' . htmlspecialchars((string)$v) . '">';
    }
    return $html . '</form><script>document.getElementById("ozow").submit();</script>';
}

/**
 * Ozow posts the result here, server to server.
 *
 * THE RULE THAT MATTERS: the order is marked paid by THIS callback, never
 * by the customer arriving back at SuccessUrl. A customer can open
 * SuccessUrl directly without paying a cent. Only the server-to-server
 * notification, with a hash that matches, is evidence of payment.
 *
 * And the amount is checked against the order. A notification that says
 * R1.00 against a R470 order is not a paid order.
 */
function ozow_handle_notification(array $post): void
{
    $c = cfg();

    // The response fields, in the order Ozow hashes them.
    $check = [
        'SiteCode'             => $post['SiteCode']             ?? '',
        'TransactionId'        => $post['TransactionId']        ?? '',
        'TransactionReference' => $post['TransactionReference'] ?? '',
        'Amount'               => $post['Amount']               ?? '',
        'Status'               => $post['Status']               ?? '',
        'Optional1'            => $post['Optional1']            ?? '',
        'Optional2'            => $post['Optional2']            ?? '',
        'Optional3'            => $post['Optional3']            ?? '',
        'Optional4'            => $post['Optional4']            ?? '',
        'Optional5'            => $post['Optional5']            ?? '',
        'CurrencyCode'         => $post['CurrencyCode']         ?? '',
        'IsTest'               => $post['IsTest']               ?? '',
        'StatusMessage'        => $post['StatusMessage']        ?? '',
    ];
    $expected = ozow_hash($check, $c['ozow_private_key']);

    // hash_equals, not ==, so the comparison cannot be timed.
    if (!hash_equals($expected, strtolower((string)($post['Hash'] ?? '')))) {
        error_log('[ozow] hash mismatch for ' . ($post['TransactionReference'] ?? '?'));
        http_response_code(400);
        return;
    }

    /*
    $ref   = (string)$post['TransactionReference'];
    $order = q1('SELECT * FROM orders WHERE reference = ?', [$ref]);
    if (!$order) {
        error_log('[ozow] notification for an unknown order: ' . $ref);
        http_response_code(404);
        return;
    }

    // The amount has to match what we charged.
    if (abs((float)$post['Amount'] - (float)$order['total']) > 0.001) {
        error_log('[ozow] amount mismatch on ' . $ref
                  . ': they say ' . $post['Amount'] . ', we charged ' . $order['total']);
        http_response_code(409);
        return;
    }

    $status = strtolower((string)$post['Status']);   // Complete / Cancelled / Error / Abandoned

    // The unique key on (gateway, gateway_ref) is what stops a resent
    // notification being counted as a second payment.
    exec_sql('INSERT INTO payments (order_id, gateway, gateway_ref, amount, status, settled_at)
              VALUES (?, "ozow", ?, ?, ?, NOW())
              ON DUPLICATE KEY UPDATE status = VALUES(status), settled_at = VALUES(settled_at)',
             [$order['id'], (string)$post['TransactionId'], (float)$post['Amount'],
              $status === 'complete' ? 'approved' : 'failed']);

    if ($status === 'complete' && $order['status'] === 'pending_payment') {
        exec_sql('UPDATE orders SET status = "paid" WHERE id = ?', [$order['id']]);
        exec_sql('INSERT INTO order_status_history (order_id, status, note)
                  VALUES (?, "paid", ?)', [$order['id'], 'Ozow ' . $post['TransactionId']]);
        // the confirmation emails that /orders sends today move here
    }
    */

    http_response_code(200);
}
