import sqlite3
import os

DB_PATH = "thesis.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file {DB_PATH} not found.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Executing migration: Updating 'User' roles to 'Student'...")
        
        # Update authorized_users table
        cursor.execute("UPDATE authorized_users SET role = 'Student' WHERE role = 'User'")
        affected = cursor.rowcount
        
        conn.commit()
        print(f"Success! {affected} record(s) updated in 'authorized_users' table.")
        
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
