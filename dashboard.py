import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date
from auth import (
    verify_user,
    initialize_auth_db,
    create_user,
    get_all_users,
    delete_user,
    initialize_subject_allocation,
    assign_subject,
    get_faculty_subjects,
    get_all_allocations,
    initialize_student_subjects,
    enroll_student,
    get_student_subjects,
    get_all_student_enrollments
)

# =====================================
# PAGE CONFIGURATION
# =====================================

st.set_page_config(
    page_title="AI Smart Attendance",
    page_icon="🎓",
    layout="wide"
)

# Initialize authentication database
initialize_auth_db()
initialize_subject_allocation()
initialize_student_subjects()

# Initialize login session
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "role" not in st.session_state:
    st.session_state.role = None


# LOGIN PAGE
if not st.session_state.logged_in:

    st.title("🔐 AI Smart Attendance System")
    st.subheader("Login Portal")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        login_button = st.form_submit_button("Login")

    if login_button:
        role = verify_user(username.strip(), password)

        if role:
            st.session_state.logged_in = True
            st.session_state.username = username.strip()
            st.session_state.role = role

            st.success("Login successful!")
            st.rerun()

        else:
            st.error("Invalid username or password.")

    st.stop()


# LOGGED-IN USER DETAILS
st.sidebar.success(
    f"Logged in as: {st.session_state.username}"
)

st.sidebar.info(
    f"Role: {st.session_state.role.upper()}"
)

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

# =====================================
# CUSTOM CSS
# =====================================

st.markdown("""
<style>
.main {
    background-color: #f5f7fb;
}

[data-testid="stMetric"] {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}

h1 {
    color: #243b64;
}

h2, h3 {
    color: #344767;
}
</style>
""", unsafe_allow_html=True)


# =====================================
# DATABASE CONNECTION
# =====================================

def get_connection():
    return sqlite3.connect("attendance.db")


# =====================================
# FETCH STUDENT DATA
# =====================================
# =====================================
# FETCH ENROLLMENT-BASED ATTENDANCE DATA
# =====================================

def get_attendance_data():

    conn = get_connection()

    query = """
    WITH subject_totals AS (

        SELECT
            UPPER(TRIM(subject)) AS subject,
            COUNT(*) AS total_classes

        FROM class_sessions

        GROUP BY UPPER(TRIM(subject))
    )

    SELECT
        s.student_id,
        s.student_name,
        ss.subject,

        COALESCE(st.total_classes, 0) AS total_classes,

        COUNT(DISTINCT
            CASE
                WHEN sa.status = 'Present'
                THEN cs.session_id
            END
        ) AS attended_classes,

        ROUND(
            COUNT(DISTINCT
                CASE
                    WHEN sa.status = 'Present'
                    THEN cs.session_id
                END
            ) * 100.0 /
            NULLIF(COALESCE(st.total_classes, 0), 0),
            2
        ) AS attendance_percentage

    FROM student_subjects ss

    JOIN students s
        ON s.student_id = ss.student_id

    LEFT JOIN subject_totals st
        ON st.subject = ss.subject

    LEFT JOIN class_sessions cs
        ON UPPER(TRIM(cs.subject)) = ss.subject

    LEFT JOIN session_attendance sa
        ON sa.session_id = cs.session_id
        AND sa.student_id = s.student_id

    GROUP BY
        s.student_id,
        s.student_name,
        ss.subject,
        st.total_classes

    ORDER BY
        s.student_name,
        ss.subject
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


# =====================================
# FETCH ATTENDANCE HISTORY
# =====================================

def get_attendance_history():

    conn = get_connection()

    query = """
    SELECT
        s.student_id,
        s.student_name,
        cs.subject,
        cs.session_date,
        cs.session_time,
        sa.status

    FROM session_attendance sa

    JOIN students s
        ON sa.student_id = s.student_id

    JOIN class_sessions cs
        ON sa.session_id = cs.session_id

    ORDER BY
        cs.session_date DESC,
        cs.session_time DESC
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


