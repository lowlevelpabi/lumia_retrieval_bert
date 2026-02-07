from sqlalchemy import Column, Integer, String, Enum
from app.models.paper import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    FACULTY = "Faculty"
    USER = "User"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.USER)
