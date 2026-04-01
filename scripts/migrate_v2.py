import sqlite3
import os

DB_PATH = "thesis.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Disable Foreign Keys
        cursor.execute("PRAGMA foreign_keys = OFF;")

        # 2. Handle 'papers' table (Add 11 columns)
        print("Migrating 'papers' table...")
        cursor.execute("ALTER TABLE papers RENAME TO papers_old;")
        
        # Create new papers table with all columns from model
        cursor.execute("""
            CREATE TABLE papers (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                title VARCHAR,
                author VARCHAR,
                year VARCHAR,
                abstract TEXT,
                department VARCHAR DEFAULT 'N/A',
                keywords TEXT DEFAULT '',
                project_type VARCHAR DEFAULT 'N/A',
                degree_program VARCHAR DEFAULT 'N/A',
                citation_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                file_path VARCHAR,
                uploaded_by VARCHAR,
                uploader_role VARCHAR,
                media JSON,
                introduction TEXT,
                methods TEXT,
                results TEXT,
                discussion TEXT,
                introduction_summary TEXT,
                methods_summary TEXT,
                results_summary TEXT,
                discussion_summary TEXT,
                created_at DATETIME,
                updated_at DATETIME
            );
        """)
        
        # Copy existing data
        cursor.execute("""
            INSERT INTO papers (
                id, title, author, year, abstract, department, keywords, 
                project_type, degree_program, citation_count, view_count, 
                file_path, created_at, updated_at
            )
            SELECT 
                id, title, author, year, abstract, department, keywords, 
                project_type, degree_program, citation_count, view_count, 
                file_path, created_at, updated_at
            FROM papers_old;
        """)

        # 3. Handle Users migration
        print("Migrating users to 'authorized_users' and 'students'...")
        
        # Create new tables first (if they don't exist)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authorized_users (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                username VARCHAR UNIQUE,
                full_name VARCHAR,
                email VARCHAR UNIQUE,
                hashed_password VARCHAR,
                role VARCHAR
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                username VARCHAR UNIQUE,
                full_name VARCHAR,
                email VARCHAR UNIQUE,
                hashed_password VARCHAR
            );
        """)

        # Migrate existing users
        cursor.execute("SELECT username, email, hashed_password, role FROM users;")
        users = cursor.fetchall()
        for username, email, hashed_password, role in users:
            if role in ('Admin', 'Faculty'):
                cursor.execute("""
                    INSERT OR IGNORE INTO authorized_users (username, email, hashed_password, role)
                    VALUES (?, ?, ?, ?);
                """, (username, email, hashed_password, role))
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO students (username, email, hashed_password)
                    VALUES (?, ?, ?);
                """, (username, email, hashed_password))

        # 4. Handle 'user_citations'
        print("Resetting 'user_citations' table...")
        cursor.execute("DROP TABLE IF EXISTS user_citations;")
        cursor.execute("""
            CREATE TABLE user_citations (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                paper_id INTEGER NOT NULL,
                created_at DATETIME,
                CONSTRAINT unique_user_paper_citation UNIQUE (user_id, paper_id),
                FOREIGN KEY(user_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY(paper_id) REFERENCES papers (id) ON DELETE CASCADE
            );
        """)

        # 5. Drop legacy tables
        print("Dropping legacy tables...")
        cursor.execute("DROP TABLE IF EXISTS papers_old;")
        cursor.execute("DROP TABLE IF EXISTS users;")
        cursor.execute("DROP TABLE IF EXISTS borrow_records;")
        cursor.execute("DROP TABLE IF EXISTS penalties;")

        # 6. Commit and Re-enable Foreign Keys
        conn.commit()
        cursor.execute("PRAGMA foreign_keys = ON;")
        print("Migration completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
