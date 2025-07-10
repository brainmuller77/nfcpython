from smartcard.System import readers
from flask import Flask, jsonify
from flask_socketio import SocketIO
import threading
import time
import pymysql
import pyttsx3
from flask import Flask, render_template_string

from db_config import DB_CONFIG

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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
    "id": "",
    "grade": "",
    "uid": "",
    "image":""
}
server = 'https://creatorsacademy.skuulmasta.com/server/'
def get_student_from_db(uid):
    try:
        with connection.cursor() as cursor:
            sql = "SELECT firstname, lastname, schoolid, class, carduuid,image FROM students WHERE carduuid = %s"
            cursor.execute(sql, (uid,))
            result = cursor.fetchone()
            if result:
                student = {
                    "uid": uid,
                    "name": result[0] +''+ result[1],
                    "id": result[2],
                    "grade": result[3],
                    "image": result[5]
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
            print(f"Card UID: {uid}")
            student = get_student_from_db(uid)
            socketio.emit("nfc-scan", student)
            time.sleep(1.5)
        except Exception as e:
            print("Reader error:", e)
            time.sleep(1)


@app.route('/')
def index():
    template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
          <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
        <title>Student ID Card</title>
        <style>
            .id-card {
                max-width: 350px;
                margin: 50px auto;
                padding: 20px;
                border: 1px solid #ccc;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.15);
                text-align: center;
            }
            .id-card h5 {
                margin-bottom: 5px;
            }
            .id-card small {
                color: #666;
            }
              .id-photo {
          width: 100px;
          height: 100px;
          object-fit: cover;
          border-radius: 50%;
          margin-bottom: 10px;
        }
        </style>
    </head>
    <body>
        <div class="id-card bg-light" id="card">
            <h4>Student ID Card</h4>
             <img src="server+{{student.image}}" alt="Photo" class="id-photo">
            <h5>{{ student.name }}</h5>
            <p>ID: {{ student.id }}</p>
            <p>Grade: {{ student.grade }}</p>
            <p class="text-muted">Card UID: {{ student.uid }}</p>
             <button id="speak-btn" class="btn btn-primary mt-2" disabled>Confirm</button>
        </div>
        <script>
    var socket = io();
    socket.on('nfc-scan', function(data) {
     const imageUrl = data.image 
    ? `https://creatorsacademy.skuulmasta.com/server/${data.image}` 
    : 'https://via.placeholder.com/100';

const html = `
    <h4>Student ID Card</h4>
    <img src="${imageUrl}" alt="Photo" class="id-photo"><h5>${data.name || 'Unknown'}</h5>
            <p>ID: ${data.id || '--'}</p>
            <p>Grade: ${data.grade || '--'}</p>
            <p class="text-muted">Card UID: ${data.uid || '--'}</p>
            <button id='speak-btn' class='btn btn-primary mt-2'>Confirm</button>
        `;
        document.getElementById("card").innerHTML = html;
        document.getElementById("speak-btn").addEventListener("click", () => {
            const message = `You Are Leaving ${data.name},  ${data.grade}`;
           for (let i = 0; i < 3; i++) {
  const utter = new SpeechSynthesisUtterance(message);
  utter.rate = 1;
  utter.pitch = 1;
  window.speechSynthesis.speak(utter);
}
        });
    });
</script>
    </body>
    </html>
    '''
    return render_template_string(template, student=latest_student)
if __name__ == '__main__':
    threading.Thread(target=read_nfc_loop, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
