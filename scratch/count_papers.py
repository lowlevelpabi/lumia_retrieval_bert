import sqlite3
import os

db_path = 'thesis.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='papers';")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) FROM papers;")
        count = cursor.fetchone()[0]
        print(f"Total papers in database: {count}")
    else:
        print("Table 'papers' not found.")
    conn.close()
else:
    print("thesis.db not found.")
