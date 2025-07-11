#!/usr/bin/env python3
"""
Test script to verify that battle data is being POSTed to the leaderboard server.
Run this to see if the data flow is working correctly.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_leaderboard_post():
    """Test posting data to the leaderboard server."""
    
    print("=== Testing Leaderboard POST Updates ===")
    print("This test will send sample battle data to the leaderboard server.")
    print("Make sure the leaderboard server is running on port 5000.\n")
    
    # Sample data to send
    test_data = {
        "bot_stats": {
            "TestBot1": {
                "username": "TestBot1",
                "elo_rating": 1250.0,
                "wins": 3,
                "losses": 1,
                "draws": 0,
                "total_battles": 4,
                "win_rate": 0.75,
                "longest_win_streak": 3,
                "current_win_streak": 2,
                "last_battle_time": datetime.now().timestamp(),
                "battle_formats": {"gen9randombattle": 4}
            },
            "TestBot2": {
                "username": "TestBot2", 
                "elo_rating": 1150.0,
                "wins": 1,
                "losses": 3,
                "draws": 0,
                "total_battles": 4,
                "win_rate": 0.25,
                "longest_win_streak": 1,
                "current_win_streak": 0,
                "last_battle_time": datetime.now().timestamp(),
                "battle_formats": {"gen9randombattle": 4}
            }
        },
        "battle_results": [
            {
                "battle_id": "test123",
                "bot1_username": "TestBot1",
                "bot2_username": "TestBot2", 
                "winner": "TestBot1",
                "battle_format": "gen9randombattle",
                "duration": 45.5,
                "turns": 12,
                "battle_log": None,
                "timestamp": datetime.now().timestamp()
            }
        ]
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print("Sending POST request to http://localhost:5000/api/update...")
            async with session.post(
                "http://localhost:5000/api/update",
                json=test_data,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                print(f"Response status: {response.status}")
                
                response_text = await response.text()
                print(f"Response body: {response_text}")
                
                if response.status == 200:
                    print("\n✅ SUCCESS: Data was posted to leaderboard server!")
                    print("Check the web interface at http://localhost:5000 to see the updates.")
                else:
                    print(f"\n❌ FAILED: Server returned status {response.status}")
                    
    except aiohttp.ClientConnectorError:
        print("\n❌ FAILED: Could not connect to leaderboard server.")
        print("Make sure the server is running: python -m src.bot_vs_bot.leaderboard_server")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_leaderboard_post())