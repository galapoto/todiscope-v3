#!/bin/bash
# Kill process using port 8400

PORT=8400
PID=$(lsof -ti:$PORT)

if [ -z "$PID" ]; then
    echo "No process found on port $PORT"
    exit 0
fi

echo "Killing process $PID on port $PORT"
kill -9 $PID
echo "Port $PORT is now free"




