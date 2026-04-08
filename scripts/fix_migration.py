import sqlite3
import os

db_path = r"C:\Users\Maruf\Documents\BSCS-4A (2025)\Undergrad Thesis 1\Thesis Backend\thesis.db"

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Quote the column name because 'references' is a reserved keyword
        cursor.execute('ALTER TABLE papers ADD COLUMN "references" TEXT')
        conn.commit()
        print("Column 'references' added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Column 'references' already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
