from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from fastapi.openapi.utils import get_openapi

from .api.v1 import sessions_router, websocket_router

app = FastAPI(
    title="Computer Use App API",
    description="""
    # Computer Use App API
    
    A powerful AI agent that can interact with your computer through a web interface.
    
    ## Features
    
    * **Session Management** - Create, manage, and delete conversation sessions
    * **Real-time Communication** - WebSocket endpoints for live agent interaction
    * **Screenshot Capabilities** - Agent can take screenshots and analyze visual content
    * **Command Execution** - Run terminal commands safely
    * **Persistent Storage** - PostgreSQL database for conversation history
    
    ## Quick Start
    
    1. Create a new session using `POST /api/session`
    2. Connect to WebSocket at `ws://localhost:8081/ws/session/{session_id}`
    3. Send messages and receive real-time responses
    4. Retrieve conversation history using `GET /api/session/{session_id}/history`
    
    ## Authentication
    
    Currently, the API doesn't require authentication. All endpoints are publicly accessible.
    
    ## WebSocket Communication
    
    The WebSocket endpoint provides real-time communication with the AI agent:
    
    * Send user messages to the agent
    * Receive agent responses, screenshots, and thinking processes
    * Handle errors and status updates
    
    For detailed WebSocket documentation, see the `/ws/session/{session_id}` endpoint.
    """,
    version="1.0.0",
    contact={
        "name": "Computer Use App Support",
        "url": "https://github.com/your-repo/computer-use-demo",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "sessions",
            "description": "Operations with sessions. Create, manage, and delete conversation sessions with the AI agent.",
        },
        {
            "name": "websocket",
            "description": "Real-time WebSocket communication with the AI agent. Send messages and receive live responses.",
        },
    ],
    servers=[
        {"url": "http://localhost:8081", "description": "Development server"},
        {"url": "https://your-domain.com", "description": "Production server"},
    ],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", tags=["root"])
def read_index():
    """
    Serve the main application interface.
    
    Returns the main HTML page for the Computer Use App.
    """
    return FileResponse("app/static/index.html")

# Add CORS middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Include API routers
app.include_router(sessions_router)
app.include_router(websocket_router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom security schemes if needed
    openapi_schema["components"]["securitySchemes"] = {
        "apiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication (not currently required)"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi