from flask import Flask, request, render_template, g, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(DATA_DIR, 'wakeywakey.db')

# --- DATABASE HELPERS ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                driver TEXT,
                status TEXT,
                seconds_closed REAL DEFAULT 0,
                timestamp TEXT
            )
        ''')
        db.commit()

# --- ROUTES ---
@app.route('/api/upload', methods=['POST'])
def upload():
    data = request.json
    if not data:
        return {"message": "No data received"}, 400

    db = get_db()
    db.execute(
        "INSERT INTO logs (driver, status, seconds_closed, timestamp) VALUES (?, ?, ?, ?)",
        (
            data.get('driver', 'Unknown'),
            data.get('status', 'N/A'),
            data.get('seconds_closed', 0),
            datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
        )
    )
    db.commit()
    return {"message": "Data stored successfully"}, 200

@app.route('/')
def dashboard():
    db = get_db()
    logs = db.execute("SELECT * FROM logs ORDER BY id DESC").fetchall()

    count_awake = db.execute("SELECT COUNT(*) FROM logs WHERE status='awake'").fetchone()[0]
    count_drowsy = db.execute("SELECT COUNT(*) FROM logs WHERE status='drowsy'").fetchone()[0]
    count_microsleep = db.execute("SELECT COUNT(*) FROM logs WHERE status='microsleep'").fetchone()[0]

    # Handle missing 'seconds_closed' gracefully
    seconds_values = [row['seconds_closed'] if 'seconds_closed' in row.keys() else 0 for row in logs][-10:]
    labels = [row['timestamp'] for row in logs][-10:]

    return render_template(
        'dashboard.html',
        logs=logs,
        labels=labels,
        seconds_values=seconds_values,
        count_awake=count_awake,
        count_drowsy=count_drowsy,
        count_microsleep=count_microsleep,
        current_year=datetime.now().year
    )

@app.route('/api/logs')
def get_logs():
    db = get_db()
    logs = db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10").fetchall()
    data = {
        "timestamps": [row['timestamp'] for row in logs][::-1],
        "seconds_closed": [row['seconds_closed'] if 'seconds_closed' in row.keys() else 0 for row in logs][::-1],
        "statuses": [row['status'] for row in logs][::-1]
    }
    return jsonify(data)

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
