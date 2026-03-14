from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client, Client
import os
import math
import csv
import io
from flask import Response
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

def get_now_ist():
    # Use UTC now and convert to IST to be server-agnostic
    return datetime.now(timezone.utc).astimezone(IST)


app = Flask(__name__)
app.secret_key = "mssquare_secret_key"

# --- Supabase Configuration ---
SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Geofencing Configuration ---
OFFICE_LAT = 17.452090
OFFICE_LNG = 78.392460
ALLOWED_RADIUS_METERS = 200

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371000 # Radius of earth in meters
    return c * r

# Sqlite connection legacy (removed)
# def get_db_connection():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn


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

    try:
        if role == "admin":
            response = supabase.table("admins").select("*").eq("username", username).eq("password", password).execute()
            admin = response.data[0] if response.data else None

            if admin:
                session["role"] = "admin"
                session["username"] = admin["username"]
                return redirect(url_for("admin_dashboard"))
            return render_template("login.html", error="Invalid admin login credentials")

        elif role == "employee":
            response = supabase.table("employees").select("*").eq("employee_id", username).eq("password", password).eq("status", "active").execute()
            emp = response.data[0] if response.data else None

            if emp:
                session["role"] = "employee"
                session["employee_id"] = emp["employee_id"]
                session["employee_name"] = emp["name"]
                return redirect(url_for("employee_home"))
            return render_template("login.html", error="Invalid employee login credentials")
            
    except Exception as e:
        print(f"Login Error: {e}", flush=True)
        return render_template("login.html", error="Database connection error. Please ensure you have run the setup_supabase.sql script in your Supabase dashboard.")

    return "Invalid login"


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    if session.get("role") == "employee":
        employee_id = session.get("employee_id")
        today = get_now_ist().strftime("%Y-%m-%d")
        logout_time = get_now_ist().strftime("%H:%M:%S")

        response = supabase.table("attendance").select("*").eq("employee_id", employee_id).eq("date", today).execute()
        record = response.data[0] if response.data else None

        if record:
            supabase.table("attendance").update({"logout_time": logout_time}).eq("employee_id", employee_id).eq("date", today).execute()
            print(f"DEBUG: Logout recorded for {employee_id}", flush=True)

    session.clear()
    return redirect(url_for("home"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    today = get_now_ist().strftime("%Y-%m-%d")

    total_employees_resp = supabase.table("employees").select("*", count="exact").eq("status", "active").execute()
    total_employees = total_employees_resp.count

    present_today_resp = supabase.table("attendance").select("*", count="exact").eq("date", today).eq("status", "Present").execute()
    present_today = present_today_resp.count

    absent_today_resp = supabase.table("attendance").select("*", count="exact").eq("date", today).eq("status", "Absent").execute()
    absent_today = absent_today_resp.count

    return render_template(
        "admin_dashboard.html",
        total_employees=total_employees,
        present_today=present_today,
        absent_today=absent_today
    )



# ---------------- DATA RESCUE ----------------
@app.route("/admin/download_db")
def download_db():
    if session.get("role") != "admin":
        return redirect(url_for("home"))
    from flask import send_file
    import os
    db_path = os.path.join(app.root_path, "database.db")
    if os.path.exists(db_path):
        return send_file(db_path, as_attachment=True, download_name="live_database.db")
    return "Database not found."

# ---------------- MANAGE ADMINS ----------------

@app.route("/admin/admins")
def manage_admins():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    search = request.args.get("search", "").strip()

    query = supabase.table("admins").select("*").order("id", desc=False)
    if search:
        query = query.ilike("username", f"%{search}%")
    
    response = query.execute()
    admins = response.data

    return render_template("manage_admins.html", admins=admins, search=search)


@app.route("/admin/add_admin", methods=["POST"])
def add_admin():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    username = request.form["username"].strip()
    password = request.form["password"].strip()

    try:
        supabase.table("admins").insert({"username": username, "password": password}).execute()
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return "Admin username already exists"
        return f"Error: {str(e)}"

    return redirect(url_for("manage_admins"))


@app.route("/admin/delete_admin/<int:id>")
def delete_admin(id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    supabase.table("admins").delete().eq("id", id).execute()

    return redirect(url_for("manage_admins"))


@app.route("/admin/reset_admin_password/<int:id>", methods=["POST"])
def reset_admin_password(id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))
    
    new_password = request.form.get("new_password", "").strip()
    if new_password:
        supabase.table("admins").update({"password": new_password}).eq("id", id).execute()
    
    return redirect(url_for("manage_admins"))


# ---------------- MANAGE EMPLOYEES ----------------

@app.route("/admin/employees")
def manage_employees():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    search = request.args.get("search", "").strip()

    query = supabase.table("employees").select("*").order("id", desc=True)
    if search:
        query = query.or_(f"employee_id.ilike.%{search}%,name.ilike.%{search}%")
    
    response = query.execute()
    employees = response.data

    return render_template("manage_employees.html", employees=employees, search=search)


@app.route("/admin/add_employee", methods=["POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    emp_id = request.form["employee_id"].strip()
    name = request.form["name"].strip()
    password = request.form["password"].strip()
    department = request.form["department"].strip()

    try:
        supabase.table("employees").insert({
            "employee_id": emp_id,
            "name": name,
            "password": password,
            "department": department,
            "status": "active"
        }).execute()
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return "Employee ID already exists"
        return f"Error: {str(e)}"

    return redirect(url_for("manage_employees"))


@app.route("/admin/delete_employee/<int:id>")
def delete_employee(id):
    if session.get("role") != "admin" :
        return redirect(url_for("home"))

    try:
        # Get employee_id because attendance table references employee_id (TEXT), not id (INT)
        emp_resp = supabase.table("employees").select("employee_id").eq("id", id).execute()
        if emp_resp.data:
            employee_id = emp_resp.data[0]["employee_id"]
            # Delete linked attendance records first to avoid Foreign Key violation
            supabase.table("attendance").delete().eq("employee_id", employee_id).execute()
        
        # Now delete the employee
        supabase.table("employees").delete().eq("id", id).execute()
    except Exception as e:
        print(f"Error deleting employee: {e}", flush=True)
        return f"Error: Could not delete employee. {str(e)}", 500

    return redirect(url_for("manage_employees"))


@app.route("/admin/reset_password/<int:id>", methods=["POST"])
def reset_password(id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))
    
    new_password = request.form.get("new_password", "").strip()
    if new_password:
        supabase.table("employees").update({"password": new_password}).eq("id", id).execute()
    
    return redirect(url_for("manage_employees"))


# ---------------- ADMIN REPORTS ----------------

@app.route("/admin/reports")
def attendance_reports():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    # Get all records with employee names using inner join (handled by supabase relation)
    response = supabase.table("attendance").select("*, employees(name)").order("date", desc=True).order("id", desc=True).execute()
    records = response.data

    # Flatten names for compatibility with templates
    for r in records:
        if r.get('employees'):
            r['name'] = r['employees'].get('name')

    # Get active employees for the download dropdown
    emp_resp = supabase.table("employees").select("employee_id, name").eq("status", "active").order("name").execute()
    employees = emp_resp.data
    
    return render_template("attendance_reports.html", records=records, employees=employees)


@app.route("/admin/edit_attendance/<int:id>", methods=["POST"])
def edit_attendance(id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    morning = int(request.form.get("morning", 0))
    afternoon = int(request.form.get("afternoon", 0))
    morning_time = request.form.get("morning_time", "").strip()
    afternoon_time = request.form.get("afternoon_time", "").strip()
    logout_time = request.form.get("logout_time", "").strip()

    # Recalculate status
    if morning == 1 and afternoon == 1:
        status = "Present"
    elif morning == 1 or afternoon == 1:
        status = "Half Day"
    else:
        status = "Absent"

    try:
        supabase.table("attendance").update({
            "morning": morning,
            "afternoon": afternoon,
            "morning_time": morning_time,
            "afternoon_time": afternoon_time,
            "logout_time": logout_time,
            "status": status
        }).eq("id", id).execute()
    except Exception as e:
        print(f"Error editing attendance: {e}", flush=True)

    return redirect(url_for("attendance_reports"))


@app.route("/admin/download_report")
def download_report():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    employee_id = request.args.get("employee_id")
    month_str = request.args.get("month") # format YYYY-MM
    
    if not employee_id or not month_str:
        return "Missing employee ID or month", 400

    # Get employee details
    emp_resp = supabase.table("employees").select("name").eq("employee_id", employee_id).execute()
    emp = emp_resp.data[0] if emp_resp.data else None
    
    if not emp:
        return "Employee not found", 404
        
    emp_name = emp["name"]

    # Fetch records for that employee where the date starts with the selected YYYY-MM
    start_date = f"{month_str}-01"
    # To use ilike for month pattern:
    records_resp = supabase.table("attendance").select("date, morning, afternoon, status, logout_time").eq("employee_id", employee_id).ilike("date", f"{month_str}-%").order("date", desc=False).execute()
    records = records_resp.data

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write Header row
    writer.writerow(['Monthly Attendance Report'])
    writer.writerow(['Employee Name:', emp_name])
    writer.writerow(['Employee ID:', employee_id])
    writer.writerow(['Month:', month_str])
    writer.writerow([]) # Empty row for spacing
    writer.writerow(['Date', 'Morning Status', 'Afternoon Status', 'Final Status', 'Logout Time'])
    
    # Write data rows
    for row in records:
        morning_val = 'Marked' if row['morning'] == 1 else 'Not Marked'
        afternoon_val = 'Marked' if row['afternoon'] == 1 else 'Not Marked'
        logout_val = row['logout_time'] if row['logout_time'] else 'N/A'
        
        # Format date for better Excel compatibility
        raw_date = str(row['date'])
        try:
            parsed_date = datetime.strptime(raw_date, "%Y-%m-%d").strftime("%d %b %Y")
        except:
            parsed_date = raw_date
        
        writer.writerow([
            parsed_date,
            morning_val,
            afternoon_val,
            row['status'],
            logout_val
        ])

    # Convert to response (add UTF-8 BOM for Excel)
    csv_data = "\ufeff" + output.getvalue()
    filename = f"Attendance_{employee_id}_{month_str}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )


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
    today = get_now_ist().strftime("%Y-%m-%d")
    msg = request.args.get("msg", "")

    # Get attendance record
    att_resp = supabase.table("attendance").select("*").eq("employee_id", employee_id).eq("date", today).execute()
    record = att_resp.data[0] if att_resp.data else None

    # Get employee details
    emp_resp = supabase.table("employees").select("*").eq("employee_id", employee_id).execute()
    employee = emp_resp.data[0] if emp_resp.data else None

    return render_template(
        "attendance.html",
        record=record,
        employee=employee,
        msg=msg
    )


@app.route("/employee/mark_attendance", methods=["POST"])
def mark_attendance():
    if session.get("role") != "employee":
        return redirect(url_for("home"))

    employee_id = session.get("employee_id")
    period = request.form["period"]
    
    now = get_now_ist()
    if now.weekday() == 6: # Sunday
        return jsonify({"message": "Today is Sunday, a holiday", "status": "Error"}), 400
    
    # Geolocation check
    lat = request.form.get("lat")
    lng = request.form.get("lng")
    
    if not lat or not lng:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return jsonify({"message": "Location access is required to mark attendance.", "status": "Error"}), 400
        return redirect(url_for("attendance_page", msg="Location required!"))

    try:
        user_lat = float(lat)
        user_lng = float(lng)
    except ValueError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return jsonify({"message": "Invalid location coordinates.", "status": "Error"}), 400
        return redirect(url_for("attendance_page", msg="Invalid location!"))

    distance = haversine(OFFICE_LAT, OFFICE_LNG, user_lat, user_lng)
    print(f"DEBUG: Office ({OFFICE_LAT}, {OFFICE_LNG}) | User ({user_lat}, {user_lng}) | Distance: {distance}m", flush=True)
    
    if distance > ALLOWED_RADIUS_METERS:
        err_msg = f"You are {int(distance)} meters away. (User: {user_lat}, {user_lng}). You must be within {ALLOWED_RADIUS_METERS} meters of the office."
        map_url = f"https://www.google.com/maps/search/?api=1&query={OFFICE_LAT},{OFFICE_LNG}"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return jsonify({"message": err_msg, "status": "OutOfRange", "map_url": map_url}), 403
        return redirect(url_for("attendance_page", msg=err_msg))

    now = get_now_ist()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    morning_deadline = "10:10"
    afternoon_deadline = "14:10"

    # Check for existing record
    try:
        att_resp = supabase.table("attendance").select("*").eq("employee_id", employee_id).eq("date", today).execute()
        record = att_resp.data[0] if att_resp.data else None
    except Exception as e:
        print(f"Supabase Error: {e}", flush=True)
        error_msg = "Database connection error. Please ensure tables are created."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept') == 'application/json':
            return jsonify({"message": error_msg, "status": "Error"}), 500
        return redirect(url_for("attendance_page", msg=error_msg))

    if not record:
        try:
            record_resp = supabase.table("attendance").insert({
                "employee_id": employee_id,
                "date": today,
                "morning": 0,
            "afternoon": 0,
            "morning_time": "",
            "afternoon_time": "",
            "status": "Absent",
            "logout_time": ""
        }).execute()
            record = record_resp.data[0]
        except Exception as e:
            print(f"Supabase Insert Error: {e}", flush=True)
            return "Database Error: Could not initialize attendance record.", 500

    message = ""
    # Convert "HH:MM" to integer for robust comparison
    val_now = now.hour * 100 + now.minute
    
    # Deadlines as integers: 10:10 -> 1010, 14:10 -> 1410, 13:45 -> 1345
    morning_deadline_val = 1010
    afternoon_start_val = 1345
    afternoon_deadline_val = 1410

    if period == "morning":
        if record["morning"] == 1:
            message = "Morning attendance already marked"
        elif val_now <= morning_deadline_val:
            supabase.table("attendance").update({
                "morning": 1,
                "morning_time": now.strftime("%H:%M:%S")
            }).eq("employee_id", employee_id).eq("date", today).execute()
            message = "attendance marked"
            record["morning"] = 1
        else:
            message = "Morning attendance already marked"

    elif period == "afternoon":
        if record["afternoon"] == 1:
            message = "Afternoon attendance already marked"
        elif val_now < afternoon_start_val:
            message = "mark after 1:45pm"
        elif val_now <= afternoon_deadline_val:
            supabase.table("attendance").update({
                "afternoon": 1,
                "afternoon_time": now.strftime("%H:%M:%S")
            }).eq("employee_id", employee_id).eq("date", today).execute()
            message = "attendance marked"
            record["afternoon"] = 1
        else:
            message = "attendance marked already"

    # New attendance logic
    if record["morning"] == 1 and record["afternoon"] == 1:
        status = "Present"
    elif record["morning"] == 1 or record["afternoon"] == 1:
        status = "Half Day"
    else:
        status = "Absent"

    supabase.table("attendance").update({"status": status}).eq("employee_id", employee_id).eq("date", today).execute()

    return redirect(url_for("attendance_page", msg=message))


# ---------------- API FOR LIVE UPDATES ----------------

@app.route("/api/attendance_status")
def get_attendance_status():
    if session.get("role") != "employee":
        return jsonify({"error": "Unauthorized"}), 401

    employee_id = session.get("employee_id")
    today = get_now_ist().strftime("%Y-%m-%d")

    # Get attendance record
    att_resp = supabase.table("attendance").select("morning, afternoon, status").eq("employee_id", employee_id).eq("date", today).execute()
    record = att_resp.data[0] if att_resp.data else None
    
    now = get_now_ist()
    if now.weekday() == 6: # Sunday
        return jsonify({
            "morning": 0,
            "afternoon": 0,
            "status": "Holiday (Sunday)",
            "message": "Today is Sunday, a holiday"
        })

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

    # Get employee details
    emp_resp = supabase.table("employees").select("*").eq("employee_id", employee_id).execute()
    employee = emp_resp.data[0] if emp_resp.data else None

    # Get attendance records
    att_resp = supabase.table("attendance").select("*").eq("employee_id", employee_id).order("date", desc=True).execute()
    records = att_resp.data

    # Aggregate statistics
    present_resp = supabase.table("attendance").select("*", count="exact").eq("employee_id", employee_id).eq("status", "Present").execute()
    present_count = present_resp.count

    half_day_resp = supabase.table("attendance").select("*", count="exact").eq("employee_id", employee_id).eq("status", "Half Day").execute()
    half_day_count = half_day_resp.count

    total_days_resp = supabase.table("attendance").select("*", count="exact").eq("employee_id", employee_id).execute()
    total_days = total_days_resp.count

    # Calculate percentage: (Present + 0.5 * Half Day) / Total
    if total_days > 0:
        attendance_value = present_count + (0.5 * half_day_count)
        percentage = round((attendance_value / total_days) * 100)
    else:
        percentage = 0

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