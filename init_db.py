"""Utility: initialize the SQLite DB for the hostel complaints app.

Run with: `python init_db.py` to create `instance/complaints.db` and the table.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'complaints.db')

def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        room TEXT,
        title TEXT,
        description TEXT,
        image TEXT,
        status TEXT DEFAULT 'open',
        created_at TEXT
    )
    ''')
    conn.commit()
    conn.close()
    print('Initialized DB at', DB_PATH)

if __name__ == '__main__':
    ensure_db()
