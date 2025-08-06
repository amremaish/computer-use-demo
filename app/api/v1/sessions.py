from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...core.database import get_db
from ...services.database_service import DatabaseService

router = APIRouter(prefix="/api", tags=["sessions"])

# Request Models
class SessionRequest(BaseModel):
    """Request model for creating a new session."""
    session_name: Optional[str] = Field(
        None, 
        description="Optional session name. If not provided, will be generated from the initial prompt.",
        example="My Computer Help Session"
    )
    display_name: Optional[str] = Field(
        None, 
        description="Display name for the session. If not provided, will be generated from the initial prompt.",
        example="Help with file organization"
    )
    initial_prompt: Optional[str] = Field(
        None, 
        description="Initial prompt to start the conversation with the AI agent.",
        example="Hello, can you help me organize my desktop files?"
    )

    class Config:
        schema_extra = {
            "example": {
                "display_name": "My Computer Help Session",
                "initial_prompt": "Hello, can you help me organize my desktop files?"
            }
        }

# Response Models
class SessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    display_name: str = Field(..., description="Display name of the session")

    class Config:
        schema_extra = {
            "example": {
                "session_id": "4dccdad3-d809-473b-9bcf-1c7dfc095850",
                "display_name": "Help with file organization"
            }
        }

class SessionStatus(BaseModel):
    """Response model for session status."""
    session_id: str = Field(..., description="Unique session identifier")
    display_name: str = Field(..., description="Display name of the session")
    status: str = Field(..., description="Current status of the session", example="running")
    created_at: datetime = Field(..., description="Session creation timestamp")
    initial_prompt: Optional[str] = Field(None, description="Initial prompt used for the session")

    class Config:
        schema_extra = {
            "example": {
                "session_id": "4dccdad3-d809-473b-9bcf-1c7dfc095850",
                "display_name": "Help with file organization",
                "status": "running",
                "created_at": "2024-01-15T10:30:00Z",
                "initial_prompt": "Hello, can you help me organize my desktop files?"
            }
        }

class ImageSource(BaseModel):
    """Model for image source information."""
    type: str = Field(..., description="Type of image source", example="base64")
    media_type: str = Field(..., description="MIME type of the image", example="image/png")
    data: str = Field(..., description="Base64 encoded image data")

class MessageContent(BaseModel):
    """Model for message content."""
    type: str = Field(..., description="Type of content", example="text")
    text: Optional[str] = Field(None, description="Text content")
    source: Optional[ImageSource] = Field(None, description="Image source information")

class Message(BaseModel):
    """Model for a single message in conversation history."""
    id: int = Field(..., description="Message ID")
    role: str = Field(..., description="Role of the message sender", example="user")
    content: List[MessageContent] = Field(..., description="Message content (text and/or images)")
    created_at: datetime = Field(..., description="Message creation timestamp")

class SessionHistory(BaseModel):
    """Response model for session history."""
    session_id: str = Field(..., description="Unique session identifier")
    display_name: str = Field(..., description="Display name of the session")
    status: str = Field(..., description="Current status of the session")
    created_at: datetime = Field(..., description="Session creation timestamp")
    initial_prompt: Optional[str] = Field(None, description="Initial prompt used for the session")
    messages: List[Message] = Field(..., description="List of messages in the conversation")

class SessionListItem(BaseModel):
    """Model for session list item."""
    session_id: str = Field(..., description="Unique session identifier")
    display_name: str = Field(..., description="Display name of the session")
    status: str = Field(..., description="Current status of the session")
    created_at: datetime = Field(..., description="Session creation timestamp")
    message_count: int = Field(..., description="Number of messages in the session")

class SessionList(BaseModel):
    """Response model for session list."""
    sessions: List[SessionListItem] = Field(..., description="List of all sessions")

class DeleteResponse(BaseModel):
    """Response model for session deletion."""
    message: str = Field(..., description="Deletion status message")

class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")

@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionRequest, 
    db: Session = Depends(get_db)
):
    """
    Create a new conversation session with the AI agent.
    
    This endpoint creates a new session that can be used for real-time communication
    with the AI agent through WebSocket connections.
    
    - **session_name**: Optional custom name for the session
    - **display_name**: Optional display name (will be generated if not provided)
    - **initial_prompt**: Optional initial message to start the conversation
    
    Returns a session ID that can be used to connect to the WebSocket endpoint.
    """
    db_service = DatabaseService(db)
    session_id = str(uuid4())
    display_name = request.display_name or generateSessionName(request.initial_prompt)
    
    # Create session in database
    session = db_service.create_session(
        session_id=session_id,
        display_name=display_name,
        initial_prompt=request.initial_prompt
    )
    
    return SessionResponse(session_id=session_id, display_name=display_name)

def generateSessionName(prompt_text):
    """Generate a session name from the initial prompt."""
    if not prompt_text:
        return "New Session"
    lines = prompt_text.split('\n')
    first_line = lines[0].strip()
    name = first_line[:20] + '...' if len(first_line) > 20 else first_line
    return name or "New Session"

@router.get("/session/{session_id}", response_model=SessionStatus)
async def get_session_status(
    session_id: str, 
    db: Session = Depends(get_db)
):
    """
    Get the current status and information of a session.
    
    Retrieves detailed information about a specific session including its status,
    creation time, and initial prompt.
    
    - **session_id**: The unique identifier of the session
    
    Returns session details or a 404 error if the session is not found.
    """
    db_service = DatabaseService(db)
    session_data = db_service.get_session_for_api(session_id)
    if session_data:
        return SessionStatus(**session_data)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found"
    )

@router.get("/session/{session_id}/history", response_model=SessionHistory)
async def get_session_history(
    session_id: str, 
    db: Session = Depends(get_db)
):
    """
    Get the complete conversation history for a session.
    
    Retrieves all messages in a session, including text messages and images.
    Messages are returned in chronological order with their content and metadata.
    
    - **session_id**: The unique identifier of the session
    
    Returns the complete conversation history or a 404 error if the session is not found.
    """
    db_service = DatabaseService(db)
    session_data = db_service.get_session_history_for_api(session_id)
    if session_data:
        return SessionHistory(**session_data)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found"
    )

@router.get("/sessions", response_model=SessionList)
async def list_sessions(db: Session = Depends(get_db)):
    """
    Get a list of all available sessions.
    
    Returns a paginated list of all sessions with their basic information
    including session ID, display name, status, creation time, and message count.
    
    This endpoint is useful for displaying a session list in the UI or
    for administrative purposes.
    """
    db_service = DatabaseService(db)
    sessions = db_service.get_session_list_for_api()
    return SessionList(sessions=sessions)

@router.delete("/session/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str, 
    db: Session = Depends(get_db)
):
    """
    Delete a session and all its associated messages.
    
    Permanently removes a session and all its conversation history from the database.
    This action cannot be undone.
    
    - **session_id**: The unique identifier of the session to delete
    
    Returns a success message or a 404 error if the session is not found.
    """
    db_service = DatabaseService(db)
    if db_service.delete_session(session_id):
        return DeleteResponse(message=f"Session {session_id} deleted successfully.")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Session {session_id} not found"
    ) 