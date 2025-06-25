#!/bin/bash

# Setup script for local Pokemon Showdown server

echo "Setting up local Pokemon Showdown server..."

# Create server directory
mkdir -p server

# Clone Pokemon Showdown if not already present
if [ ! -d "server/pokemon-showdown" ]; then
    echo "Cloning Pokemon Showdown..."
    git clone https://github.com/smogon/pokemon-showdown.git server/pokemon-showdown
else
    echo "Pokemon Showdown already cloned, pulling latest..."
    cd server/pokemon-showdown && git pull && cd ../..
fi

# Install dependencies
echo "Installing server dependencies..."
cd server/pokemon-showdown
npm install

# Create custom config
echo "Creating server configuration..."
cat > config/config.js << 'EOF'
'use strict';

exports.port = 8000;
exports.bindaddress = '127.0.0.1';
exports.serverid = 'localhost';
exports.servertoken = 'unused';

// No authentication required for local testing
exports.noipchecks = true;
exports.nothrottle = true;

// Allow bots
exports.allowrequesttoken = true;
exports.tournamentsmanagement = false;

// Logging
exports.logchat = false;
exports.logchallenges = false;
exports.logbattles = false;

// Disable most features for simplicity
exports.disablehotpatchall = true;
EOF

echo "Server setup complete!"
echo ""
echo "To start the server, run: ./start_server.sh"