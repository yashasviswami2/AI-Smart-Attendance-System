import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Clear old test attendance
cursor.execute("DELETE FROM session_attendance")

# Clear old test sessions
cursor.execute("DELETE FROM class_sessions")

conn.commit()
conn.close()

print("Old test records cleared successfully!")
