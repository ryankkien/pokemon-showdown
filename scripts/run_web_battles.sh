#!/bin/bash

# Script to run the web-based battle system

echo "🚀 Starting Pokemon Showdown LLM Battle Arena..."
echo ""

# Kill previous processes
echo "🔄 Killing any existing processes..."

# Kill Pokemon Showdown server processes
pkill -f "node pokemon-showdown" 2>/dev/null || true
pkill -f "pokemon-showdown" 2>/dev/null || true

# Kill backend Python processes
pkill -f "src/bot_vs_bot/run_bot_vs_bot.py" 2>/dev/null || true
pkill -f "bot_vs_bot" 2>/dev/null || true

# Kill React dev server
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Kill any processes using the specific ports
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :5000 | xargs kill -9 2>/dev/null || true
lsof -ti :5001 | xargs kill -9 2>/dev/null || true
lsof -ti :3000 | xargs kill -9 2>/dev/null || true

# Wait a moment for processes to die
sleep 2

echo "✅ Previous processes killed"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root (parent of scripts directory)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "src/bot_vs_bot/run_bot_vs_bot.py" ]; then
    echo "Error: Cannot find bot_vs_bot files. Expected to be in: $PROJECT_ROOT"
    exit 1
fi

# Start the local Pokemon Showdown server
echo "🎮 Starting local Pokemon Showdown server..."
if [ -d "server/pokemon-showdown" ]; then
    cd server/pokemon-showdown && node pokemon-showdown &
    SHOWDOWN_PID=$!
    echo "Showdown PID: $SHOWDOWN_PID"
    cd "$PROJECT_ROOT"
    sleep 3
else
    echo "⚠️  Local Pokemon Showdown not found in server/pokemon-showdown"
    echo "   Chat integration will not work without it"
fi

# Set Python path and start the backend with web server
echo "📊 Starting backend server with web interface..."
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
python3 src/bot_vs_bot/run_bot_vs_bot.py \
    --mode web \
    --leaderboard \
    --leaderboard-port 5000 \
    --models gemini openai anthropic &

BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

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
echo "✅ Services started successfully!"
echo ""
echo "🌐 Web Interface: http://localhost:3000"
echo "📊 API Server: http://localhost:5000" 
echo "🔌 WebSocket Server: http://localhost:5001"
if [ ! -z "$SHOWDOWN_PID" ]; then
    echo "🎮 Pokemon Showdown: http://localhost:8000"
fi
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID $SHOWDOWN_PID 2>/dev/null; exit" INT

# Keep script running
wait