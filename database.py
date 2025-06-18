import sqlite3
from datetime import datetime
import csv

DB_PATH = "applications.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            city TEXT,
            phone TEXT,
            finance TEXT,
            problems TEXT,
            status TEXT DEFAULT 'pending',
            user_id INTEGER,
            username TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_application(data: dict, user_id: int, username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO applications (name, age, city, phone, finance, problems, status, user_id, username)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
    ''', (
        data['name'],
        data['age'],
        data['city'],
        data['phone'],
        data['finance'],
        data['problems'],
        user_id,
        username
    ))
    conn.commit()
    conn.close()

def update_application_status(user_id: int, status: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE applications SET status = ?, submitted_at = ?
        WHERE user_id = ?
    ''', (status, datetime.now(), user_id))
    conn.commit()
    conn.close()

def list_last_applications(limit=10):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, name, age, city, phone, status FROM applications
        ORDER BY submitted_at DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def export_applications_to_csv(filename="applications_export.csv"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM applications ORDER BY submitted_at DESC")
    rows = c.fetchall()
    headers = [description[0] for description in c.description]
    conn.close()

    with open(filename, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return filename
