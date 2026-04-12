import uuid
from sqlalchemy import Column, Integer, String
from app.core.database import Base
from app.models.enums import UserRole

class AuthorizedUser(Base):
    __tablename__ = "authorized_users"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    role = Column(String) # Admin or Faculty
