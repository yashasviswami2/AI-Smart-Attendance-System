import cv2
import mediapipe as mp
import json
import random
import time
import sqlite3

from database import register_student

from session_database import (
    initialize_sessions,
    create_session,
    mark_session_attendance
)


# =====================================
# CONFIGURATION
# =====================================

DB_NAME = "attendance.db"

CONFIDENCE_THRESHOLD = 65
REQUIRED_FRAMES = 8
CHALLENGE_TIMEOUT = 30


# =====================================
# LOAD FACE RECOGNITION MODEL
# =====================================

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read("models/face_model.yml")

with open("models/student_details.json", "r") as file:
    student_details = json.load(file)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


# =====================================
# INITIALIZE DATABASE
# =====================================

initialize_sessions()

for student_id, student_name in student_details.items():

    register_student(
        int(student_id),
        student_name
    )


# =====================================
# CREATE CLASS SESSION
# =====================================

subject = input("\nEnter Subject Name: ").strip()

if not subject:
    raise ValueError("Subject name cannot be empty.")

session_id = create_session(subject)

print("\nClass session created successfully!")
print("Subject:", subject)
print("Session ID:", session_id)


# =====================================
# LOAD ALREADY MARKED STUDENTS
# =====================================

conn = sqlite3.connect(DB_NAME)

cursor = conn.cursor()

cursor.execute("""
SELECT student_id
FROM session_attendance
WHERE session_id = ?
AND status = 'Present'
""", (session_id,))

marked_students = {
    row[0] for row in cursor.fetchall()
}

conn.close()


# =====================================
# MEDIAPIPE INITIALIZATION
# =====================================

BaseOptions = mp.tasks.BaseOptions

HandLandmarker = mp.tasks.vision.HandLandmarker

HandLandmarkerOptions = (
    mp.tasks.vision.HandLandmarkerOptions
)

RunningMode = mp.tasks.vision.RunningMode


options = HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="hand_landmarker.task"
    ),
    running_mode=RunningMode.VIDEO,
    num_hands=1
)


# =====================================
# GESTURE CLASSIFICATION
# =====================================

def detect_gesture(landmarks):

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    fingers = []

    for tip, pip in zip(tips, pips):

        if landmarks[tip].y < landmarks[pip].y:
            fingers.append(1)

        else:
            fingers.append(0)

    total = sum(fingers)

    if total == 0:
        return "FIST"

    elif total == 4:
        return "OPEN PALM"

    elif fingers == [1, 1, 0, 0]:
        return "VICTORY"

    elif fingers == [1, 0, 0, 0]:
        return "ONE FINGER"

    return "OTHER"


# =====================================
# GESTURE CHALLENGES
# =====================================

challenges = {
    "FIST": "MAKE A FIST",
    "OPEN PALM": "SHOW OPEN PALM",
    "VICTORY": "SHOW TWO FINGERS",
    "ONE FINGER": "SHOW ONE FINGER"
}


def create_student_challenge():

    return {
        "gesture": random.choice(list(challenges.keys())),
        "stable_count": 0,
        "start_time": time.monotonic()
    }


# Each student gets an independent challenge.

student_challenges = {}


# =====================================
# WEBCAM INITIALIZATION
# =====================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Webcam not accessible")


timestamp = 0

print("\n================================")
print("AI SMART CLASSROOM ATTENDANCE")
print("================================")

print("Subject:", subject)
print("Total Registered Students:", len(student_details))
print("Already Marked:", len(marked_students))

print("\nStudents can approach the webcam.")
print("Press Q to exit.")


# =====================================
# MAIN APPLICATION
# =====================================

