"""
reset_storage.py   Lumia Selective Storage Reset Tool
=====================================================

Usage (interactive):
    python reset_storage.py

Usage (flags):
    --qdrant          Wipe Qdrant vector storage directory
    --papers          Drop paper-related tables (papers, citations, borrow, penalties)
    --uploads         Delete all uploaded PDF files
    --users           Drop user account tables (students, authorized_users)
    --all             Wipe everything EXCEPT the database file itself (papers + qdrant + uploads)
    --nuke            [!] COMPLETE WIPE: delete the entire thesis.db file + qdrant + uploads
                        Then recreates the DB schema from scratch via migrate.py
    --force           Skip the confirmation prompt
"""

import shutil
import os
import sys
import sqlite3
import argparse
import pathlib
import subprocess

from app.core.config import settings

# ── Constants ────────────────────────────────────────────────────────────────
DB_PATH     = "thesis.db"
QDRANT_DIR  = settings.QDRANT_PATH
UPLOADS_DIR = settings.UPLOAD_DIR

# Drop order: children before parents to satisfy FK constraints
ALL_TABLES_DROP_ORDER = [
    "user_citations",    # FK → students, papers
    "penalties",         # FK → borrow_records
    "borrow_records",    # FK → papers, students
    "activity_logs",
    "students",
    "authorized_users",
    "papers",
]

# Only paper-data tables (leaves user accounts intact)
PAPER_RELATED_TABLES = [
    "user_citations",
    "penalties",
    "borrow_records",
    "papers",
]

