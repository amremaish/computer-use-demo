import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio
from ...core.database import get_db
from ...models import Session
from ...services.database_service import DatabaseService
from app.tools.agentic_loop import sampling_loop, APIProvider
from anthropic.types.beta import BetaTextBlockParam, BetaMessageParam

from ...tools.websocket_agent_handler import WebSocketAgentHandler

router = APIRouter(tags=["websocket"])

# WebSocket Message Models for Documentation
class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages."""
    type: str = Field(..., description="Type of message", example="agent_message")
    message: Optional[str] = Field(None, description="Message content")
    data: Optional[str] = Field(None, description="Base64 encoded image data")
    content: Optional[Dict[str, Any]] = Field(None, description="Additional content")

class UserMessage(BaseModel):
    """Model for user messages sent to the WebSocket."""
    message: str = Field(..., description="User message to send to the AI agent", example="Take a screenshot of my desktop")

class AgentMessage(BaseModel):
    """Model for agent response messages."""
    type: str = Field("agent_message", description="Message type")
    message: str = Field(..., description="Agent's response text")

class ImageMessage(BaseModel):
    """Model for image messages."""
    type: str = Field("image", description="Message type")
    data: str = Field(..., description="Base64 encoded image data")

class ThinkingMessage(BaseModel):
    """Model for thinking process messages."""
    type: str = Field("thinking", description="Message type")
    message: str = Field(..., description="Agent's thinking process")

class ErrorMessage(BaseModel):
    """Model for error messages."""
    type: str = Field("agent_message", description="Message type")
    message: str = Field(..., description="Error message")

@router.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time communication with the AI agent.
    
    This endpoint establishes a WebSocket connection for live communication with the AI agent.
    It handles bidirectional communication where users can send messages and receive
    real-time responses including text, images, and thinking processes.
    
    ## Connection
    
    Connect to: `ws://localhost:8081/ws/session/{session_id}`
    
    ## Message Types
    
    ### Sending Messages (Client → Server)
    ```json
    {
        "message": "Take a screenshot of my desktop"
    }
    ```
    
    ### Receiving Messages (Server → Client)
    
    **Agent Text Response:**
    ```json
    {
        "type": "agent_message",
        "message": "I've taken a screenshot of your desktop. Here's what I can see..."
    }
    ```
    
    **Image Response:**
    ```json
    {
        "type": "image",
        "data": "base64-encoded-image-data"
    }
    ```
    
    **Thinking Process:**
    ```json
    {
        "type": "thinking",
        "message": "I need to take a screenshot to see the current desktop state..."
    }
    ```
    
    **Error Message:**
    ```json
    {
        "type": "agent_message",
        "message": "Error: Unable to take screenshot due to permission issues"
    }
    ```
    
    ## Features
    
    - **Real-time Communication**: Instant message exchange
    - **Image Support**: Receive screenshots and visual content
    - **Thinking Process**: See the agent's reasoning
    - **Error Handling**: Graceful error reporting
    - **Session Persistence**: Messages are saved to database
    
    ## Usage Example
    
    ```javascript
    const ws = new WebSocket(`ws://localhost:8081/ws/session/${sessionId}`);
    
    ws.onopen = () => {
        console.log('Connected to AI agent');
        ws.send(JSON.stringify({
            message: "Hello, can you help me organize my files?"
        }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch(data.type) {
            case 'agent_message':
                console.log('Agent:', data.message);
                break;
            case 'image':
                console.log('Received image:', data.data);
                break;
            case 'thinking':
                console.log('Agent thinking:', data.message);
                break;
        }
    };
    ```
    """
    try:
        print(f"[WebSocket] Accepting connection for session: {session_id}")
        await websocket.accept()
        print(f"[WebSocket] Connection accepted for session: {session_id}")
        
        # Create db_service instance
        db_service = DatabaseService(db)
        
        # Verify session exists
        session = db_service.get_session(session_id)
        if not session:
            print(f"[WebSocket] Session not found: {session_id}")
            await websocket.close(code=4004, reason="Session not found")
            return
        
        print(f"[WebSocket] Session found: {session_id}, status: {session.status}")
        
        # Instantiate and run the handler
        handler = WebSocketAgentHandler(
            websocket=websocket,
            session_id=session_id,
            db_service=db_service,
            api_provider=APIProvider.ANTHROPIC,
            sampling_loop=sampling_loop,
            messages_for_api=[]
        )

        await handler.handle()
        
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[WebSocket] Error in websocket_endpoint: {e}")
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass