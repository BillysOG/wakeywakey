from flask import Flask, request, render_template, g
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

# --- Set up folder for database ---
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
                score INTEGER DEFAULT 0,
                timestamp TEXT
            )
        ''')
        db.commit()

# --- ROUTES ---

# Receive data from Raspberry Pi or any client
@app.route('/api/upload', methods=['POST'])
def upload():
    data = request.json
    if not data:
        return {"message": "No data received"}, 400

    db = get_db()
    db.execute(
        "INSERT INTO logs (driver, status, score, timestamp) VALUES (?, ?, ?, ?)",
        (
            data.get('driver', 'Unknown'),
            data.get('status', 'N/A'),
            data.get('score', 0),
            datetime.now().strftime("%d %b %Y, %I:%M:%S %p")  # includes seconds
        )
    )
    db.commit()
    return {"message": "Data stored successfully"}, 200


# Serve the dashboard page
@app.route('/')
def dashboard():
    db = get_db()
    logs = db.execute("SELECT * FROM logs ORDER BY id DESC").fetchall()

    count_awake = db.execute("SELECT COUNT(*) FROM logs WHERE status='awake'").fetchone()[0]
    count_drowsy = db.execute("SELECT COUNT(*) FROM logs WHERE status='drowsy'").fetchone()[0]
    count_microsleep = db.execute("SELECT COUNT(*) FROM logs WHERE status='microsleep'").fetchone()[0]

    labels = [row['timestamp'] for row in logs][-10:]
    scores = [row['score'] for row in logs][-10:]

    return render_template(
        'dashboard.html',
        logs=logs,
        labels=labels,
        scores=scores,
        count_awake=count_awake,
        count_drowsy=count_drowsy,
        count_microsleep=count_microsleep,
        current_year=datetime.now().year
    )


# --- API route for live chart data ---
@app.route('/api/logs')
def get_logs():
    db = get_db()
    logs = db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10").fetchall()
    data = {
        "labels": [row['timestamp'] for row in logs][::-1],
        "scores": [row['score'] for row in logs][::-1],
        "statuses": [row['status'] for row in logs][::-1]
    }
    return data


# --- MAIN EXECUTION ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)
