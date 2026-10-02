<?php
/**
 * Router for PHP's built-in web server, so the whole site can be run with
 * one command while developing:
 *
 *     php -S localhost:8000 -t . backend/router.php
 *
 * It does what the .htaccess does on Apache: /api/... goes to the API, and
 * everything else is served as a plain file. On a real host you do not need
 * this file at all.
 */
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if (preg_match('#^/api(/.*)?$#', $path, $m)) {
    $_SERVER['PATH_INFO'] = $m[1] ?? '/';
    require __DIR__ . '/api/index.php';
    return true;
}

$file = __DIR__ . '/..' . $path;
if ($path !== '/' && is_file($file)) {
    return false;          // let the built-in server serve it
}
if ($path === '/' ) {
    require __DIR__ . '/../index.html';
    return true;
}
http_response_code(404);
echo 'Not found';
return true;
