from supabase import create_client, Client
from datetime import datetime, timedelta, timezone
import os

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

IST = timezone(timedelta(hours=5, minutes=30))

def test():
    print("--- Time Debug ---")
    now_utc = datetime.now(timezone.utc)
    print(f"UTC Time: {now_utc}")
    
    now_ist = datetime.now(IST)
    print(f"IST Time: {now_ist}")
    print(f"IST Hour:Minute: {now_ist.strftime('%H:%M')}")

    print("\n--- Supabase Debug ---")
    try:
        res = supabase.table("employees").select("*", count="exact").execute()
        print(f"Connection Successful. Employees table found. Count: {res.count}")
    except Exception as e:
        print(f"Error connecting to employees table: {e}")

    try:
        res = supabase.table("attendance").select("*", count="exact").execute()
        print(f"Connection Successful. Attendance table found. Count: {res.count}")
    except Exception as e:
        print(f"Error connecting to attendance table: {e}")

if __name__ == "__main__":
    test()
