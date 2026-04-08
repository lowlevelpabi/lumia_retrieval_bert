import sqlite3
import os

db_path = r"C:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Thesis Backend\thesis.db"

def list_tables():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [tbl[0] for tbl in cursor.fetchall()]
        print("Tables in database:")
        for table in tables:
            print(f"- {table}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    list_tables()
