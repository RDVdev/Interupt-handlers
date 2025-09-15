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

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS data (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            device_id TEXT NOT NULL,
                            data TEXT NOT NULL,
                            timestamp TEXT NOT NULL)''')
        conn.commit()

@app.route('/<device_id>/data', methods=['POST'])
def receive_data(device_id):
    data = request.get_json()
    print(data)

    if data.get("message") != "skywalker":  
        return "Wrong Transmitter", 403 

    # Store data with timestamp
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO data (device_id, data, timestamp) VALUES (?, ?, ?)", 
                       (device_id, json.dumps(data), timestamp))
        conn.commit()

    # Emit update event to all connected clients
    socketio.emit('new_data', {
        'device_id': device_id,
        'data': data,
        'timestamp': timestamp
    })

    return "Data received and stored", 201

@app.route('/')
def index():
    # Retrieve the latest 20 stored data entries
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT device_id, data, timestamp FROM data ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        # Reverse so newest is at the bottom
        rows.reverse()

    # HTML template with Socket.IO client script
    html = """
    <html>
        <head>
            <title>Device Data</title>
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
                        cell1.innerHTML = msg.device_id;
                        cell2.innerHTML = JSON.stringify(msg.data);
                        cell3.innerHTML = msg.timestamp;

                        // Keep only the latest 20 rows
                        if (table.rows.length > 21) {  // 1 header row + 20 data rows
                            table.deleteRow(1); // delete the oldest row (below header)
                        }
                    });
                });
            </script>
        </head>
        <body>
            <h1>Device Data (Latest 20)</h1>
            <table border="1" id="data-table">
                <tr><th>Device ID</th><th>Data</th><th>Timestamp (UTC)</th></tr>
                {% for device_id, data, timestamp in rows %}
                    <tr><td>{{ device_id }}</td><td>{{ data }}</td><td>{{ timestamp }}</td></tr>
                {% endfor %}
            </table>
        </body>
    </html>
    """
    
    return render_template_string(html, rows=rows)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host="0.0.0.0")
