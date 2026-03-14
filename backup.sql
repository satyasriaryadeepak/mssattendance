BEGIN TRANSACTION;
CREATE TABLE admins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);
INSERT INTO "admins" VALUES(1,'admin','admin123');
CREATE TABLE attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    date TEXT,
    morning INTEGER,
    afternoon INTEGER,
    status TEXT
, logout_time TEXT DEFAULT '');
INSERT INTO "attendance" VALUES(1,'mss01','2026-03-11',1,1,'Present','23:10:59');
INSERT INTO "attendance" VALUES(2,'mss02','2026-03-11',0,0,'Absent','17:36:29');
CREATE TABLE employees(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT UNIQUE,
    name TEXT,
    password TEXT,
    department TEXT,
    status TEXT DEFAULT 'active'
);
INSERT INTO "employees" VALUES(3,'mss01','Arya','Arya@2004','employe','active');
INSERT INTO "employees" VALUES(4,'mss02','chandan','chandan123','employe','active');
INSERT INTO "employees" VALUES(5,'test1','Test User','pass','Testing','active');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('admins',5);
INSERT INTO "sqlite_sequence" VALUES('employees',5);
INSERT INTO "sqlite_sequence" VALUES('attendance',2);
COMMIT;
