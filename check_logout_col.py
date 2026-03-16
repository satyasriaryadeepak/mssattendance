from supabase import create_client

URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase = create_client(URL, KEY)

def check_logout_time():
    print("Checking 'logout_time' column...")
    try:
        supabase.table("attendance").select("logout_time").limit(1).execute()
        print("logout_time: EXISTS")
    except Exception as e:
        print(f"logout_time: MISSING ({e})")

if __name__ == "__main__":
    check_logout_time()
