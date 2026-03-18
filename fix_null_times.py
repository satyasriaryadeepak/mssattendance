"""
Fix script: Backfill null morning_time / afternoon_time for records where
morning=1 or afternoon=1 but the time column is null.
Sets a placeholder time so the reports show something meaningful.
"""
from supabase import create_client

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch all records where morning=1 but morning_time is null
morning_null = supabase.table("attendance").select("id, employee_id, date, morning_time, afternoon_time, morning, afternoon") \
    .eq("morning", 1).is_("morning_time", "null").execute()

print(f"Records with morning=1 but morning_time=null: {len(morning_null.data)}")
for r in morning_null.data:
    supabase.table("attendance").update({"morning_time": "09:00:00"}).eq("id", r["id"]).execute()
    print(f"  Fixed morning_time for {r['employee_id']} on {r['date']}")

# Fetch all records where afternoon=1 but afternoon_time is null
afternoon_null = supabase.table("attendance").select("id, employee_id, date, afternoon_time, afternoon") \
    .eq("afternoon", 1).is_("afternoon_time", "null").execute()

print(f"\nRecords with afternoon=1 but afternoon_time=null: {len(afternoon_null.data)}")
for r in afternoon_null.data:
    supabase.table("attendance").update({"afternoon_time": "13:45:00"}).eq("id", r["id"]).execute()
    print(f"  Fixed afternoon_time for {r['employee_id']} on {r['date']}")

print("\nDone! All null times have been backfilled.")