try:

    with HandLandmarker.create_from_options(options) as landmarker:

        while True:

            ret, frame = cap.read()

            if not ret:
                print("Unable to read webcam.")
                break

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )

            current_message = ""

            # =================================
            # EXACTLY ONE FACE
            # =================================

            if len(faces) == 1:

                x, y, w, h = faces[0]

                face = gray[y:y+h, x:x+w]

                face = cv2.resize(
                    face,
                    (200, 200)
                )

                predicted_id, confidence = (
                    recognizer.predict(face)
                )

                student_id = int(predicted_id)

                student_name = student_details.get(
                    str(student_id)
                )

                # =============================
                # UNKNOWN STUDENT
                # =============================

                if (
                    confidence >= CONFIDENCE_THRESHOLD
                    or student_name is None
                ):

                    current_message = "UNKNOWN STUDENT"

                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x+w, y+h),
                        (0, 0, 255),
                        2
                    )

                    cv2.putText(
                        frame,
                        current_message,
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 255),
                        2
                    )

                # =============================
                # RECOGNIZED STUDENT
                # =============================

                else:

                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x+w, y+h),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"{student_name} | ID: {student_id}",
                        (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 0),
                        2
                    )

                    # =========================
                    # ALREADY MARKED
                    # =========================

                    if student_id in marked_students:

                        current_message = (
                            "ATTENDANCE ALREADY MARKED"
                        )

                    # =========================
                    # NEW STUDENT VERIFICATION
                    # =========================

                    else:

                        # Create independent challenge
                        if student_id not in student_challenges:

                            student_challenges[
                                student_id
                            ] = create_student_challenge()

                        challenge_data = student_challenges[
                            student_id
                        ]

                        target_gesture = challenge_data[
                            "gesture"
                        ]

                        # =====================
                        # TIMEOUT
                        # =====================

                        if (
                            time.monotonic()
                            - challenge_data["start_time"]
                            > CHALLENGE_TIMEOUT
                        ):

                            student_challenges[
                                student_id
                            ] = create_student_challenge()

                            challenge_data = student_challenges[
                                student_id
                            ]

                            target_gesture = challenge_data[
                                "gesture"
                            ]

                        # =====================
                        # HAND DETECTION
                        # =====================

                        rgb = cv2.cvtColor(
                            frame,
                            cv2.COLOR_BGR2RGB
                        )

                        mp_image = mp.Image(
                            image_format=mp.ImageFormat.SRGB,
                            data=rgb
                        )

                        timestamp = max(
                            timestamp + 1,
                            int(time.monotonic() * 1000)
                        )

                        result = landmarker.detect_for_video(
                            mp_image,
                            timestamp
                        )

                        gesture = "NO HAND"

                        if result.hand_landmarks:

                            gesture = detect_gesture(
                                result.hand_landmarks[0]
                            )

                        # =====================
                        # DISPLAY CHALLENGE
                        # =====================

                        current_message = (
                            "CHALLENGE: "
                            + challenges[target_gesture]
                        )

                        cv2.putText(
                            frame,
                            current_message,
                            (20, 85),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (255, 0, 0),
                            2
                        )

                        cv2.putText(
                            frame,
                            "Detected: " + gesture,
                            (20, 125),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 255),
                            2
                        )

                        # =====================
                        # STABLE GESTURE CHECK
                        # =====================

                        if gesture == target_gesture:

                            challenge_data[
                                "stable_count"
                            ] += 1

                        else:

                            challenge_data[
                                "stable_count"
                            ] = 0

                        # =====================
                        # MARK ATTENDANCE
                        # =====================

                        if (
                            challenge_data["stable_count"]
                            >= REQUIRED_FRAMES
                        ):

                            success = mark_session_attendance(
                                session_id,
                                student_id
                            )

                            if success:

                                marked_students.add(
                                    student_id
                                )

                                print(
                                    f"\nAttendance marked: "
                                    f"{student_name} "
                                    f"(ID: {student_id})"
                                )

                                current_message = (
                                    "ATTENDANCE MARKED SUCCESSFULLY!"
                                )

                            else:

                                marked_students.add(
                                    student_id
                                )

                                current_message = (
                                    "ATTENDANCE ALREADY MARKED"
                                )

                            # Remove completed challenge
                            student_challenges.pop(
                                student_id,
                                None
                            )

            # =================================
            # NO FACE OR MULTIPLE FACES
            # =================================

            else:

                if len(faces) == 0:

                    current_message = "SHOW YOUR FACE"

                else:

                    current_message = (
                        "ONLY ONE STUDENT AT A TIME"
                    )

            # =================================
            # LIVE ATTENDANCE COUNT
            # =================================

            total_students = len(student_details)

            present_count = len(marked_students)

            cv2.putText(
                frame,
                f"Subject: {subject}",
                (20, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                f"Attendance: {present_count}/{total_students}",
                (20, 215),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                current_message,
                (20, 260),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2
            )

            # =================================
            # DISPLAY
            # =================================

            cv2.imshow(
                "AI Smart Classroom Attendance",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


finally:

    cap.release()

    cv2.destroyAllWindows()

    print("\n================================")
    print("CLASS ATTENDANCE SESSION CLOSED")
    print("================================")

    print("Subject:", subject)
    print("Total Registered:", len(student_details))
    print("Total Present:", len(marked_students))

    print("\nAttendance system closed.")