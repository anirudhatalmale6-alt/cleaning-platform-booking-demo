<?php
/**
 * Worker document and photo uploads.
 *
 * These are ID copies, passports and police clearances. If one of them
 * ends up on a URL somebody can guess, that is the worst leak this system
 * is capable of, so the rules here are deliberately strict:
 *
 *  1. THE FILES LIVE OUTSIDE THE PUBLIC FOLDER. Nothing serves them except
 *     the download endpoint, and that endpoint checks who is asking.
 *
 *  2. THE CLIENT'S FILENAME IS NEVER USED AS A PATH. A name arriving from
 *     a browser can carry a directory ("../../index.php"), a null byte, or
 *     a second extension ("cv.pdf.php"). We generate the stored name and
 *     keep theirs only to show on screen.
 *
 *  3. THE TYPE IS SNIFFED FROM THE BYTES. The Content-Type in the request
 *     and the extension on the name are both written by whoever is
 *     uploading. finfo reads the file itself.
 *
 *  4. IMAGES MUST DECODE. getimagesize() failing means it is not the image
 *     it claims to be, whatever the first few bytes say.
 */
declare(strict_types=1);

/** Where the files go. Absolute, and ideally nowhere near the web root. */
function storage_root(): string
{
    $c = cfg();
    $path = $c['storage_path'] ?? (__DIR__ . '/../storage');
    $real = realpath($path);
    if ($real === false) {
        if (!@mkdir($path, 0750, true) && !is_dir($path)) {
            fail('Upload storage is not writable', 500);
        }
        $real = realpath($path);
    }
    return rtrim((string)$real, '/');
}

const DOC_TYPES = ['id', 'photo', 'criminal_check', 'work_permit'];

/**
 * What a worker can ACTUALLY upload, in MB.
 *
 * settings.max_upload_mb is what you want. PHP's own upload_max_filesize
 * and post_max_size are what the server will physically accept, and on a
 * default install they are 2 MB. Setting 5 in the admin screen while PHP
 * says 2 means workers hit a wall at 2 and get an error about php.ini,
 * which tells them nothing. So the smaller of the two is the real limit,
 * and it is the number the booking screen is told about.
 */
function php_limit_mb(): float
{
    $toMb = function (string $v): float {
        $v = trim($v);
        if ($v === '' || $v === '0') {
            return INF;                      // 0 means unlimited in php.ini
        }
        $unit = strtolower(substr($v, -1));
        $n = (float)$v;
        return match ($unit) {
            'g' => $n * 1024,
            'm' => $n,
            'k' => $n / 1024,
            default => $n / 1048576,
        };
    };
    return min($toMb((string)ini_get('upload_max_filesize')),
               $toMb((string)ini_get('post_max_size')));
}

function effective_upload_mb(): float
{
    return min((float)setting('max_upload_mb', '5'), php_limit_mb());
}

/** mime => [extension, is_image] */
const ALLOWED_TYPES = [
    'application/pdf' => ['pdf', false],
    'image/jpeg'      => ['jpg', true],
    'image/png'       => ['png', true],
    'image/webp'      => ['webp', true],
    'image/heic'      => ['heic', true],   // what an iPhone sends by default
];

/**
 * Check one uploaded file and move it into storage.
 * Returns the row to write, or calls fail() with something a person can act on.
 */
function accept_upload(array $file, int $employeeId, string $docType): array
{
    if (!in_array($docType, DOC_TYPES, true)) {
        fail('Unknown document type', 422);
    }

    // PHP's own error first: this is where "the file is too big for the
    // server" shows up, and it is nothing like "the file is too big for us".
    $err = $file['error'] ?? UPLOAD_ERR_NO_FILE;
    if ($err !== UPLOAD_ERR_OK) {
        $msgs = [
            UPLOAD_ERR_INI_SIZE   => sprintf(
                'That file is larger than %s MB, which is all this server currently '
                . 'accepts. Raise upload_max_filesize and post_max_size in php.ini '
                . 'to allow bigger documents.', rtrim(rtrim(number_format(php_limit_mb(), 1), '0'), '.')),
            UPLOAD_ERR_FORM_SIZE  => 'That file is too large.',
            UPLOAD_ERR_PARTIAL    => 'The upload was interrupted. Try again.',
            UPLOAD_ERR_NO_FILE    => 'No file was attached.',
            UPLOAD_ERR_NO_TMP_DIR => 'The server has no temporary folder configured.',
            UPLOAD_ERR_CANT_WRITE => 'The server could not write the file to disk.',
            UPLOAD_ERR_EXTENSION  => 'A PHP extension stopped the upload.',
        ];
        fail($msgs[$err] ?? 'That file did not upload', 422);
    }

    $tmp = $file['tmp_name'] ?? '';
    // Without this check, any readable path on the server could be passed
    // off as an upload.
    if (!$tmp || !is_uploaded_file($tmp)) {
        fail('That was not an uploaded file', 422);
    }

    $maxMb = effective_upload_mb();
    $size  = (int)filesize($tmp);
    if ($size <= 0) {
        fail('That file is empty', 422);
    }
    if ($size > $maxMb * 1024 * 1024) {
        fail(sprintf('That file is %.1f MB. The limit is %s MB.',
                     $size / 1048576, rtrim(rtrim((string)$maxMb, '0'), '.')), 422);
    }

    // The real type, read out of the bytes.
    $finfo = new finfo(FILEINFO_MIME_TYPE);
    $mime  = (string)$finfo->file($tmp);
    if (!isset(ALLOWED_TYPES[$mime])) {
        fail('That file is a ' . $mime . '. Upload a PDF or a photo.', 422);
    }
    [$ext, $isImage] = ALLOWED_TYPES[$mime];

    $width = $height = null;
    if ($isImage && $mime !== 'image/heic') {
        // A file can start with valid JPEG magic bytes and still not be a
        // JPEG. If it will not decode, it is not a photo.
        $info = @getimagesize($tmp);
        if ($info === false) {
            fail('That image could not be read. Try saving it again, or send a PDF.', 422);
        }
        [$width, $height] = $info;
        if ($width < 200 || $height < 200) {
            fail('That image is too small to be useful. At least 200 by 200 pixels.', 422);
        }
        if ($width > 12000 || $height > 12000) {
            fail('That image is unusually large. Please resize it first.', 422);
        }
    }

    // A photo is the picture customers see, so it has to be an image.
    if ($docType === 'photo' && !$isImage) {
        fail('Your profile photo must be a picture, not a PDF.', 422);
    }

    $dir = storage_root() . '/employees/' . $employeeId;
    if (!is_dir($dir) && !@mkdir($dir, 0750, true) && !is_dir($dir)) {
        fail('Upload storage is not writable', 500);
    }

    // Our name, not theirs.
    $stored = $docType . '-' . bin2hex(random_bytes(8)) . '.' . $ext;
    $dest   = $dir . '/' . $stored;
    if (!move_uploaded_file($tmp, $dest)) {
        fail('The file could not be saved', 500);
    }
    @chmod($dest, 0640);

    // Theirs, kept for display only, with any path stripped off it.
    $original = basename(str_replace('\\', '/', (string)($file['name'] ?? 'document')));
    $original = preg_replace('/[^\PC\s]/u', '', $original);     // drop control chars
    $original = mb_substr(trim($original) ?: 'document', 0, 190);

    return [
        'employee_id'   => $employeeId,
        'doc_type'      => $docType,
        'file_path'     => 'employees/' . $employeeId . '/' . $stored,
        'original_name' => $original,
        'mime_type'     => $mime,
        'size_bytes'    => $size,
        'width_px'      => $width,
        'height_px'     => $height,
    ];
}

