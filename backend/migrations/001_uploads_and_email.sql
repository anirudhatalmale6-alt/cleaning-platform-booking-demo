-- =====================================================================
--  Migration 001 — document uploads, and your email addresses
--
--  Only needed if you already loaded schema.sql BEFORE 3 Oct 2026. On a
--  fresh database schema.sql already contains all of this.
--
--      mysql -u root -p sparrow < migrations/001_uploads_and_email.sql
-- =====================================================================
USE sparrow;

-- An applicant has no account yet, so they cannot be signed in to upload
-- their ID. The application hands back a one-time token instead.
ALTER TABLE employees
  ADD COLUMN upload_token_hash    CHAR(64) NULL AFTER decided_at,
  ADD COLUMN upload_token_expires DATETIME NULL AFTER upload_token_hash;

ALTER TABLE employee_documents
  ADD COLUMN width_px  SMALLINT UNSIGNED NULL AFTER size_bytes,
  ADD COLUMN height_px SMALLINT UNSIGNED NULL AFTER width_px;

-- One current document of each kind per worker: uploading again replaces
-- it instead of leaving three police clearances to choose between.
-- Clear duplicates first, keeping the newest of each kind.
DELETE d FROM employee_documents d
  JOIN employee_documents newer
    ON newer.employee_id = d.employee_id
   AND newer.doc_type    = d.doc_type
   AND newer.id          > d.id;
ALTER TABLE employee_documents
  ADD UNIQUE KEY uq_doc_kind (employee_id, doc_type);

-- ====== PUT YOUR OWN EMAIL ADDRESSES HERE ======
INSERT INTO settings (setting_key, setting_value, description) VALUES
  ('orders_email',  'orders@yourcompany.co.za',  'New order alerts go here. CHANGE THIS to your address.'),
  ('from_email',    'noreply@yourcompany.co.za', 'Customer confirmations are sent from here. CHANGE THIS.'),
  ('from_name',     'Sparrow Cleaning',          'The name customers see the email come from'),
  ('support_email', 'help@yourcompany.co.za',    'Printed at the bottom of customer emails'),
  ('max_upload_mb', '5',                         'Largest document or photo a worker may upload')
ON DUPLICATE KEY UPDATE description = VALUES(description);
