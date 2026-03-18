from supabase import create_client

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check today's records and their time values
res = supabase.table("attendance").select("employee_id, date, morning, morning_time, afternoon, afternoon_time, status").eq("date", "2026-03-17").execute()

print(f"Total records for today: {len(res.data)}")
for r in res.data:
    print(f"  {r['employee_id']} | morning={r['morning']} time={r.get('morning_time')!r} | afternoon={r['afternoon']} time={r.get('afternoon_time')!r} | status={r['status']}")
