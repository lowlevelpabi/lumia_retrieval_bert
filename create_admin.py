import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.database import SessionLocal
from app.models.authorized_user import AuthorizedUser
from app.core.security import get_password_hash # Changed from app.core.hash to app.core.security

def create_admin(username, email, password, full_name="Admin"):
    db = SessionLocal()
    try:
        # Check if user already exists
        existing = db.query(AuthorizedUser).filter(AuthorizedUser.username == username).first()
        if existing:
            print(f"User '{username}' already exists.")
            return

        admin = AuthorizedUser(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role="Admin"
        )
        db.add(admin)
        db.commit()
        print(f"Success: Admin user '{username}' created with password '{password}'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_admin.py <username> <email> <password> [full_name]")
    else:
        full_name = sys.argv[4] if len(sys.argv) > 4 else sys.argv[1]
        create_admin(sys.argv[1], sys.argv[2], sys.argv[3], full_name)
