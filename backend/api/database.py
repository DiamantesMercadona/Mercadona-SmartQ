import sqlite3
from typing import List, Dict

DATABASE_PATH = "queues.db"

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            length INTEGER NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    # Insertar datos de ejemplo
    cursor.execute("INSERT OR IGNORE INTO queues (id, name, length, status) VALUES (1, 'Caja 1', 5, 'activa')")
    cursor.execute("INSERT OR IGNORE INTO queues (id, name, length, status) VALUES (2, 'Caja 2', 3, 'activa')")
    cursor.execute("INSERT OR IGNORE INTO queues (id, name, length, status) VALUES (3, 'Caja 3', 0, 'cerrada')")
    conn.commit()
    conn.close()

def get_queues() -> List[Dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, length, status FROM queues")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "name": row[1], "length": row[2], "status": row[3]} for row in rows]

def update_queue(queue_id: int, length: int, status: str):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE queues SET length = ?, status = ? WHERE id = ?", (length, status, queue_id))
    conn.commit()
    conn.close()