# =====================================
# SIDEBAR
# =====================================

st.sidebar.title("🎓 AI Attendance")

# ROLE-BASED NAVIGATION

# ROLE-BASED NAVIGATION

if st.session_state.role == "admin":

    pages = [
        "Dashboard",
        "Live Faculty Panel",
        "Student Reports",
        "Attendance History",
        "Low Attendance Alerts",
        "Faculty Management",
        "Subject Allocation",
        "Student Enrollment"
    ]

else:

    pages = [
        "Dashboard",
        "My Subjects",
        "Live Faculty Panel",
        "Attendance History"
    ]

page = st.sidebar.radio("Navigation", pages)

# =====================================
# LOAD DATA
# =====================================

# =====================================
# LOAD ROLE-BASED DATA
# =====================================

attendance_df = get_attendance_data()
history_df = get_attendance_history()

conn = get_connection()

if st.session_state.role == "faculty":

    # Get subjects assigned to logged-in faculty
    assigned_subjects = get_faculty_subjects(
        st.session_state.username
    )

    # Restrict attendance data
    attendance_df = attendance_df[
        attendance_df["subject"].isin(assigned_subjects)
    ]

    history_df = history_df[
        history_df["subject"].isin(assigned_subjects)
    ]

    # Calculate faculty-specific metrics
    total_students = attendance_df["student_id"].nunique()

    total_classes = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM class_sessions
        WHERE subject IN (
            SELECT subject
            FROM faculty_subjects
            WHERE faculty_username = ?
        )
        """,
        conn,
        params=(st.session_state.username,)
    ).iloc[0]["total"]

    total_present = history_df[
        history_df["status"] == "Present"
    ].shape[0]

else:

    total_students = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM students",
        conn
    ).iloc[0]["total"]

    total_classes = pd.read_sql_query(
        "SELECT COUNT(*) AS total FROM class_sessions",
        conn
    ).iloc[0]["total"]

    total_present = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM session_attendance
        WHERE status = 'Present'
        """,
        conn
    ).iloc[0]["total"]

conn.close()


# =====================================
# DASHBOARD PAGE
# =====================================

if page == "Dashboard":

    st.title("🎓 AI Smart Attendance Dashboard")

    st.write(
        "Monitor student attendance, subject performance "
        "and academic participation."
    )

    st.markdown("---")

    # KPI CARDS

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Students", total_students)

    col2.metric("Total Classes", total_classes)

    col3.metric("Present Records", total_present)

    if not attendance_df.empty:
        avg_attendance = attendance_df[
            "attendance_percentage"
        ].mean()
    else:
        avg_attendance = 0

    col4.metric(
        "Average Attendance",
        f"{avg_attendance:.2f}%"
    )

    st.markdown("---")

    if not attendance_df.empty:

        # SUBJECT FILTER

        subjects = ["All"] + sorted(
            attendance_df["subject"].unique().tolist()
        )

        selected_subject = st.selectbox(
            "Select Subject",
            subjects
        )

        if selected_subject != "All":
            filtered_df = attendance_df[
                attendance_df["subject"] == selected_subject
            ]
        else:
            filtered_df = attendance_df

        # ATTENDANCE CHART

        st.subheader("📊 Student Attendance Analysis")

        fig = px.bar(
            filtered_df,
            x="student_name",
            y="attendance_percentage",
            color="subject",
            barmode="group",
            text="attendance_percentage",
            title="Subject-wise Attendance Percentage"
        )

        fig.update_layout(
            yaxis_title="Attendance (%)",
            xaxis_title="Students",
            yaxis_range=[0, 110]
        )

        st.plotly_chart(fig, use_container_width=True)

        # DATA TABLE

        st.subheader("📋 Attendance Overview")

        st.dataframe(
            filtered_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No attendance data available yet.")


# =====================================
# STUDENT REPORTS
# =====================================

elif page == "Student Reports":

    st.title("👩‍🎓 Student Reports")

    if not attendance_df.empty:

        student_options = attendance_df[
            ["student_id", "student_name"]
        ].drop_duplicates()

        selected_student = st.selectbox(
            "Select Student",
            student_options["student_id"],
            format_func=lambda x: (
                student_options.loc[
                    student_options["student_id"] == x,
                    "student_name"
                ].iloc[0]
                + f" ({x})"
            )
        )

        student_df = attendance_df[
            attendance_df["student_id"] == selected_student
        ]

        st.subheader("Subject-wise Performance")

        st.dataframe(
            student_df,
            use_container_width=True,
            hide_index=True
        )

        fig = px.pie(
            student_df,
            names="subject",
            values="attended_classes",
            title="Attended Classes by Subject"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:

        st.info("No student records available.")


# =====================================
# ATTENDANCE HISTORY
# =====================================

elif page == "Attendance History":

    st.title("📅 Attendance History")

    if not history_df.empty:

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True
        )

        csv = history_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download Attendance CSV",
            csv,
            "attendance_history.csv",
            "text/csv"
        )

    else:

        st.info("No attendance history available.")


