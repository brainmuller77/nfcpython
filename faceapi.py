from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
import math
import json
import os

# ==============================
# CONFIGURATION
# ==============================
app = Flask(__name__)
CORS(app)  # Allow Angular requests (configure allowed origins in prod)

# Load database credentials from environment variables (safer than hardcoding!)
DB_USER = os.getenv("DB_USER", "your_mysql_user")
DB_PASS = os.getenv("DB_PASS", "your_mysql_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "facesdb")

app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JSON_SORT_KEYS"] = False  # Keep JSON responses ordered

db = SQLAlchemy(app)

# ==============================
# DATABASE MODEL
# ==============================
class Face(db.Model):
    __tablename__ = "faces"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    descriptor = db.Column(db.JSON, nullable=False)  # Store as JSON directly (MySQL 5.7+ supports JSON)


# Create DB tables if they don’t exist
with app.app_context():
    db.create_all()


# ==============================
# HELPER FUNCTIONS
# ==============================
def euclidean_distance(desc1, desc2):
    """Calculate Euclidean distance between two descriptors."""
    try:
        return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(desc1, desc2)))
    except Exception:
        return float("inf")  # Return infinite distance if invalid data


# ==============================
# ROUTES
# ==============================

@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.get_json(force=True)
        name = data.get("name")
        descriptor = data.get("descriptor")

        if not name or not isinstance(name, str):
            return jsonify({"error": "Valid name is required"}), 400
        if not descriptor or not isinstance(descriptor, list):
            return jsonify({"error": "Valid descriptor list is required"}), 400

        # Save to DB
        new_face = Face(name=name.strip(), descriptor=descriptor)
        db.session.add(new_face)
        db.session.commit()

        return jsonify({"message": f"Face registered for {name}"}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route("/recognize", methods=["POST"])
def recognize():
    try:
        data = request.get_json(force=True)
        descriptor = data.get("descriptor")

        if not descriptor or not isinstance(descriptor, list):
            return jsonify({"error": "Valid descriptor list is required"}), 400

        faces = Face.query.all()
        if not faces:
            return jsonify({"name": "Unknown", "distance": None}), 200

        best_match = None
        lowest_distance = float("inf")

        for face in faces:
            stored_descriptor = face.descriptor
            dist = euclidean_distance(descriptor, stored_descriptor)
            if dist < lowest_distance:
                lowest_distance = dist
                best_match = face.name

        threshold = 0.6  # tune based on your recognition model
        if lowest_distance < threshold:
            return jsonify({"name": best_match, "distance": round(lowest_distance, 4)}), 200
        else:
            return jsonify({"name": "Unknown", "distance": round(lowest_distance, 4)}), 200

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    # In production, use a proper WSGI server like gunicorn or uWSGI
    app.run(host="0.0.0.0", port=5000, debug=False)
