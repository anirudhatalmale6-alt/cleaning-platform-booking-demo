-- =====================================================================
--  Sparrow — demo rows
--
--  Generated from the prototype's own data object, and every order total
--  below is the number priceBooking() in assets/app.js produces, not a
--  second implementation that could drift from it.
--
--  The people are fictional. The ID numbers are structurally valid but
--  invented, so the application form's check digit test passes on them.
--
--  Run after schema.sql:
--      mysql -u root -p sparrow < seed.sql
-- =====================================================================
USE sparrow;
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE order_status_history; TRUNCATE TABLE order_ratings;
TRUNCATE TABLE order_extras; TRUNCATE TABLE payments; TRUNCATE TABLE orders;
TRUNCATE TABLE customer_favourites; TRUNCATE TABLE customer_payment_methods;
TRUNCATE TABLE customer_addresses; TRUNCATE TABLE customers;
TRUNCATE TABLE employee_unavailability; TRUNCATE TABLE employee_documents;
TRUNCATE TABLE employee_areas; TRUNCATE TABLE employee_languages;
TRUNCATE TABLE employees; TRUNCATE TABLE messages_sent; TRUNCATE TABLE admins;
TRUNCATE TABLE service_extras; TRUNCATE TABLE services;
SET FOREIGN_KEY_CHECKS = 1;


-- Services. flat_rate_override is set on window cleaning only.
INSERT INTO services (code,name,description,service_group,pricing_model,flat_rate_override,est_hours,add_hours,extra_set,hours_are_estimated,is_active,sort_order) VALUES
  ('standard','Standard house cleaning','Kitchen, bathrooms, bedrooms and living areas','indoor','bedrooms',NULL,NULL,0,'home',0,1,10),
  ('deep','Deep clean','Everything in a standard clean, done to the corners','indoor','bedrooms',NULL,NULL,2,'home',1,1,20),
  ('move','Move-in / move-out','Empty property, cupboards and appliances inside','indoor','bedrooms',NULL,NULL,3,'home',1,1,30),
  ('laundry','Laundry & ironing','Wash, dry, iron and fold','indoor','laundry',NULL,NULL,0,NULL,0,1,40),
  ('office','Office cleaning','Desks, floors, kitchen and bathrooms','indoor','hours',NULL,5,0,NULL,1,1,50),
  ('outdoor','Outdoor cleaning','Patios, driveways, walls and paving','outdoor','hours',NULL,4,0,'outdoor',1,1,60),
  ('garden','Gardening','Mowing, weeding, trimming and clearing','outdoor','hours',NULL,4,0,'outdoor',1,1,70),
  ('windows','Window cleaning','In and out — glass, frames and sills, both sides','outdoor','rooms',110,NULL,0,'outdoor',0,1,80),
  ('carwash','Car wash','Wash, rinse and dry, inside and out','outdoor','vehicle',NULL,NULL,0,NULL,0,1,90);

INSERT INTO service_extras (code,name,description,extra_set,minutes,price,price_is_estimated,is_active,sort_order) VALUES
  ('oven','Oven clean',NULL,'home',30,35.0,0,1,10),
  ('fridge','Fridge clean',NULL,'home',30,35.0,0,1,20),
  ('cupboard','Cupboard clean',NULL,'home',60,35.0,0,1,30),
  ('washfold','Basic wash, dry and fold',NULL,'home',60,180.0,0,1,40),
  ('washiron','Wash, dry and iron',NULL,'home',120,250.0,0,1,50),
  ('pool','Pool service','Skim, vacuum, brush and a chemical check','outdoor',120,70.0,1,1,60);

-- Demo password for every account below is: demo1234
INSERT INTO admins (id,first_name,last_name,email,phone,password_hash,role) VALUES
  (1,'Lebo','Mthembu','lebo@sparrow.co.za','+27 82 111 0001','$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','superadmin'),
  (2,'Pieter','Naude','pieter@sparrow.co.za','+27 82 111 0002','$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','admin');

