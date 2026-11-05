import cv2
import os
import json
import numpy as np

# Initialize LBPH Face Recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

faces = []
labels = []

# Store student information
student_details = {}

dataset_path = "dataset"

print("Loading student datasets...")

# Read student folders
for folder in os.listdir(dataset_path):

    folder_path = os.path.join(dataset_path, folder)

    if not os.path.isdir(folder_path):
        continue

    # Extract student ID and name
    student_id, student_name = folder.split("_", 1)

    student_id = int(student_id)

    student_details[str(student_id)] = student_name

    print(f"Processing: {student_name}")

    # Read images
    for image_name in os.listdir(folder_path):

        image_path = os.path.join(folder_path, image_name)

        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is None:
            continue

        image = cv2.resize(image, (200, 200))

        faces.append(image)
        labels.append(student_id)

# Convert labels into NumPy array
labels = np.array(labels, dtype=np.int32)

if len(faces) == 0:
    raise ValueError("No training images found!")

# Train model
print("\nTraining face recognition model...")

recognizer.train(faces, labels)

# Save trained model
os.makedirs("models", exist_ok=True)

recognizer.save("models/face_model.yml")

# Save student details
with open("models/student_details.json", "w") as file:
    json.dump(student_details, file, indent=4)

print("\nTraining completed successfully!")
print(f"Total images used: {len(faces)}")
print(f"Total students: {len(student_details)}")
print("Model saved in models/face_model.yml")