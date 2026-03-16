-- Create admins table
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Create employees table
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    employee_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    department TEXT NOT NULL,
    status TEXT DEFAULT 'active'
);

-- Create attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id),
    date DATE NOT NULL,
    morning INTEGER DEFAULT 0,
    afternoon INTEGER DEFAULT 0,
    morning_time TEXT,
    afternoon_time TEXT,
    status TEXT NOT NULL,
    logout_time TEXT,
    UNIQUE(employee_id, date)
);

-- Create holidays table
CREATE TABLE IF NOT EXISTS holidays (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    description TEXT
);

-- Insert a default admin if none exists
INSERT INTO admins (username, password) 
VALUES ('admin', 'admin123')
ON CONFLICT (username) DO NOTHING;
