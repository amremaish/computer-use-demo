from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import List, Optional, Dict, Any

from ..models import Session as SessionModel, Message as MessageModel

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
    
    # Session operations
    def create_session(self, session_id: str, display_name: str = None, initial_prompt: str = None) -> SessionModel:
        """Create a new session"""
        session = SessionModel(
            session_id=session_id,
            display_name=display_name,
            status="running",
            created_at=datetime.utcnow(),
            initial_prompt=initial_prompt
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get a session by ID"""
        return self.db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    
    def get_all_sessions(self) -> List[SessionModel]:
        """Get all sessions ordered by creation date"""
        return self.db.query(SessionModel).order_by(desc(SessionModel.created_at)).all()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        session = self.get_session(session_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status"""
        session = self.get_session(session_id)
        if session:
            session.status = status
            self.db.commit()
            return True
        return False
    
    # Message operations
    def add_message(self, session_id: str, role: str, content: List[Dict[str, Any]]) -> MessageModel:
        """Add a message to a session"""
        message = MessageModel(
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.utcnow()
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_session_messages(self, session_id: str) -> List[MessageModel]:
        """Get all messages for a session ordered by creation time"""
        return self.db.query(MessageModel).filter(
            MessageModel.session_id == session_id
        ).order_by(MessageModel.created_at).all()
    
    def get_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session"""
        return self.db.query(MessageModel).filter(
            MessageModel.session_id == session_id
        ).count()
    
    # Utility methods for API responses
    def get_session_for_api(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data formatted for API response"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "display_name": session.display_name or "New Session",
            "status": session.status,
            "created_at": session.created_at,
            "initial_prompt": session.initial_prompt,
            "message_count": self.get_message_count(session_id)
        }
    
    def get_session_list_for_api(self) -> List[Dict[str, Any]]:
        """Get all sessions formatted for API response"""
        sessions = self.get_all_sessions()
        return [
            {
                "session_id": session.session_id,
                "display_name": session.display_name or "New Session",
                "status": session.status,
                "message_count": self.get_message_count(session.session_id),
                "created_at": session.created_at
            }
            for session in sessions
        ]
    
    def get_session_history_for_api(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session history formatted for API response"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        messages = self.get_session_messages(session_id)
        message_list = []
        
        for msg in messages:
            message_list.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at
            })
        
        return {
            "session_id": session_id,
            "display_name": session.display_name or "New Session",
            "status": session.status,
            "created_at": session.created_at,
            "initial_prompt": session.initial_prompt,
            "messages": message_list
        } 