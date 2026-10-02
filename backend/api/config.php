<?php
/**
 * Database and app configuration.
 *
 * Copy config.local.example.php to config.local.php and put your real
 * credentials there. config.local.php is gitignored, so your database
 * password never ends up in a repository.
 */
declare(strict_types=1);

$defaults = [
    'db_host'    => '127.0.0.1',
    'db_port'    => 3306,
    'db_socket'  => null,          // set this instead of host/port if you use one
    'db_name'    => 'sparrow',
    'db_user'    => 'root',
    'db_pass'    => '',
    'debug'      => false,         // true prints the real SQL error. Never on a live site.

    // Where uploaded ID copies, photos and police clearances are written.
    // On a real host, point this OUTSIDE the public folder. An ID document
    // on a guessable URL is the worst leak this system could have.
    //   e.g. '/home/youraccount/sparrow-storage'
    'storage_path' => __DIR__ . '/../storage',

    // Used to build the return URLs Ozow sends the customer back to.
    'site_url'     => '',          // e.g. https://www.yourcompany.co.za

    // --- Ozow. Not live yet; see api/gateway_ozow.php ---
    'ozow_site_code'   => '',
    'ozow_private_key' => '',      // SECRET. config.local.php only.
    'ozow_api_key'     => '',
    'ozow_is_test'     => true,

    // Browsers calling this API from a different origin. Empty means
    // same-origin only, which is what you want once the site and the API
    // are served from the same domain.
    'cors_origins' => [],
];

$local = __DIR__ . '/config.local.php';
$config = file_exists($local)
    ? array_merge($defaults, require $local)
    : $defaults;

// Environment variables win, so the same code runs on a host where you
// cannot write a config file.
foreach (['DB_HOST' => 'db_host', 'DB_PORT' => 'db_port', 'DB_SOCKET' => 'db_socket',
          'DB_NAME' => 'db_name', 'DB_USER' => 'db_user', 'DB_PASS' => 'db_pass',
          'STORAGE_PATH' => 'storage_path', 'SITE_URL' => 'site_url',
          'OZOW_SITE_CODE' => 'ozow_site_code', 'OZOW_PRIVATE_KEY' => 'ozow_private_key',
          'OZOW_API_KEY' => 'ozow_api_key'] as $env => $key) {
    $v = getenv($env);
    if ($v !== false && $v !== '') {
        $config[$key] = $v;
    }
}

return $config;
