from flask import Flask, request, jsonify
import pytesseract
from PIL import Image
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_NAME = 'skuulma1_creatorsacademy'

# Create the database if it doesn't exist
def create_table():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS studentsmarks (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            student_name TEXT,
                            student_id TEXT,
                            class_score REAL,
                            exam_score REAL,
                            project_work REAL
                        )''')
create_table()

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image)

        # Split lines and parse
        lines = text.strip().split('\n')
        headers = [h.strip().lower() for h in lines[0].split()]

        expected = ['student', 'name', 'student', 'id', 'classcore', 'examscore', 'projectwork']
        if not all(any(e in h for h in headers) for e in expected):
            return jsonify({"error": "Invalid table headers detected"}), 400

        inserted = []
        for line in lines[1:]:
            if line.strip() == "":
                continue
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            name = parts[0] + " " + parts[1]  # Combine first two as name
            student_id = parts[2]
            class_score = float(parts[3])
            exam_score = float(parts[4])
            project_work = float(parts[5]) if len(parts) > 5 else 0.0

            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO studentsmarks (student_name, student_id, class_score, exam_score, project_work) VALUES (?, ?, ?, ?, ?)",
                             (name, student_id, class_score, exam_score, project_work))
                inserted.append(student_id)

        return jsonify({"message": "Upload and extraction successful", "inserted_ids": inserted})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
