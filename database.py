import sqlite3
from datetime import datetime

# Connect to database
connection = sqlite3.connect("attendance.db")

cursor = connection.cursor()

# Create students table
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY,
    student_name TEXT NOT NULL
)
""")

# Create attendance table
cursor.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    student_name TEXT,
    attendance_date TEXT,
    attendance_time TEXT,
    status TEXT DEFAULT 'Present',
    FOREIGN KEY(student_id) REFERENCES students(student_id),
    UNIQUE(student_id, attendance_date)
)
""")

connection.commit()


# Register student
def register_student(student_id, student_name):

    cursor.execute("""
    INSERT OR IGNORE INTO students
    (student_id, student_name)
    VALUES (?, ?)
    """, (student_id, student_name))

    connection.commit()


# Mark attendance
def mark_attendance(student_id, student_name):

    now = datetime.now()

    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")

    try:
        cursor.execute("""
        INSERT INTO attendance
        (student_id, student_name,
         attendance_date, attendance_time)
        VALUES (?, ?, ?, ?)
        """, (student_id, student_name, date, time))

        connection.commit()

        print("\nAttendance marked successfully!")
        print("Student:", student_name)
        print("ID:", student_id)
        print("Date:", date)
        print("Time:", time)

    except sqlite3.IntegrityError:

        print("\nAttendance already marked today!")


# Display attendance
def view_attendance():

    cursor.execute("""
    SELECT * FROM attendance
    ORDER BY attendance_date DESC
    """)

    records = cursor.fetchall()

    print("\n========== ATTENDANCE RECORDS ==========")

    for record in records:
        print(record)


# Close database connection
def close_database():

    connection.close()


# Main execution
if __name__ == "__main__":

    register_student(1521, "Yashasvi")

    mark_attendance(1521, "Yashasvi")

    view_attendance()

    close_database()