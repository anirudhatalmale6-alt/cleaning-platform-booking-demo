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
          'DB_NAME' => 'db_name', 'DB_USER' => 'db_user', 'DB_PASS' => 'db_pass'] as $env => $key) {
    $v = getenv($env);
    if ($v !== false && $v !== '') {
        $config[$key] = $v;
    }
}

return $config;