INSERT INTO customers (id,first_name,last_name,email,phone,password_hash,is_guest) VALUES
  (1,'Thandi','Mokoena','thandi.m@example.co.za','+27 82 445 1190','$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni',0),
  (2,'Riaan','van Wyk','riaan.vw@example.co.za','+27 83 220 7712','$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni',0),
  (3,'Aisha','Patel','aisha.p@example.co.za','+27 71 998 0032','$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni',0),
  (4,'Johan','Botha','j.botha@example.co.za','+27 84 551 3390','$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni',0);

INSERT INTO customer_addresses (id,customer_id,label,property_type,street_line,unit_number,suburb,city,province,access_notes,is_primary) VALUES
  (1,1,'Home','Flat / Apartment','18 Ocean View Drive','Flat 4B','Sea Point','Cape Town','Western Cape','Buzzer 12. Two cats — keep the balcony door shut.',1),
  (2,1,'Mom’s place','House','7 Protea Street',NULL,'Rondebosch','Cape Town','Western Cape','Key under the ceramic pot.',0),
  (3,1,'Office','Townhouse','12 Prestwich Street','Unit 3','Green Point','Cape Town','Western Cape','Reception has the access card.',0),
  (4,2,'Home','House','24 Kloof Nek Road',NULL,'Tamboerskloof','Cape Town','Western Cape','Gate code 4417. Dog is friendly.',1),
  (5,3,'Home','Flat / Apartment','5 Bree Street','Unit 806','Cape Town CBD','Cape Town','Western Cape','Security desk holds the spare key.',1),
  (6,4,'Home','Townhouse','31 Rhodes Avenue','Unit 12','Newlands','Cape Town','Western Cape','Park in the visitor bay.',1);

-- Workers. cl5 and cl6 are still pending, cl9 was declined with a
-- reason, so the sign-in gate has all three states to show.
INSERT INTO employees (id,first_name,last_name,email,phone,date_of_birth,id_type,id_number,service_group,years_experience,has_own_transport,password_hash,account_status,decline_reason,decided_by_admin_id) VALUES
  (1,'Nomsa','Mabaso','nomsa.m@example.co.za','+27 71 103 1011','2001-06-08','sa_id','0106085101082','indoor',6,0,'$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','approved',NULL,1),
  (2,'Sipho','Dlamini','sipho.d@example.co.za','+27 72 106 1022','1998-11-15','sa_id','9811155102081','outdoor',4,0,'$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','approved',NULL,1),
  (3,'Grace','Nkosi','grace.n@example.co.za','+27 73 109 1033','1995-04-22','sa_id','9504225103086','indoor',9,1,'$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','approved',NULL,1),
  (4,'Zanele','Ndlovu','zanele.n@example.co.za','+27 74 112 1044','1992-09-02','sa_id','9209025104082','indoor',3,0,'$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','approved',NULL,1),
  (5,'Thabo','Maseko','thabo.m@example.co.za','+27 75 115 1055','1989-02-09','sa_id','8902095105085','outdoor',2,0,'$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','approved',NULL,1),
  (6,'Lerato','Molefe','lerato.m@example.co.za','+27 76 118 1066','1986-07-16','sa_id','8607165106083','indoor',3,1,'$2y$10$KNC84mm0k7C3WF0QTJtBpOWyCK/tk34dyo.y9OtXMTkhz7SIDd2ni','approved',NULL,1),
  (7,'Andile','Khumalo','andile.k@example.co.za','+27 77 121 1077','1983-12-23','sa_id','8312235107084','outdoor',2,0,NULL,'pending',NULL,NULL),
  (8,'Precious','Sithole','precious.s@example.co.za','+27 78 124 1088','2004-05-03','sa_id','0405035108084','indoor',5,0,NULL,'pending',NULL,NULL),
  (9,'Bongani','Zulu','bongani.z@example.co.za','+27 79 127 1099','2001-10-10','sa_id','0110105109083','outdoor',1,1,NULL,'declined','Criminal record check came back unresolved. Welcome to reapply once it clears.',1);

INSERT INTO employee_languages (employee_id,language) VALUES
  (1,'English'),
  (1,'isiZulu'),
  (1,'isiXhosa'),
  (2,'English'),
  (2,'isiZulu'),
  (3,'English'),
  (3,'Sesotho'),
  (4,'English'),
  (4,'isiZulu'),
  (5,'English'),
  (5,'Sesotho'),
  (6,'English'),
  (6,'Setswana'),
  (7,'English'),
  (7,'isiXhosa'),
  (8,'English'),
  (8,'isiZulu'),
  (9,'English');