# Only user account tables
USER_TABLES = [
    "students",
    "authorized_users",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def print_banner(title: str):
    print(f"\n{'=' * 62}")
    print(f"  {title}")
    print(f"{'=' * 62}")


def _drop_tables(table_list: list[str], label: str):
    if not os.path.exists(DB_PATH):
        print(f"  ! {DB_PATH} not found — nothing to drop.")
        return

    print(f"\n--- Dropping {label} tables ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = OFF")
        for table in table_list:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if cursor.fetchone():
                cursor.execute(f"DROP TABLE {table}")
                print(f"  + Dropped  : {table}")
            else:
                print(f"  - Skipped  : {table} (not found)")
        conn.commit()
        print(f"  ✓ {label} tables dropped.")
        print(f"  ! Run 'python migrate.py upgrade' to recreate the schema.\n")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        conn.rollback()
    finally:
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.close()


def wipe_papers():
    _drop_tables(PAPER_RELATED_TABLES, "paper-related")


def wipe_users():
    _drop_tables(USER_TABLES, "user account")


def wipe_all_tables():
    _drop_tables(ALL_TABLES_DROP_ORDER, "ALL")


def clear_directory(path: pathlib.Path, name: str):
    if path.exists():
        try:
            print(f"--- Clearing {name} ---")
            shutil.rmtree(path)
            path.mkdir(parents=True)
            print(f"  + Cleared  : {name}")
        except PermissionError:
            print(f"  ! ERROR: Could not clear {name}. Stop the server first.")
        except Exception as e:
            print(f"  ! ERROR clearing {name}: {e}")
    else:
        path.mkdir(parents=True, exist_ok=True)
        print(f"  + Created  : {name} (was already empty)")


def nuke_database():
    """Delete the entire .db file and recreate the schema from scratch."""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"  + Deleted  : {DB_PATH}")
        except PermissionError:
            print(f"  ! ERROR: Cannot delete {DB_PATH}. Stop the backend server first.")
            return False
        except Exception as e:
            print(f"  ! ERROR deleting database: {e}")
            return False
    else:
        print(f"  - {DB_PATH} not found (already gone).")

    # Recreate schema via migrate.py
    print("\n--- Recreating schema via migrate.py upgrade ---")
    result = subprocess.run(
        [sys.executable, "migrate.py", "upgrade"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    if result.returncode == 0:
        print("  + Schema recreated successfully.")
    else:
        print("  ! migrate.py returned an error. Run it manually.")
    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Lumia Selective Storage Reset Tool",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--qdrant",   action="store_true", help="Wipe Qdrant vector storage")
    parser.add_argument("--papers",   action="store_true", help="Drop paper-related tables (papers, citations, borrow, penalties)")
    parser.add_argument("--users",    action="store_true", help="Drop user account tables (students, authorized_users)")
    parser.add_argument("--uploads",  action="store_true", help="Delete all uploaded PDF files")
    parser.add_argument("--all",      action="store_true", help="Wipe everything except user accounts (papers + qdrant + uploads)")
    parser.add_argument("--nuke",     action="store_true", help="[!] COMPLETE WIPE: delete the entire DB file + qdrant + uploads, then rebuild schema")
    parser.add_argument("--force",    action="store_true", help="Skip confirmation prompt")

    args = parser.parse_args()

    # Interactive mode when called with no flags
    if not any([args.qdrant, args.papers, args.users, args.uploads, args.all, args.nuke]):
        print_banner("Lumia Storage Reset - Interactive Mode")
        print("  Select what you want to wipe (space-separated numbers, e.g. '1 3'):\n")
        print("  1. Qdrant Vector Storage")
        print("  2. Papers & Related Tables  (papers, citations, borrow, penalties)")
        print("  3. User Account Tables      (students, authorized_users)")
        print("  4. Uploads Folder           (physical PDF files)")
        print("  5. ALL of the above         (same as --all + --users)")
        print("  6. [!] NUKE -- Delete entire database file + qdrant + uploads")
        print("         then automatically rebuild the schema from scratch")
        print("  0. Cancel\n")

        choice = input("  Choice: ").strip().split()
        if "0" in choice or not choice:
            print("  Aborted.")
            return

        if "6" in choice:
            args.nuke = True
        elif "5" in choice:
            args.all = True
            args.users = True
        else:
            if "1" in choice: args.qdrant  = True
            if "2" in choice: args.papers  = True
            if "3" in choice: args.users   = True
            if "4" in choice: args.uploads = True

    # --all expands to papers + qdrant + uploads (not users or nuke)
    if args.all:
        args.papers  = True
        args.qdrant  = True
        args.uploads = True

    # --nuke expands to everything
    if args.nuke:
        args.qdrant  = True
        args.uploads = True

    # Build human-readable target list for the confirmation message
    targets = []
    if args.nuke:    targets.append("[!] ENTIRE DATABASE FILE (thesis.db) -- complete wipe + schema rebuild")
    elif args.papers: targets.append("Paper-related tables (papers, citations, borrow, penalties)")
    if args.users:   targets.append("User account tables (students, authorized_users)")
    if args.qdrant:  targets.append("Qdrant vector storage")
    if args.uploads: targets.append("Uploads folder (all PDFs)")

    if not targets:
        print("  Nothing selected. Exiting.")
        return

    # Confirmation
    if not args.force:
        print(f"\n  WARNING: You are about to PERMANENTLY WIPE:\n")
        for t in targets:
            print(f"     - {t}")
        confirm = input("\n  Type YES to confirm: ").strip()
        if confirm != "YES":
            print("  Aborted.")
            return

    # ── Execute ────────────────────────────────────────────────────────────
    print_banner("Executing Reset")

    if args.nuke:
        nuke_database()
        clear_directory(pathlib.Path(QDRANT_DIR), "Qdrant")
        clear_directory(pathlib.Path(UPLOADS_DIR), "Uploads")
    else:
        if args.qdrant:
            clear_directory(pathlib.Path(QDRANT_DIR), "Qdrant")
        if args.uploads:
            clear_directory(pathlib.Path(UPLOADS_DIR), "Uploads")
        if args.papers:
            wipe_papers()
        if args.users:
            wipe_users()

    print_banner("Reset Complete")
    print("  Restart the backend server before using the system.")
    if args.papers and not args.nuke:
        print("  IMPORTANT: Run 'python migrate.py upgrade' to recreate the dropped tables.")
    if args.users and not args.nuke:
        print("  IMPORTANT: Run 'python migrate.py upgrade' then 'python create_admin.py' to recreate user tables + admin account.")
    print()


if __name__ == "__main__":
    main()
