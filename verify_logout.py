from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
import os

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

IST = timezone(timedelta(hours=5, minutes=30))

def check_logout():
    today = datetime.now(timezone.utc).astimezone(IST).strftime("%Y-%m-%d")
    try:
        res = supabase.table("attendance").select("logout_time").eq("employee_id", "INTM2601").eq("date", today).execute()
        if res.data:
            print(f"Logout time for today: {res.data[0]['logout_time']}")
        else:
            print("No record for today")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_logout()
