import datetime
import traceback
from smartcard.System import readers
from flask import Flask,request, jsonify
from flask_socketio import SocketIO
import threading
import time
import pymysql
import pyttsx3
from flask import Flask, render_template_string
from smartcard.util import toHexString, toBytes
import requests
import os
from werkzeug.utils import secure_filename
from flask_cors import CORS


from db_config import DB_CONFIG


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


students = {
    "04A224D7AA3380": {"name": "John Doe", "id": "12345", "grade": "A"},
    "04589A87BC1155": {"name": "Jane Smith", "id": "67890", "grade": "B"},
}

# Connect to remote MySQL database using imported config
connection = pymysql.connect(**DB_CONFIG)


engine = pyttsx3.init()
engine.setProperty('rate', 160)

def speak_name_and_grade(name, grade):
    try:
        engine.say(f"You Are Leaving {name}. class {grade}")
        engine.runAndWait()
    except Exception as e:
        print("TTS Error:", e)

latest_student = {
    "name": "",
    "schoolid": "",
    "grade": "",
    "uid": "",
    "image":"",
    "classcode":""
}


def insert_attendance_if_new(student):
    try:
        with connection.cursor() as cursor:
            check_sql = "SELECT id FROM attendance WHERE carduuid = %s AND DATE(date) = CURDATE()"
            cursor.execute(check_sql, (student['uid'],))
            if cursor.fetchone():
                return False
            insert_sql = """
            INSERT INTO attendance (
                schoolid, studentname, status, class, date, subject,
                term, academicyear, classcode, teaid, day, month, time, carduuid
            ) VALUES (
                %s, %s, %s, %s, CURDATE(), %s,
                %s, %s, %s, %s, %s, MONTH(CURDATE()), CURTIME(), %s
            )
            """
            values = (
                student['schoolid'],
                student['name'],
                1,
                student['grade'],
                "General",
                "Term 1",
                "2024-2025",
                student['classcode'],
                "TEA123",
                1,
                student['uid']
            )
            cursor.execute(insert_sql, values)
            connection.commit()
             # Emit event after successful insert
            socketio.emit("attendance-inserted", student)
            return True
    except Exception as e:
        print("Attendance Insert Error:", e)
        return False

def send_sms_to_parent(name, grade, contact):
    try:
        # Ensure contact is a list/array
        if not isinstance(contact, list):
            contact = [contact]
        payload = {
            "list": ",".join(contact),  # Convert array to comma-separated string
            "message": f"Dear Parent, Your Ward {name} has successfully entered school. Class: {grade}"
        }
        response = requests.post("https://creatorsacademy.skuulmasta.com/server/sendsms.php", data=payload)
        print(f"SMS sent to {contact}: {response.status_code}")
    except Exception as e:
        print("SMS Error:", e)

def insert_scanned_card(uid):
    try:
        with connection.cursor() as cursor:
            insert_sql = "INSERT INTO scanned_cards (carduid, scan_time) VALUES (%s, NOW())"
            cursor.execute(insert_sql, (uid,))
            connection.commit()
    except Exception as e:
        print("Scanned Card Insert Error:", e)

server = 'https://creatorsacademy.skuulmasta.com/server/'
def get_student_from_db(uid):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT firstname, lastname, schoolid, class, carduuid,image,care_contact, classcode FROM students WHERE carduuid = %s"
            cursor.execute(sql, (uid,))
            result = cursor.fetchone()
            if result:
                student = {
                    "uid": uid,
                    "name": result[0] +' '+ result[1],
                    "schoolid": result[2],
                    "grade": result[3],
                    "image": result[5],
                    "contact":'0248616502',
                    "classcode":result[7]
                }
                global latest_student
                latest_student = student
           
                return student
            else:
                return {"error": "Unknown card", "uid": uid}
    except Exception as e:
        print("DB Error:", e)
        return {"error": "Database error", "uid": uid}
    

def read_nfc_loop():
    last_uid = None
    while True:
        try:
            r = readers()
            if not r:
                print("No readers found")
                time.sleep(1)
                continue
            reader = r[0]
            connection_card = reader.createConnection()
            connection_card.connect()
            SELECT = [0xFF, 0xCA, 0x00, 0x00, 0x00]  # Get card UID
            data, sw1, sw2 = connection_card.transmit(SELECT)
            uid = ''.join(format(x, '02X') for x in data)
            if uid != last_uid:
                insert_scanned_card(uid)
                print(f"Card UID: {uid}")
                student = get_student_from_db(uid)
                if "contact" in student:
                    send_sms_to_parent(student["name"], student["grade"], student["contact"])
                insert_attendance_if_new(student)
                socketio.emit("nfc-scan", student)
                last_uid = uid
            # Try to detect card removal
            time.sleep(0.5)
            try:
                connection_card.disconnect()
            except:
                pass
            # Check if card is removed
            card_removed = False
            for _ in range(10):  # Check for 5 seconds (10 * 0.5s)
                try:
                    connection_card.connect()
                    connection_card.disconnect()
                    time.sleep(0.5)
                except:
                    card_removed = True
                    break
            if card_removed:
                last_uid = None
        except Exception as e:
            print("Reader error:", e)
            last_uid = None
            time.sleep(1)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(save_path)
        # Insert filename/path into database

        data = request.form
        try:
            with connection.cursor() as cursor:
                # Check if already present today
                check_sql = "SELECT id,schoolid,studentname FROM files WHERE schoolid = %s AND DATE(datetime) = CURDATE()"
                cursor.execute(check_sql, (data.get('studentid'),))
                if cursor.fetchone():
                    return jsonify({'error': 'File already uploaded today'}), 400

                # Insert new file record
                insert_sql = """
                INSERT INTO files (
                     `filename`, `filepath`, `class`, `classcode`, `subject`,
                    `subjectcode`, `studentname`, `schoolid`, `status`, `term`, `acayear`
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """
                values = (
                    filename,
                    save_path,
                    data.get('class'),  # class
                    data.get('classcode'),  # classcode
                    data.get('subject'),  # subject
                    data.get('subjectcode'),  # subjectcode
                    data.get('nos'),  # studentname
                    data.get('studentid'),  # schoolid
                    1   , # status
                     data.get('term'),  # term
                     data.get('acayear'),  # academicyear
                )
                cursor.execute(insert_sql, values)
                connection.commit()
                # Emit event after successful upload
                # Select all attendance for today
                select_sql = "SELECT * FROM files WHERE DATE(datetime) = CURDATE()"
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                attendance_today = [dict(zip(columns, row)) for row in rows]

            # Convert datetime objects to string
            for record in attendance_today:
                for key, value in record.items():
                    if isinstance(value, (datetime.datetime, datetime.date)):
                        record[key] = value.isoformat()
                # Emit to all connected clients
                socketio.emit("attendance-today", attendance_today)
            return jsonify({'message': 'File uploaded', 'filename': filename}), 200
        except Exception as e:
            print("Attendance Insert Error:", e)
            traceback.print_exc() 
            return jsonify({'error': 'Database error', 'details': str(e)}), 500
    return jsonify({'error': 'Invalid file type'}), 400


@app.route('/scancards')
def index():
    return jsonify({"status": "NFC server is running", "message": "Listening for card scans"})

if __name__ == '__main__':
    threading.Thread(target=read_nfc_loop, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
