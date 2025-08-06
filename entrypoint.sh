#!/bin/bash
set -e

./start_all.sh
./novnc_startup.sh

python http_server.py > /tmp/server_logs.txt 2>&1 &

STREAMLIT_SERVER_PORT=8501 python -m streamlit run ./app/tools/streamlit.py > /tmp/streamlit_stdout.log &

echo "✨ Starting FastAPI server on port 8081..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload &
echo "✨ Computer Use Demo is ready!"
echo "➡️  Open http://localhost:8080 in your browser to begin"

# Keep the container running
tail -f /dev/null
