import cv2
import os
import re
from database import register_student

# =====================================
# CONFIGURATION
# =====================================

DATASET_PATH = "dataset"
TOTAL_IMAGES = 100

os.makedirs(DATASET_PATH, exist_ok=True)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

# =====================================
# STUDENT DETAILS
# =====================================

print("\n===== STUDENT REGISTRATION =====")

while True:
    try:
        student_id = int(input("Enter Student ID: "))

        if student_id <= 0:
            print("Student ID must be positive.")
            continue

        break

    except ValueError:
        print("Please enter a valid numeric ID.")

student_name = input("Enter Student Name: ").strip()

if not student_name:
    raise ValueError("Student name cannot be empty.")

# Create a safe folder name
safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", student_name)

folder_name = f"{student_id}_{safe_name}"
student_folder = os.path.join(DATASET_PATH, folder_name)

# Prevent accidental overwriting
if os.path.exists(student_folder):
    print("This student already has a dataset.")
    raise SystemExit

os.makedirs(student_folder)

# =====================================
# WEBCAM INITIALIZATION
# =====================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Cannot access webcam.")

count = 0

print("\nRegistration started!")
print("Look at the camera and move your face slightly.")
print("Press Q to cancel.")

# =====================================
# CAPTURE FACE IMAGES
# =====================================

try:
    while count < TOTAL_IMAGES:

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

        if len(faces) == 1:

            x, y, w, h = faces[0]

            face = gray[y:y+h, x:x+w]

            face = cv2.resize(
                face,
                (200, 200)
            )

            count += 1

            image_path = os.path.join(
                student_folder,
                f"{count}.jpg"
            )

            cv2.imwrite(image_path, face)

            cv2.rectangle(
                frame,
                (x, y),
                (x+w, y+h),
                (0, 255, 0),
                2
            )

        cv2.putText(
            frame,
            f"Images: {count}/{TOTAL_IMAGES}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow(
            "Student Registration",
            frame
        )

        if cv2.waitKey(100) & 0xFF == ord("q"):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()

# =====================================
# SAVE STUDENT DETAILS
# =====================================

if count == TOTAL_IMAGES:

    register_student(
        student_id,
        student_name
    )

    print("\nRegistration successful!")
    print("Student ID:", student_id)
    print("Student Name:", student_name)
    print("Images captured:", count)

else:

    # Remove incomplete dataset
    import shutil

    shutil.rmtree(student_folder)

    print("\nRegistration cancelled.")
    print("Incomplete dataset removed.")