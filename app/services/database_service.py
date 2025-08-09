from sqlalchemy.orm import Session
from sqlalchemy import desc, cast, String
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import List, Optional, Dict, Any
import re

from ..models import Session as SessionModel, Message as MessageModel
from ..models.message import MessageType

class DatabaseService:
    def __init__(self, db: Session):
        self.db = db
    
    # Session operations
    def create_session(self, session_code: str, display_name: str = None, initial_prompt: str = None) -> SessionModel:
        """Create a new session"""
        session = SessionModel(
            session_code=session_code,
            display_name=display_name,
            status="running",
            created_at=datetime.utcnow(),
            initial_prompt=initial_prompt
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def get_session(self, session_code: str) -> Optional[SessionModel]:
        """Get a session by ID"""
        return self.db.query(SessionModel).filter(SessionModel.session_code == session_code).first()
    
    def get_all_sessions(self) -> List[SessionModel]:
        """Get all sessions ordered by creation date"""
        return self.db.query(SessionModel).order_by(desc(SessionModel.created_at)).all()
    
    def delete_session(self, session_code: str) -> bool:
        """Delete a session and all its messages"""
        session = self.get_session(session_code)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False
    
    def update_session_status(self, session_code: str, status: str) -> bool:
        """Update session status"""
        session = self.get_session(session_code)
        if session:
            session.status = status
            self.db.commit()
            return True
        return False
    
    # Message operations
    def add_message(self, session_code: str, role: str, content: List[Dict[str, Any]]) -> MessageModel:
        """Add a message to a session"""
        # Ensure content is always a list
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        elif not isinstance(content, list):
            content = [{"type": "text", "text": str(content)}]
        
        # Resolve internal numeric id
        session = self.get_session(session_code)
        if not session:
            raise ValueError(f"Session not found: {session_code}")

        # Determine message type: if any image blocks, classify as IMAGE; else TEXT
        message_type: MessageType = MessageType.TEXT
        try:
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image":
                    message_type = MessageType.IMAGE
                    break
        except Exception:
            message_type = MessageType.TEXT
        message = MessageModel(
            session_id=session.id,
            role=role,
            content=content,
            message_type=message_type,
            created_at=datetime.utcnow()
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_session_messages(self, session_code: str) -> List[MessageModel]:
        """Get all messages for a session ordered by creation time"""
        session = self.get_session(session_code)
        if not session:
            return []
        return (
            self.db.query(MessageModel)
            .filter(MessageModel.session_id == session.id)
            .order_by(MessageModel.id.asc())
            .all()
        )
    
    def get_message_count(self, session_code: str) -> int:
        """Get the number of messages in a session"""
        session = self.get_session(session_code)
        if not session:
            return 0
        return self.db.query(MessageModel).filter(
            MessageModel.session_id == session.id
        ).count()
    
    # Utility methods for API responses
    def get_session_for_api(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get session data formatted for API response"""
        session = self.get_session(session_code)
        if not session:
            return None
        
        return {
            "session_id": session.session_code,
            "display_name": session.display_name or "New Session",
            "status": session.status,
            "created_at": session.created_at,
            "initial_prompt": session.initial_prompt,
            "message_count": self.get_message_count(session_code)
        }
    
    def get_session_list_for_api(self) -> List[Dict[str, Any]]:
        """Get all sessions formatted for API response"""
        sessions = self.get_all_sessions()
        return [
            {
                "session_id": session.session_code,
                "display_name": session.display_name or "New Session",
                "status": session.status,
                "message_count": self.get_message_count(session.session_code),
                "created_at": session.created_at
            }
            for session in sessions
        ]
    
    def get_session_history_for_api(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get session history formatted for API response"""
        session = self.get_session(session_code)
        if not session:
            return None
        
        messages = self.get_session_messages(session_code)
        message_list = []
        
        for msg in messages:
            # Handle case where content might be a string instead of a list
            content = msg.content
            if isinstance(content, str):
                # Convert string content to proper format
                content = [{"type": "text", "text": content}]
            elif not isinstance(content, list):
                # Fallback for any other unexpected type
                content = [{"type": "text", "text": str(content)}]
            
            message_list.append({
                "id": msg.id,
                "role": msg.role,
                "content": content,
                "created_at": msg.created_at
            })
        
        return {
            "session_id": session_code,
            "display_name": session.display_name or "New Session",
            "status": session.status,
            "created_at": session.created_at,
            "initial_prompt": session.initial_prompt,
            "messages": message_list
        } 

    def search_sessions_by_message_text(self, query_text: Optional[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """Search sessions by TEXT messages using JSONB path query (case-insensitive substring).

        Only TEXT messages are considered; images are excluded.
        Returns at most one most-recent matching message per session.
        """
        if not query_text:
            return []

        q = (
            self.db.query(SessionModel, MessageModel)
            .join(MessageModel, MessageModel.session_id == SessionModel.id)
            .filter(MessageModel.message_type == MessageType.TEXT)
        )

        # Choose implementation depending on DB dialect
        dialect_name = None
        try:
            bind = self.db.get_bind()
            if bind is not None and hasattr(bind, "dialect"):
                dialect_name = bind.dialect.name
        except Exception:
            dialect_name = None

        if dialect_name == "postgresql":
            # PostgreSQL: use JSONB path exists with case-insensitive regex
            safe = re.escape(query_text)
            pattern = f".*{safe}.*"
            jsonpath = f'$.** ? (@.type == "text" && @.text like_regex "{pattern}" flag "i")'
            q = q.filter(func.jsonb_path_exists(cast(MessageModel.content, JSONB), jsonpath))
        else:
            # Fallback for SQLite/others: simple case-insensitive match on serialized content
            safe = query_text
            q = q.filter(cast(MessageModel.content, String).ilike(f"%{safe}%"))

        rows = q.order_by(desc(MessageModel.created_at)).limit(max_results).all()

        results: List[Dict[str, Any]] = []
        seen_session_codes = set()
        for session, message in rows:
            if session.session_code in seen_session_codes:
                continue
            seen_session_codes.add(session.session_code)
            content = message.content
            try:
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_value = block.get("text")
                            if isinstance(text_value, str) and text_value:
                                text_parts.append(text_value)
                    snippet_text = " ".join(text_parts) if text_parts else None
                else:
                    snippet_text = str(content) if content is not None else None
            except Exception:
                snippet_text = None

            if snippet_text:
                snippet_text = snippet_text[:200]

            results.append({
                "session_id": session.session_code,
                "display_name": session.display_name,
                "created_at": session.created_at,
                "message_id": message.id,
                "message_created_at": message.created_at,
                "snippet": snippet_text,
            })

        return results