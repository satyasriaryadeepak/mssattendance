from supabase import create_client

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch all records where morning_time was set to '09:00:00' by the previous script
res = supabase.table("attendance").select("id, employee_id, date").eq("morning_time", "09:00:00").execute()

print(f"Found {len(res.data)} records to clear.")
for r in res.data:
    supabase.table("attendance").update({"morning_time": ""}).eq("id", r["id"]).execute()
    print(f"  Cleared morning_time for {r['employee_id']} on {r['date']}")

print("\nDone! All fallback 09:00:00 morning times have been cleared to empty strings.")
