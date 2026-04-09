import os
import shutil
import pathlib
import sys
import sqlite3
import argparse

# --- Constants ---
DB_PATH = "thesis.db"
QDRANT_DIR = "qdrant_storage"
UPLOADS_DIR = "uploads"

# Tables to wipe when 'papers' is selected (including dependents)
PAPER_RELATED_TABLES = [
    "user_citations",
    "penalties",
    "borrow_records",
    "papers",
]

def print_banner(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

def clear_directory(path: pathlib.Path, name: str):
    if path.exists():
        try:
            print(f"--- Clearing {name} ---")
            shutil.rmtree(path)
            path.mkdir()
            print(f"✓ Successfully cleared {name}")
        except PermissionError:
            print(f"✗ ERROR: Could not clear {name}. Is the server still running?")
        except Exception as e:
            print(f"✗ ERROR clearing {name}: {e}")
    else:
        path.mkdir()
        print(f"✓ Created {name} folder (already clean)")

def wipe_tables():
    if not os.path.exists(DB_PATH):
        print(f"! {DB_PATH} not found. Nothing to wipe.")
        return

    print("--- Wiping Database Tables (Papers & Dependents) ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Disable foreign keys temporarily if needed, though we drop in order
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        for table in PAPER_RELATED_TABLES:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"  - Dropping table: {table}")
                cursor.execute(f"DROP TABLE {table}")
            else:
                print(f"  ! Table {table} not found (skipping)")
        
        conn.commit()
        print("✓ Successfully wiped paper-related tables.")
        print("! NOTE: You MUST run 'python migrate.py upgrade' to recreate these tables.")
        
    except Exception as e:
        print(f"✗ ERROR wiping database: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Lumia Selective Storage Reset Tool")
    parser.add_argument("--qdrant", action="store_true", help="Wipe Qdrant vector storage")
    parser.add_argument("--papers", action="store_true", help="Wipe papers table and dependents")
    parser.add_argument("--uploads", action="store_true", help="Wipe uploads folder")
    parser.add_argument("--all", action="store_true", help="Wipe everything (except user accounts)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    
    args = parser.parse_args()

    # Interactive mode if no specific wipe requested
    if not (args.qdrant or args.papers or args.uploads or args.all):
        print_banner("Lumia Storage Reset - Interactive Mode")
        print("Select what you want to wipe (separate by space, e.g., '1 3'):")
        print("1. Qdrant Vector Storage")
        print("2. Papers Database (including citations and records)")
        print("3. Uploads Folder (physical PDF files)")
        print("4. ALL of the above")
        print("0. Cancel")
        
        choice = input("\nChoice: ").strip().split()
        if '0' in choice or not choice:
            print("Aborted.")
            return
            
        if '4' in choice:
            args.all = True
        else:
            if '1' in choice: args.qdrant = True
            if '2' in choice: args.papers = True
            if '3' in choice: args.uploads = True

    # Aggregator for 'all'
    if args.all:
        args.qdrant = args.papers = args.uploads = True

    # Final confirmation
    if not args.force:
        targets = []
        if args.qdrant: targets.append("Qdrant storage")
        if args.papers: targets.append("Database tables (papers, citations, records)")
        if args.uploads: targets.append("Uploads folder")
        
        print(f"\nWARNING: You are about to PERMANENTLY WIPE: {', '.join(targets)}")
        confirm = input("Type 'YES' to confirm: ").strip()
        if confirm != "YES":
            print("Aborted.")
            return

    # Execute
    if args.qdrant:
        clear_directory(pathlib.Path(QDRANT_DIR), "Qdrant")
        
    if args.uploads:
        clear_directory(pathlib.Path(UPLOADS_DIR), "Uploads")
        
    if args.papers:
        wipe_tables()

    print_banner("Reset Complete")
    print("Please restart the backend server.")
    if args.papers:
        print("IMPORTANT: Run 'python migrate.py upgrade' to recreate the papers schema.")

if __name__ == "__main__":
    main()
