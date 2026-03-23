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
# Prioritize environment variables, fallback to hardcoded keys
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ytecwdhmuparsfcuzusm.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk")

print(f"DEBUG: Initializing Supabase with URL: {SUPABASE_URL}", flush=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("DEBUG: Supabase client initialized", flush=True)

def is_holiday(date_str):
    """Check if a date is a holiday. Fails gracefully if table missing."""
    try:
        res = supabase.table("holidays").select("*").eq("date", date_str).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        # Silently fail if table doesn't exist yet
        return None

# --- Attendance Configuration ---
OFFICE_LAT = 17.452069
OFFICE_LNG = 78.392615
OFFICE_RANGE_METERS = 40

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth."""
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371000 # Radius of earth in meters. Use 3956 for miles
    return c * r

# Sqlite connection legacy (removed)
# def get_db_connection():
#     conn = sqlite3.connect(DB_PATH)
#     conn.row_factory = sqlite3.Row
#     return conn


# ---------------- HOME ----------------

@app.route("/")
def home():
    print("DEBUG: Home route hit", flush=True)
    return render_template("login.html")

@app.route("/health")
def health():
    return {"status": "healthy"}, 200


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
    record_logout = request.args.get("record") == "1"
    if record_logout and session.get("role") == "employee":
        employee_id = session.get("employee_id")
        now = get_now_ist()
        today = now.strftime("%Y-%m-%d")
        logout_time_str = now.strftime("%H:%M:%S")

        # Use select("*") to find the record
        response = supabase.table("attendance").select("*").eq("employee_id", employee_id).eq("date", today).execute()
        record = response.data[0] if response.data else None

        if record:
            supabase.table("attendance").update({"logout_time": logout_time_str}).eq("employee_id", employee_id).eq("date", today).execute()
        else:
            # Create a record if none exists
            init_data = {
                "employee_id": employee_id,
                "date": today,
                "morning": 0,
                "afternoon": 0,
                "morning_time": "-",
                "afternoon_time": "-",
                "status": "Absent",
                "logout_time": logout_time_str
            }
            supabase.table("attendance").insert(init_data).execute()
            
        print(f"DEBUG: Logout recorded for {employee_id} at {logout_time_str}", flush=True)

    session.clear()
    return redirect(url_for("home"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    today = get_now_ist().strftime("%Y-%m-%d")
    
    # Check if today is a holiday
    holiday = is_holiday(today)

    total_employees_resp = supabase.table("employees").select("*", count="exact").eq("status", "active").execute()
    total_employees = total_employees_resp.count

    if holiday:
        present_today = total_employees
    else:
        try:
            present_today_resp = supabase.table("attendance").select("*", count="exact").eq("date", today).in_("status", ["Present", "Half Day"]).execute()
            present_today = present_today_resp.count
        except:
            present_today = 0

    # Absent is total active employees minus those currently marked Present
    absent_today = total_employees - present_today

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


# ---------------- MANAGE HOLIDAYS ----------------

@app.route("/admin/holidays")
def manage_holidays():
    if session.get("role") != "admin":
        return redirect(url_for("home"))
    
    holidays_data = supabase.table("holidays").select("*").order("date", desc=True).execute().data
    return render_template("manage_holidays.html", holidays=holidays_data)

@app.route("/admin/holidays/add", methods=["POST"])
def add_holiday():
    if session.get("role") != "admin":
        return redirect(url_for("home"))
        
    date_val = request.form.get("date")
    description = request.form.get("description")
    
    if date_val:
        supabase.table("holidays").insert({"date": date_val, "description": description}).execute()
        
    return redirect(url_for("manage_holidays"))

@app.route("/admin/holidays/delete/<id>")
def delete_holiday(id):
    if session.get("role") != "admin":
        return redirect(url_for("home"))
        
    supabase.table("holidays").delete().eq("id", id).execute()
    return redirect(url_for("manage_holidays"))


# ---------------- ADMIN REPORTS ----------------

@app.route("/admin/reports")
def attendance_reports():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    today = get_now_ist().strftime("%Y-%m-%d")

    # Accept a ?date= query param; validate and fall back to today if invalid
    selected_date = request.args.get("date", today).strip()
    try:
        datetime.strptime(selected_date, "%Y-%m-%d")
    except ValueError:
        selected_date = today
    
    # Check holiday for the selected date
    holiday = is_holiday(selected_date)
    
    # Check if selected date is a Sunday
    selected_dt = datetime.strptime(selected_date, "%Y-%m-%d")
    is_sunday = selected_dt.weekday() == 6
    
    # Get all active employees
    emp_resp = supabase.table("employees").select("employee_id, name").eq("status", "active").order("name").execute()
    all_employees = emp_resp.data if emp_resp.data else []
    
    # Get attendance records for the selected date
    att_resp = supabase.table("attendance").select("*").eq("date", selected_date).execute()
    att_map = {a["employee_id"]: a for a in att_resp.data} if att_resp.data else {}

    # Merge: ensure every active employee is represented
    final_records = []
    for emp in all_employees:
        eid = emp["employee_id"]
        if eid in att_map:
            record = att_map[eid]
            record["name"] = emp["name"]
            if holiday:
                record["status"] = "Holiday"
            final_records.append(record)
        else:
            # Virtual record logic
            if is_sunday:
                status_val = "Present"
            elif holiday:
                status_val = "Holiday"
            else:
                status_val = "Absent"

            final_records.append({
                "id": None,
                "employee_id": eid,
                "name": emp["name"],
                "date": selected_date,
                "morning": 0,
                "afternoon": 0,
                "morning_time": "-",
                "afternoon_time": "-",
                "status": status_val,
                "logout_time": "-"
            })

    # Finalize status for report display:
    # morning-only records are stored as "Present" live, but finalize to "Half Day"
    # if the afternoon deadline has passed (or if it's a past date entirely).
    now_ist = get_now_ist()
    afternoon_deadline_str = "14:10"
    is_past_day = (selected_date < today)
    afternoon_passed = is_past_day or (now_ist.strftime("%H:%M") > afternoon_deadline_str)

    for r in final_records:
        if r["morning"] == 1 and r["afternoon"] == 0 and afternoon_passed:
            r["status"] = "Half Day"

    return render_template(
        "attendance_reports.html",
        records=final_records,
        employees=all_employees,
        selected_date=selected_date,
        today=today
    )


@app.route("/admin/save_attendance", methods=["POST"])
def save_attendance():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    employee_id = request.form.get("employee_id")
    date = request.form.get("date")
    morning = int(request.form.get("morning", 0))
    afternoon = int(request.form.get("afternoon", 0))
    morning_time = request.form.get("morning_time", "").strip()
    afternoon_time = request.form.get("afternoon_time", "").strip()
    logout_time = request.form.get("logout_time", "").strip()
    # Preserve the date the admin was viewing so we redirect back to it
    selected_date = request.form.get("selected_date", "").strip()

    # Recalculate status
    if morning == 1 and afternoon == 1:
        status = "Present"
    elif morning == 1 or afternoon == 1:
        status = "Half Day"
    else:
        status = "Absent"

    try:
        data = {
            "employee_id": employee_id,
            "date": date,
            "morning": morning,
            "afternoon": afternoon,
            "morning_time": morning_time,
            "afternoon_time": afternoon_time,
            "logout_time": logout_time,
            "status": status
        }
        
        # Explicit check-then-act logic instead of upsert to avoid schema cache issues
        existing = supabase.table("attendance").select("id").eq("employee_id", employee_id).eq("date", date).execute()
        
        print(f"DEBUG Admin Save: {employee_id} on {date} - Morning: {morning} Afternoon: {afternoon}", flush=True)
        if existing.data:
            supabase.table("attendance").update(data).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.table("attendance").insert(data).execute()
            
    except Exception as e:
        print(f"Error saving attendance: {e}", flush=True)

    # Redirect back to the same date the admin was viewing
    redirect_date = selected_date if selected_date else date
    return redirect(url_for("attendance_reports", date=redirect_date))


@app.route("/admin/edit_attendance/<int:id>", methods=["POST"])
def edit_attendance(id):
    # This route is now legacy but kept for potential direct calls
    return save_attendance()


@app.route("/admin/download_report")
def download_report():
    if session.get("role") != "admin":
        return redirect(url_for("home"))

    employee_id = request.args.get("employee_id")
    month_str = request.args.get("month")  # format YYYY-MM

    if not employee_id or not month_str:
        return "Missing employee ID or month", 400

    try:
        # Get employee details
        emp_resp = supabase.table("employees").select("name").eq("employee_id", employee_id).execute()
        emp = emp_resp.data[0] if emp_resp.data else None

        if not emp:
            return "Employee not found", 404

        emp_name = emp["name"]

        # Calculate first and last day of the selected month for gte/lte range filter
        # (ilike does not work on Supabase date-type columns)
        import calendar
        year, month = int(month_str.split("-")[0]), int(month_str.split("-")[1])
        start_date = f"{month_str}-01"
        last_day = calendar.monthrange(year, month)[1]
        end_date = f"{month_str}-{last_day:02d}"
        # Get earliest attendance date as "created day"
        first_rec_resp = (
            supabase.table("attendance")
            .select("date")
            .eq("employee_id", employee_id)
            .order("date", desc=False)
            .limit(1)
            .execute()
        )
        first_date_str = first_rec_resp.data[0]["date"] if first_rec_resp.data else end_date

        records_resp = (
            supabase.table("attendance")
            .select("date, morning, afternoon, morning_time, afternoon_time, status, logout_time")
            .eq("employee_id", employee_id)
            .gte("date", start_date)
            .lte("date", end_date)
            .order("date", desc=False)
            .execute()
        )
        existing_records = {row['date']: row for row in records_resp.data} if records_resp.data else {}

        # Fetch holidays for the month
        holidays_resp = (
            supabase.table("holidays")
            .select("date, description")
            .gte("date", start_date)
            .lte("date", end_date)
            .execute()
        )
        holidays_map = {h['date']: h['description'] for h in holidays_resp.data} if holidays_resp.data else {}

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header rows
        writer.writerow(['Monthly Attendance Report'])
        writer.writerow(['Employee Name:', emp_name])
        writer.writerow(['Employee ID:', employee_id])
        writer.writerow(['Month:', month_str])
        writer.writerow([])  # Empty row for spacing
        writer.writerow(['Date', 'Morning Status', 'Morning Time', 'Afternoon Status', 'Afternoon Time', 'Final Status', 'Logout Time'])

        # Generate all dates for the month
        for day in range(1, last_day + 1):
            date_obj = datetime(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")
            
            # Skip dates before the employee's "created day"
            if date_str < first_date_str:
                continue

            weekday = date_obj.weekday()  # 0=Monday, 6=Sunday

            if date_str in existing_records:
                # Existing record from DB
                row = existing_records[date_str]
                morning_val = 'Marked' if row.get('morning') == 1 else 'Not Marked'
                afternoon_val = 'Marked' if row.get('afternoon') == 1 else 'Not Marked'
                morning_time_val = row.get('morning_time') or 'N/A'
                afternoon_time_val = row.get('afternoon_time') or 'N/A'
                status_val = row.get('status', 'N/A')
                logout_val = row.get('logout_time') or 'N/A'
            else:
                # Virtual record logic
                morning_val = 'N/A'
                afternoon_val = 'N/A'
                morning_time_val = 'N/A'
                afternoon_time_val = 'N/A'
                logout_val = 'N/A'

                if weekday == 6: # Sunday
                    status_val = 'Present'
                elif date_str in holidays_map:
                    status_val = 'Holiday'
                else:
                    status_val = 'Absent'

            # Format date for better Excel compatibility
            formatted_date = date_obj.strftime("%d %b %Y")

            writer.writerow([
                formatted_date,
                morning_val,
                morning_time_val,
                afternoon_val,
                afternoon_time_val,
                status_val,
                logout_val
            ])

        # Convert to response (add UTF-8 BOM for Excel compatibility)
        csv_data = "\ufeff" + output.getvalue()
        filename = f"Attendance_{employee_id}_{month_str}.csv"

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        print(f"Report Download Error: {e}", flush=True)
        return f"Server Error while generating report: {str(e)}", 500


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
        return jsonify({"message": "Unauthorized", "status": "Error"}), 401

    try:
        employee_id = session.get("employee_id")
        period = request.form.get("period")
        lat = request.form.get("lat")
        lng = request.form.get("lng")
        
        now = get_now_ist()
        today = now.strftime("%Y-%m-%d")
        
        # 1. Sunday Check
        if now.weekday() == 6: # Sunday
            return jsonify({"message": "Today is Sunday. You are automatically marked as Present.", "status": "Error"}), 400
        
        # 2. Geolocation Check
        if not lat or not lng:
            return jsonify({"message": "Location access is required to mark attendance.", "status": "Error"}), 400
            
        try:
            user_lat = float(lat)
            user_lng = float(lng)
            distance = calculate_distance(user_lat, user_lng, OFFICE_LAT, OFFICE_LNG)
            
            print(f"DEBUG: User Location: {user_lat}, {user_lng} | Distance: {distance:.2f}m", flush=True)
            
            if distance > OFFICE_RANGE_METERS:
                office_map_url = f"https://www.google.com/maps/search/?api=1&query={OFFICE_LAT},{OFFICE_LNG}"
                return jsonify({
                    "message": f"You are out of range ({distance:.1f}m). Please be within {OFFICE_RANGE_METERS}m of the office.",
                    "status": "OutOfRange",
                    "distance": distance,
                    "map_url": office_map_url
                }), 400
        except ValueError:
            return jsonify({"message": "Invalid location data received.", "status": "Error"}), 400

        # 3. Get or Initialize record
        att_resp = supabase.table("attendance").select("*").eq("employee_id", employee_id).eq("date", today).execute()
        record = att_resp.data[0] if att_resp.data else None

        if not record:
            # Upsert into attendance to ensure initial record exists
            init_data = {
                "employee_id": employee_id,
                "date": today,
                "morning": 0,
                "afternoon": 0,
                "morning_time": "",
                "afternoon_time": "",
                "status": "Absent",
                "logout_time": ""
            }
            record_resp = supabase.table("attendance").insert(init_data).execute()
            if not record_resp.data:
                print(f"DEBUG Error: Failed to initialize attendance for {employee_id} on {today}", flush=True)
                return jsonify({"message": "Failed to initialize attendance record.", "status": "Error"}), 500
            print(f"DEBUG: Initialized attendance record for {employee_id} - {today}", flush=True)
            record = record_resp.data[0]

        # 4. Marking Logic
        val_now = now.hour * 100 + now.minute
        morning_deadline_val = 1010
        afternoon_start_val = 1345
        afternoon_deadline_val = 1410
        
        update_data = {}
        message = ""
        success = True

        if period == "morning":
            if record["morning"] == 1:
                message = "Morning attendance already marked"
                success = False
            elif val_now <= morning_deadline_val:
                update_data["morning"] = 1
                update_data["morning_time"] = now.strftime("%H:%M:%S")
                message = "Morning attendance marked"
                record["morning"] = 1
            else:
                message = "Morning attendance deadline (10:10 AM) has passed"
                success = False

        elif period == "afternoon":
            if record["afternoon"] == 1:
                message = "Afternoon attendance already marked"
                success = False
            elif val_now < afternoon_start_val:
                message = "Please mark after 1:45 PM"
                success = False
            elif val_now <= afternoon_deadline_val:
                update_data["afternoon"] = 1
                update_data["afternoon_time"] = now.strftime("%H:%M:%S")
                message = "Afternoon attendance marked"
                record["afternoon"] = 1
            else:
                message = "Afternoon attendance deadline (2:10 PM) has passed"
                success = False
        else:
            return jsonify({"message": "Invalid period", "status": "Error"}), 400

        # 5. Perform Update and Status Calculation
        if update_data:
            # Status logic:
            # Both marked     → Present
            # Morning only    → Present (live; finalizes to Half Day after afternoon deadline)
            # Afternoon only  → Half Day
            # Neither         → Absent
            if record["morning"] == 1 and record["afternoon"] == 1:
                status = "Present"
            elif record["morning"] == 1 and record["afternoon"] == 0:
                status = "Present"  # Live status; becomes Half Day at end of day
            elif record["morning"] == 0 and record["afternoon"] == 1:
                status = "Half Day"
            else:
                status = "Absent"
            
            update_data["status"] = status
            print(f"DEBUG: Updating attendance for {employee_id} on {today} with {update_data}", flush=True)
            supabase.table("attendance").update(update_data).eq("employee_id", employee_id).eq("date", today).execute()

        return jsonify({
            "message": message, 
            "status": "Success" if success else "Error",
            "morning": record["morning"],
            "afternoon": record["afternoon"]
        }), 200 if success else 400

    except Exception as e:
        print(f"Attendance Marking Error: {e}", flush=True)
        return jsonify({"message": f"Server Error: {str(e)}", "status": "Error"}), 500


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
            "morning": 1, 
            "afternoon": 1,
            "status": "Present",
            "message": "Today is Sunday. You are automatically marked as Present."
        })

    current_time = now.strftime("%H:%M")
    morning_deadline = "10:10"
    afternoon_deadline = "14:10"

    if record:
        morning = record["morning"]
        afternoon = record["afternoon"]
        # Finalize morning-only to Half Day if afternoon deadline has passed
        if morning == 1 and afternoon == 0 and current_time > afternoon_deadline:
            status = "Half Day"
        else:
            status = record["status"]
    else:
        morning = 0
        afternoon = 0
        if current_time > afternoon_deadline:
            status = "Absent"
        elif current_time > morning_deadline:
            status = "Absent"  # Missed morning mark window
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
    now = get_now_ist()
    today_str = now.strftime("%Y-%m-%d")
    year = now.year
    month = now.month
    
    # Get employee details
    emp_resp = supabase.table("employees").select("*").eq("employee_id", employee_id).execute()
    employee = emp_resp.data[0] if emp_resp.data else None

    # Calculate month range
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-{last_day:02d}"

    # Get attendance records for the month
    att_resp = (
        supabase.table("attendance")
        .select("*")
        .eq("employee_id", employee_id)
        .gte("date", start_date)
        .lte("date", end_date)
        .execute()
    )
    existing_records = {row['date']: row for row in att_resp.data} if att_resp.data else {}

    # Get holidays for the month
    holidays_resp = (
        supabase.table("holidays")
        .select("date, description")
        .gte("date", start_date)
        .lte("date", end_date)
        .execute()
    )
    holidays_map = {h['date']: h['description'] for h in holidays_resp.data} if holidays_resp.data else {}

    # Get earliest attendance date as "created day"
    first_rec_resp = (
        supabase.table("attendance")
        .select("date")
        .eq("employee_id", employee_id)
        .order("date", desc=False)
        .limit(1)
        .execute()
    )
    first_date_str = first_rec_resp.data[0]["date"] if first_rec_resp.data else today_str

    # Generate merged records list (from MAX(1st of month, first_date) to today)
    merged_records = []
    current_day = now.day
    
    present_count = 0
    half_day_count = 0
    total_days = 0 

    # Loop from 1 to current_day to show report up to today
    for d in range(1, current_day + 1):
        date_obj = datetime(year, month, d)
        d_str = date_obj.strftime("%Y-%m-%d")
        
        # Skip dates before the employee's "created day"
        if d_str < first_date_str:
            continue
            
        weekday = date_obj.weekday() # 0=Mon, 6=Sun
        
        total_days += 1
        
        if d_str in existing_records:
            rec = existing_records[d_str]
            status = rec.get("status", "Absent")
            merged_records.append({
                "date": d_str,
                "morning_time": rec.get("morning_time", "-"),
                "afternoon_time": rec.get("afternoon_time", "-"),
                "logout_time": rec.get("logout_time", "-"),
                "status": status
            })
            if status == "Present":
                present_count += 1
            elif status == "Half Day":
                half_day_count += 1
        else:
            # Virtual record
            if weekday == 6: # Sunday
                status = "Present"
                present_count += 1
            elif d_str in holidays_map:
                status = "Holiday" # Usually treated as present in some systems, but we'll show Holiday
                # present_count += 1 # Uncomment if holidays count as present
            else:
                status = "Absent"
                
            merged_records.append({
                "date": d_str,
                "morning_time": "-",
                "afternoon_time": "-",
                "logout_time": "-",
                "status": status
            })

    # Sort records descending (newest first)
    merged_records.sort(key=lambda x: x['date'], reverse=True)

    # Calculate percentage
    if total_days > 0:
        attendance_value = present_count + (0.5 * half_day_count)
        percentage = round((attendance_value / total_days) * 100)
    else:
        percentage = 0

    return render_template(
        "profile.html",
        employee=employee,
        records=merged_records,
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

# Already imported os at the top

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting server on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)