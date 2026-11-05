
import cv2
import json

# Load trained face recognition model
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("models/face_model.yml")

# Load student details
with open("models/student_details.json", "r") as file:
    student_details = json.load(file)

# Load face detector
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)

# Open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot access webcam!")
    exit()

print("Face Recognition Started!")
print("Press Q to exit.")

while True:

    ret, frame = cap.read()

    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )

    for (x, y, w, h) in faces:

        face = gray[y:y+h, x:x+w]
        face = cv2.resize(face, (200, 200))

        # Predict student identity
        student_id, confidence = recognizer.predict(face)

        # Lower confidence means a better match
        if confidence < 65:

            student_name = student_details.get(
                str(student_id), "Unknown"
            )

            label = f"{student_name} | ID: {student_id}"
            color = (0, 255, 0)

        else:

            label = "Unknown Person"
            color = (0, 0, 255)

        # Draw bounding box
        cv2.rectangle(
            frame,
            (x, y),
            (x+w, y+h),
            color,
            2
        )

        cv2.putText(
            frame,
            label,
            (x, y-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

    cv2.imshow("AI Smart Attendance - Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

