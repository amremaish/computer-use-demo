from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_code = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=True)
    status = Column(String(50), default="running")
    created_at = Column(DateTime, default=datetime.utcnow)
    initial_prompt = Column(Text, nullable=True)
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan") 