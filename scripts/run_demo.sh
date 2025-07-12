#!/bin/bash

# Script to run the demo web interface

echo "🚀 Starting Pokemon Showdown LLM Battle Arena (Demo Mode)..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root (parent of scripts directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Kill any existing processes
echo "Cleaning up any existing processes..."
pkill -f "demo_battle_server.py" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

# Start the demo battle server
echo "📊 Starting demo battle server..."
python3 src/bot_vs_bot/demo_battle_server.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Start the React dev server
echo ""
echo "🌐 Starting React development server..."
if [ -d "$PROJECT_ROOT/web" ]; then
    cd "$PROJECT_ROOT/web"
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "Installing web dependencies..."
        npm install
    fi
    npm run dev &
    FRONTEND_PID=$!
    echo "Frontend PID: $FRONTEND_PID"
else
    echo "⚠️  Web directory not found at $PROJECT_ROOT/web"
    echo "   Web interface will not be available"
fi

# Display URLs
echo ""
echo "✅ Demo server started successfully!"
echo ""
echo "🌐 Web Interface: http://localhost:3000"
echo "📊 API Server: http://localhost:5000"
echo ""
echo "The demo will automatically simulate battles between LLM models."
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

# Keep script running
wait