from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String(255), primary_key=True)
    display_name = Column(String(255), nullable=True)
    status = Column(String(50), default="running")
    created_at = Column(DateTime, default=datetime.utcnow)
    initial_prompt = Column(Text, nullable=True)
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan") 