INSERT INTO employee_areas (employee_id,province,city) VALUES
  (1,'Western Cape','Cape Town'),
  (2,'Western Cape','Cape Town'),
  (3,'Western Cape','Cape Town'),
  (4,'Western Cape','Cape Town'),
  (5,'Western Cape','Cape Town'),
  (6,'Gauteng','Johannesburg'),
  (7,'KwaZulu-Natal','Durban'),
  (8,'Western Cape','Cape Town'),
  (9,'Western Cape','Cape Town');

INSERT INTO employee_documents (employee_id,doc_type,file_path,original_name,size_bytes) VALUES
  (1,'id','storage/employees/1/id-document.pdf','id-document.pdf',421888),
  (1,'photo','storage/employees/1/profile-photo.jpg','profile-photo.jpg',274432),
  (1,'criminal_check','storage/employees/1/police-clearance.pdf','police-clearance.pdf',717824),
  (2,'id','storage/employees/2/id-document.pdf','id-document.pdf',421888),
  (2,'photo','storage/employees/2/profile-photo.jpg','profile-photo.jpg',274432),
  (2,'criminal_check','storage/employees/2/police-clearance.pdf','police-clearance.pdf',717824),
  (3,'id','storage/employees/3/id-document.pdf','id-document.pdf',421888),
  (3,'photo','storage/employees/3/profile-photo.jpg','profile-photo.jpg',274432),
  (3,'criminal_check','storage/employees/3/police-clearance.pdf','police-clearance.pdf',717824),
  (4,'id','storage/employees/4/id-document.pdf','id-document.pdf',421888),
  (4,'photo','storage/employees/4/profile-photo.jpg','profile-photo.jpg',274432),
  (4,'criminal_check','storage/employees/4/police-clearance.pdf','police-clearance.pdf',717824),
  (4,'work_permit','storage/employees/4/work-permit.pdf','work-permit.pdf',363520),
  (5,'id','storage/employees/5/id-document.pdf','id-document.pdf',421888),
  (5,'photo','storage/employees/5/profile-photo.jpg','profile-photo.jpg',274432),
  (5,'criminal_check','storage/employees/5/police-clearance.pdf','police-clearance.pdf',717824),
  (6,'id','storage/employees/6/id-document.pdf','id-document.pdf',421888),
  (6,'photo','storage/employees/6/profile-photo.jpg','profile-photo.jpg',274432),
  (6,'criminal_check','storage/employees/6/police-clearance.pdf','police-clearance.pdf',717824),
  (7,'id','storage/employees/7/id-document.pdf','id-document.pdf',421888),
  (7,'photo','storage/employees/7/profile-photo.jpg','profile-photo.jpg',274432),
  (7,'criminal_check','storage/employees/7/police-clearance.pdf','police-clearance.pdf',717824),
  (8,'id','storage/employees/8/id-document.pdf','id-document.pdf',421888),
  (8,'photo','storage/employees/8/profile-photo.jpg','profile-photo.jpg',274432),
  (8,'criminal_check','storage/employees/8/police-clearance.pdf','police-clearance.pdf',717824),
  (8,'work_permit','storage/employees/8/work-permit.pdf','work-permit.pdf',363520),
  (9,'id','storage/employees/9/id-document.pdf','id-document.pdf',421888),
  (9,'photo','storage/employees/9/profile-photo.jpg','profile-photo.jpg',274432),
  (9,'criminal_check','storage/employees/9/police-clearance.pdf','police-clearance.pdf',717824);

-- The cleaner calendar writes these. Without them a blocked day is
-- invisible to the shortlist query.
INSERT INTO employee_unavailability (employee_id,unavailable_date,reason) VALUES
  (1,'2026-08-24','Not available'),
  (4,'2026-08-20','Not available');

