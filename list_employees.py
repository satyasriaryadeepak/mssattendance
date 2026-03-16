from supabase import create_client, Client
import os

SUPABASE_URL = "https://ytecwdhmuparsfcuzusm.supabase.co"
SUPABASE_KEY = "sb_publishable_klyKYGGpx1igJqXpb0YV2A_SYm0Asyk"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_emps():
    try:
        res = supabase.table("employees").select("*").execute()
        for emp in res.data:
            print(f"ID: {emp['employee_id']}, Name: {emp['name']}, Password: {emp['password']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_emps()