# =====================================
# LOW ATTENDANCE ALERTS
# =====================================

elif page == "Low Attendance Alerts":

    st.title("⚠️ Low Attendance Alerts")

    threshold = st.slider(
        "Minimum Required Attendance (%)",
        min_value=50,
        max_value=100,
        value=75
    )

    if not attendance_df.empty:

        low_df = attendance_df[
            attendance_df["attendance_percentage"] < threshold
        ]

        if not low_df.empty:

            st.error(
                f"{len(low_df)} student-subject records "
                f"are below {threshold}% attendance."
            )

            st.dataframe(
                low_df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.success(
                "All student-subject records meet the attendance threshold!"
            )

    else:

        st.info("No attendance data available.")

# =====================================
# LIVE FACULTY PANEL
# =====================================
# =====================================
# LIVE FACULTY PANEL
# =====================================

elif page == "Live Faculty Panel":

    st.title("🎓 Live Faculty Attendance Panel")

    st.write(
        "Monitor student attendance for individual class sessions."
    )

    if st.button("🔄 Refresh Attendance"):
        st.rerun()

    conn = get_connection()

    # Get available sessions based on user role

    if st.session_state.role == "admin":

        sessions_df = pd.read_sql_query("""
            SELECT
                session_id,
                subject,
                session_date,
                session_time
            FROM class_sessions
            ORDER BY session_id DESC
        """, conn)

    else:

        sessions_df = pd.read_sql_query(
            """
            SELECT
                cs.session_id,
                cs.subject,
                cs.session_date,
                cs.session_time
            FROM class_sessions cs
            INNER JOIN faculty_subjects fs
                ON UPPER(TRIM(cs.subject)) = fs.subject
            WHERE fs.faculty_username = ?
            ORDER BY cs.session_id DESC
            """,
            conn,
            params=(st.session_state.username,)
        )

    if sessions_df.empty:

        st.info("No class sessions available.")
        conn.close()

    else:

        selected_session = st.selectbox(
            "Select Class Session",
            sessions_df["session_id"],
            format_func=lambda x: (
                sessions_df.loc[
                    sessions_df["session_id"] == x,
                    "subject"
                ].iloc[0]
                + " | Session "
                + str(x)
            )
        )

        session_info = sessions_df[
            sessions_df["session_id"] == selected_session
        ].iloc[0]

        # Get all registered students
                # Get only students enrolled in this session's subject

                # Get only students enrolled in this session's subject

        students_df = pd.read_sql_query(
            """
            SELECT
                s.student_id,
                s.student_name
            FROM student_subjects ss
            JOIN students s
                ON ss.student_id = s.student_id
            WHERE ss.subject = ?
            ORDER BY s.student_name
            """,
            conn,
            params=(session_info["subject"].strip().upper(),)
        )

        # Get attendance for selected session

        present_df = pd.read_sql_query(
            """
            SELECT
                s.student_id,
                s.student_name,
                sa.status
            FROM session_attendance sa
            JOIN students s
                ON sa.student_id = s.student_id
            WHERE sa.session_id = ?
            """,
            conn,
            params=(int(selected_session),)
        )

        conn.close()

        total = len(students_df)

        present_ids = set(
            present_df.loc[
                present_df["status"] == "Present",
                "student_id"
            ]
        )

        eligible_ids = set(students_df["student_id"])

        # Get only students enrolled in this session's subject

        # Get only students enrolled in this session's subject

        students_df = pd.read_sql_query(
            """
            SELECT
                s.student_id,
                s.student_name
            FROM student_subjects ss
            JOIN students s
                ON ss.student_id = s.student_id
            WHERE ss.subject = ?
            ORDER BY s.student_name
            """,
            conn,
            params=(session_info["subject"].strip().upper(),)
        )

        # Get attendance for selected session

        present_df = pd.read_sql_query(
            """
            SELECT
                s.student_id,
                s.student_name,
                sa.status
            FROM session_attendance sa
            JOIN students s
                ON sa.student_id = s.student_id
            WHERE sa.session_id = ?
            """,
            conn,
            params=(int(selected_session),)
        )

        conn.close()

        total = len(students_df)

        present_ids = set(
            present_df.loc[
                present_df["status"] == "Present",
                "student_id"
            ]
        )

        eligible_ids = set(students_df["student_id"])

        present = len(present_ids.intersection(eligible_ids))

        absent = total - present

        percentage = (
            (present / total) * 100
            if total > 0 else 0
        )

        st.subheader(
            f"Subject: {session_info['subject']}"
        )

        st.write(
            f"Date: {session_info['session_date']}"
        )

        st.write(
            f"Time: {session_info['session_time']}"
        )

        # Attendance metrics

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Students", total)
        col2.metric("Present", present)
        col3.metric("Absent", absent)

        col4.metric(
            "Attendance",
            f"{percentage:.2f}%"
        )

        st.markdown("---")

        # Progress bar

        st.subheader("📊 Session Progress")

        st.progress(
            int(percentage) / 100
        )

        # Merge student list with attendance

        report_df = students_df.merge(
            present_df,
            on=["student_id", "student_name"],
            how="left"
        )

        report_df["status"] = (
            report_df["status"].fillna("Absent")
        )

        st.subheader("👩‍🎓 Student Attendance Register")

        st.dataframe(
            report_df,
            use_container_width=True,
            hide_index=True
        )

        # Download report

        csv = report_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "📥 Download Session Report",
            csv,
            f"session_{selected_session}_attendance.csv",
            "text/csv"
        )

