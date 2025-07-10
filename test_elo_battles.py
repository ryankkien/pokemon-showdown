#!/usr/bin/env python3
"""
Quick test script to verify ELO changes during actual battles
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_quick_battles():
    """Run a quick 2-minute test with 3 bots to see ELO changes"""
    print("Starting quick ELO test battles...")
    print("This will run for 2 minutes with 3 bots to demonstrate ELO changes")
    print("-" * 60)
    
    # Import here to avoid early logging
    from src.bot_vs_bot.run_bot_vs_bot import main
    
    # Simulate command line args for a quick test
    test_args = [
        "test_elo_battles.py",
        "--mode", "continuous",
        "--duration", "2",  # 2 minutes
        "--models", "gemini", "gpt-4o", "claude",  # Just 3 models
        "--verbose"
    ]
    
    # Override sys.argv
    original_argv = sys.argv
    sys.argv = test_args
    
    try:
        # Run the bot vs bot system
        result = await main()
        print(f"\nTest completed with result: {result}")
    finally:
        # Restore original argv
        sys.argv = original_argv
    
    print("\n" + "=" * 60)
    print("ELO Test Complete!")
    print("Check http://localhost:5000 to see the leaderboard with updated ELO ratings")
    print("The leaderboard shows:")
    print("- Real-time ELO ratings")
    print("- Win/Loss/Draw records")
    print("- Win rates")
    print("- Recent form tracking")

if __name__ == "__main__":
    print("ELO System Test")
    print("=" * 60)
    print("This test will:")
    print("1. Start the leaderboard server (default enabled)")
    print("2. Run battles between 3 bots for 2 minutes")
    print("3. Show ELO rating changes in real-time")
    print("\nMake sure the Pokemon Showdown server is running on port 8000!")
    print("=" * 60)
    
    asyncio.run(test_quick_battles())