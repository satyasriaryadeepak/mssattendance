from supabase import create_client

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_holidays_table():
    try:
        # Try to select from holidays table
        res = supabase.table("holidays").select("*").limit(1).execute()
        print("SUCCESS: 'holidays' table exists and is accessible.")
        print(f"Data: {res.data}")
    except Exception as e:
        print(f"FAILURE: Could not access 'holidays' table. Error: {e}")

if __name__ == "__main__":
    check_holidays_table()
