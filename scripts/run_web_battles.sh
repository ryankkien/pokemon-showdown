#!/bin/bash

# Script to run the web-based battle system

echo "🚀 Starting Pokemon Showdown LLM Battle Arena..."
echo ""

# Check if we're in the right directory
if [ ! -f "src/bot_vs_bot/run_bot_vs_bot.py" ]; then
    echo "Error: Please run this script from the pokemon-showdown root directory"
    exit 1
fi

# Start the backend with web server
echo "📊 Starting backend server with web interface..."
python3 src/bot_vs_bot/run_bot_vs_bot.py \
    --mode continuous \
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
cd web && npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Display URLs
echo ""
echo "✅ Services started successfully!"
echo ""
echo "🌐 Web Interface: http://localhost:3000"
echo "📊 API Server: http://localhost:5000" 
echo "🔌 WebSocket Server: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT

# Keep script running
wait