from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "mssquare_secret_key"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------

@app.route("/")
def home():
    print("DEBUG: Home route accessed /", flush=True)
    return render_template("login.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():
    role = request.form["role"].strip()
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    if role == "admin":
        cursor.execute(
            "SELECT * FROM admins WHERE username=? AND password=?",
            (username, password)
        )
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session["role"] = "admin"
            session["username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        return render_template("login.html", error="Invalid admin login credentials")

    elif role == "employee":
        cursor.execute(
            "SELECT * FROM employees WHERE employee_id=? AND password=? AND status='active'",
            (username, password)
        )
        emp = cursor.fetchone()
        conn.close()

        if emp:
            session["role"] = "employee"
            session["employee_id"] = emp["employee_id"]
            session["employee_name"] = emp["name"]
            return redirect(url_for("employee_home"))
        return render_template("login.html", error="Invalid employee login credentials")

    conn.close()
    return "Invalid login"


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    if session.get("role") == "employee":
        employee_id = session.get("employee_id")
        today = datetime.now().strftime("%Y-%m-%d")
        logout_time = datetime.now().strftime("%H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date=?
        """, (employee_id, today))

        record = cursor.fetchone()

        if record:
            cursor.execute("""
            UPDATE attendance
            SET logout_time=?
            WHERE employee_id=? AND date=?
            """, (logout_time, employee_id, today))

            conn.commit()
            print(f"DEBUG: Logout recorded for {employee_id}", flush=True)
        conn.close()

    session.clear()
    return redirect(url_for("home"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM employees WHERE status='active'")
    total_employees = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present'",
        (today,)
    )
    present_today = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM attendance WHERE date=? AND status='Absent'",
        (today,)
    )
    absent_today = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_employees=total_employees,
        present_today=present_today,
        absent_today=absent_today
    )


# ---------------- MANAGE EMPLOYEES ----------------

@app.route("/admin/employees")
def manage_employees():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    if search:
        cursor.execute("""
            SELECT * FROM employees
            WHERE employee_id LIKE ? OR name LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM employees ORDER BY id DESC")

    employees = cursor.fetchall()
    conn.close()

    return render_template("manage_employees.html", employees=employees, search=search)


@app.route("/admin/add_employee", methods=["POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    emp_id = request.form["employee_id"].strip()
    name = request.form["name"].strip()
    password = request.form["password"].strip()
    department = request.form["department"].strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO employees (employee_id, name, password, department, status)
            VALUES (?, ?, ?, ?, 'active')
        """, (emp_id, name, password, department))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "Employee ID already exists"

    conn.close()
    return redirect(url_for("manage_employees"))


@app.route("/admin/delete_employee/<int:id>")
def delete_employee(id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM employees WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect(url_for("manage_employees"))


# ---------------- ADMIN REPORTS ----------------

@app.route("/admin/reports")
def attendance_reports():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT attendance.*, employees.name
        FROM attendance
        JOIN employees ON attendance.employee_id = employees.employee_id
        ORDER BY attendance.date DESC, attendance.id DESC
    """)
    records = cursor.fetchall()

    conn.close()

    return render_template("attendance_reports.html", records=records)


# ---------------- EMPLOYEE HOME ----------------

@app.route("/employee/home")
def employee_home():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    return render_template(
        "employee_home.html",
        employee_name=session.get("employee_name"),
        employee_id=session.get("employee_id")
    )


# ---------------- ATTENDANCE PAGE ----------------

@app.route("/employee/attendance")
def attendance_page():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    employee_id = session.get("employee_id")
    today = datetime.now().strftime("%Y-%m-%d")
    msg = request.args.get("msg", "")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date=?
    """, (employee_id, today))
    record = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM employees
        WHERE employee_id=?
    """, (employee_id,))
    employee = cursor.fetchone()

    conn.close()

    return render_template(
        "attendance.html",
        record=record,
        employee=employee,
        msg=msg
    )


# ---------------- MARK ATTENDANCE ----------------

@app.route("/employee/mark_attendance", methods=["POST"])
def mark_attendance():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    employee_id = session.get("employee_id")
    period = request.form["period"]

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    morning_deadline = "10:10"
    afternoon_deadline = "14:10"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date=?
    """, (employee_id, today))
    record = cursor.fetchone()

    if not record:
        cursor.execute("""
            INSERT INTO attendance
            (employee_id, date, morning, afternoon, status, logout_time)
            VALUES (?, ?, 0, 0, 'Absent', '')
        """, (employee_id, today))
        conn.commit()

        cursor.execute("""
            SELECT * FROM attendance
            WHERE employee_id=? AND date=?
        """, (employee_id, today))
        record = cursor.fetchone()

    message = ""

    if period == "morning":
        if record["morning"] == 1:
            message = "Morning attendance already marked"
        elif current_time <= morning_deadline:
            cursor.execute("""
                UPDATE attendance
                SET morning=1
                WHERE employee_id=? AND date=?
            """, (employee_id, today))
            conn.commit()
            message = "attendace should be mark on time"
        else:
            message = "Morning attendance already marked"

    elif period == "afternoon":
        afternoon_start = "13:45"
        if record["afternoon"] == 1:
            message = "Afternoon attendance already marked"
        elif current_time < afternoon_start:
            message = "you can only mark after 1:45"
        elif current_time <= afternoon_deadline:
            cursor.execute("""
                UPDATE attendance
                SET afternoon=1
                WHERE employee_id=? AND date=?
            """, (employee_id, today))
            conn.commit()
            message = "attendace should be mark on time"
        else:
            message = "the time is over attendance is already marked"

    cursor.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date=?
    """, (employee_id, today))
    updated = cursor.fetchone()

    # New attendance logic
    if updated["morning"] == 1 and updated["afternoon"] == 1:
        status = "Present"
    elif updated["morning"] == 1 or updated["afternoon"] == 1:
        status = "Half Day"
    else:
        status = "Absent"

    cursor.execute("""
        UPDATE attendance
        SET status=?
        WHERE employee_id=? AND date=?
    """, (status, employee_id, today))

    conn.commit()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
       request.headers.get('Accept') == 'application/json':
        return jsonify({"message": message, "status": status})

    return redirect(url_for("attendance_page", msg=message))


# ---------------- API FOR LIVE UPDATES ----------------

@app.route("/api/attendance_status")
def get_attendance_status():
    if session.get("role") != "employee":
        return jsonify({"error": "Unauthorized"}), 401

    employee_id = session.get("employee_id")
    today = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT morning, afternoon, status FROM attendance
        WHERE employee_id=? AND date=?
    """, (employee_id, today))
    record = cursor.fetchone()
    
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    morning_deadline = "10:10"
    afternoon_deadline = "14:10"

    # If no record, calculate what it should be based on deadlines
    if record:
        morning = record["morning"]
        afternoon = record["afternoon"]
        status = record["status"]
    else:
        morning = 0
        afternoon = 0
        if current_time > afternoon_deadline:
            status = "Absent"
        elif current_time > morning_deadline:
            status = "Half Day" # Potentially, if they miss morning
        else:
            status = "Pending"

    conn.close()

    return jsonify({
        "morning": morning,
        "afternoon": afternoon,
        "status": status,
        "current_time": current_time
    })


# ---------------- PROFILE ----------------

@app.route("/employee/profile")
def profile():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    employee_id = session.get("employee_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM employees WHERE employee_id=?",
        (employee_id,)
    )
    employee = cursor.fetchone()

    cursor.execute("""
        SELECT * FROM attendance
        WHERE employee_id=?
        ORDER BY date DESC
    """, (employee_id,))
    records = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE employee_id=? AND status='Present'
    """, (employee_id,))
    present_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE employee_id=? AND status='Half Day'
    """, (employee_id,))
    half_day_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE employee_id=?
    """, (employee_id,))
    total_days = cursor.fetchone()[0]

    # Calculate percentage: (Present + 0.5 * Half Day) / Total
    if total_days > 0:
        attendance_value = present_count + (0.5 * half_day_count)
        percentage = round((attendance_value / total_days) * 100)
    else:
        percentage = 0

    conn.close()

    return render_template(
        "profile.html",
        employee=employee,
        records=records,
        present_count=present_count,
        half_day_count=half_day_count,
        total_days=total_days,
        percentage=percentage
    )


# ---------------- CONTACT ----------------

@app.route("/employee/contact")
def contact():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    return render_template("contact.html")


# ---------------- RUN SERVER ----------------

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)