import sqlite3
import os

def migrate():
    db_path = 'thesis.db'
    if not os.path.exists(db_path):
        print("Database not found. Skipping migration.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Update 'papers' table
    print("Migrating 'papers' table...")
    columns_to_add = [
        ("department", "TEXT DEFAULT 'N/A'"),
        ("keywords", "TEXT DEFAULT ''"),
        ("citation_count", "INTEGER DEFAULT 0")
    ]

    for col_name, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE papers ADD COLUMN {col_name} {col_def}")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError:
            print(f"Column '{col_name}' already exists.")

    # 2. Create 'users' table
    print("Creating 'users' table if it doesn't exist...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            hashed_password TEXT,
            role TEXT DEFAULT 'User'
        )
    """)
    print("Users table ready.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
