import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

def check_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(attendance)")
    columns = cursor.fetchall()
    print("--- ATTENDANCE COLUMNS ---")
    for col in columns:
        print(f"Col {col[0]}: {col[1]} ({col[2]})")
    
    cursor.execute("SELECT * FROM attendance LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("\n--- SAMPLE RECORD ---")
        col_names = [c[1] for c in columns]
        record_dict = {name: val for name, val in zip(col_names, row)}
        print(record_dict)
    else:
        print("\nNo records found in attendance table.")
    
    conn.close()

if __name__ == "__main__":
    check_schema()
