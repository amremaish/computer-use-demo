from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from enum import Enum


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(JSON, nullable=False)
    message_type = Column(SAEnum(MessageType, name="message_type"), nullable=False, default=MessageType.TEXT)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="messages") 