# =====================================
# FACULTY MANAGEMENT
# =====================================

elif page == "Faculty Management":

    if st.session_state.role != "admin":
        st.error("Access denied. Admin privileges required.")
        st.stop()

    st.title("👩‍🏫 Faculty Management")

    st.write("Create and manage faculty accounts.")

    st.markdown("---")

    # ADD FACULTY
    st.subheader("➕ Create Faculty Account")

    with st.form("add_faculty_form"):

        new_username = st.text_input("Faculty Username")
        new_password = st.text_input(
            "Password",
            type="password"
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password"
        )

        create_button = st.form_submit_button(
            "Create Faculty Account"
        )

    if create_button:

        if not new_username.strip():
            st.error("Username cannot be empty.")

        elif len(new_password) < 8:
            st.error("Password must contain at least 8 characters.")

        elif new_password != confirm_password:
            st.error("Passwords do not match.")

        else:

            success = create_user(
                new_username.strip(),
                new_password,
                "faculty"
            )

            if success:
                st.success("Faculty account created successfully!")
                st.rerun()

            else:
                st.error("Username already exists.")

    st.markdown("---")

    # VIEW USERS
    st.subheader("📋 Registered Users")

    users = get_all_users()

    if users:

        users_df = pd.DataFrame(
            users,
            columns=["Username", "Role"]
        )

        st.dataframe(
            users_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No registered users found.")

    st.markdown("---")

    # DELETE FACULTY
    st.subheader("🗑️ Remove Faculty Account")

    faculty_users = [
        username
        for username, role in users
        if role == "faculty"
    ]

    if faculty_users:

        selected_faculty = st.selectbox(
            "Select Faculty",
            faculty_users
        )

        confirm_delete = st.checkbox(
            "I confirm that I want to delete this faculty account."
        )

        if st.button("Delete Faculty Account"):

            if confirm_delete:

                if delete_user(selected_faculty):
                    st.success("Faculty account deleted successfully!")
                    st.rerun()

                else:
                    st.error("Unable to delete faculty account.")

            else:
                st.warning("Please confirm before deleting.")

    else:
        st.info("No faculty accounts available to delete.")
# =====================================
# FACULTY SUBJECT ALLOCATION
# =====================================

elif page == "Subject Allocation":

    if st.session_state.role != "admin":
        st.error("Admin access required.")
        st.stop()

    st.title("📚 Faculty Subject Allocation")

    st.write(
        "Assign academic subjects to registered faculty members."
    )

    st.markdown("---")

    # GET FACULTY USERS
    all_users = get_all_users()

    faculty_list = [
        username
        for username, role in all_users
        if role == "faculty"
    ]

    # GET SUBJECTS FROM DATABASE
    conn = get_connection()

    subjects_df = pd.read_sql_query(
        """
        SELECT DISTINCT subject
        FROM class_sessions
        WHERE subject IS NOT NULL
        ORDER BY subject
        """,
        conn
    )

    conn.close()

    subjects = subjects_df["subject"].tolist()

    # ASSIGN SUBJECT
    st.subheader("➕ Assign Subject")

    if faculty_list and subjects:

        with st.form("subject_allocation_form"):

            selected_faculty = st.selectbox(
                "Select Faculty",
                faculty_list
            )

            selected_subject = st.selectbox(
                "Select Subject",
                subjects
            )

            assign_button = st.form_submit_button(
                "Assign Subject"
            )

        if assign_button:

            success = assign_subject(
                selected_faculty,
                selected_subject
            )

            if success:
                st.success("Subject assigned successfully!")
                st.rerun()

            else:
                st.warning(
                    "This subject is already assigned "
                    "or the faculty account is invalid."
                )

    elif not faculty_list:

        st.warning("Create a faculty account first.")

    else:

        st.warning(
            "No subjects found. Create a class session first "
            "to register a subject."
        )

    st.markdown("---")

    # VIEW ALLOCATIONS
    st.subheader("📋 Current Subject Allocations")

    allocations = get_all_allocations()

    if allocations:

        allocation_df = pd.DataFrame(
            allocations,
            columns=["Faculty Username", "Assigned Subject"]
        )

        st.dataframe(
            allocation_df,
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "Total Allocations",
            len(allocations)
        )

    else:

        st.info("No subjects have been assigned yet.")
# =====================================
# FACULTY MY SUBJECTS
# =====================================

elif page == "My Subjects":

    st.title("📚 My Assigned Subjects")

    faculty_username = st.session_state.username

    assigned_subjects = get_faculty_subjects(
        faculty_username
    )

    if assigned_subjects:

        st.success(
            f"You have {len(assigned_subjects)} assigned subjects."
        )

        for subject in assigned_subjects:

            st.markdown(
                f"### 📖 {subject}"
            )

            conn = get_connection()

            subject_data = pd.read_sql_query(
                """
                SELECT
                    COUNT(DISTINCT cs.session_id) AS total_classes,
                    COUNT(DISTINCT
                        CASE
                            WHEN sa.status = 'Present'
                            THEN sa.session_id
                        END
                    ) AS attended_classes
                FROM class_sessions cs
                LEFT JOIN session_attendance sa
                    ON cs.session_id = sa.session_id
                WHERE cs.subject = ?
                AND sa.student_id IN (
                    SELECT student_id FROM students
                )
                """,
                conn,
                params=(subject,)
            )

            conn.close()

            total = int(subject_data.iloc[0]["total_classes"])
            attended = int(subject_data.iloc[0]["attended_classes"])

            col1, col2, col3 = st.columns(3)

            col1.metric("Total Classes", total)
            col2.metric("Present Records", attended)

            percentage = (
                attended / total * 100
                if total > 0 else 0
            )

            col3.metric(
                "Attendance Activity",
                f"{percentage:.2f}%"
            )

            st.markdown("---")

    else:

        st.warning(
            "No subjects have been assigned to your account yet. "
            "Please contact the administrator."
        )
# =====================================
# STUDENT ENROLLMENT MANAGEMENT
# =====================================

elif page == "Student Enrollment":

    if st.session_state.role != "admin":
        st.error("Admin access required.")
        st.stop()

    st.title("🎓 Student Enrollment Management")

    st.write("Enroll students in their respective subjects.")

    st.markdown("---")

    conn = get_connection()

    # Fetch registered students
    students_df = pd.read_sql_query("""
        SELECT student_id, student_name
        FROM students
        ORDER BY student_name
    """, conn)

    # Fetch available subjects
    subjects_df = pd.read_sql_query("""
        SELECT DISTINCT UPPER(TRIM(subject)) AS subject
        FROM class_sessions
        WHERE subject IS NOT NULL
        AND TRIM(subject) != ''
        ORDER BY subject
    """, conn)

    conn.close()

    subjects = subjects_df["subject"].tolist()

    # =================================
    # ENROLL STUDENT
    # =================================

    st.subheader("➕ Enroll Student")

    if not students_df.empty and subjects:

        with st.form("student_enrollment_form"):

            selected_student = st.selectbox(
                "Select Student",
                students_df["student_id"],
                format_func=lambda x: (
                    students_df.loc[
                        students_df["student_id"] == x,
                        "student_name"
                    ].iloc[0] + f" ({x})"
                )
            )

            selected_subject = st.selectbox(
                "Select Subject",
                subjects
            )

            enroll_button = st.form_submit_button(
                "Enroll Student"
            )

        if enroll_button:

            success = enroll_student(
                int(selected_student),
                selected_subject
            )

            if success:
                st.success("Student enrolled successfully!")
                st.rerun()

            else:
                st.warning(
                    "Student is already enrolled "
                    "or the enrollment could not be completed."
                )

    elif students_df.empty:

        st.warning("Register students before enrolling them.")

    else:

        st.warning(
            "No subjects found. Create a class session first."
        )

    st.markdown("---")

    # =================================
    # VIEW ENROLLMENTS
    # =================================

    st.subheader("📋 Student Enrollment Records")

    enrollments = get_all_student_enrollments()

    if enrollments:

        enrollment_df = pd.DataFrame(
            enrollments,
            columns=[
                "Student ID",
                "Student Name",
                "Subject"
            ]
        )

        st.dataframe(
            enrollment_df,
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "Total Enrollments",
            len(enrollments)
        )

        csv = enrollment_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "📥 Download Enrollment Records",
            csv,
            "student_enrollments.csv",
            "text/csv"
        )

    else:

        st.info("No student enrollments available yet.")

# =====================================
# FOOTER
# =====================================

st.sidebar.markdown("---")
st.sidebar.caption("AI Smart Attendance System | Version 2.0")