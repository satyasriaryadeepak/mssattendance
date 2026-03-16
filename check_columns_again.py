from supabase import create_client

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_columns():
    try:
        # Try to select from attendance table
        res = supabase.table("attendance").select("morning_time, afternoon_time").limit(1).execute()
        print("SUCCESS: 'morning_time' and 'afternoon_time' columns exist.")
    except Exception as e:
        print(f"FAILURE: Columns missing in 'attendance' table. Error: {e}")

if __name__ == "__main__":
    check_columns()
