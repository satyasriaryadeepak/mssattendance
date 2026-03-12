import sqlite3, csv, io
conn = sqlite3.connect('c:/Users/arya9/OneDrive/Desktop/mssattendance/database.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT date, morning, afternoon, status, logout_time FROM attendance WHERE employee_id='mss01' AND date LIKE '2026-03-%'")
records = c.fetchall()

output = io.StringIO()
writer = csv.writer(output)

writer.writerow(['Monthly Attendance Report'])
writer.writerow(['Employee Name:', 'Test Name'])
writer.writerow(['Employee ID:', 'mss01'])
writer.writerow(['Month:', '2026-03'])
writer.writerow([])
writer.writerow(['Date', 'Morning Status', 'Afternoon Status', 'Final Status', 'Logout Time'])

for row in records:
    morning_val = 'Marked' if row['morning'] == 1 else 'Not Marked'
    afternoon_val = 'Marked' if row['afternoon'] == 1 else 'Not Marked'
    logout_val = row['logout_time'] if row['logout_time'] else 'N/A'
    
    writer.writerow([
        row['date'],
        morning_val,
        afternoon_val,
        row['status'],
        logout_val
    ])

with open('c:/Users/arya9/OneDrive/Desktop/mssattendance/test_output.csv', 'w', newline='') as f:
    f.write(output.getvalue())
print("CSV generated successfully")
