
import cv2
import mediapipe as mp
import json
import random
import time

# -------------------------------
# LOAD FACE RECOGNITION MODEL
# -------------------------------

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("models/face_model.yml")

with open("models/student_details.json", "r") as file:
    student_details = json.load(file)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

# -------------------------------
# MEDIAPIPE HAND LANDMARK MODEL
# -------------------------------

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="hand_landmarker.task"
    ),
    running_mode=RunningMode.VIDEO,
    num_hands=1
)

# -------------------------------
# GESTURE CLASSIFICATION
# -------------------------------

def detect_gesture(landmarks):

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    fingers = []

    for tip, pip in zip(tips, pips):
        fingers.append(
            1 if landmarks[tip].y < landmarks[pip].y else 0
        )

    total = sum(fingers)

    if total == 0:
        return "FIST"

    if total == 4:
        return "OPEN PALM"

    if fingers == [1, 1, 0, 0]:
        return "VICTORY"

    if fingers == [1, 0, 0, 0]:
        return "ONE FINGER"

    return f"{total} FINGERS"


# -------------------------------
# RANDOM CHALLENGE
# -------------------------------

challenges = {
    "FIST": "MAKE A FIST",
    "OPEN PALM": "SHOW OPEN PALM",
    "VICTORY": "SHOW TWO FINGERS",
    "ONE FINGER": "SHOW ONE FINGER"
}

target_gesture = random.choice(list(challenges.keys()))

# -------------------------------
# START WEBCAM
# -------------------------------

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Cannot access webcam")

verified = False
recognized_student = None
start_time = time.monotonic()
timestamp = 0

print("AI Attendance Verification Started!")

with HandLandmarker.create_from_options(options) as landmarker:

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(
            gray, 1.1, 5, minSize=(100, 100)
        )

        # Require exactly one detected face
        if len(faces) == 1:

            x, y, w, h = faces[0]

            face = gray[y:y+h, x:x+w]
            face = cv2.resize(face, (200, 200))

            student_id, confidence = recognizer.predict(face)

            if confidence < 65:
                recognized_student = student_details.get(
                    str(student_id)
                )
            else:
                recognized_student = None

            color = (0, 255, 0) if recognized_student else (0, 0, 255)

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)

            if recognized_student and not verified:

                cv2.putText(
                    frame,
                    f"Student: {recognized_student}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=rgb
                )

                timestamp = max(
                    timestamp + 1,
                    int(time.monotonic() * 1000)
                )

                result = landmarker.detect_for_video(
                    mp_image, timestamp
                )

                gesture = "NO HAND"

                if result.hand_landmarks:
                    gesture = detect_gesture(
                        result.hand_landmarks[0]
                    )

                cv2.putText(
                    frame,
                    "CHALLENGE: " + challenges[target_gesture],
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

                if gesture == target_gesture:
                    verified = True

            elif not recognized_student:

                cv2.putText(
                    frame,
                    "UNKNOWN STUDENT",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

        else:
            recognized_student = None

            cv2.putText(
                frame,
                "Please show exactly one face",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        if verified:
            cv2.putText(
                frame,
                "VERIFICATION SUCCESSFUL!",
                (20, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        elif time.monotonic() - start_time > 30:
            cv2.putText(
                frame,
                "CHALLENGE EXPIRED - RESTART",
                (20, 180),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        cv2.imshow("AI Smart Attendance Verification", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
