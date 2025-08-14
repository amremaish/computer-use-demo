from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
 

from .api.v1 import sessions_router, websocket_router

tags_metadata = [
    {
        "name": "sessions",
        "description": "Manage chat sessions and retrieve histories.",
    },
    {
        "name": "websocket",
        "description": "Real-time interaction endpoint using WebSocket (not part of OpenAPI).",
    },
]

app = FastAPI(
    title="Claude WebSocket Chat",
    description=(
        "A simple chat application using Claude's WebSocket API.\n\n"
        "- Swagger UI: `/api/docs`\n"
        "- ReDoc: `/api/redoc`\n"
        "- OpenAPI JSON: `/api/openapi.json`\n"
        "WebSocket endpoints are documented for reference but are not part of the OpenAPI schema."
    ),
    version="0.1.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "Anthropic Quickstarts",
        "url": "https://github.com/anthropics/anthropic-quickstarts",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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

 