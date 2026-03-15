import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def test_ports():
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "04252002") # Using the one from .env
    dbname = os.getenv("POSTGRES_DB", "thesis_db")
    
    ports = [5432, 5433]
    
    for port in ports:
        print(f"\n--- Testing Port {port} ---")
        try:
            # Try to connect to 'postgres' first
            conn = psycopg2.connect(
                dbname='postgres',
                user=user,
                password=password,
                host='localhost',
                port=port,
                connect_timeout=3
            )
            print(f"✅ SUCCESS: Connected to 'postgres' on port {port}")
            
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (dbname,))
            if not cur.fetchone():
                print(f"Database '{dbname}' missing. Creating...")
                cur.execute(f'CREATE DATABASE {dbname}')
                print(f"✅ Database '{dbname}' created.")
            else:
                print(f"Database '{dbname}' already exists.")
            
            cur.close()
            conn.close()
            
            # Now verify connection to the target DB
            conn = psycopg2.connect(
                dbname=dbname,
                user=user,
                password=password,
                host='localhost',
                port=port
            )
            print(f"✅ SUCCESS: Connected to '{dbname}' on port {port}")
            conn.close()
            return port
            
        except psycopg2.OperationalError as e:
            if "password authentication failed" in str(e):
                print(f"❌ AUTH FAILED on port {port}")
            else:
                print(f"❌ ERROR on port {port}: {e}")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR on port {port}: {e}")
            
    return None

if __name__ == "__main__":
    test_ports()
