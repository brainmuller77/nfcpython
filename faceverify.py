from flask import Flask, request, jsonify
from deepface import DeepFace
import cv2
import mediapipe as mp
import numpy as np
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'temp_uploads'
KNOWN_FACE_PATH = 'known_faces/user1.jpg'  # Pre-registered face

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize MediaPipe once
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.7)

@app.route("/verify", methods=["POST"])
def verify_face():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    img_file = request.files['image']
    img_path = os.path.join(UPLOAD_FOLDER, img_file.filename)
    img_file.save(img_path)

    # Load the image using OpenCV
    frame = cv2.imread(img_path)
    if frame is None:
        return jsonify({"error": "Failed to read image"}), 400

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detector.process(rgb)

    if not results.detections:
        return jsonify({"error": "No face detected"}), 400

    # Face detected, run verification
    try:
        result = DeepFace.verify(img1_path=KNOWN_FACE_PATH, img2_path=img_path, enforce_detection=False)
        os.remove(img_path)
        return jsonify({
            "verified": result["verified"],
            "distance": result["distance"],
            "threshold": result["threshold"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
