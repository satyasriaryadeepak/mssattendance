import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, "database.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT UNIQUE,
    name TEXT,
    password TEXT,
    department TEXT,
    status TEXT DEFAULT 'active'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    date TEXT,
    morning INTEGER,
    afternoon INTEGER,
    status TEXT,
    logout_time TEXT
)
""")

cursor.execute("""
INSERT OR IGNORE INTO admins (username, password)
VALUES ('admin', 'admin123')
""")

conn.commit()
conn.close()

print("Database created successfully!")