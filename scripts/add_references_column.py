import sqlite3
import os

db_path = r"C:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Thesis Backend\thesis.db"

def migrate():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Checking for 'references' column in 'papers' table...")
        cursor.execute("PRAGMA table_info(papers)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'references' not in columns:
            print("Adding 'references' column...")
            cursor.execute("ALTER TABLE papers ADD COLUMN references TEXT")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column 'references' already exists.")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
