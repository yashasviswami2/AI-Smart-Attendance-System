import sqlite3
import pandas as pd

DB_NAME = "attendance.db"


def get_attendance_analytics():

    conn = sqlite3.connect(DB_NAME)

    query = """
    SELECT
        s.student_id,
        s.student_name,
        COUNT(cs.session_id) AS total_classes,

        COUNT(sa.session_id) AS attended_classes,

        CASE
            WHEN COUNT(cs.session_id) = 0 THEN 0
            ELSE ROUND(
                COUNT(sa.session_id) * 100.0 /
                COUNT(cs.session_id), 2
            )
        END AS attendance_percentage

    FROM students s

    CROSS JOIN class_sessions cs

    LEFT JOIN session_attendance sa
        ON s.student_id = sa.student_id
        AND cs.session_id = sa.session_id

    GROUP BY s.student_id, s.student_name
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


if __name__ == "__main__":

    import sqlite3
import pandas as pd

DB_NAME = "attendance.db"


def get_attendance_analytics():

    conn = sqlite3.connect(DB_NAME)

    query = """
    SELECT
        s.student_id,
        s.student_name,
        cs.subject,

        COUNT(DISTINCT cs.session_id) AS total_classes,

        COUNT(DISTINCT sa.session_id) AS attended_classes,

        ROUND(
            COUNT(DISTINCT sa.session_id) * 100.0 /
            NULLIF(COUNT(DISTINCT cs.session_id), 0),
            2
        ) AS attendance_percentage

    FROM students s

    CROSS JOIN (
        SELECT DISTINCT subject
        FROM class_sessions
    ) subjects

    JOIN class_sessions cs
        ON cs.subject = subjects.subject

    LEFT JOIN session_attendance sa
        ON sa.student_id = s.student_id
        AND sa.session_id = cs.session_id

    GROUP BY
        s.student_id,
        s.student_name,
        cs.subject

    ORDER BY s.student_name
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


if __name__ == "__main__":

    data = get_attendance_analytics()

    print("\nSUBJECT-WISE ATTENDANCE")

    print(data.to_string(index=False))

    analytics = get_attendance_analytics()

    print("\nATTENDANCE ANALYTICS")

    print(analytics)