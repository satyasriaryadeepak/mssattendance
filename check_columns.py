from supabase import create_client, Client
import os

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_columns():
    try:
        # Try to select all columns
        res = supabase.table("attendance").select("*").limit(1).execute()
        if res.data:
            print(f"Columns in database: {res.data[0].keys()}")
        else:
            # Try specific columns to see which one fails
            cols = ["morning_time", "afternoon_time", "logout_time"]
            for col in cols:
                try:
                    supabase.table("attendance").select(col).limit(1).execute()
                    print(f"Column '{col}' EXISTS")
                except Exception as e:
                    print(f"Column '{col}' MISSING: {e}")
    except Exception as e:
        print(f"General error: {e}")

if __name__ == "__main__":
    check_columns()
