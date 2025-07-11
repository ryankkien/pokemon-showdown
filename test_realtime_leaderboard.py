#!/usr/bin/env python3
"""
Test script to verify real-time leaderboard updates.
Run this and watch the web leaderboard to see updates after each battle.
"""

import asyncio
import json
import time
from datetime import datetime

print("=== Real-time Leaderboard Update Test ===")
print("1. Open http://localhost:5000 in your browser")
print("2. Watch as the leaderboard updates after each battle")
print("3. The green dot next to the header pulses to show real-time updates")
print("\nStarting battles in 5 seconds...\n")

time.sleep(5)

# Check current leaderboard state
try:
    with open('leaderboard_data.json', 'r') as f:
        data = json.load(f)
        print(f"Current leaderboard has {len(data.get('battle_history', []))} battles")
        print(f"Tracking {len(data.get('bot_stats', {}))} bots")
except:
    print("No existing leaderboard data")

print("\nStarting bot battles with real-time updates...")
print("Check the web interface - it should update within 5 seconds of each battle completion")
print("\nPress Ctrl+C to stop\n")

# Run the bot vs bot system
import subprocess
import sys

try:
    # Run for 5 minutes to observe real-time updates
    subprocess.run([
        sys.executable,
        "-m", "src.bot_vs_bot.run_bot_vs_bot",
        "--mode", "continuous",
        "--duration", "5",
        "--models", "gemini", "gpt", "claude"  # Use whatever models you have API keys for
    ])
except KeyboardInterrupt:
    print("\nTest stopped by user")

print("\n=== Test Complete ===")
print("Did you see the leaderboard update after each battle?")
print("The update should happen within 5 seconds of battle completion.")