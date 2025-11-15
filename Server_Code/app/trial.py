import os
import sqlite3
import app as app_module

TEST_DB = 'data_store/device_data.db'
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

app_module.DATABASE_PATH = TEST_DB
app_module.init_db()
client = app_module.app.test_client()

resp = client.get('/data/all')
assert resp.status_code == 200, resp.status_code
assert resp.get_json()['rows'] == []

payload = {
    'device_id': 'RX001',
    'seq': 1,
    'packet_loss': 0.0,
    'data': '{"rssi": -55}',
    'timestamp': '2024-01-01T00:00:00'
}
with sqlite3.connect(TEST_DB) as conn:
    conn.execute("INSERT INTO data (device_id, seq, packet_loss, data, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (payload['device_id'], payload['seq'], payload['packet_loss'], payload['data'], payload['timestamp']))
    conn.commit()