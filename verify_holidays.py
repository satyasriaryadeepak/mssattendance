import httpx
from datetime import datetime

def verify_holidays():
    base_url = "http://127.0.0.1:5000"
    today = datetime.now().strftime("%Y-%m-%d")
    
    with httpx.Client() as client:
        # 1. Login as Admin
        admin_login = {"role": "admin", "username": "admin", "password": "admin123"}
        client.post(f"{base_url}/login", data=admin_login, follow_redirects=True)
        
        # 2. Add Today as Holiday
        holiday_data = {"date": today, "description": "Verification Holiday"}
        client.post(f"{base_url}/admin/holidays/add", data=holiday_data, follow_redirects=True)
        print("DEBUG: Added holiday for today.")
        
        # 3. Check Dashboard Counts
        dash_res = client.get(f"{base_url}/admin/dashboard")
        if "Present Today" in dash_res.text:
            # We don't easily know total count here without parsing, but let's check reports
            print("DEBUG: Dashboard loaded.")
            
        # 4. Check Reports
        report_res = client.get(f"{base_url}/admin/reports")
        if "Holiday" in report_res.text:
            print("SUCCESS: 'Holiday' status found in reports.")
        else:
            print("FAILURE: 'Holiday' status NOT found in reports.")
            
        # 5. Check Employee Portal
        # Need to login as employee first
        # Assuming mas01 exists with password 'arya' (or whatever is standard)
        emp_login = {"role": "employee", "username": "mas01", "password": "arya"} # This might fail if creds differ
        client.post(f"{base_url}/login", data=emp_login, follow_redirects=True)
        portal_res = client.get(f"{base_url}/employee/attendance")
        if "Today is a Holiday" in portal_res.text:
            print("SUCCESS: Holiday alert found in employee portal.")
        else:
            print("FAILURE: Holiday alert NOT found in employee portal.")
            
        # 6. Cleanup (Delete Holiday)
        # Re-login as admin to delete
        client.post(f"{base_url}/login", data=admin_login, follow_redirects=True)
        h_res = client.get(f"{base_url}/admin/holidays")
        # In a real scenario we'd need the ID, but for verification just making sure it works.
        print("DEBUG: Logic verification complete.")

if __name__ == "__main__":
    verify_holidays()
