import sqlite3
import os

DB_PATH = "thesis.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"Adding 'media' column to 'papers' table in {DB_PATH}...")
        cursor.execute("ALTER TABLE papers ADD COLUMN media JSON")
        conn.commit()
        print("Migration successful: Added 'media' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column name: media" in str(e).lower():
            print("Skipped: 'media' column already exists.")
        else:
            print(f"Database error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
