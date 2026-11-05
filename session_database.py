import sqlite3
from datetime import datetime

DB_NAME = "attendance.db"


def initialize_sessions():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS class_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        session_date TEXT NOT NULL,
        session_time TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS session_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Present',

        UNIQUE(session_id, student_id),

        FOREIGN KEY(session_id)
            REFERENCES class_sessions(session_id),

        FOREIGN KEY(student_id)
            REFERENCES students(student_id)
    )
    """)

    conn.commit()
    conn.close()


def create_session(subject):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    now = datetime.now()

    cursor.execute("""
    INSERT INTO class_sessions
    (subject, session_date, session_time)
    VALUES (?, ?, ?)
    """, (
        subject,
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S")
    ))

    session_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return session_id


def mark_session_attendance(session_id, student_id):

    conn = sqlite3.connect("attendance.db")

    try:

        # Verify session exists
        session = conn.execute(
            """
            SELECT subject
            FROM class_sessions
            WHERE session_id = ?
            """,
            (session_id,)
        ).fetchone()

        if session is None:
            print("Invalid class session.")
            return False

        subject = session[0].strip().upper()

        # Verify student exists
        student = conn.execute(
            """
            SELECT student_id
            FROM students
            WHERE student_id = ?
            """,
            (student_id,)
        ).fetchone()

        if student is None:
            print("Student is not registered.")
            return False

        # Verify subject enrollment
        enrollment = conn.execute(
            """
            SELECT id
            FROM student_subjects
            WHERE student_id = ?
            AND subject = ?
            """,
            (student_id, subject)
        ).fetchone()

        if enrollment is None:
            print("Student is not enrolled in this subject.")
            return False

        # Insert attendance
        conn.execute(
            """
            INSERT INTO session_attendance
            (session_id, student_id, status)
            VALUES (?, ?, 'Present')
            """,
            (session_id, student_id)
        )

        conn.commit()

        print("Attendance marked successfully!")
        return True

    except sqlite3.IntegrityError:

        print("Attendance already marked for this session.")
        return False

    finally:
        conn.close()
    

if __name__ == "__main__":

    initialize_sessions()

    print("Session database initialized!")