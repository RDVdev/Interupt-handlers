from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit
import sqlite3
import json
from datetime import datetime
import time
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", logger=True, engineio_logger=True)

# Add custom template filter for JSON parsing
@app.template_filter('from_json')
def from_json_filter(value):
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

# SQLite DB setup
# finaltime = ""
# DATABASE_NAME = ""
# DATABASE_PATH = ""

# Track last sequence number per device for packet loss calculation
last_seq = {}

def init_db():
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS data (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            device_id TEXT NOT NULL,
                            seq INTEGER NOT NULL,
                            packet_loss INTEGER DEFAULT 0,
                            data TEXT NOT NULL,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS loss(
                       recieverid TEXT PRIMARY KEY,
                       diffpacket REAL DEFAULT 0)
                       ''')
        # Check if timestamp column exists and add it if it doesn't (for existing databases)
        cursor.execute("PRAGMA table_info(data)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'timestamp' not in columns:
            # SQLite doesn't allow non-constant defaults in ALTER TABLE, so we add without default
            cursor.execute('ALTER TABLE data ADD COLUMN timestamp DATETIME')
            # Update existing rows with current timestamp
            current_time = datetime.now().isoformat()
            cursor.execute('UPDATE data SET timestamp = ? WHERE timestamp IS NULL', (current_time,))
        
        conn.commit()

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@app.route('/<device_id>/data', methods=['POST'])
def receive_data(device_id):
    data = request.get_json()
    print(data)

    if(data["message"] != "skywalker"):  
        return "Wrong Transmitter", 403 
    
    current_seq = int(data['seq'])
    
    # Calculate packet loss
    # In receive_data function:
    diff_packet = 0
    with sqlite3.connect(DATABASE_PATH) as con:
        cursor = con.cursor()
        # Fix: Use proper parameter tuple and column name
        result = cursor.execute("SELECT diffpacket FROM loss WHERE recieverid=?", (device_id,)).fetchone()
        
        if result is None:
            # Device not in table yet, insert it
            cursor.execute("INSERT INTO loss (recieverid, diffpacket) VALUES (?,?)", (device_id, 0))
            diff_packet = 0
        else:
            diff_packet = result[0]
        
        if device_id in last_seq:
            expected_seq = last_seq[device_id] + 1
            if current_seq > expected_seq:
                packets_lost_now = current_seq - expected_seq
                diff_packet += packets_lost_now
                cursor.execute("UPDATE loss SET diffpacket=? WHERE recieverid=?", (diff_packet, device_id))
        
        con.commit()

    
    # Update last sequence number for this device
    last_seq[device_id] = current_seq
    
    # Store data in the SQLite database with current timestamp
    current_timestamp = datetime.now().isoformat()
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        if(current_seq>0):c_packetloss = round((diff_packet/current_seq)*100,2)
        else:c_packetloss = 0
        cursor.execute("INSERT INTO data (device_id, data, seq, packet_loss, timestamp) VALUES (?, ?, ?, ?, ?)",
                       (device_id, json.dumps(data), current_seq, c_packetloss, current_timestamp))
        conn.commit()

    # Emit update event to all connected clients
    emit_data = {
        'device_id': device_id,
        'data': data,
        'seq': current_seq,
        'packet_loss': c_packetloss
    }
    print(f"Emitting SocketIO event: {emit_data}")
    socketio.emit('new_data', emit_data)

    return "Data received and stored", 201

@app.route('/')
def index():
    # Retrieve the latest 20 stored data entries
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT device_id, data, seq, packet_loss, timestamp FROM data ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        # Reverse so newest is at the bottom
        rows.reverse()

    # HTML template with Socket.IO client script
    html = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>IoT Receiver Monitor</title>
            
            <!-- Google Fonts - Inter font family -->
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            
            <style>
                /* CSS Custom Properties - Corporate Color Palette */
                :root { 
                    /* Primary Colors */
                    --color-background: #F9FAFB;
                    --color-text-primary: #111827;
                    --color-text-secondary: #6B7280;
                    --color-white: #FFFFFF;
                    
                    /* Status Colors */
                    --color-success: #16A34A;
                    --color-warning: #F59E0B;
                    --color-danger: #DC2626;
                    --color-info: #2563EB;
                    
                    /* UI Colors */
                    --color-border: #E5E7EB;
                    --color-surface: #F3F4F6;
                    --color-surface-alt: #F9FAFB;
                    
                    /* Typography */
                    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    --font-size-xs: 12px;
                    --font-size-sm: 14px;
                    --font-size-base: 16px;
                    --font-size-lg: 18px;
                    --font-size-xl: 20px;
                    --font-size-2xl: 24px;
                    
                    /* Font Weights */
                    --font-weight-normal: 400;
                    --font-weight-medium: 500;
                    --font-weight-semibold: 600;
                    --font-weight-bold: 700;
                    
                    /* Spacing */
                    --spacing-xs: 4px;
                    --spacing-sm: 8px;
                    --spacing-md: 12px;
                    --spacing-lg: 16px;
                    --spacing-xl: 20px;
                    --spacing-2xl: 24px;
                    --spacing-3xl: 32px;
                    
                    /* Border Radius */
                    --radius-sm: 6px;
                    --radius-md: 8px;
                    --radius-lg: 12px;
                    
                    /* Shadows */
                    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    
                    /* Transitions */
                    --transition-fast: 150ms ease-in-out;
                    --transition-normal: 200ms ease-in-out;
                    --transition-slow: 300ms ease-in-out;
                }
                
                /* Base Reset and Typography */
                * {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }
                
                html {
                    font-size: 16px;
                    line-height: 1.5;
                }
                
                body {
                    font-family: var(--font-family);
                    font-size: var(--font-size-base);
                    font-weight: var(--font-weight-normal);
                    color: var(--color-text-primary);
                    background-color: var(--color-background);
                    line-height: 1.6;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }
                
                /* Typography Styles */
                h1, h2, h3, h4, h5, h6 {
                    font-weight: var(--font-weight-semibold);
                    line-height: 1.25;
                    margin-bottom: var(--spacing-md);
                }
                
                h1 {
                    font-size: var(--font-size-2xl);
                    font-weight: var(--font-weight-bold);
                }
                
                h2 {
                    font-size: var(--font-size-xl);
                }
                
                h3 {
                    font-size: var(--font-size-lg);
                }
                
                p {
                    margin-bottom: var(--spacing-md);
                }
                
                /* Responsive Breakpoints */
                /* Mobile First Approach */
                
                /* Small devices (landscape phones, 576px and up) */
                @media (min-width: 576px) {
                    .container {
                        max-width: 540px;
                    }
                }
                
                /* Medium devices (tablets, 768px and up) */
                @media (min-width: 768px) {
                    .container {
                        max-width: 720px;
                    }
                    
                    html {
                        font-size: 16px;
                    }
                }
                
                /* Large devices (desktops, 992px and up) */
                @media (min-width: 992px) {
                    .container {
                        max-width: 960px;
                    }
                }
                
                /* Extra large devices (large desktops, 1200px and up) */
                @media (min-width: 1200px) {
                    .container {
                        max-width: 1140px;
                    }
                }
                
                /* Container and Layout Utilities */
                .container {
                    width: 100%;
                    padding-right: var(--spacing-lg);
                    padding-left: var(--spacing-lg);
                    margin-right: auto;
                    margin-left: auto;
                }
                
                /* Utility Classes */
                .text-primary { color: var(--color-text-primary); }
                .text-secondary { color: var(--color-text-secondary); }
                .text-success { color: var(--color-success); }
                .text-warning { color: var(--color-warning); }
                .text-danger { color: var(--color-danger); }
                .text-info { color: var(--color-info); }
                
                .bg-white { background-color: var(--color-white); }
                .bg-surface { background-color: var(--color-surface); }
                .bg-surface-alt { background-color: var(--color-surface-alt); }
                
                .font-medium { font-weight: var(--font-weight-medium); }
                .font-semibold { font-weight: var(--font-weight-semibold); }
                .font-bold { font-weight: var(--font-weight-bold); }
                
                .text-xs { font-size: var(--font-size-xs); }
                .text-sm { font-size: var(--font-size-sm); }
                .text-base { font-size: var(--font-size-base); }
                .text-lg { font-size: var(--font-size-lg); }
                .text-xl { font-size: var(--font-size-xl); }
                .text-2xl { font-size: var(--font-size-2xl); }
                
                .rounded-sm { border-radius: var(--radius-sm); }
                .rounded-md { border-radius: var(--radius-md); }
                .rounded-lg { border-radius: var(--radius-lg); }
                
                .shadow-sm { box-shadow: var(--shadow-sm); }
                .shadow-md { box-shadow: var(--shadow-md); }
                
                .transition { transition: all var(--transition-normal); }
                .transition-fast { transition: all var(--transition-fast); }
                .transition-slow { transition: all var(--transition-slow); }
                
                /* Navigation Bar Component */
                .navbar {
                    height: 64px;
                    background-color: var(--color-white);
                    box-shadow: var(--shadow-sm);
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 var(--spacing-2xl);
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    border-bottom: 1px solid var(--color-border);
                }
                
                .navbar-brand {
                    font-size: var(--font-size-lg);
                    font-weight: var(--font-weight-bold);
                    color: var(--color-text-primary);
                }
                
                .navbar-status {
                    font-size: var(--font-size-sm);
                    color: var(--color-text-secondary);
                    font-weight: var(--font-weight-medium);
                }
                
                .navbar-status #last-update {
                    font-weight: var(--font-weight-semibold);
                }
                
                /* Main Content Container */
                .main-content {
                    padding: var(--spacing-2xl);
                }
                
                /* Dashboard Grid Layout */
                .dashboard-grid {
                    display: grid;
                    gap: var(--spacing-2xl);
                    height: calc(100vh - 64px - (var(--spacing-2xl) * 2)); /* Full height minus navbar and padding */
                    min-height: 600px;
                }
                
                /* Mobile First - Single Column Layout */
                .dashboard-grid {
                    grid-template-columns: 1fr;
                    grid-template-rows: auto 1fr;
                    grid-template-areas: 
                        "receivers"
                        "feed";
                }
                
                /* Tablet Layout - 768px and up */
                @media (min-width: 768px) {
                    .dashboard-grid {
                        grid-template-columns: 1fr 1fr;
                        grid-template-rows: auto auto 1fr;
                        grid-template-areas: 
                            "receivers receivers"
                            "receivers receivers"
                            "feed feed";
                    }
                }
                
                /* Desktop Layout - 992px and up */
                @media (min-width: 992px) {
                    .dashboard-grid {
                        grid-template-columns: 1fr 1fr;
                        grid-template-rows: 1fr;
                        grid-template-areas: "receivers feed";
                    }
                }
                
                /* Large Desktop Layout - 1200px and up */
                @media (min-width: 1200px) {
                    .dashboard-grid {
                        grid-template-columns: 1.2fr 1fr;
                        grid-template-areas: "receivers feed";
                    }
                }
                
                /* Panel Components */
                .receivers-panel {
                    grid-area: receivers;
                    background-color: var(--color-white);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-sm);
                    padding: var(--spacing-2xl);
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }
                
                .live-feed-panel {
                    grid-area: feed;
                    background-color: var(--color-white);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-sm);
                    padding: var(--spacing-2xl);
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }
                
                /* Panel Headers */
                .panel-header {
                    margin-bottom: var(--spacing-xl);
                    padding-bottom: var(--spacing-md);
                    border-bottom: 1px solid var(--color-border);
                }
                
                .panel-title {
                    font-size: var(--font-size-lg);
                    font-weight: var(--font-weight-semibold);
                    color: var(--color-text-primary);
                    margin: 0;
                }
                
                /* Receivers Grid Container */
                .receivers-grid {
                    display: grid;
                    gap: var(--spacing-lg);
                    flex: 1;
                    overflow-y: auto;
                }
                
                /* Mobile - Single column for receiver cards */
                .receivers-grid {
                    grid-template-columns: 1fr;
                }
                
                /* Tablet - 2x2 grid for receiver cards */
                @media (min-width: 768px) {
                    .receivers-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                
                /* Desktop - Flexible columns based on available space */
                @media (min-width: 992px) {
                    .receivers-grid {
                        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    }
                }
                
                /* Receiver Card Component - Enhanced Visual Elements */
                .receiver-card {
                    width: 320px;
                    height: 200px;
                    background-color: var(--color-white);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-sm);
                    border: 1px solid var(--color-border);
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    transition: all var(--transition-normal);
                    position: relative;
                    justify-self: center; /* Center cards in grid */
                }
                
                /* Card Hover Effects */
                .receiver-card:hover {
                    box-shadow: var(--shadow-md);
                    transform: translateY(-2px);
                }
                
                /* Card Update Flash Animation - Requirements 2.8 */
                .receiver-card.flash-update {
                    border: 2px solid #2563EB;
                    animation: flashBorder 500ms ease-out;
                }
                
                @keyframes flashBorder {
                    0% {
                        border-color: #2563EB;
                        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.3);
                    }
                    100% {
                        border-color: var(--color-border);
                        box-shadow: var(--shadow-sm);
                    }
                }
                
                /* Responsive card sizing */
                @media (max-width: 767px) {
                    .receiver-card {
                        width: 100%;
                        max-width: 320px;
                        height: 200px;
                    }
                }
                
                /* Card Header */
                .card-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: var(--spacing-lg);
                    border-bottom: 1px solid var(--color-border);
                    background-color: var(--color-white);
                }
                
                .receiver-name {
                    font-size: var(--font-size-base);
                    font-weight: var(--font-weight-bold);
                    color: var(--color-text-primary);
                    margin: 0;
                }
                
                /* Status Badge Styling - Enhanced - Requirements 5.3, 5.4, 5.5 */
                .status-badge {
                    font-size: var(--font-size-xs);
                    font-weight: var(--font-weight-medium);
                    padding: var(--spacing-xs) var(--spacing-sm);
                    border-radius: var(--radius-sm);
                    text-transform: uppercase;
                    letter-spacing: 0.025em;
                    transition: all var(--transition-normal);
                    box-shadow: var(--shadow-sm);
                    border: 1px solid transparent;
                }
                
                /* Active Status Badge - Requirements 5.4 */
                .status-badge[data-status="active"] {
                    background-color: #16A34A; /* Requirement 5.4 - #16A34A background */
                    color: var(--color-white);
                    border-color: #15803D;
                }
                
                .status-badge[data-status="active"]:hover {
                    background-color: #15803D;
                    transform: translateY(-1px);
                }
                
                /* Disconnected Status Badge - Requirements 5.5 */
                .status-badge[data-status="disconnected"] {
                    background-color: #DC2626; /* Requirement 5.5 - #DC2626 background */
                    color: var(--color-white);
                    border-color: #B91C1C;
                }
                
                .status-badge[data-status="disconnected"]:hover {
                    background-color: #B91C1C;
                    transform: translateY(-1px);
                }
                
                /* Card Body */
                .card-body {
                    flex: 1;
                    padding: var(--spacing-lg);
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    grid-template-rows: auto auto;
                    gap: var(--spacing-md);
                    position: relative;
                }
                
                /* Device ID Display - Enhanced Prominence - Requirements 2.4 */
                .device-id {
                    grid-column: 1 / -1;
                    font-size: var(--font-size-2xl);
                    font-weight: var(--font-weight-bold);
                    color: var(--color-text-primary);
                    text-align: center;
                    margin-bottom: var(--spacing-sm);
                    letter-spacing: 0.025em;
                    text-transform: uppercase;
                    background: linear-gradient(135deg, var(--color-text-primary) 0%, #374151 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
                }
                
                /* RSSI Display - Enhanced Color-Coding System */
                .rssi-display {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: var(--spacing-sm);
                    border-radius: var(--radius-md);
                    transition: all var(--transition-normal);
                }
                
                .rssi-value {
                    font-size: var(--font-size-2xl);
                    font-weight: var(--font-weight-bold);
                    line-height: 1;
                    transition: color var(--transition-normal);
                }
                
                /* RSSI Color-Coding System - Requirements 2.5 */
                .rssi-value[data-strength="good"] {
                    color: var(--color-success); /* #16A34A - Green for good signal */
                }
                
                .rssi-value[data-strength="medium"] {
                    color: var(--color-warning); /* #F59E0B - Amber for medium signal */
                }
                
                .rssi-value[data-strength="poor"] {
                    color: var(--color-danger); /* #DC2626 - Red for poor signal */
                }
                
                .rssi-label {
                    font-size: var(--font-size-xs);
                    color: var(--color-text-secondary);
                    font-weight: var(--font-weight-medium);
                    margin-top: var(--spacing-xs);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                
                /* Packet Loss Indicator - Enhanced SVG Circular Progress - Requirements 2.6 */
                .packet-loss-indicator {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    padding: var(--spacing-sm);
                }
                
                .progress-circle {
                    width: 48px;
                    height: 48px;
                    transform: rotate(-90deg);
                    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
                }
                
                .progress-bg {
                    fill: none;
                    stroke: #E5E7EB; /* Requirement 2.6 - #E5E7EB background */
                    stroke-width: 4;
                    cx: 24;
                    cy: 24;
                    r: 20;
                }
                
                .progress-arc {
                    fill: none;
                    stroke: #2563EB; /* Requirement 2.6 - #2563EB progress arc */
                    stroke-width: 4;
                    stroke-linecap: round;
                    cx: 24;
                    cy: 24;
                    r: 20;
                    stroke-dasharray: 125.66; /* 2 * π * 20 */
                    stroke-dashoffset: 125.66;
                    transition: stroke-dashoffset var(--transition-slow);
                }
                
                /* Dynamic Progress Arc Calculations for Any Percentage */
                .progress-arc[data-percentage="0"] {
                    stroke-dashoffset: 125.66;
                }
                
                .progress-arc[data-percentage="1"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.01));
                }
                
                .progress-arc[data-percentage="2"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.02));
                }
                
                .progress-arc[data-percentage="3"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.03));
                }
                
                .progress-arc[data-percentage="4"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.04));
                }
                
                .progress-arc[data-percentage="5"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.05));
                }
                
                .progress-arc[data-percentage="10"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.10));
                }
                
                .progress-arc[data-percentage="15"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.15));
                }
                
                .progress-arc[data-percentage="20"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.20));
                }
                
                .progress-arc[data-percentage="25"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.25));
                }
                
                .progress-arc[data-percentage="30"] {
                    stroke-dashoffset: calc(125.66 - (125.66 * 0.30));
                }
                
                .loss-percentage {
                    position: absolute;
                    font-size: var(--font-size-xs);
                    font-weight: var(--font-weight-semibold);
                    color: var(--color-text-primary);
                    text-align: center;
                    line-height: 1;
                }
                
                /* Sequence Number - Enhanced Positioning - Requirements 2.7 */
                .sequence-number {
                    position: absolute;
                    bottom: var(--spacing-sm);
                    right: var(--spacing-sm);
                    font-size: var(--font-size-xs);
                    color: var(--color-text-secondary);
                    font-weight: var(--font-weight-medium);
                    background-color: rgba(255, 255, 255, 0.8);
                    padding: var(--spacing-xs) var(--spacing-sm);
                    border-radius: var(--radius-sm);
                    backdrop-filter: blur(4px);
                    border: 1px solid rgba(107, 114, 128, 0.2);
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    letter-spacing: 0.05em;
                }
                
                /* Live Feed Container */
                .feed-content {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }
                
                /* Feed Header with Search/Filter - Task 8 - Requirements 5.1, 5.2 */
                .feed-header {
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                    margin-bottom: var(--spacing-lg);
                    padding: 0 var(--spacing-xs);
                }
                
                /* Filter Input Styling - Requirement 5.1 */
                .filter-input {
                    width: 240px;
                    padding: var(--spacing-sm) var(--spacing-md);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    font-size: var(--font-size-sm);
                    font-family: var(--font-family);
                    color: var(--color-text-primary);
                    background-color: var(--color-white);
                    transition: all var(--transition-normal);
                    box-shadow: var(--shadow-sm);
                }
                
                .filter-input:focus {
                    outline: none;
                    border-color: var(--color-info);
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
                }
                
                .filter-input::placeholder {
                    color: var(--color-text-secondary);
                    font-style: italic;
                }
                
                /* Responsive filter input */
                @media (max-width: 767px) {
                    .feed-header {
                        justify-content: center;
                        margin-bottom: var(--spacing-md);
                    }
                    
                    .filter-input {
                        width: 100%;
                        max-width: 280px;
                    }
                }
                
                /* Responsive Behavior Enhancements */
                @media (max-width: 767px) {
                    .main-content {
                        padding: var(--spacing-lg);
                    }
                    
                    .dashboard-grid {
                        gap: var(--spacing-lg);
                        height: auto;
                        min-height: auto;
                    }
                    
                    .receivers-panel,
                    .live-feed-panel {
                        padding: var(--spacing-lg);
                    }
                    
                    /* Make live feed collapsible on mobile */
                    .live-feed-panel {
                        max-height: 400px;
                    }
                }
                
                /* Smooth transitions for responsive changes */
                .dashboard-grid,
                .receivers-grid,
                .receivers-panel,
                .live-feed-panel {
                    transition: all var(--transition-normal);
                }
                
                /* Live Feed Table Structure and Styling - Task 7 */
                /* Requirements: 3.1, 3.2, 3.3, 3.4, 3.8 */
                
                /* Scrollable table container with white background and border radius - Requirement 3.1 */
                .table-container {
                    flex: 1;
                    overflow-y: auto;
                    background-color: var(--color-white);
                    border-radius: var(--radius-lg);
                    border: 1px solid var(--color-border);
                    box-shadow: var(--shadow-sm);
                }
                
                /* Data table styling - Requirements 3.2, 3.4 */
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: var(--font-size-sm); /* 14px font - Requirement 3.4 */
                    background-color: var(--color-white);
                    margin: 0;
                }
                
                /* Sticky header with specified colors - Requirement 3.3 */
                .sticky-header {
                    position: sticky;
                    top: 0;
                    z-index: 10;
                }
                
                .sticky-header th {
                    background-color: #F3F4F6; /* Requirement 3.3 - #F3F4F6 background */
                    color: #6B7280; /* Requirement 3.3 - #6B7280 text */
                    font-weight: var(--font-weight-bold); /* 14px bold font - Requirement 3.3 */
                    font-size: var(--font-size-sm);
                    padding: var(--spacing-md) var(--spacing-lg);
                    text-align: left;
                    border: none;
                    border-bottom: 1px solid var(--color-border);
                    text-transform: uppercase;
                    letter-spacing: 0.025em;
                    white-space: nowrap;
                }
                
                /* Table body styling */
                .data-table tbody tr {
                    transition: background-color var(--transition-fast);
                }
                
                /* Alternating row backgrounds - Requirement 3.4 */
                .data-table tbody tr:nth-child(odd) {
                    background-color: #FFFFFF; /* Requirement 3.4 - #FFFFFF */
                }
                
                .data-table tbody tr:nth-child(even) {
                    background-color: #F9FAFB; /* Requirement 3.4 - #F9FAFB */
                }
                
                /* Table cell styling - Requirement 3.4 */
                .data-table td {
                    padding: var(--spacing-md) var(--spacing-lg);
                    border: none;
                    border-bottom: 1px solid rgba(229, 231, 235, 0.5);
                    color: var(--color-text-primary);
                    font-size: var(--font-size-sm); /* 14px font - Requirement 3.4 */
                    vertical-align: middle;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                /* Hover effects for better UX */
                .data-table tbody tr:hover {
                    background-color: rgba(37, 99, 235, 0.05);
                }
                
                /* Specific column styling */
                .data-table .device-id-col {
                    font-weight: var(--font-weight-semibold);
                    color: var(--color-text-primary);
                }
                
                .data-table .rssi-col {
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-weight: var(--font-weight-medium);
                }
                
                .data-table .seq-col,
                .data-table .packet-loss-col {
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    text-align: center;
                }
                
                .data-table .time-col {
                    color: var(--color-text-secondary);
                    font-size: var(--font-size-xs);
                }
                
                .data-table .uid-col {
                    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                    font-size: var(--font-size-xs);
                    color: var(--color-text-secondary);
                    max-width: 120px;
                }
                
                /* Responsive table behavior */
                @media (max-width: 767px) {
                    .table-container {
                        border-radius: var(--radius-md);
                    }
                    
                    .sticky-header th,
                    .data-table td {
                        padding: var(--spacing-sm) var(--spacing-md);
                        font-size: var(--font-size-xs);
                    }
                    
                    /* Hide less critical columns on mobile */
                    .data-table .uid-col,
                    .data-table .receiver-col {
                        display: none;
                    }
                }
            </style>
            
            <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
            <script>
                /**
                 * Filter functionality for live feed table - Task 8
                 * Requirements: 5.1, 5.2 - Real-time filtering by Device ID
                 */
                function applyFilter() {
                    const filterInput = document.getElementById('device-filter');
                    const filterValue = filterInput.value.toLowerCase().trim();
                    const tableBody = document.getElementById('data-rows');
                    const rows = tableBody.getElementsByTagName('tr');
                    
                    // Show/hide rows based on filter - Requirement 5.2
                    for (let i = 0; i < rows.length; i++) {
                        const row = rows[i];
                        const deviceIdCell = row.querySelector('.device-id-col');
                        
                        if (deviceIdCell) {
                            const deviceId = deviceIdCell.textContent.toLowerCase();
                            
                            // Show row if filter is empty or device ID contains filter text
                            if (filterValue === '' || deviceId.includes(filterValue)) {
                                row.style.display = '';
                            } else {
                                row.style.display = 'none';
                            }
                        }
                    }
                }
                
                document.addEventListener("DOMContentLoaded", function() {
                    var socket = io();
                    
                    // Initialize last update timestamp on page load
                    var now = new Date();
                    var timeString = now.toLocaleTimeString('en-US', { 
                        hour12: false, 
                        hour: '2-digit', 
                        minute: '2-digit', 
                        second: '2-digit' 
                    });
                    document.getElementById('last-update').textContent = timeString;
                    
                    // Initialize filter functionality - Task 8 - Requirements 5.1, 5.2
                    const filterInput = document.getElementById('device-filter');
                    
                    if (filterInput) {
                        // Real-time filtering on input - Requirement 5.2
                        filterInput.addEventListener('input', function() {
                            applyFilter();
                        });
                        
                        // Also filter on keyup for better responsiveness
                        filterInput.addEventListener('keyup', function() {
                            applyFilter();
                        });
                        
                        // Clear filter on Escape key
                        filterInput.addEventListener('keydown', function(event) {
                            if (event.key === 'Escape') {
                                filterInput.value = '';
                                applyFilter();
                            }
                        });
                    }
                    
                    // WebSocket connection status
                    socket.on('connect', function() {
                        console.log('WebSocket connected');
                    });
                    
                    socket.on('disconnect', function() {
                        console.log('WebSocket disconnected');
                    });

                    /**
                     * Update receiver card data and trigger flash animation
                     * Requirements: 2.8, 6.1, 6.2, 6.3
                     */
                    function updateReceiverCard(deviceId, data, seq, packetLoss) {
                        // Find the receiver card for this device
                        let receiverCard = document.querySelector(`[data-device-id="${deviceId}"]`);
                        
                        // If card doesn't exist, create it
                        if (!receiverCard) {
                            receiverCard = createReceiverCard(deviceId);
                        }
                        
                        // Update RSSI value and color coding
                        const rssiValue = receiverCard.querySelector('.rssi-value');
                        if (rssiValue) {
                            if (data.rssi) {
                                rssiValue.textContent = data.rssi;
                                
                                // Update RSSI color coding based on signal strength
                                rssiValue.removeAttribute('data-strength');
                                if (data.rssi >= -50) {
                                    rssiValue.setAttribute('data-strength', 'good');
                                } else if (data.rssi >= -70) {
                                    rssiValue.setAttribute('data-strength', 'medium');
                                } else {
                                    rssiValue.setAttribute('data-strength', 'poor');
                                }
                            } else {
                                rssiValue.textContent = '--';
                                rssiValue.removeAttribute('data-strength');
                            }
                        }
                        
                        // Update sequence number
                        const sequenceNumber = receiverCard.querySelector('.sequence-number');
                        if (sequenceNumber) {
                            sequenceNumber.textContent = `Seq: ${seq}`;
                        }
                        
                        // Update packet loss indicator
                        const lossPercentage = receiverCard.querySelector('.loss-percentage');
                        const progressArc = receiverCard.querySelector('.progress-arc');
                        if (lossPercentage && progressArc) {
                            // Calculate packet loss percentage (simple approximation)
                            const lossPercent = Math.min(packetLoss, 30); // Cap at 30% for display
                            lossPercentage.textContent = `${lossPercent}%`;
                            progressArc.setAttribute('data-percentage', lossPercent.toString());
                            
                            // Update stroke-dashoffset for progress arc
                            const circumference = 125.66; // 2 * π * 20
                            const offset = circumference - (circumference * (lossPercent / 100));
                            progressArc.style.strokeDashoffset = offset;
                        }
                        
                        // Update status badge to active when receiving data
                        const statusBadge = receiverCard.querySelector('.status-badge');
                        if (statusBadge) {
                            statusBadge.setAttribute('data-status', 'active');
                            statusBadge.textContent = 'Active';
                        }
                        
                        // Add flash-update class to trigger animation
                        receiverCard.classList.add('flash-update');
                        
                        // Remove the class after animation completes (500ms)
                        setTimeout(() => {
                            receiverCard.classList.remove('flash-update');
                        }, 500);
                    }

                    /**
                     * Create a new receiver card for a device
                     */
                    function createReceiverCard(deviceId) {
                        const container = document.getElementById('receivers-container');
                        
                        // Create the card HTML
                        const cardHTML = `
                            <div class="receiver-card" data-device-id="${deviceId}">
                                <div class="card-header">
                                    <h3 class="receiver-name">${deviceId}</h3>
                                    <span class="status-badge" data-status="disconnected">Disconnected</span>
                                </div>
                                <div class="card-body">
                                    <div class="device-id">${deviceId}</div>
                                    <div class="rssi-display">
                                        <span class="rssi-value">--</span>
                                        <span class="rssi-label">RSSI</span>
                                    </div>
                                    <div class="packet-loss-indicator">
                                        <svg class="progress-circle">
                                            <circle class="progress-bg" cx="24" cy="24" r="20"></circle>
                                            <circle class="progress-arc" cx="24" cy="24" r="20" data-percentage="0"></circle>
                                        </svg>
                                        <span class="loss-percentage">0%</span>
                                    </div>
                                    <div class="sequence-number">Seq: --</div>
                                </div>
                            </div>
                        `;
                        
                        // Create a temporary div to hold the HTML
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = cardHTML;
                        const newCard = tempDiv.firstElementChild;
                        
                        // Add the card to the container
                        container.appendChild(newCard);
                        
                        return newCard;
                    }

                    socket.on('new_data', function(msg) {
                        console.log('Received new data:', msg); // Debug log
                        
                        // Update last update timestamp
                        var now = new Date();
                        var timeString = now.toLocaleTimeString('en-US', { 
                            hour12: false, 
                            hour: '2-digit', 
                            minute: '2-digit', 
                            second: '2-digit' 
                        });
                        document.getElementById('last-update').textContent = timeString;
                        
                        // Update the corresponding receiver card with new data and flash animation
                        updateReceiverCard(msg.device_id, msg.data, msg.seq, msg.packet_loss);
                        
                        // Add new row to live feed table with proper structure - Task 7
                        var tableBody = document.getElementById("data-rows");
                        var row = tableBody.insertRow(0); // Insert at top for newest first
                        
                        // Create cells with proper classes and data - Requirements 3.2, 3.4
                        var deviceIdCell = row.insertCell(0);
                        deviceIdCell.className = 'device-id-col';
                        deviceIdCell.textContent = msg.device_id;
                        
                        var receiverCell = row.insertCell(1);
                        receiverCell.className = 'receiver-col';
                        receiverCell.textContent = `Receiver ${msg.device_id.replace(/[^0-9]/g, '') || '1'}`;
                        
                        var seqCell = row.insertCell(2);
                        seqCell.className = 'seq-col';
                        seqCell.textContent = msg.seq;
                        
                        var packetLossCell = row.insertCell(3);
                        packetLossCell.className = 'packet-loss-col';
                        packetLossCell.textContent = msg.packet_loss;
                        
                        var rssiCell = row.insertCell(4);
                        rssiCell.className = 'rssi-col';
                        rssiCell.textContent = msg.data.rssi || '--';
                        
                        var timeCell = row.insertCell(5);
                        timeCell.className = 'time-col';
                        timeCell.textContent = timeString;

                        // Keep only the latest 20 rows
                        var rows = tableBody.getElementsByTagName('tr');
                        if (rows.length > 20) {
                            tableBody.removeChild(rows[rows.length - 1]); // Remove oldest row
                        }
                        
                        // Apply current filter to new row - Requirement 5.2
                        applyFilter();
                    });

                });
            </script>
        </head>
        <body>
            <!-- Navigation Bar Component -->
            <nav class="navbar">
                <div class="navbar-brand">IoT Receiver Monitor</div>
                <div class="navbar-status">Last Update: <span id="last-update">--</span></div>
            </nav>
            
            <div class="main-content">
                <div class="dashboard-grid">
                    <!-- Receivers Overview Panel -->
                    <div class="receivers-panel">
                        <div class="panel-header">
                            <h2 class="panel-title">Receiver Overview</h2>
                        </div>
                        <div class="receivers-grid" id="receivers-container">
                            <!-- Receiver cards will be dynamically created when devices send data -->
                        </div>
                    </div>
                    
                    <!-- Live Feed Panel -->
                    <div class="live-feed-panel">
                        <div class="panel-header">
                            <h2 class="panel-title">Live Data Feed</h2>
                        </div>
                        <div class="feed-content">
                            <!-- Search/Filter Header - Task 8 - Requirements 5.1, 5.2 -->
                            <div class="feed-header">
                                <input type="text" class="filter-input" id="device-filter" placeholder="Filter by Device ID..." autocomplete="off">
                            </div>
                            <!-- Scrollable table container with proper structure - Task 7 -->
                            <div class="table-container">
                                <table class="data-table" id="data-table">
                                    <!-- Sticky header with proper columns - Requirements 3.2, 3.3 -->
                                    <thead class="sticky-header">
                                        <tr>
                                            <th class="device-id-header">Device ID</th>
                                            <th class="receiver-header">Receiver</th>
                                            <th class="seq-header">Seq #</th>
                                            <th class="packet-loss-header">Packet Loss</th>
                                            <th class="rssi-header">RSSI</th>
                                            <th class="time-header">Time</th>
                                        </tr>
                                    </thead>
                                    <!-- Table body with alternating row backgrounds - Requirement 3.4 -->
                                    <tbody id="data-rows">
                                        {% for device_id, data, seq, packet_loss, timestamp in rows %}
                                            {% set data_obj = data|from_json if data else {} %}
                                            <tr>
                                                <td class="device-id-col">{{ device_id }}</td>
                                                <td class="receiver-col">Receiver {{ device_id.replace('RX', '').replace('rx', '') or loop.index }}</td>
                                                <td class="seq-col">{{ seq }}</td>
                                                <td class="packet-loss-col">{{ packet_loss }}</td>
                                                <td class="rssi-col">{{ data_obj.get('rssi', '--') if data_obj else '--' }}</td>
                                                <td class="time-col">{{ timestamp.split('T')[1].split('.')[0] if timestamp else '--:--:--' }}</td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    
    return render_template_string(html, rows=rows)

if __name__ == '__main__':
    global finaltime
    global DATABASE_PATH
    global DATABASE_NAME
    finaltime = time.ctime()
    DATABASE_NAME = str("device_data_"+finaltime+"_.db").replace(" ", "_").replace(":", "_")
    DATABASE_PATH = os.getcwd() + "/" + DATABASE_NAME
    init_db()
    socketio.run(app, debug=True, host="0.0.0.0", port=8000, allow_unsafe_werkzeug=True, use_reloader=True)
