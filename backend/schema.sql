-- =====================================================================
--  Sparrow cleaning platform — MySQL 8.0 schema
--
--  Covers all three roles: customers, employees (workers) and admins,
--  plus the orders that join them and the pricing the orders freeze.
--
--  Run:  mysql -u root -p < schema.sql
--  Then: mysql -u root -p sparrow < seed.sql     (demo rows, optional)
--
--  Conventions used throughout, and why:
--
--  * InnoDB and utf8mb4 everywhere. utf8mb4 is the only charset that
--    holds the full range of characters a South African name, an
--    address or a customer note can contain.
--
--  * Money is DECIMAL(10,2), never FLOAT. Half an hour at R35 is
--    R17.50, so totals land on 50c, and FLOAT would eventually turn
--    242.50 into 242.49999999. DECIMAL is exact.
--
--  * Every table that a person creates has created_at, and every table
--    a person edits has updated_at. You will want them the first time
--    something looks wrong.
--
--  * Foreign keys state what happens on delete rather than leaving it
--    to chance. Addresses die with their customer; orders never do,
--    because an order is a financial record.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS sparrow
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE sparrow;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS
  order_status_history, order_ratings, order_extras, payments, orders,
  customer_favourites, customer_payment_methods, customer_addresses, customers,
  employee_unavailability, employee_documents, employee_areas,
  employee_languages, employees,
  messages_sent, admins,
  service_extras, services, settings;
SET FOREIGN_KEY_CHECKS = 1;