/** Write the row, replacing any previous document of the same kind. */
function save_document(array $row): int
{
    $old = q1('SELECT id, file_path FROM employee_documents
               WHERE employee_id = ? AND doc_type = ?',
              [$row['employee_id'], $row['doc_type']]);

    exec_sql(
        'INSERT INTO employee_documents
            (employee_id, doc_type, file_path, original_name, mime_type,
             size_bytes, width_px, height_px)
         VALUES (?,?,?,?,?,?,?,?)
         ON DUPLICATE KEY UPDATE
            file_path = VALUES(file_path), original_name = VALUES(original_name),
            mime_type = VALUES(mime_type), size_bytes = VALUES(size_bytes),
            width_px  = VALUES(width_px),  height_px = VALUES(height_px),
            uploaded_at = CURRENT_TIMESTAMP',
        [$row['employee_id'], $row['doc_type'], $row['file_path'], $row['original_name'],
         $row['mime_type'], $row['size_bytes'], $row['width_px'], $row['height_px']]
    );

    // Delete the replaced file only after the new row is committed, so a
    // failed write never leaves a row pointing at nothing.
    if ($old && $old['file_path'] !== $row['file_path']) {
        $p = storage_root() . '/' . $old['file_path'];
        if (is_file($p)) {
            @unlink($p);
        }
    }

    $id = q1('SELECT id FROM employee_documents WHERE employee_id = ? AND doc_type = ?',
             [$row['employee_id'], $row['doc_type']]);
    return (int)$id['id'];
}

/**
 * Stream a document to someone allowed to see it.
 *
 * Content-Disposition is attachment and the type is forced, because a
 * stored file that a browser decides to render in place is how an upload
 * becomes a cross-site scripting hole.
 */
function stream_document(int $docId): never
{
    $d = q1('SELECT * FROM employee_documents WHERE id = ?', [$docId]);
    if (!$d) {
        fail('No such document', 404);
    }
    $path = storage_root() . '/' . $d['file_path'];
    // realpath, then confirm it is still inside storage: a file_path that
    // ever gained a "../" must not be able to read outside the folder.
    $real = realpath($path);
    if ($real === false || !str_starts_with($real, storage_root() . '/')) {
        fail('That file is missing from storage', 410);
    }

    header('Content-Type: ' . $d['mime_type']);
    header('Content-Length: ' . filesize($real));
    header('Content-Disposition: attachment; filename="'
           . str_replace('"', '', $d['original_name']) . '"');
    header('X-Content-Type-Options: nosniff');
    header('Cache-Control: private, no-store');
    readfile($real);
    exit;
}

/* ---------------------------------------------------------------------
   Upload tokens — how an applicant with no account proves the upload is
   theirs. Hashed in the database exactly like a password would be, so a
   leaked backup does not hand out upload rights.
   --------------------------------------------------------------------- */

function issue_upload_token(int $employeeId): string
{
    $token = bin2hex(random_bytes(24));
    exec_sql('UPDATE employees SET upload_token_hash = ?,
              upload_token_expires = DATE_ADD(NOW(), INTERVAL 2 HOUR) WHERE id = ?',
             [hash('sha256', $token), $employeeId]);
    return $token;
}

function check_upload_token(int $employeeId, string $token): bool
{
    $e = q1('SELECT upload_token_hash, upload_token_expires FROM employees WHERE id = ?',
            [$employeeId]);
    if (!$e || !$e['upload_token_hash'] || !$e['upload_token_expires']) {
        return false;
    }
    if (strtotime((string)$e['upload_token_expires']) < time()) {
        return false;
    }
    // Constant time, so the comparison cannot be used to guess the token
    // one character at a time.
    return hash_equals((string)$e['upload_token_hash'], hash('sha256', $token));
}
