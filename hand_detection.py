import cv2
import mediapipe as mp
import time

# Initialize MediaPipe Tasks
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path="hand_landmarker.task"
    ),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

def detect_gesture(landmarks):

    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]

    fingers = []

    for tip, pip in zip(finger_tips, finger_pips):
        fingers.append(
            1 if landmarks[tip].y < landmarks[pip].y else 0
        )

    total = sum(fingers)

    if total == 0:
        return "FIST"

    elif total == 4:
        return "OPEN PALM"

    elif fingers == [1, 1, 0, 0]:
        return "VICTORY"

    elif fingers == [1, 0, 0, 0]:
        return "ONE FINGER"

    return f"{total} FINGERS"


cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Camera not accessible!")
    raise SystemExit

print("Hand Recognition Started!")
print("Press Q to exit.")

with HandLandmarker.create_from_options(options) as landmarker:

    while True:

        success, frame = cap.read()

        if not success:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        timestamp = int(time.monotonic() * 1000)

        result = landmarker.detect_for_video(
            mp_image,
            timestamp
        )

        gesture = "NO HAND DETECTED"

        if result.hand_landmarks:

            for landmarks in result.hand_landmarks:

                gesture = detect_gesture(landmarks)

                h, w, _ = frame.shape

                # Draw hand landmarks
                for point in landmarks:

                    x = int(point.x * w)
                    y = int(point.y * h)

                    cv2.circle(
                        frame,
                        (x, y),
                        5,
                        (0, 255, 0),
                        -1
                    )

                # Draw gesture label
                cv2.putText(
                    frame,
                    gesture,
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

        else:
            cv2.putText(
                frame,
                gesture,
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )

        cv2.imshow("AI Smart Attendance - Hand Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()