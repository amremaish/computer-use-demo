import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from ...core.database import get_db
from ...services.database_service import DatabaseService
from app.tools.agentic_loop import sampling_loop, APIProvider
from anthropic.types.beta import BetaTextBlockParam

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
async def websocket_endpoint(websocket: WebSocket, session_id: str):
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
    print("[*] WebSocket route hit")
    await websocket.accept()
    print(f"[+] WebSocket connected: {session_id}")

    # Get database session
    db = next(get_db())
    db_service = DatabaseService(db)
    
    # Get or create session
    session = db_service.get_session(session_id)
    if not session:
        # Create a basic session if it doesn't exist
        session = db_service.create_session(session_id)
    
    # Get existing messages for this session
    messages = db_service.get_session_messages(session_id)
    # Convert to the format expected by sampling_loop
    messages_for_api = [
        {
            "role": msg.role,
            "content": msg.content
        }
        for msg in messages
    ]
    


    async def send_message(message: dict):
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"[WebSocket Error] Failed to send: {e}")

    def output_callback(block):
        if block["type"] == "thinking":
            thinking_text = block.get("text", "") or block.get("thinking", "")
            if thinking_text:
                asyncio.create_task(send_message({
                    "type": "thinking",
                    "message": thinking_text
                }))

        elif block["type"] == "text":
            asyncio.create_task(send_message({
                "type": "agent_message",
                "message": block["text"]
            }))

        elif block["type"] == "image":
            # Handle image blocks from tool results
            if block.get("source") and block["source"].get("type") == "base64":
                asyncio.create_task(send_message({
                    "type": "image",
                    "data": block["source"]["data"]
                }))

        elif block["type"] == "tool_use":
            tool_id = block.get("id", "")
            tool_name = block.get("name", "")
            tool_input = block.get("input", {})

            print(f"[*] Tool requested: {tool_name} (id={tool_id})")
            
            # Don't send tool use notification to frontend to avoid "undefined" display

        else:
            asyncio.create_task(send_message({
                "type": "output",
                "content": block
            }))

    def tool_output_callback(tool_result, tool_use_id):
        # Send tool results through WebSocket for real-time display
        if tool_result.output:
            asyncio.create_task(send_message({
                "type": "agent_message",
                "message": tool_result.output
            }))
        
        if tool_result.base64_image:
            asyncio.create_task(send_message({
                "type": "image",
                "data": tool_result.base64_image
            }))
        
        if tool_result.error:
            asyncio.create_task(send_message({
                "type": "agent_message",
                "message": f"Error: {tool_result.error}"
            }))

        # Store tool result message in database
        tool_result_content = []
        if tool_result.output:
            tool_result_content.append({
                "type": "text",
                "text": tool_result.output
            })
        if tool_result.base64_image:
            tool_result_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": tool_result.base64_image
                }
            })
        if tool_result.error:
            tool_result_content.append({
                "type": "text",
                "text": f"Error: {tool_result.error}"
            })
        
        if tool_result_content:
            # Tool results are added as 'user' messages in the sampling loop
            # We need to save them to the database here.
            db_service.add_message(session_id, "user", tool_result_content)

    def api_response_callback(req, res, err):
        if err:
            print(f"[API Error] {err}")
            asyncio.create_task(send_message({
                "type": "agent_message",
                "message": f"API Error: {err}"
            }))

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            
            if not user_message:
                continue
            
            print(f"[*] Received message: {user_message}")
            
            # Add user message to database
            db_service.add_message(session_id, "user", [{"type": "text", "text": user_message}])
            
            # Add user message to messages_for_api
            messages_for_api.append({
                "role": "user",
                "content": [{"type": "text", "text": user_message}]
            })
            
            # Store original message count
            original_message_count = len(messages_for_api)
            
            # Run the sampling loop
            try:
                await sampling_loop(
                    messages=messages_for_api,
                    api_provider=APIProvider(),
                    output_callback=output_callback,
                    tool_output_callback=tool_output_callback,
                    api_response_callback=api_response_callback
                )
            except Exception as e:
                print(f"[Error] Sampling loop failed: {e}")
                asyncio.create_task(send_message({
                    "type": "agent_message",
                    "message": f"Error: {str(e)}"
                }))
            
            # Save any new messages to database (both assistant and tool result messages)
            if len(messages_for_api) > original_message_count:
                for i in range(original_message_count, len(messages_for_api)):
                    message = messages_for_api[i]
                    if message.get("role") == "assistant":
                        db_service.add_message(session_id, "assistant", message["content"])
                    elif message.get("role") == "user" and any(
                        isinstance(content, dict) and content.get("type") == "tool_result"
                        for content in message.get("content", [])
                    ):
                        # This is a tool result message (contains images)
                        db_service.add_message(session_id, "user", message["content"])
    
    except WebSocketDisconnect:
        print(f"[-] WebSocket disconnected: {session_id}")
    except Exception as e:
        print(f"[Error] WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "agent_message",
                "message": f"Connection error: {str(e)}"
            })
        except:
            pass 