import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Correct subject capitalization
cursor.execute("""
UPDATE class_sessions
SET subject = 'DAA'
WHERE LOWER(subject) = 'daa'
""")

# Remove empty test sessions
cursor.execute("""
DELETE FROM class_sessions
WHERE NOT EXISTS (
    SELECT 1
    FROM session_attendance
    WHERE session_attendance.session_id = class_sessions.session_id
)
""")

conn.commit()

print("Subject names corrected!")
print("Empty test sessions removed!")

conn.close()