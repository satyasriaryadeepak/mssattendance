import sqlite3
conn = sqlite3.connect('c:/Users/arya9/OneDrive/Desktop/mssattendance/database.db')
c = conn.cursor()
c.execute("SELECT date FROM attendance WHERE date IS NULL OR date = ''")
print("Empty dates:", c.fetchall())
