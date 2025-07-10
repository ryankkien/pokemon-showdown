#!/usr/bin/env python3
"""
Wrapper script to run bot vs bot from the root directory.
"""
import asyncio
import sys
from src.bot_vs_bot.run_bot_vs_bot import main

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))