-- Orders. Every total here is what priceBooking() produces in the
-- prototype, and the rates are frozen onto the row.
INSERT INTO orders (id,reference,customer_id,employee_id,service_code,scheduled_date,scheduled_time,hours_booked,bedroom_band,laundry_wash,laundry_finish,window_rooms,vehicle_size,address_id,address_line,address_unit,address_suburb,address_city,address_province,access_notes,note_for_worker,flat_rate,hourly_rate,labour_total,extras_total,service_fee,total) VALUES
  (1,'SPW-104312',1,1,'standard','2026-08-21','09:00:00',6.0,'b34',NULL,NULL,NULL,NULL,1,'18 Ocean View Drive','Flat 4B','Sea Point','Cape Town','Western Cape','Buzzer 12. Two cats — keep the balcony door shut.','Please start with the kitchen.',155.0,35.0,210.0,70.0,35.0,470.0),
  (2,'SPW-104298',1,2,'garden','2026-08-22','11:00:00',4.0,NULL,NULL,NULL,NULL,NULL,2,'7 Protea Street',NULL,'Rondebosch','Cape Town','Western Cape','Key under the ceramic pot.','Back garden only.',155.0,35.0,140.0,0.0,35.0,330.0),
  (3,'SPW-104201',1,3,'laundry','2026-08-25','07:00:00',7.5,NULL,'machine','dryiron',NULL,NULL,3,'12 Prestwich Street','Unit 3','Green Point','Cape Town','Western Cape','Reception has the access card.',NULL,155.0,35.0,262.5,0.0,35.0,452.5),
  (4,'SPW-103980',1,1,'standard','2026-08-11','09:00:00',6.0,'b34',NULL,NULL,NULL,NULL,1,'18 Ocean View Drive','Flat 4B','Sea Point','Cape Town','Western Cape','Buzzer 12. Two cats — keep the balcony door shut.',NULL,155.0,35.0,210.0,180.0,35.0,580.0),
  (5,'SPW-103844',1,3,'deep','2026-07-29','08:00:00',8.0,'b34',NULL,NULL,NULL,NULL,1,'18 Ocean View Drive','Flat 4B','Sea Point','Cape Town','Western Cape','Buzzer 12. Two cats — keep the balcony door shut.',NULL,155.0,35.0,280.0,35.0,35.0,505.0),
  (6,'SPW-103702',1,2,'windows','2026-07-15','10:00:00',4.5,NULL,NULL,NULL,5,NULL,2,'7 Protea Street',NULL,'Rondebosch','Cape Town','Western Cape','Key under the ceramic pot.',NULL,110.0,35.0,157.5,0.0,35.0,302.5),
  (7,'SPW-103688',1,5,'carwash','2026-07-04','11:00:00',1.5,NULL,NULL,NULL,NULL,'suv',1,'18 Ocean View Drive','Flat 4B','Sea Point','Cape Town','Western Cape','Buzzer 12. Two cats — keep the balcony door shut.','Parked in bay 12.',155.0,35.0,52.5,0.0,35.0,242.5),
  (8,'SPW-103551',1,5,'outdoor','2026-06-30','13:00:00',4.0,NULL,NULL,NULL,NULL,NULL,1,'18 Ocean View Drive','Flat 4B','Sea Point','Cape Town','Western Cape','Buzzer 12. Two cats — keep the balcony door shut.',NULL,155.0,35.0,140.0,0.0,35.0,330.0),
  (9,'SPW-104355',2,4,'standard','2026-08-20','10:00:00',4.0,'b12',NULL,NULL,NULL,NULL,4,'24 Kloof Nek Road',NULL,'Tamboerskloof','Cape Town','Western Cape','Gate code 4417. Dog is friendly.','Gate code 4471.',155.0,35.0,140.0,35.0,35.0,365.0),
  (10,'SPW-104361',3,3,'standard','2026-08-20','08:00:00',8.0,'b5',NULL,NULL,NULL,NULL,5,'5 Bree Street','Unit 806','Cape Town CBD','Cape Town','Western Cape','Security desk holds the spare key.',NULL,155.0,35.0,280.0,70.0,35.0,540.0),
  (11,'SPW-104366',4,5,'garden','2026-08-21','09:00:00',4.0,NULL,NULL,NULL,NULL,NULL,6,'31 Rhodes Avenue','Unit 12','Newlands','Cape Town','Western Cape','Park in the visitor bay.',NULL,155.0,35.0,140.0,0.0,35.0,330.0),
  (12,'SPW-104290',3,1,'laundry','2026-08-08','07:00:00',7.0,NULL,'hand','dryfold',NULL,NULL,5,'5 Bree Street','Unit 806','Cape Town CBD','Cape Town','Western Cape','Security desk holds the spare key.',NULL,155.0,35.0,245.0,0.0,35.0,435.0),
  (13,'SPW-104277',2,4,'standard','2026-08-05','09:00:00',4.0,'b12',NULL,NULL,NULL,NULL,4,'24 Kloof Nek Road',NULL,'Tamboerskloof','Cape Town','Western Cape','Gate code 4417. Dog is friendly.',NULL,155.0,35.0,140.0,0.0,35.0,330.0);

