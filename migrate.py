"""
migrate.py  —  Standalone database migration script
Smart Research API

Usage:
    python migrate.py            # Run all pending migrations (default)
    python migrate.py upgrade    # Same as above
    python migrate.py downgrade  # Drop all managed tables
    python migrate.py reset      # Drop then recreate all tables (⚠ destructive)
    python migrate.py status     # Show current schema state

This script does NOT require Alembic.  It uses SQLAlchemy's MetaData
inspection to detect which tables already exist and only creates missing ones.
"""

import sys
import os

# ── Make sure the project root is on the path ─────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Imports ───────────────────────────────────────────────────────────────────
from sqlalchemy import inspect, text
from app.core.config import settings
from app.core.database import engine

# Import every model so they all register on the shared Base.
# Order matters only for clarity — SQLAlchemy resolves FK ordering automatically.
from app.models.paper import Base, Paper                     # Base is defined here
from app.models.user import Student                          # students table
from app.models.authorized_user import AuthorizedUser        # authorized_users table
from app.models.citation import UserCitation                 # user_citations table
from app.models.activity_log import ActivityLog              # activity_logs table

# ── Table registry ────────────────────────────────────────────────────────────
# Explicit drop-order (children before parents) for the downgrade path.
DROP_ORDER = [
    "user_citations",    # FK → students, papers
    "activity_logs",     # no FK
    "students",
    "authorized_users",
    "papers",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _existing_tables(connection) -> set[str]:
    inspector = inspect(connection)
    return set(inspector.get_table_names())


def _print_banner(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ── Commands ──────────────────────────────────────────────────────────────────

def upgrade():
    """Create all tables that don't exist yet (safe, non-destructive)."""
    _print_banner("UPGRADE  —  creating missing tables")

    with engine.begin() as conn:
        existing = _existing_tables(conn)
        all_tables = set(Base.metadata.tables.keys())
        missing = all_tables - existing

        if not missing:
            print("  ✓  All tables already exist — nothing to do.")
            return

        print(f"  Tables already present : {sorted(existing & all_tables) or '(none)'}")
        print(f"  Tables to create       : {sorted(missing)}")
        print()

        # Let SQLAlchemy create only what's missing, respecting FK order.
        Base.metadata.create_all(bind=conn, checkfirst=True)

        print("  ✓  Done.")


def downgrade():
    """Drop all managed tables in safe FK-respecting order."""
    _print_banner("DOWNGRADE  —  dropping all managed tables")

    with engine.begin() as conn:
        existing = _existing_tables(conn)

        for table_name in DROP_ORDER:
            if table_name in existing:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                print(f"  ✗  Dropped  : {table_name}")
            else:
                print(f"  –  Skipped  : {table_name} (does not exist)")

        # Also drop any managed tables not in our explicit list
        extra = set(Base.metadata.tables.keys()) - set(DROP_ORDER)
        for table_name in extra:
            if table_name in existing:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                print(f"  ✗  Dropped  : {table_name} (extra)")

    print("  ✓  Done.")


def reset():
    """Drop all managed tables and recreate them from scratch (⚠ destructive)."""
    _print_banner("RESET  —  drop + recreate (ALL DATA WILL BE LOST)")
    confirm = input("  Type  YES  to continue: ").strip()
    if confirm != "YES":
        print("  Aborted.")
        return
    downgrade()
    upgrade()


def status():
    """Print the current state of each managed table."""
    _print_banner("STATUS  —  current schema")

    with engine.connect() as conn:
        existing = _existing_tables(conn)
        all_tables = set(Base.metadata.tables.keys())

        print(f"  Database : {settings.DATABASE_URL}\n")

        for table_name in sorted(all_tables):
            exists = table_name in existing
            mark = "✓" if exists else "✗"
            state = "exists" if exists else "MISSING"

            if exists:
                inspector = inspect(conn)
                cols = inspector.get_columns(table_name)
                col_names = ", ".join(c["name"] for c in cols)
                print(f"  [{mark}] {table_name:<25} ({state}) — columns: {col_names}")
            else:
                print(f"  [{mark}] {table_name:<25} ({state})")

    print()


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "upgrade":   upgrade,
    "downgrade": downgrade,
    "reset":     reset,
    "status":    status,
}

if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "upgrade"

    if cmd not in COMMANDS:
        print(f"Unknown command '{cmd}'. Choose from: {', '.join(COMMANDS)}")
        sys.exit(1)

    try:
        COMMANDS[cmd]()
    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        sys.exit(1)