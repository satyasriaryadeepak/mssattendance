import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Try to fetch one record and see keys
    response = supabase.table("attendance").select("*").limit(1).execute()
    if response.data:
        print("Columns found in attendance table:")
        print(response.data[0].keys())
    else:
        # If no data, try to fetch columns some other way or just print that it's empty
        print("No data in attendance table to inspect columns. Trying a dummy select.")
        # We can try to select specific columns to see if they error
        columns_to_test = ["morning_time", "afternoon_time"]
        for col in columns_to_test:
            try:
                supabase.table("attendance").select(col).limit(1).execute()
                print(f"Column '{col}' EXISTS")
            except Exception as e:
                print(f"Column '{col}' MISSING or error: {e}")
except Exception as e:
    print(f"Error checking columns: {e}")
