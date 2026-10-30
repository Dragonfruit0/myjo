-- Myjo School Demo, Order & Academic Support Portal · MySQL 8 schema
-- Generated from the SQLAlchemy models (flask --app wsgi export-schema).
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE audit_log (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	at DATETIME NOT NULL, 
	user_id INTEGER, 
	user_label VARCHAR(200) NOT NULL, 
	entity VARCHAR(40) NOT NULL, 
	ref VARCHAR(60) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	field VARCHAR(60), 
	old TEXT, 
	new TEXT, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_audit_log_ref ON audit_log (ref);
CREATE INDEX ix_audit_log_entity ON audit_log (entity);
CREATE INDEX ix_audit_log_at ON audit_log (at);

CREATE TABLE book_series (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(120) NOT NULL, 
	color VARCHAR(9) NOT NULL, 
	active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE notifications (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	at DATETIME NOT NULL, 
	event VARCHAR(80) NOT NULL, 
	message TEXT NOT NULL, 
	ref VARCHAR(40), 
	recipients JSON NOT NULL, 
	channel VARCHAR(30) NOT NULL, 
	status VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_notifications_at ON notifications (at);

CREATE TABLE role_permissions (
	`role` VARCHAR(16) NOT NULL, 
	kind VARCHAR(8) NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	PRIMARY KEY (`role`, kind, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE sequences (
	name VARCHAR(40) NOT NULL, 
	value INTEGER NOT NULL, 
	PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE subjects (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(80) NOT NULL, 
	active BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE trainings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	no VARCHAR(12) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	type VARCHAR(40) NOT NULL, 
	ay VARCHAR(9) NOT NULL, 
	series JSON NOT NULL, 
	classes JSON NOT NULL, 
	subjects JSON NOT NULL, 
	at DATETIME NOT NULL, 
	mode VARCHAR(8) NOT NULL, 
	trainer VARCHAR(120) NOT NULL, 
	link VARCHAR(500), 
	venue TEXT, 
	agenda TEXT NOT NULL, 
	remarks TEXT, 
	instructions TEXT, 
	status VARCHAR(12) NOT NULL, 
	resource_ids JSON NOT NULL, 
	completion JSON, 
	reminded BOOL NOT NULL, 
	reminded_on DATE, 
	created_at DATETIME NOT NULL, 
	cancel_reason TEXT, 
	cancel_by VARCHAR(120), 
	cancel_at DATETIME, 
	cancel_approved_by VARCHAR(120), 
	cancelled BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_trainings_status ON trainings (status);
CREATE INDEX ix_trainings_at ON trainings (at);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(64) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	email VARCHAR(190) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	`role` VARCHAR(16) NOT NULL, 
	org VARCHAR(160), 
	school_request_id INTEGER, 
	active BOOL NOT NULL, 
	pw_hash VARCHAR(255) NOT NULL, 
	pin_hash VARCHAR(255), 
	must_change BOOL NOT NULL, 
	failed_attempts INTEGER NOT NULL, 
	locked_until DATETIME, 
	token_version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_users_role ON users (`role`);

CREATE TABLE files (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(255) NOT NULL, 
	`stored` VARCHAR(80) NOT NULL, 
	mime VARCHAR(120) NOT NULL, 
	size INTEGER NOT NULL, 
	uploaded_by INTEGER, 
	at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (`stored`), 
	FOREIGN KEY(uploaded_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE schools (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(200) NOT NULL, 
	address VARCHAR(300) NOT NULL, 
	city VARCHAR(80) NOT NULL, 
	state VARCHAR(80) NOT NULL, 
	pincode VARCHAR(6) NOT NULL, 
	board VARCHAR(20) NOT NULL, 
	strength INTEGER, 
	contact VARCHAR(120) NOT NULL, 
	designation VARCHAR(80) NOT NULL, 
	mobile VARCHAR(15) NOT NULL, 
	email VARCHAR(190) NOT NULL, 
	distributor_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(distributor_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_schools_city ON schools (city);
CREATE INDEX ix_schools_state ON schools (state);

CREATE TABLE training_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	training_id INTEGER NOT NULL, 
	at DATETIME NOT NULL, 
	`by` VARCHAR(120) NOT NULL, 
	school VARCHAR(200) NOT NULL, 
	action TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(training_id) REFERENCES trainings (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_training_history_training_id ON training_history (training_id);

CREATE TABLE attachments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	entity VARCHAR(30) NOT NULL, 
	entity_id INTEGER NOT NULL, 
	file_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(file_id) REFERENCES files (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_attach_entity ON attachments (entity, entity_id);

CREATE TABLE demo_requests (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	no VARCHAR(24) NOT NULL, 
	school_id INTEGER NOT NULL, 
	distributor_id INTEGER NOT NULL, 
	ay VARCHAR(9) NOT NULL, 
	classes JSON NOT NULL, 
	subjects JSON NOT NULL, 
	series JSON NOT NULL, 
	exp_qty INTEGER, 
	pref_date DATE, 
	pref_time VARCHAR(5), 
	remarks TEXT, 
	status VARCHAR(24) NOT NULL, 
	order_status VARCHAR(24), 
	assigned_to VARCHAR(120), 
	direct BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	created_by INTEGER, 
	cancel_reason TEXT, 
	cancel_by VARCHAR(120), 
	cancel_at DATETIME, 
	cancel_approved_by VARCHAR(120), 
	cancelled BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (no), 
	FOREIGN KEY(school_id) REFERENCES schools (id), 
	FOREIGN KEY(distributor_id) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_demo_requests_distributor_id ON demo_requests (distributor_id);
CREATE INDEX ix_demo_requests_created_at ON demo_requests (created_at);
CREATE INDEX ix_req_school_ay ON demo_requests (school_id, ay);
CREATE INDEX ix_demo_requests_status ON demo_requests (status);

CREATE TABLE resources (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	no VARCHAR(12) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	type VARCHAR(40) NOT NULL, 
	series VARCHAR(120) NOT NULL, 
	cls VARCHAR(12) NOT NULL, 
	subject VARCHAR(80) NOT NULL, 
	ay VARCHAR(9) NOT NULL, 
	description TEXT, 
	file_id INTEGER, 
	link VARCHAR(500), 
	version VARCHAR(20) NOT NULL, 
	upload_date DATE NOT NULL, 
	uploaded_by VARCHAR(120) NOT NULL, 
	access VARCHAR(30) NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	cancel_reason TEXT, 
	cancel_by VARCHAR(120), 
	cancel_at DATETIME, 
	cancel_approved_by VARCHAR(120), 
	cancelled BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (no), 
	FOREIGN KEY(file_id) REFERENCES files (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_resources_series ON resources (series);
CREATE INDEX ix_resources_status ON resources (status);

CREATE TABLE academic_packs (
	request_id INTEGER NOT NULL, 
	at DATETIME NOT NULL, 
	`by` VARCHAR(120) NOT NULL, 
	training_id INTEGER, 
	paper_ids JSON NOT NULL, 
	resource_ids JSON NOT NULL, 
	PRIMARY KEY (request_id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id), 
	FOREIGN KEY(training_id) REFERENCES trainings (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE demo_feedback (
	request_id INTEGER NOT NULL, 
	`by` VARCHAR(120) NOT NULL, 
	date DATE NOT NULL, 
	attendees TEXT NOT NULL, 
	designations TEXT, 
	classes JSON NOT NULL, 
	subjects JSON NOT NULL, 
	series JSON NOT NULL, 
	interest VARCHAR(8) NOT NULL, 
	requirements TEXT, 
	requested JSON NOT NULL, 
	objections TEXT, 
	competitor VARCHAR(120), 
	next_follow DATE, 
	remarks TEXT, 
	PRIMARY KEY (request_id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE demo_schedules (
	request_id INTEGER NOT NULL, 
	at DATETIME NOT NULL, 
	mode VARCHAR(8) NOT NULL, 
	presenter VARCHAR(120) NOT NULL, 
	marketing VARCHAR(120) NOT NULL, 
	platform VARCHAR(30), 
	link VARCHAR(500), 
	venue TEXT, 
	agenda TEXT, 
	instructions TEXT, 
	shared_at DATETIME, 
	reminded BOOL NOT NULL, 
	PRIMARY KEY (request_id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE distributor_orders (
	request_id INTEGER NOT NULL, 
	status VARCHAR(12) NOT NULL, 
	direct BOOL NOT NULL, 
	ay VARCHAR(9) NOT NULL, 
	po VARCHAR(80) NOT NULL, 
	series JSON NOT NULL, 
	classes JSON NOT NULL, 
	subjects JSON NOT NULL, 
	qty INTEGER NOT NULL, 
	req_delivery DATE NOT NULL, 
	remarks TEXT, 
	`by` VARCHAR(120) NOT NULL, 
	at DATETIME NOT NULL, 
	review_note TEXT, 
	reviewed_by VARCHAR(120), 
	reviewed_at DATETIME, 
	PRIMARY KEY (request_id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_distributor_orders_po ON distributor_orders (po);

CREATE TABLE downloads (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	at DATETIME NOT NULL, 
	request_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	user_name VARCHAR(160) NOT NULL, 
	school_name VARCHAR(200) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	item_ref VARCHAR(20) NOT NULL, 
	item VARCHAR(300) NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_downloads_request_id ON downloads (request_id);
CREATE INDEX ix_downloads_at ON downloads (at);

CREATE TABLE followups (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	request_id INTEGER NOT NULL, 
	at DATETIME NOT NULL, 
	method VARCHAR(20) NOT NULL, 
	person VARCHAR(120) NOT NULL, 
	summary TEXT NOT NULL, 
	next_action VARCHAR(255), 
	next_date DATE, 
	`by` VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_followups_request_id ON followups (request_id);

CREATE TABLE marketing_feedback (
	request_id INTEGER NOT NULL, 
	potential VARCHAR(8) NOT NULL, 
	dm_name VARCHAR(120) NOT NULL, 
	dm_desig VARCHAR(80), 
	dm_mobile VARCHAR(15), 
	dm_email VARCHAR(190), 
	competitor VARCHAR(120), 
	exp_qty INTEGER, 
	decision_date DATE, 
	stage VARCHAR(40), 
	remarks TEXT, 
	next_action VARCHAR(255), 
	next_follow DATE, 
	person VARCHAR(120) NOT NULL, 
	reminded_on DATE, 
	PRIMARY KEY (request_id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_marketing_feedback_next_follow ON marketing_feedback (next_follow);

CREATE TABLE orders (
	request_id INTEGER NOT NULL, 
	ay VARCHAR(9) NOT NULL, 
	po VARCHAR(80) NOT NULL, 
	series JSON NOT NULL, 
	classes JSON NOT NULL, 
	subjects JSON NOT NULL, 
	qty INTEGER NOT NULL, 
	conf_date DATE NOT NULL, 
	del_date DATE NOT NULL, 
	payment VARCHAR(20) NOT NULL, 
	remarks TEXT, 
	source VARCHAR(12) NOT NULL, 
	PRIMARY KEY (request_id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id), 
	UNIQUE (po)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE question_papers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	no VARCHAR(12) NOT NULL, 
	request_id INTEGER NOT NULL, 
	ay VARCHAR(9) NOT NULL, 
	cls VARCHAR(10) NOT NULL, 
	subject VARCHAR(80) NOT NULL, 
	series VARCHAR(120) NOT NULL, 
	exam VARCHAR(20) NOT NULL, 
	due_date DATE NOT NULL, 
	assignee VARCHAR(120), 
	max_marks INTEGER, 
	delivery_date DATE, 
	status VARCHAR(20) NOT NULL, 
	qp_file_id INTEGER, 
	ak_file_id INTEGER, 
	remarks TEXT, 
	raised_by VARCHAR(30) NOT NULL, 
	published_at DATETIME, 
	reminded_on DATE, 
	cancel_reason TEXT, 
	cancel_by VARCHAR(120), 
	cancel_at DATETIME, 
	cancel_approved_by VARCHAR(120), 
	cancelled BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (no), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id), 
	FOREIGN KEY(qp_file_id) REFERENCES files (id), 
	FOREIGN KEY(ak_file_id) REFERENCES files (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_question_papers_status ON question_papers (status);
CREATE INDEX ix_question_papers_request_id ON question_papers (request_id);

CREATE TABLE resource_revocations (
	resource_id INTEGER NOT NULL, 
	request_id INTEGER NOT NULL, 
	PRIMARY KEY (resource_id, request_id), 
	FOREIGN KEY(resource_id) REFERENCES resources (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE resource_schools (
	resource_id INTEGER NOT NULL, 
	request_id INTEGER NOT NULL, 
	PRIMARY KEY (resource_id, request_id), 
	FOREIGN KEY(resource_id) REFERENCES resources (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE review_notes (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	request_id INTEGER NOT NULL, 
	at DATETIME NOT NULL, 
	`by` VARCHAR(120) NOT NULL, 
	type VARCHAR(60) NOT NULL, 
	text TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_review_notes_request_id ON review_notes (request_id);

CREATE TABLE training_schools (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	training_id INTEGER NOT NULL, 
	request_id INTEGER NOT NULL, 
	expected INTEGER NOT NULL, 
	school_confirm VARCHAR(10), 
	school_teachers INTEGER, 
	attended INTEGER, 
	attendance VARCHAR(20), 
	myjo_feedback TEXT, 
	fb_rating INTEGER, 
	fb_text TEXT, 
	fb_attended INTEGER, 
	fb_by VARCHAR(120), 
	fb_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (training_id, request_id), 
	FOREIGN KEY(training_id) REFERENCES trainings (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_training_schools_request_id ON training_schools (request_id);
CREATE INDEX ix_training_schools_training_id ON training_schools (training_id);

CREATE TABLE paper_revocations (
	paper_id INTEGER NOT NULL, 
	request_id INTEGER NOT NULL, 
	PRIMARY KEY (paper_id, request_id), 
	FOREIGN KEY(paper_id) REFERENCES question_papers (id), 
	FOREIGN KEY(request_id) REFERENCES demo_requests (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


SET FOREIGN_KEY_CHECKS = 1;