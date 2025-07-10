from smartcard.System import readers
from flask import Flask
from flask_socketio import SocketIO
import threading
import time
from flask import Flask, render_template_string

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


def read_nfc_loop():
    while True:
        try:
            r = readers()
            if not r:
                print("No readers found")
                time.sleep(1)
                continue
            reader = r[0]
            connection = reader.createConnection()
            connection.connect()
            # Get UID
            SELECT = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.transmit(SELECT)
            uid = ''.join(format(x, '02X') for x in data)
            # Authenticate block 4 (default key for MIFARE Classic)
            AUTH = [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, 0x04, 0x60, 0x00]
            connection.transmit(AUTH)
            # Read block 4
            READ = [0xFF, 0xB0, 0x00, 0x04, 0x10]
            block_data, sw1, sw2 = connection.transmit(READ)
            card_text = ''.join(chr(x) for x in block_data if 32 <= x <= 126).strip()
            print(f"Card UID: {uid}, Data: {card_text}")
            socketio.emit("nfc-scan", {"uid": uid, "data": card_text})
            time.sleep(1.5)
        except Exception as e:
         
            time.sleep(1)

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NFC Card Reader</title>
        <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    </head>
    <body>
        <h1>NFC Card Reader</h1>
        <div id="output">Waiting for card...</div>
        <script>
            var socket = io();
            socket.on('nfc-scan', function(data) {
                if (data.data) {
                    document.getElementById('output').innerText = "Card Data: " + data.data + " (UID: " + data.uid + ")";
                } else if (data.uid) {
                    document.getElementById('output').innerText = "Card UID: " + data.uid;
                } else if (data.error) {
                    document.getElementById('output').innerText = data.error + " (UID: " + data.uid + ")";
                }
            });
        </script>
    </body>
    </html>
    """)

if __name__ == '__main__':
    threading.Thread(target=read_nfc_loop, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000)
