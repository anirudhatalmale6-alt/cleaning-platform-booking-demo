<?php
/**
 * Copy this to config.local.php and fill in your own details.
 * config.local.php is gitignored on purpose: a database password does not
 * belong in a repository, not even a private one.
 */
return [
    'db_host' => '127.0.0.1',
    'db_port' => 3306,
    'db_name' => 'sparrow',
    'db_user' => 'sparrow_app',
    'db_pass' => 'change-me',

    // Turn this on only while you are debugging on your own machine. On a
    // live site it would print your SQL, and your SQL names your columns.
    'debug'   => false,

    // Only needed if the website and the API are on different domains.
    'cors_origins' => [],
];
