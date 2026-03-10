from flask import Flask, render_template, request, redirect, url_for, session
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
        return "Invalid admin login"

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
        return "Invalid employee login"

    conn.close()
    return "Invalid login"


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

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

        conn.close()

    # clear login session
    session.clear()

    # redirect to login page
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
            message = "Morning attendance marked successfully"
        else:
            message = "Morning attendance time missed"

    elif period == "afternoon":
        if record["afternoon"] == 1:
            message = "Afternoon attendance already marked"
        elif current_time <= afternoon_deadline:
            cursor.execute("""
                UPDATE attendance
                SET afternoon=1
                WHERE employee_id=? AND date=?
            """, (employee_id, today))
            conn.commit()
            message = "Afternoon attendance marked successfully"
        else:
            message = "Afternoon attendance time missed"

    cursor.execute("""
        SELECT * FROM attendance
        WHERE employee_id=? AND date=?
    """, (employee_id, today))
    updated = cursor.fetchone()

    status = "Present" if updated["morning"] == 1 and updated["afternoon"] == 1 else "Absent"

    cursor.execute("""
        UPDATE attendance
        SET status=?
        WHERE employee_id=? AND date=?
    """, (status, employee_id, today))

    conn.commit()
    conn.close()

    return redirect(url_for("attendance_page", msg=message))


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
    present = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM attendance
        WHERE employee_id=?
    """, (employee_id,))
    total = cursor.fetchone()[0]

    percentage = (present / total * 100) if total > 0 else 0

    conn.close()

    return render_template(
        "profile.html",
        employee=employee,
        records=records,
        percentage=round(percentage, 2)
    )


# ---------------- CONTACT ----------------

@app.route("/employee/contact")
def contact():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    return render_template("contact.html")


# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)