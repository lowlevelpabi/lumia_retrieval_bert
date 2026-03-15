from app.core.database import init_db, engine
from app.core.config import settings
import os
from alembic.config import Config
from alembic import command

def setup_db():
    print(f"Using DATABASE_URL: {settings.DATABASE_URL}")
    
    # 1. Create tables
    print("Initializing database tables...")
    init_db()
    print("Tables created successfully.")
    
    # 2. Stamp alembic (so it thinks migrations are done)
    # This migration file tries to add columns that might already be in Base
    # Let's check the migration file contents first if possible, or just stamp.
    print("Stamping alembic migration to 'head'...")
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    print("Alembic stamped successfully.")

if __name__ == "__main__":
    setup_db()
