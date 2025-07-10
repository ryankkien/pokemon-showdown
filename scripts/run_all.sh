
#!/bin/bash

# All-in-one script to run the bot with automatic server setup

echo "Pokemon Showdown LLM Bot Runner"
echo "==============================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is required but not installed."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# # Install Python dependencies if needed
# echo "Checking Python dependencies..."
# echo "Using Python: $(which python3)"
# echo "Python version: $(python3 --version)"

# # Upgrade pip first if needed
# echo "Upgrading pip..."
# python3 -m pip install --upgrade pip

# echo "Installing dependencies..."
# # Install each dependency separately to handle failures
# python3 -m pip install poke-env
# python3 -m pip install "requests>=2.28.0"
# python3 -m pip install python-dotenv
# python3 -m pip install openai
# python3 -m pip install psutil

# For Python 3.8, we need older numpy
if python3 -c "import sys; exit(0 if sys.version_info < (3, 9) else 1)"; then
    echo "Python 3.8 detected, installing compatible numpy..."
    python3 -m pip install "numpy<1.24.0"
fi

# Run the bot with server management
echo ""
echo "Starting bot with integrated server management..."
echo ""
cd "$(dirname "$0")/.." && python3 run_bot.py