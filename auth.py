import sqlite3
import hashlib
import secrets
import hmac
from getpass import getpass

DB_NAME = "attendance.db"
ITERATIONS = 200000


# =====================================
# DATABASE INITIALIZATION
# =====================================

def initialize_auth_db():
    """Create the users table if it does not already exist."""
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'faculty'))
            )
        """)
        conn.commit()
    finally:
        conn.close()


def initialize_subject_allocation():
    """Create the faculty-to-subject allocation table."""
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS faculty_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_username TEXT NOT NULL,
                subject TEXT NOT NULL,
                UNIQUE(faculty_username, subject),
                FOREIGN KEY(faculty_username)
                    REFERENCES users(username)
                    ON DELETE CASCADE
            )
        """)
        conn.commit()
    finally:
        conn.close()


def initialize_student_subjects():
    """Create the student-to-subject enrollment table."""
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS student_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                UNIQUE(student_id, subject),
                FOREIGN KEY(student_id)
                    REFERENCES students(student_id)
                    ON DELETE CASCADE
            )
        """)
        conn.commit()
    finally:
        conn.close()


# =====================================
# USER MANAGEMENT
# =====================================

def create_user(username, password, role):
    """Create an admin or faculty account with a salted password hash."""
    username = username.strip()

    if not username:
        print("Username cannot be empty.")
        return False

    if role not in ("admin", "faculty"):
        print("Invalid role.")
        return False

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return False

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )

    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, salt, role)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash.hex(), salt.hex(), role)
        )
        conn.commit()
        print(f"{role.title()} account created successfully!")
        return True
    except sqlite3.IntegrityError:
        print("Username already exists.")
        return False
    finally:
        conn.close()


def verify_user(username, password):
    """Return the user's role if credentials are valid; otherwise None."""
    conn = sqlite3.connect(DB_NAME)
    try:
        user = conn.execute(
            """
            SELECT password_hash, salt, role
            FROM users
            WHERE username = ?
            """,
            (username.strip(),)
        ).fetchone()
    finally:
        conn.close()

    if user is None:
        return None

    stored_hash, salt, role = user
    entered_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS
    ).hex()

    if hmac.compare_digest(stored_hash, entered_hash):
        return role

    return None


def get_all_users():
    """Return all usernames and roles."""
    conn = sqlite3.connect(DB_NAME)
    try:
        return conn.execute("""
            SELECT username, role
            FROM users
            ORDER BY role, username
        """).fetchall()
    finally:
        conn.close()


def delete_user(username):
    """Delete a faculty account and its subject allocations; never delete admins."""
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            "DELETE FROM faculty_subjects WHERE faculty_username = ?",
            (username,)
        )
        cursor = conn.execute(
            """
            DELETE FROM users
            WHERE username = ? AND role = 'faculty'
            """,
            (username,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


# =====================================
# FACULTY SUBJECT ALLOCATION
# =====================================

def assign_subject(faculty_username, subject):
    """Assign a subject to an existing faculty account."""
    if not subject or not subject.strip():
        return False

    conn = sqlite3.connect(DB_NAME)
    try:
        user = conn.execute(
            "SELECT role FROM users WHERE username = ?",
            (faculty_username,)
        ).fetchone()

        if user is None or user[0] != "faculty":
            return False

        conn.execute(
            """
            INSERT INTO faculty_subjects (faculty_username, subject)
            VALUES (?, ?)
            """,
            (faculty_username, subject.strip().upper())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_faculty_subjects(faculty_username):
    """Return the subjects assigned to one faculty account."""
    conn = sqlite3.connect(DB_NAME)
    try:
        rows = conn.execute(
            """
            SELECT subject
            FROM faculty_subjects
            WHERE faculty_username = ?
            ORDER BY subject
            """,
            (faculty_username,)
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def get_all_allocations():
    """Return all faculty-subject allocations."""
    conn = sqlite3.connect(DB_NAME)
    try:
        return conn.execute("""
            SELECT faculty_username, subject
            FROM faculty_subjects
            ORDER BY faculty_username, subject
        """).fetchall()
    finally:
        conn.close()


# =====================================
# STUDENT SUBJECT ENROLLMENT
# =====================================

def enroll_student(student_id, subject):
    """Enroll an existing student in a subject."""
    if not subject or not subject.strip():
        return False

    conn = sqlite3.connect(DB_NAME)
    try:
        student = conn.execute(
            "SELECT student_id FROM students WHERE student_id = ?",
            (student_id,)
        ).fetchone()

        if student is None:
            return False

        conn.execute(
            """
            INSERT INTO student_subjects (student_id, subject)
            VALUES (?, ?)
            """,
            (student_id, subject.strip().upper())
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_student_subjects(student_id):
    """Return the subjects in which one student is enrolled."""
    conn = sqlite3.connect(DB_NAME)
    try:
        rows = conn.execute(
            """
            SELECT subject
            FROM student_subjects
            WHERE student_id = ?
            ORDER BY subject
            """,
            (student_id,)
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def get_all_student_enrollments():
    """Return all student-subject enrollment records."""
    conn = sqlite3.connect(DB_NAME)
    try:
        return conn.execute("""
            SELECT
                ss.student_id,
                s.student_name,
                ss.subject
            FROM student_subjects ss
            JOIN students s
                ON ss.student_id = s.student_id
            ORDER BY s.student_name, ss.subject
        """).fetchall()
    finally:
        conn.close()


# =====================================
# MAIN PROGRAM: CREATE AN ACCOUNT
# =====================================

if __name__ == "__main__":
    initialize_auth_db()
    initialize_subject_allocation()
    initialize_student_subjects()

    print("\n===== CREATE USER ACCOUNT =====")
    username = input("Enter username: ").strip()
    role = input("Enter role (admin/faculty): ").strip().lower()
    password = getpass("Enter password: ")
    confirm_password = getpass("Confirm password: ")

    if not username:
        print("Username cannot be empty.")
    elif password != confirm_password:
        print("Passwords do not match.")
    elif len(password) < 8:
        print("Password must contain at least 8 characters.")
    else:
        create_user(username, password, role)
