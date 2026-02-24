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
        ("project_type", "TEXT DEFAULT 'N/A'"),
        ("degree_program", "TEXT DEFAULT 'N/A'"),
        ("citation_count", "INTEGER DEFAULT 0"),
        ("view_count", "INTEGER DEFAULT 0"),
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

    # 3. Create 'user_citations' junction table
    print("Creating 'user_citations' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            paper_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
            UNIQUE (user_id, paper_id)
        )
    """)
    print("user_citations table ready.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
