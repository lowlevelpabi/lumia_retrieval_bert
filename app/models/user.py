import uuid
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.paper import Base
from app.models.enums import UserRole

class Student(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)
    dark_mode = Column(Integer, default=0) # 0 for Light, 1 for Dark
    avatar_url = Column(String, nullable=True)

    @property
    def role(self):
        return UserRole.STUDENT