INSERT INTO order_extras (order_id,extra_code,name,minutes,price) VALUES
  (1,'oven','Oven clean',30,35.0),
  (1,'fridge','Fridge clean',30,35.0),
  (4,'washfold','Basic wash, dry and fold',60,180.0),
  (5,'oven','Oven clean',30,35.0),
  (9,'fridge','Fridge clean',30,35.0),
  (10,'oven','Oven clean',30,35.0),
  (10,'fridge','Fridge clean',30,35.0);

INSERT INTO order_ratings (order_id,stars,comment) VALUES
  (4,5,'Nomsa was early, thorough and lovely with the cats. Booking her again.'),
  (5,4,'Great clean overall, skirting boards in the hallway were missed.'),
  (7,5,'Thabo did the inside as well without being asked.'),
  (12,5,'Everything came back folded beautifully.'),
  (13,4,'Good job, arrived a little late.');

INSERT INTO order_status_history (order_id,status) VALUES
  (1,'upcoming'),
  (2,'upcoming'),
  (3,'upcoming'),
  (4,'completed'),
  (5,'completed'),
  (6,'completed'),
  (7,'completed'),
  (8,'cancelled'),
  (9,'upcoming'),
  (10,'upcoming'),
  (11,'upcoming'),
  (12,'completed'),
  (13,'completed');

INSERT INTO payments (order_id,gateway,gateway_ref,amount,status) VALUES
  (1,'payfast','PF-DEMO-00001',470.0,'approved'),
  (2,'payfast','PF-DEMO-00002',330.0,'approved'),
  (3,'payfast','PF-DEMO-00003',452.5,'approved'),
  (4,'payfast','PF-DEMO-00004',580.0,'approved'),
  (5,'payfast','PF-DEMO-00005',505.0,'approved'),
  (6,'payfast','PF-DEMO-00006',302.5,'approved'),
  (7,'payfast','PF-DEMO-00007',242.5,'approved'),
  (9,'payfast','PF-DEMO-00009',365.0,'approved'),
  (10,'payfast','PF-DEMO-00010',540.0,'approved'),
  (11,'payfast','PF-DEMO-00011',330.0,'approved'),
  (12,'payfast','PF-DEMO-00012',435.0,'approved'),
  (13,'payfast','PF-DEMO-00013',330.0,'approved');

-- set the live status on each order
UPDATE orders SET status='upcoming' WHERE id=1;
UPDATE orders SET status='upcoming' WHERE id=2;
UPDATE orders SET status='upcoming' WHERE id=3;
UPDATE orders SET status='completed' WHERE id=4;
UPDATE orders SET status='completed' WHERE id=5;
UPDATE orders SET status='completed' WHERE id=6;
UPDATE orders SET status='completed' WHERE id=7;
UPDATE orders SET status='cancelled' WHERE id=8;
UPDATE orders SET status='upcoming' WHERE id=9;
UPDATE orders SET status='upcoming' WHERE id=10;
UPDATE orders SET status='upcoming' WHERE id=11;
UPDATE orders SET status='completed' WHERE id=12;
UPDATE orders SET status='completed' WHERE id=13;

INSERT INTO customer_favourites (customer_id,employee_id) VALUES
  (1,1),
  (1,2);
