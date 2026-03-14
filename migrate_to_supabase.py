import sqlite3
from supabase import create_client, Client
import os

# --- Configuration ---
SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
DB_PATH = "database.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Starting migration...")

    # 1. Migrate Admins
    print("Migrating Admins...")
    cursor.execute("SELECT * FROM admins")
    admins = cursor.fetchall()
    for admin in admins:
        data = dict(admin)
        # Remove local ID to let Supabase generate its own or keep it if you want
        # Keeping ID if possible to maintain relations, but Serial handles it.
        try:
            supabase.table("admins").upsert({
                "username": data["username"],
                "password": data["password"]
            }).execute()
        except Exception as e:
            print(f"Error migrating admin {data['username']}: {e}")

    # 2. Migrate Employees
    print("Migrating Employees...")
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()
    for emp in employees:
        data = dict(emp)
        try:
            supabase.table("employees").upsert({
                "employee_id": data["employee_id"],
                "name": data["name"],
                "password": data["password"],
                "department": data["department"],
                "status": data["status"]
            }).execute()
        except Exception as e:
            print(f"Error migrating employee {data['employee_id']}: {e}")

    # 3. Migrate Attendance
    print("Migrating Attendance...")
    cursor.execute("SELECT * FROM attendance")
    attendance = cursor.fetchall()
    for att in attendance:
        data = dict(att)
        try:
            supabase.table("attendance").upsert({
                "employee_id": data["employee_id"],
                "date": data["date"],
                "morning": data["morning"],
                "afternoon": data["afternoon"],
                "status": data["status"],
                "logout_time": data["logout_time"]
            }).execute()
        except Exception as e:
            print(f"Error migrating attendance record for {data['employee_id']} on {data['date']}: {e}")

    conn.close()
    print("Migration finished!")

if __name__ == "__main__":
    migrate()
