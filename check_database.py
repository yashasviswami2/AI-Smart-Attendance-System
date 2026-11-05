import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

print("\nCLASS SESSIONS:")
cursor.execute("SELECT * FROM class_sessions")
for row in cursor.fetchall():
    print(row)

print("\nSESSION ATTENDANCE:")
cursor.execute("SELECT * FROM session_attendance")
for row in cursor.fetchall():
    print(row)

print("\nREGISTERED STUDENTS:")
cursor.execute("SELECT * FROM students")
for row in cursor.fetchall():
    print(row)

conn.close()