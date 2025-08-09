from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
 

from .api.v1 import sessions_router, websocket_router

app = FastAPI(
    title="Claude WebSocket Chat",
    description="A simple chat application using Claude's WebSocket API",
    version="0.1.0"
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

 