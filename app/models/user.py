from sqlalchemy import Column, Integer, String
from app.models.paper import Base
from app.models.enums import UserRole

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)

    @property
    def role(self):
        return UserRole.USER