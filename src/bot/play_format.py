#!/usr/bin/env python3
"""
Convenience script to play different Pokemon Showdown formats.
Usage: python play_format.py [format] [battles]
"""

import sys
import os
import subprocess
from dotenv import load_dotenv, set_key

# Available formats with descriptions
FORMATS = {
    "gen9": "gen9randombattle",
    "gen8": "gen8randombattle", 
    "gen7": "gen7randombattle",
    "gen6": "gen6randombattle",
    "gen5": "gen5randombattle",
    "gen4": "gen4randombattle",
    "gen3": "gen3randombattle",
    "gen2": "gen2randombattle", 
    "gen1": "gen1randombattle",
    "gen9doubles": "gen9randomdoublesbattle",
    "gen8doubles": "gen8randomdoublesbattle"
}

# All supported random battle formats for validation
SUPPORTED_RANDOM_BATTLE_FORMATS = [
    "gen9randombattle",
    "gen8randombattle", 
    "gen7randombattle",
    "gen6randombattle",
    "gen5randombattle",
    "gen4randombattle",
    "gen3randombattle",
    "gen2randombattle", 
    "gen1randombattle",
    "gen9randomdoublesbattle",
    "gen8randomdoublesbattle"
]

FORMAT_DESCRIPTIONS = {
    "gen9": "Current generation (Scarlet/Violet)",
    "gen8": "Sword/Shield generation", 
    "gen7": "Ultra Sun/Ultra Moon generation",
    "gen6": "Omega Ruby/Alpha Sapphire generation",
    "gen5": "Black 2/White 2 generation",
    "gen4": "Diamond/Pearl/Platinum generation",
    "gen3": "Ruby/Sapphire/Emerald generation",
    "gen2": "Gold/Silver/Crystal generation",
    "gen1": "Red/Blue/Yellow generation",
    "gen9doubles": "Current generation doubles",
    "gen8doubles": "Sword/Shield doubles"
}

def show_help():
    """Show available formats."""
    print("Pokemon Showdown Bot - Format Selector")
    print("=" * 40)
    print("\nUsage: python play_format.py [format] [battles]")
    print("\nAvailable formats:")
    for short, desc in FORMAT_DESCRIPTIONS.items():
        print(f"  {short:<12} - {desc}")
    print("\nExamples:")
    print("  python play_format.py gen1")
    print("  python play_format.py gen8 10")
    print("  python play_format.py gen9doubles 3")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        show_help()
        return
    
    format_arg = sys.argv[1].lower()
    battles = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    if format_arg not in FORMATS:
        print(f"Error: Unknown format '{format_arg}'")
        print("Run 'python play_format.py help' to see available formats")
        return
    
    battle_format = FORMATS[format_arg]
    
    print(f"Setting up bot for {FORMAT_DESCRIPTIONS[format_arg]} ({battle_format})")
    print(f"Playing {battles} battles...")
    
    # Update .env file
    env_path = ".env"
    if os.path.exists(env_path):
        set_key(env_path, "PS_BATTLE_FORMAT", battle_format)
        print(f"Updated PS_BATTLE_FORMAT to {battle_format}")
    else:
        print("Warning: .env file not found, using default configuration")
    
    # Set environment variable for this session
    os.environ["PS_BATTLE_FORMAT"] = battle_format
    
    # Run the bot
    try:
        result = subprocess.run([sys.executable, "-m", "src.bot.run_bot"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running bot: {e}")
    except KeyboardInterrupt:
        print("\nBot stopped by user")

if __name__ == "__main__":
    main()