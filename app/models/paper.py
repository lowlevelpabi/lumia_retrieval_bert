from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    year = Column(String)
    abstract = Column(Text)
    department = Column(String, default="N/A")
    keywords = Column(Text, default="")
    project_type = Column(String, default="N/A")
    degree_program = Column(String, default="N/A")
    citation_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    file_path = Column(String)
    
    # Persistent IMRAD sections (extracted and potentially edited)
    introduction = Column(Text, nullable=True)
    methods = Column(Text, nullable=True)
    results = Column(Text, nullable=True)
    discussion = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
