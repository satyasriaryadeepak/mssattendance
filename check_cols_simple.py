from supabase import create_client
import os

URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase = create_client(URL, KEY)

def check_cols():
    print("Checking attendance table columns...")
    try:
        res = supabase.table("attendance").select("*").limit(1).execute()
        if res.data:
            print(f"Columns: {list(res.data[0].keys())}")
        else:
            print("No data in attendance table to check columns.")
            
        test_cols = ["morning_time", "afternoon_time"]
        for col in test_cols:
            try:
                supabase.table("attendance").select(col).limit(1).execute()
                print(f"Column '{col}' exists.")
            except Exception as e:
                print(f"Column '{col}' does NOT exist or error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_cols()
