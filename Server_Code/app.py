from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# SQLite DB setup
DATABASE = 'device_data.db'

# Track last sequence number per device for packet loss calculation
last_seq = {}

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS data (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            device_id TEXT NOT NULL,
                            seq INTEGER NOT NULL,
                            packet_loss INTEGER DEFAULT 0,
                            data TEXT NOT NULL)''')
        conn.commit()

@app.route('/<device_id>/data', methods=['POST'])
def receive_data(device_id):
    data = request.get_json()
    print(data)

    if data.get("message") != "skywalker":  
        return "Wrong Transmitter", 403 
    
    current_seq = int(data['seq'])
    
    # Calculate packet loss
    packet_loss = 0
    if device_id in last_seq:
        expected_seq = last_seq[device_id] + 1
        if current_seq > expected_seq:
            packet_loss = current_seq - expected_seq
            print(f"Packet loss detected for {device_id}: {packet_loss} packets lost")
    
    # Update last sequence number for this device
    last_seq[device_id] = current_seq
    
    # Store data in the SQLite database
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO data (device_id, data, seq, packet_loss) VALUES (?, ?, ?, ?)",
                       (device_id, json.dumps(data), current_seq, packet_loss))
        conn.commit()

    # Emit update event to all connected clients
    socketio.emit('new_data', {
        'device_id': device_id,
        'data': data,
        'seq': current_seq,
        'packet_loss': packet_loss
    }, broadcast=True)

    return "Data received and stored", 201

@app.route('/')
def index():
    # Retrieve the latest 20 stored data entries
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT device_id, data, seq, packet_loss FROM data ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        # Reverse so newest is at the bottom
        rows.reverse()

    # HTML template with Socket.IO client script
    html = """
    <html>
        <head>
            <title>Device Data with Packet Loss Tracking</title>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
            <script>
                document.addEventListener("DOMContentLoaded", function() {
                    var socket = io();

                    socket.on('new_data', function(msg) {
                        var table = document.getElementById("data-table");
                        var row = table.insertRow(-1);
                        var cell1 = row.insertCell(0);
                        var cell2 = row.insertCell(1);
                        var cell3 = row.insertCell(2);
                        var cell4 = row.insertCell(3);
                        cell1.innerHTML = msg.device_id;
                        cell2.innerHTML = JSON.stringify(msg.data);
                        cell3.innerHTML = msg.seq;
                        cell4.innerHTML = msg.packet_loss;

                        // Keep only the latest 20 rows
                        if (table.rows.length > 21) {  // 1 header row + 20 data rows
                            table.deleteRow(1); // delete the oldest row (below header)
                        }
                    });
                });
            </script>
        </head>
        <body>
            <h1>Device Data with Packet Loss Tracking (Latest 20)</h1>
            <table border="1" id="data-table">
                <tr><th>Device ID</th><th>Data</th><th>Sequence</th><th>Packet Loss</th></tr>
                {% for device_id, data, seq, packet_loss in rows %}
                    <tr><td>{{ device_id }}</td><td>{{ data }}</td><td>{{ seq }}</td><td>{{ packet_loss }}</td></tr>
                {% endfor %}
            </table>
        </body>
    </html>
    """
    
    return render_template_string(html, rows=rows)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host="0.0.0.0")
