#!/usr/bin/env python3
"""
Test script to verify bot error handling improvements.
This will run a few battles and monitor for invalid move attempts.
"""

import asyncio
import sys
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, '.')

from src.bot_vs_bot.run_bot_vs_bot import run_continuous_matchmaking
from src.bot_vs_bot.bot_vs_bot_config import BotVsBotConfigManager, create_quick_battle_config, BotConfig, MatchmakingStrategy

# Set up detailed logging to see retry behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'bot_error_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Enable debug logging for bot decisions
logging.getLogger('src.bot.bot').setLevel(logging.DEBUG)
logging.getLogger('src.bot.response_parser').setLevel(logging.DEBUG)

async def test_bot_error_handling():
    """Run a short test to see if bots handle invalid moves properly."""
    
    print("=== Testing Bot Error Handling ===")
    print("This test will run a few battles and monitor for invalid move attempts.")
    print("Check the log file for detailed retry behavior.\n")
    
    # Create a simple config with just a few bots
    config_manager = BotVsBotConfigManager()
    config_manager.config = create_quick_battle_config()
    
    # Use only a subset of bots for faster testing
    test_bots = [
        BotConfig(username="TestGemini", llm_provider="gemini", model_name="gemini-1.5-flash"),
        BotConfig(username="TestGPT", llm_provider="openai", model_name="gpt-4o-mini"),
        BotConfig(username="TestClaude", llm_provider="anthropic", model_name="claude-3-haiku-20240307"),
    ]
    
    # Filter to only use available bots based on environment
    available_bots = []
    for bot in test_bots:
        if bot.llm_provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
            print(f"Skipping {bot.username} - no GEMINI_API_KEY")
        elif bot.llm_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            print(f"Skipping {bot.username} - no OPENAI_API_KEY")
        elif bot.llm_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            print(f"Skipping {bot.username} - no ANTHROPIC_API_KEY")
        else:
            available_bots.append(bot)
    
    if len(available_bots) < 2:
        print("ERROR: Need at least 2 bots with API keys configured")
        print("Please set environment variables for at least 2 of: GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY")
        return
    
    config_manager.config.bot_configs = available_bots
    config_manager.config.matchmaking_strategy = MatchmakingStrategy.RANDOM_PAIRING
    
    print(f"Running test with {len(available_bots)} bots: {[b.username for b in available_bots]}")
    print("Running for 3 minutes to observe retry behavior...\n")
    
    # Run for 3 minutes
    await run_continuous_matchmaking(config_manager, duration_minutes=3)
    
    print("\n=== Test Complete ===")
    print("Check the log file for:")
    print("1. 'Invalid action on attempt' messages showing retry behavior")
    print("2. 'Previous attempt(s) failed' in prompts")
    print("3. 'VALID OPTIONS ONLY' sections in retry prompts")
    print("4. Specific failure reasons like 'Move not available' or 'Did you mean'")

import os

if __name__ == "__main__":
    asyncio.run(test_bot_error_handling())