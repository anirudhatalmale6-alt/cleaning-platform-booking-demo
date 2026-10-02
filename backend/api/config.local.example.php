<?php
/**
 * Copy this to config.local.php and fill in your own details.
 * config.local.php is gitignored on purpose: a database password and a
 * payment private key do not belong in a repository, not even a private one.
 */
return [
    // --- database ---
    'db_host' => '127.0.0.1',
    'db_port' => 3306,
    'db_name' => 'sparrow',
    'db_user' => 'sparrow_app',
    'db_pass' => 'change-me',

    // --- uploads ---
    // PUT THIS OUTSIDE YOUR public_html / www FOLDER.
    // Worker ID copies and police clearances are stored here, and nothing
    // should be able to reach them except the admin download endpoint.
    'storage_path' => '/home/youraccount/sparrow-storage',

    // --- your site ---
    'site_url' => 'https://www.yourcompany.co.za',

    // --- Ozow (not live yet, see api/gateway_ozow.php) ---
    'ozow_site_code'   => '',       // from Ozow Merchant Admin
    'ozow_private_key' => '',       // SECRET
    'ozow_api_key'     => '',
    'ozow_is_test'     => true,     // false when you go live

    // Turn this on only while you are debugging on your own machine. On a
    // live site it would print your SQL, and your SQL names your columns.
    'debug'   => false,

    // Only needed if the website and the API are on different domains.
    'cors_origins' => [],
];
