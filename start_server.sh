#!/bin/bash

# Start script for local Pokemon Showdown server

echo "Starting Pokemon Showdown server..."

# Kill any existing Pokemon Showdown processes
echo "Checking for existing Pokemon Showdown processes..."
if pgrep -f "pokemon-showdown" > /dev/null; then
    echo "Found existing Pokemon Showdown processes, killing them..."
    pkill -f "pokemon-showdown"
    sleep 2
fi

# Also check if anything is using port 8000
if lsof -i :8000 | grep -q LISTEN; then
    echo "Found process using port 8000, attempting to kill it..."
    # Get the PID of the process listening on port 8000
    PID=$(lsof -t -i :8000)
    if [ ! -z "$PID" ]; then
        kill -9 $PID 2>/dev/null || true
        echo "Killed process $PID"
        # Wait a moment for the port to be released
        sleep 2
    fi
fi

# Check if server is set up
if [ ! -d "server/pokemon-showdown" ]; then
    echo "Server not found. Running setup first..."
    ./setup_server.sh
fi

# Start the server
cd server/pokemon-showdown
echo "Starting server on http://localhost:8000"

# Clear the error log
> logs/errors.txt

# Start the server (it will run in foreground)
echo "Server is starting... Press Ctrl+C to stop"
echo ""
node pokemon-showdown start --no-security