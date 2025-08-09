# Computer Use App

A powerful AI agent that can interact with your computer through a web interface, capable of taking screenshots, running commands, editing files, and more. Built with FastAPI and Anthropic's Claude API.

## 🚀 Features

- **Real-time AI Agent Interaction**: Chat with an AI agent that can control your computer
- **Screenshot Capabilities**: Agent can take screenshots and analyze visual content
- **Command Execution**: Run terminal commands safely
- **WebSocket Communication**: Real-time updates and streaming responses
- **Session Management**: Persistent conversation history with database storage
- **VNC Integration**: Remote desktop access through noVNC
- **Interactive API Documentation**: Full Swagger/OpenAPI documentation with live testing

## 📋 Prerequisites

- Docker and Docker Compose
- Anthropic API key
- PostgreSQL (included in Docker setup)

## 🛠️ Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd computer-use-demo
```

### 2. Set Up Environment Variables

```bash
cp env_template.txt .env
```

Edit `.env` file with your configuration:

```env
# API Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# PostgreSQL Configuration
POSTGRES_DB=chat_sessions
POSTGRES_USER=computeruse
POSTGRES_PASSWORD=computeruse123
POSTGRES_PORT=5432
```

### 3. Run the Application

```bash
docker-compose up --build
```

### 4. Access the Application

Once the containers are running, you can access:

- **Main Application**: http://localhost:8080
- **VNC Desktop**: http://localhost:6080 (noVNC)
- **FastAPI App**: http://localhost:8081/
- **API Base URL**: http://localhost:8081

Note: Swagger/OpenAPI UI is disabled in this build.

## 🏗️ Project Structure

```
computer-use-demo/
├── app/                          # Main application code
│   ├── api/v1/                   # API endpoints
│   │   ├── sessions.py           # Session management API
│   │   └── websocket.py          # WebSocket endpoints
│   ├── core/                     # Core configuration
│   │   ├── config.py             # Application settings
│   │   └── database.py           # Database connection
│   ├── models/                   # Database models
│   │   ├── session.py            # Session model
│   │   └── message.py            # Message model
│   ├── services/                 # Business logic
│   │   └── database_service.py   # Database operations
│   ├── tools/                    # Agent tools
│   │   ├── agentic_loop.py       # Main agent logic
│   └── main.py                   # FastAPI application
├── agent_dashboard/              # Desktop environment setup
├── docker-compose.yml            # Docker services configuration
├── Dockerfile                    # Application container
├── requirements.txt              # Python dependencies
└── entrypoint.sh                 # Container startup script
```

## Sequence Diagram

The following diagram shows the end-to-end flow between the browser UI, FastAPI backend, the agent, database, and the VNC stack.

![Sequence Diagram](docs/sequance_diagrams.png)

## 📚 API Documentation

### Base URL
```
http://localhost:8081
```

### Authentication
Currently, the API doesn't require authentication. All endpoints are publicly accessible.

### REST API Endpoints

#### 1. Create Session
**POST** `/api/session`

Creates a new conversation session with the AI agent.

**Request Body:**
```json
{
  "session_name": "string (optional)",
  "display_name": "string (optional)", 
  "initial_prompt": "string (optional)"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "display_name": "string"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8081/api/session" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "My First Session",
    "initial_prompt": "Hello, can you help me with my computer?"
  }'
```

#### 2. Get Session Status
**GET** `/api/session/{session_id}`

Retrieves the current status and information of a session.

**Response:**
```json
{
  "session_id": "string",
  "display_name": "string",
  "status": "running|completed|error",
  "created_at": "datetime",
  "initial_prompt": "string"
}
```

**Example:**
```bash
curl "http://localhost:8081/api/session/4dccdad3-d809-473b-9bcf-1c7dfc095850"
```

#### 3. Get Session History
**GET** `/api/session/{session_id}/history`

Retrieves the complete conversation history for a session, including messages with images.

**Response:**
```json
{
  "session_id": "string",
  "display_name": "string",
  "status": "string",
  "created_at": "datetime",
  "initial_prompt": "string",
  "messages": [
    {
      "id": "integer",
      "role": "user|assistant",
      "content": [
        {
          "type": "text",
          "text": "string"
        },
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": "base64-encoded-image"
          }
        }
      ],
      "created_at": "datetime"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8081/api/session/4dccdad3-d809-473b-9bcf-1c7dfc095850/history"
```

#### 4. List All Sessions
**GET** `/api/sessions`

Retrieves a list of all available sessions.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "string",
      "display_name": "string",
      "status": "string",
      "created_at": "datetime",
      "message_count": "integer"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8081/api/sessions"
```

#### 5. Delete Session
**DELETE** `/api/session/{session_id}`

Deletes a session and all its associated messages.

**Response:**
```json
{
  "message": "Session {session_id} deleted successfully."
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8081/api/session/4dccdad3-d809-473b-9bcf-1c7dfc095850"
```

### WebSocket API

#### WebSocket Connection
**WebSocket** `/ws/session/{session_id}`

Establishes a real-time WebSocket connection for live communication with the AI agent.

**Connection:**
```javascript
const ws = new WebSocket(`ws://localhost:8081/ws/session/${sessionId}`);
```

**Message Types:**

1. **Agent Message** (text response from AI):
```json
{
  "type": "agent_message",
  "message": "string"
}
```

2. **Image** (screenshot or visual content):
```json
{
  "type": "image",
  "data": "base64-encoded-image"
}
```

3. **Thinking** (agent's thought process):
```json
{
  "type": "thinking",
  "message": "string"
}
```

4. **Error** (error messages):
```json
{
  "type": "agent_message",
  "message": "Error: error description"
}
```

**Sending Messages:**
```javascript
// Send a user message to the agent
ws.send(JSON.stringify({
  "message": "Take a screenshot of my desktop"
}));
```
## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request