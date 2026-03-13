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
        # IMRAD extracted text
        ("introduction", "TEXT"),
        ("methods", "TEXT"),
        ("results", "TEXT"),
        ("discussion", "TEXT"),
        # IMRAD summaries (2-column view)
        ("introduction_summary", "TEXT"),
        ("methods_summary", "TEXT"),
        ("results_summary", "TEXT"),
        ("discussion_summary", "TEXT"),
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

    # 4. Create 'borrow_records' table
    print("Creating 'borrow_records' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            borrow_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            due_date DATETIME NOT NULL,
            return_date DATETIME,
            status TEXT DEFAULT 'Borrowed',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
        )
    """)
    print("borrow_records table ready.")

    # 5. Create 'penalties' table
    print("Creating 'penalties' table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            borrow_record_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Unpaid',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (borrow_record_id) REFERENCES borrow_records(id) ON DELETE CASCADE
        )
    """)
    print("penalties table ready.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

def reindex_with_imrad():
    """
    Re-indexes all existing papers in Qdrant with IMRAD section vectors.
    Run once after deploying the IMRAD feature to upgrade existing papers.
    Usage: python migrate_db.py --reindex-imrad
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from app.services.imrad_service import imrad_service
    from app.services.vector_db import vector_db
    from pypdf import PdfReader

    db_path = 'thesis.db'
    if not os.path.exists(db_path):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, abstract, file_path FROM papers")
    papers = cursor.fetchall()
    conn.close()

    print(f"\n📚 Re-indexing {len(papers)} papers with IMRAD vectors...\n")
    success, skipped, failed = 0, 0, 0

    for paper_id, title, abstract, file_path in papers:
        print(f"[{paper_id}] {title[:60]}...")
        full_text = abstract or ""

        # Try to read the full PDF for richer section detection
        if file_path and os.path.exists(file_path):
            try:
                reader = PdfReader(file_path)
                for i in range(min(20, len(reader.pages))):
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        full_text += page_text + "\n"
            except Exception as e:
                print(f"  ⚠️ PDF read error: {e} — falling back to abstract only")

        if not full_text.strip():
            print(f"  ⚠️ No content found. Skipping.")
            skipped += 1
            continue

        try:
            sections = imrad_service.extract_sections(full_text)
            all_vectors = imrad_service.build_vectors(
                title=title or "",
                sections=sections,
                abstract=abstract or ""
            )
            vector_db.upsert_paper(
                paper_id=paper_id,
                vectors=all_vectors,
                metadata={
                    "title": title,
                    "abstract": abstract,
                }
            )
            detected = [k for k in sections.keys()] if sections else []
            print(f"  ✅ Vectors built: {list(all_vectors.keys())} | IMRAD detected: {detected}")
            success += 1
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Re-indexing complete: {success} success | {skipped} skipped | {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys
    if "--reindex-imrad" in sys.argv:
        reindex_with_imrad()
    else:
        migrate()