-- =====================================================================
--  1. SETTINGS — the price levers, editable from the admin dashboard
--
--  These are the client's four numbers plus the time rules. They live
--  in a table rather than in code so that changing a price is data,
--  never a deployment. Orders freeze their own copy (see `orders`), so
--  editing a row here never reprices an order already taken.
-- =====================================================================
CREATE TABLE settings (
  setting_key    VARCHAR(50)   NOT NULL PRIMARY KEY,
  setting_value  VARCHAR(255)  NOT NULL,
  description    VARCHAR(255)      NULL,
  updated_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                             ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO settings (setting_key, setting_value, description) VALUES
  ('hourly_rate',       '35.00', 'R35 per hour'),
  ('service_fee',       '35.00', 'R35 service fee, once per order'),
  ('flat_rate',        '155.00', 'R155 flat rate, once per order'),
  ('max_hours',           '10',  'An employee may not be booked past 10 hours in a day'),
  ('step_minutes',        '30',  'Hours move in 30-minute steps'),
  ('reduce_minutes',      '30',  'The customer may take at most 30 minutes off the estimate'),
  ('car_wash_hours',     '1.5', 'Every vehicle size is estimated at 1h30 (client, 1 Oct 2026)'),
  ('currency',            'ZAR', 'Displayed as R'),
  ('company_name',    'Sparrow', 'Shown on emails and invoices');


-- =====================================================================
--  2. SERVICES and EXTRA TASKS
--
--  pricing_model decides which question the booking screen asks, and
--  therefore which of the five answer columns on `orders` is filled in:
--
--    bedrooms  -> bedroom_band     (1-2 / 3-4 / 5+)
--    laundry   -> laundry_wash + laundry_finish
--    rooms     -> window_rooms
--    vehicle   -> vehicle_size
--    hours     -> nothing extra, just hours_booked
--
--  flat_rate_override is NULL for every service except window cleaning,
--  which the client set to R110 on 22 Aug and confirmed on 1 Oct as
--  "the R110 is for all windows base fee" — all window jobs, and window
--  cleaning only.
-- =====================================================================
CREATE TABLE services (
  code                VARCHAR(20)  NOT NULL PRIMARY KEY,
  name                VARCHAR(80)  NOT NULL,
  description         VARCHAR(255)     NULL,
  service_group       ENUM('indoor','outdoor') NOT NULL,
  pricing_model       ENUM('bedrooms','laundry','rooms','vehicle','hours') NOT NULL,
  flat_rate_override  DECIMAL(10,2)    NULL
                      COMMENT 'NULL means use settings.flat_rate (R155)',
  est_hours           DECIMAL(4,2)     NULL
                      COMMENT 'pricing_model=hours only',
  add_hours           DECIMAL(4,2) NOT NULL DEFAULT 0
                      COMMENT 'added to the bedroom band: deep clean +2, move-out +3',
  extra_set           ENUM('home','outdoor') NULL
                      COMMENT 'which extra tasks this service offers; NULL = none',
  hours_are_estimated TINYINT(1)   NOT NULL DEFAULT 0
                      COMMENT '1 = the duration is a developer guess, not a client figure',
  is_active           TINYINT(1)   NOT NULL DEFAULT 1,
  sort_order          SMALLINT     NOT NULL DEFAULT 0,
  created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_services_group (service_group, is_active, sort_order)
) ENGINE=InnoDB;

CREATE TABLE service_extras (
  code          VARCHAR(20)   NOT NULL PRIMARY KEY,
  name          VARCHAR(80)   NOT NULL,
  description   VARCHAR(255)      NULL,
  extra_set     ENUM('home','outdoor') NOT NULL
                COMMENT 'matched against services.extra_set so an extra cannot leak between services',
  minutes       SMALLINT      NOT NULL,
  price         DECIMAL(10,2) NOT NULL,
  price_is_estimated TINYINT(1) NOT NULL DEFAULT 0,
  is_active     TINYINT(1)    NOT NULL DEFAULT 1,
  sort_order    SMALLINT      NOT NULL DEFAULT 0,
  created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_extras_set (extra_set, is_active, sort_order)
) ENGINE=InnoDB;


-- =====================================================================
--  3. CUSTOMERS
--
--  A guest checkout still creates a row. You need somewhere to send the
--  confirmation email and somewhere to hang the order, and if that
--  person signs up later you can match them on email instead of
--  orphaning their history. is_guest = 1 and password_hash IS NULL is
--  what tells the two apart.
-- =====================================================================
CREATE TABLE customers (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  first_name     VARCHAR(60)  NOT NULL,
  last_name      VARCHAR(60)  NOT NULL,
  email          VARCHAR(190) NOT NULL,
  phone          VARCHAR(30)      NULL,
  password_hash  VARCHAR(255)     NULL
                 COMMENT 'NULL for a guest. Store a password_hash() result, never the password',
  is_guest       TINYINT(1)   NOT NULL DEFAULT 0,
  marketing_opt_in TINYINT(1) NOT NULL DEFAULT 0,
  last_login_at  DATETIME         NULL,
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_customers_email (email),
  INDEX idx_customers_created (created_at)
) ENGINE=InnoDB;

CREATE TABLE customer_addresses (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  customer_id   BIGINT UNSIGNED NOT NULL,
  label         VARCHAR(60)  NOT NULL DEFAULT 'Home',
  property_type ENUM('House','Flat / Apartment','Townhouse','Cottage','Bachelor unit')
                NOT NULL DEFAULT 'House',
  street_line   VARCHAR(160) NOT NULL,
  unit_number   VARCHAR(40)      NULL,
  suburb        VARCHAR(80)  NOT NULL,
  city          VARCHAR(80)  NOT NULL,
  province      VARCHAR(60)  NOT NULL,
  postal_code   VARCHAR(10)      NULL,
  -- filled in by the Google Places confirmation step, so the worker
  -- gets a pin instead of a paragraph
  latitude      DECIMAL(10,7)    NULL,
  longitude     DECIMAL(10,7)    NULL,
  place_id      VARCHAR(255)     NULL COMMENT 'Google Places id, for re-resolving later',
  access_notes  TEXT             NULL COMMENT 'buzzer number, where the key is, pets, parking',
  is_primary    TINYINT(1)   NOT NULL DEFAULT 0,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                          ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_addr_customer FOREIGN KEY (customer_id)
    REFERENCES customers(id) ON DELETE CASCADE,
  INDEX idx_addr_customer (customer_id, is_primary),
  INDEX idx_addr_city (city)
) ENGINE=InnoDB;

-- Card data belongs to your payment gateway, not to you. Store the
-- token it gives back and the four digits needed to show "•••• 4242",
-- and nothing else. A full card number in this table would put you
-- inside PCI scope.
CREATE TABLE customer_payment_methods (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  customer_id    BIGINT UNSIGNED NOT NULL,
  brand          VARCHAR(30)  NOT NULL COMMENT 'Visa, Mastercard, …',
  last4          CHAR(4)      NOT NULL,
  exp_month      TINYINT UNSIGNED NOT NULL,
  exp_year       SMALLINT UNSIGNED NOT NULL,
  gateway        VARCHAR(30)  NOT NULL COMMENT 'payfast, paystack, stripe, …',
  gateway_token  VARCHAR(255) NOT NULL,
  is_default     TINYINT(1)   NOT NULL DEFAULT 0,
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pm_customer FOREIGN KEY (customer_id)
    REFERENCES customers(id) ON DELETE CASCADE,
  CONSTRAINT chk_pm_month CHECK (exp_month BETWEEN 1 AND 12),
  INDEX idx_pm_customer (customer_id, is_default)
) ENGINE=InnoDB;


-- =====================================================================
--  4. ADMINS
-- =====================================================================
CREATE TABLE admins (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  first_name    VARCHAR(60)  NOT NULL,
  last_name     VARCHAR(60)  NOT NULL,
  email         VARCHAR(190) NOT NULL,
  phone         VARCHAR(30)      NULL,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('admin','superadmin') NOT NULL DEFAULT 'admin'
                COMMENT 'cheapest to add now; superadmin is the one who can create other admins',
  is_active     TINYINT(1)   NOT NULL DEFAULT 1,
  last_login_at DATETIME         NULL,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                          ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_admins_email (email)
) ENGINE=InnoDB;


-- =====================================================================
--  5. EMPLOYEES — the workers
--
--  account_status is the sign-in gate. 'pending' and 'declined' must
--  not be able to log in; only 'approved' may. Enforce that in the
--  query, not only in the interface.
--
--  NOTE: the column is service_group, not `group`. GROUP is a reserved
--  word in MySQL and naming a column that forces back-ticks into every
--  query you ever write.
-- =====================================================================
CREATE TABLE employees (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  first_name         VARCHAR(60)  NOT NULL,
  last_name          VARCHAR(60)  NOT NULL,
  email              VARCHAR(190) NOT NULL,
  phone              VARCHAR(30)  NOT NULL,
  date_of_birth      DATE         NOT NULL COMMENT '18+ is enforced at the application form',
  id_type            ENUM('sa_id','passport') NOT NULL DEFAULT 'sa_id',
  id_number          VARCHAR(30)  NOT NULL
                     COMMENT 'SA ID is validated on its own check digit, and the birth date inside it is compared with date_of_birth',
  service_group      ENUM('indoor','outdoor') NOT NULL,
  years_experience   TINYINT UNSIGNED NOT NULL DEFAULT 0,
  has_own_transport  TINYINT(1)   NOT NULL DEFAULT 0,
  password_hash      VARCHAR(255)     NULL
                     COMMENT 'set when the admin approves them, not at application time',
  profile_photo_path VARCHAR(255)     NULL COMMENT 'they can change this after approval',

  account_status     ENUM('pending','approved','declined') NOT NULL DEFAULT 'pending',
  decline_reason     TEXT             NULL
                     COMMENT 'typed by the admin; this exact text is what the applicant sees and is emailed',
  decided_by_admin_id BIGINT UNSIGNED NULL,
  decided_at         DATETIME         NULL,

  applied_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at      DATETIME         NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                               ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uq_employees_email (email),
  UNIQUE KEY uq_employees_id_number (id_number),
  CONSTRAINT fk_emp_decided_by FOREIGN KEY (decided_by_admin_id)
    REFERENCES admins(id) ON DELETE SET NULL,
  -- a decline without a reason is the one state the screens cannot render
  CONSTRAINT chk_emp_decline_reason
    CHECK (account_status <> 'declined' OR decline_reason IS NOT NULL),
  -- the shortlist query: approved workers of the right type
  INDEX idx_emp_status_group (account_status, service_group),
  INDEX idx_emp_applied (applied_at)
) ENGINE=InnoDB;

CREATE TABLE employee_languages (
  employee_id BIGINT UNSIGNED NOT NULL,
  language    VARCHAR(40)     NOT NULL,
  PRIMARY KEY (employee_id, language),
  CONSTRAINT fk_lang_employee FOREIGN KEY (employee_id)
    REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Which areas a worker covers. One worker, many cities, so it cannot
-- live as a column on employees.
CREATE TABLE employee_areas (
  employee_id BIGINT UNSIGNED NOT NULL,
  province    VARCHAR(60)     NOT NULL,
  city        VARCHAR(80)     NOT NULL,
  PRIMARY KEY (employee_id, city),
  CONSTRAINT fk_area_employee FOREIGN KEY (employee_id)
    REFERENCES employees(id) ON DELETE CASCADE,
  INDEX idx_area_city (city)
) ENGINE=InnoDB;

CREATE TABLE employee_documents (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id   BIGINT UNSIGNED NOT NULL,
  doc_type      ENUM('id','photo','criminal_check','work_permit') NOT NULL,
  file_path     VARCHAR(255) NOT NULL COMMENT 'path or object key. Keep these OUT of the public web root',
  original_name VARCHAR(190) NOT NULL,
  mime_type     VARCHAR(100)     NULL,
  size_bytes    INT UNSIGNED     NULL,
  uploaded_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_doc_employee FOREIGN KEY (employee_id)
    REFERENCES employees(id) ON DELETE CASCADE,
  INDEX idx_doc_employee (employee_id, doc_type)
) ENGINE=InnoDB;

-- The cleaner calendar writes here. Without this table the calendar is
-- decoration: nothing on the customer side shows it, but the shortlist
-- query reads it, so a worker who blocked a day would still be offered.
CREATE TABLE employee_unavailability (
  id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  employee_id       BIGINT UNSIGNED NOT NULL,
  unavailable_date  DATE         NOT NULL,
  reason            VARCHAR(190)     NULL,
  created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_unavail_employee FOREIGN KEY (employee_id)
    REFERENCES employees(id) ON DELETE CASCADE,
  -- blocking the same day twice is a double-click, not two days off
  UNIQUE KEY uq_unavail (employee_id, unavailable_date),
  INDEX idx_unavail_date (unavailable_date)
) ENGINE=InnoDB;


-- =====================================================================
--  6. ORDERS
--
--  Two things here matter more than the rest.
--
--  (a) THE MONEY IS FROZEN. flat_rate, hourly_rate, service_fee and
--      every extra's price are copied onto the order at checkout. If
--      you stored only service_code and recomputed from `settings`,
--      then raising the hourly rate from R35 to R40 would silently
--      reprice every order you had ever taken: refunds stop matching,
--      reports stop matching, and the customer's history disagrees with
--      their bank statement. An order is a record of what was charged,
--      not a sum to work out again.
--
--  (b) THE ADDRESS IS COPIED, not only referenced. address_id keeps the
--      link for "book this again", but the five snapshot columns hold
--      where the worker actually went. A customer editing or deleting
--      a saved address must not rewrite the history of a job that was
--      already done there.
-- =====================================================================
CREATE TABLE orders (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  reference          VARCHAR(20)  NOT NULL COMMENT 'the SPW-104312 the customer sees',
  customer_id        BIGINT UNSIGNED NOT NULL,
  employee_id        BIGINT UNSIGNED NULL
                     COMMENT 'the customer picks their own worker at checkout',
  service_code       VARCHAR(20)  NOT NULL,

  -- when
  scheduled_date     DATE         NOT NULL,
  scheduled_time     TIME         NOT NULL,
  hours_booked       DECIMAL(4,2) NOT NULL
                     COMMENT 'after the stepper. Service hours only, extras add their own time',

  -- the per-service answer. Exactly one group of these is filled in,
  -- decided by services.pricing_model.
  bedroom_band       ENUM('b12','b34','b5')                 NULL,
  laundry_wash       ENUM('hand','machine')                 NULL,
  laundry_finish     ENUM('dryfold','dryiron')              NULL,
  window_rooms       TINYINT UNSIGNED                       NULL,
  vehicle_size       ENUM('small','medium','big','suv','bakkie','truck') NULL,

  -- where the worker actually went (snapshot, see note (b) above)
  address_id         BIGINT UNSIGNED NULL,
  address_line       VARCHAR(160) NOT NULL,
  address_unit       VARCHAR(40)      NULL,
  address_suburb     VARCHAR(80)  NOT NULL,
  address_city       VARCHAR(80)  NOT NULL,
  address_province   VARCHAR(60)  NOT NULL,
  address_latitude   DECIMAL(10,7)    NULL,
  address_longitude  DECIMAL(10,7)    NULL,
  access_notes       TEXT             NULL,

  note_for_worker    TEXT             NULL COMMENT 'left at checkout',

  -- the money, frozen (see note (a) above)
  flat_rate          DECIMAL(10,2) NOT NULL,
  hourly_rate        DECIMAL(10,2) NOT NULL,
  labour_total       DECIMAL(10,2) NOT NULL COMMENT 'hours_booked * hourly_rate',
  extras_total       DECIMAL(10,2) NOT NULL DEFAULT 0,
  service_fee        DECIMAL(10,2) NOT NULL,
  total              DECIMAL(10,2) NOT NULL
                     COMMENT 'flat_rate + labour_total + extras_total + service_fee',

  status             ENUM('pending_payment','paid','upcoming','inprogress','completed','cancelled')
                     NOT NULL DEFAULT 'pending_payment',
  cancelled_reason   VARCHAR(255)     NULL,

  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                               ON UPDATE CURRENT_TIMESTAMP,

  UNIQUE KEY uq_orders_reference (reference),
  CONSTRAINT fk_order_customer FOREIGN KEY (customer_id)
    REFERENCES customers(id) ON DELETE RESTRICT,
  CONSTRAINT fk_order_employee FOREIGN KEY (employee_id)
    REFERENCES employees(id) ON DELETE RESTRICT,
  CONSTRAINT fk_order_service FOREIGN KEY (service_code)
    REFERENCES services(code) ON DELETE RESTRICT,
  CONSTRAINT fk_order_address FOREIGN KEY (address_id)
    REFERENCES customer_addresses(id) ON DELETE SET NULL,
  CONSTRAINT chk_order_hours CHECK (hours_booked > 0 AND hours_booked <= 24),

  -- the hot query: how many hours does this worker already have on this
  -- day? It runs once per candidate on every booking.
  INDEX idx_orders_employee_date (employee_id, scheduled_date, status),
  INDEX idx_orders_customer (customer_id, scheduled_date),
  INDEX idx_orders_status_date (status, scheduled_date),
  INDEX idx_orders_created (created_at)
) ENGINE=InnoDB;

-- An extra is copied onto the order with the price and duration it had
-- on the day, for the same reason the rates are.
CREATE TABLE order_extras (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  order_id    BIGINT UNSIGNED NOT NULL,
  extra_code  VARCHAR(20)   NOT NULL,
  name        VARCHAR(80)   NOT NULL COMMENT 'copied, so renaming the task later does not rewrite old orders',
  minutes     SMALLINT      NOT NULL,
  price       DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_oe_order FOREIGN KEY (order_id)
    REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_oe_extra FOREIGN KEY (extra_code)
    REFERENCES service_extras(code) ON DELETE RESTRICT,
  UNIQUE KEY uq_oe (order_id, extra_code)
) ENGINE=InnoDB;

CREATE TABLE payments (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  order_id      BIGINT UNSIGNED NOT NULL,
  gateway       VARCHAR(30)   NOT NULL COMMENT 'payfast, paystack, …',
  gateway_ref   VARCHAR(190)      NULL,
  amount        DECIMAL(10,2) NOT NULL,
  status        ENUM('initiated','approved','failed','refunded') NOT NULL DEFAULT 'initiated',
  failure_reason VARCHAR(255)     NULL,
  created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  settled_at    DATETIME          NULL,
  CONSTRAINT fk_pay_order FOREIGN KEY (order_id)
    REFERENCES orders(id) ON DELETE RESTRICT,
  INDEX idx_pay_order (order_id, status),
  -- a gateway resending its callback must not create a second payment
  UNIQUE KEY uq_pay_gateway_ref (gateway, gateway_ref)
) ENGINE=InnoDB;

-- One rating per order, which is what makes the average honest: a
-- customer cannot rate the same job twice, and a worker's score is
-- derived from jobs actually done.
CREATE TABLE order_ratings (
  order_id    BIGINT UNSIGNED NOT NULL PRIMARY KEY,
  stars       TINYINT UNSIGNED NOT NULL,
  comment     TEXT             NULL,
  created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_rating_order FOREIGN KEY (order_id)
    REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT chk_rating_stars CHECK (stars BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE order_status_history (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  order_id       BIGINT UNSIGNED NOT NULL,
  status         ENUM('pending_payment','paid','upcoming','inprogress','completed','cancelled') NOT NULL,
  changed_by_admin_id BIGINT UNSIGNED NULL,
  note           VARCHAR(255)     NULL,
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_hist_order FOREIGN KEY (order_id)
    REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_hist_admin FOREIGN KEY (changed_by_admin_id)
    REFERENCES admins(id) ON DELETE SET NULL,
  INDEX idx_hist_order (order_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE customer_favourites (
  customer_id BIGINT UNSIGNED NOT NULL,
  employee_id BIGINT UNSIGNED NOT NULL,
  created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (customer_id, employee_id),
  CONSTRAINT fk_fav_customer FOREIGN KEY (customer_id)
    REFERENCES customers(id) ON DELETE CASCADE,
  CONSTRAINT fk_fav_employee FOREIGN KEY (employee_id)
    REFERENCES employees(id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- =====================================================================
--  7. MESSAGES SENT
--
--  Every automatic email and SMS in the brief: the order confirmation,
--  the job details to the worker, the new-order alert to the admins,
--  the approval, and the decline with its reason. Keeping the body is
--  what you will want the first time a worker says they were never told
--  about a job.
-- =====================================================================
CREATE TABLE messages_sent (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  channel        ENUM('email','sms','whatsapp') NOT NULL,
  recipient_type ENUM('customer','employee','admin') NOT NULL,
  recipient_id   BIGINT UNSIGNED  NULL
                 COMMENT 'nullable so a guest or a failed lookup still records the attempt',
  to_address     VARCHAR(190) NOT NULL COMMENT 'the email or number actually used',
  subject        VARCHAR(255)     NULL,
  body           MEDIUMTEXT   NOT NULL,
  order_id       BIGINT UNSIGNED  NULL,
  status         ENUM('queued','sent','failed') NOT NULL DEFAULT 'queued',
  error          VARCHAR(255)     NULL,
  created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  sent_at        DATETIME         NULL,
  CONSTRAINT fk_msg_order FOREIGN KEY (order_id)
    REFERENCES orders(id) ON DELETE SET NULL,
  INDEX idx_msg_recipient (recipient_type, recipient_id, created_at),
  INDEX idx_msg_status (status, created_at)
) ENGINE=InnoDB;


-- =====================================================================
--  8. VIEWS — the two sums the dashboards ask for constantly
-- =====================================================================

-- A worker's rating comes from completed jobs, so it is derived and can
-- never drift out of step with the reviews shown next to it.
CREATE OR REPLACE VIEW v_employee_ratings AS
SELECT e.id                              AS employee_id,
       COUNT(r.order_id)                 AS rating_count,
       ROUND(AVG(r.stars), 2)            AS rating_avg,
       SUM(o.status = 'completed')       AS jobs_completed
FROM employees e
LEFT JOIN orders o        ON o.employee_id = e.id
LEFT JOIN order_ratings r ON r.order_id    = o.id
GROUP BY e.id;

-- Hours already committed per worker per day. The booking screen
-- subtracts this from the 10-hour cap; cancelled jobs free their hours
-- back up, which is why the status filter is here and not in the app.
CREATE OR REPLACE VIEW v_employee_day_load AS
SELECT o.employee_id,
       o.scheduled_date,
       SUM(o.hours_booked
           + COALESCE((SELECT SUM(oe.minutes) / 60
                       FROM order_extras oe
                       WHERE oe.order_id = o.id), 0)) AS hours_committed
FROM orders o
WHERE o.status IN ('paid','upcoming','inprogress','completed')
  AND o.employee_id IS NOT NULL
GROUP BY o.employee_id, o.scheduled_date;
