#!/bin/bash
set -e

./start_all.sh
./novnc_startup.sh

python http_server.py > /tmp/server_logs.txt 2>&1 &


echo "✨ Starting FastAPI server on port 8081..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload &
echo "✨ Computer Use Demo is ready!"

# Keep the container running
tail -f /dev/null
