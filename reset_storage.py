import os
import shutil
import pathlib

def reset_storage():
    print("--- Lumia Storage Reset Started ---")
    
    # 1. Reset SQLite Database
    db_path = pathlib.Path("thesis.db")
    if db_path.exists():
        try:
            db_path.unlink()
            print("✓ Deleted thesis.db")
        except PermissionError:
            print("✗ ERROR: Could not delete thesis.db. Is the server still running?")
    else:
        print("! thesis.db not found (already clean)")

    # 2. Reset Qdrant Vector Storage
    qdrant_dir = pathlib.Path("qdrant_storage")
    if qdrant_dir.exists():
        try:
            shutil.rmtree(qdrant_dir)
            qdrant_dir.mkdir()
            print("✓ Cleared qdrant_storage folder")
        except PermissionError:
             print("✗ ERROR: Could not clear qdrant_storage. Is the server still running?")
        except Exception as e:
            print(f"✗ ERROR clearing Qdrant: {e}")
    else:
        qdrant_dir.mkdir()
        print("✓ Created qdrant_storage folder")

    # 3. Reset Uploads Folder
    uploads_dir = pathlib.Path("uploads")
    if uploads_dir.exists():
        try:
            shutil.rmtree(uploads_dir)
            uploads_dir.mkdir()
            print("✓ Cleared uploads folder")
        except PermissionError:
             print("✗ ERROR: Could not clear uploads. Is the server still running?")
        except Exception as e:
            print(f"✗ ERROR clearing uploads: {e}")
    else:
        uploads_dir.mkdir()
        print("✓ Created uploads folder")

    print("--- Reset Complete. Please restart the backend server ---")

if __name__ == "__main__":
    reset_storage()
