#!/usr/bin/env python3
"""
Unified Pokemon Showdown Bot CLI interface.
Provides a single entry point for all bot functionality.
"""
import argparse
import asyncio
import sys

def main():
    """Main CLI interface for Pokemon Showdown bot system."""
    parser = argparse.ArgumentParser(
        description="Pokemon Showdown Bot System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Single bot command
    bot_parser = subparsers.add_parser('bot', help='Run a single bot')
    bot_parser.set_defaults(func=run_single_bot)
    
    # Bot vs bot command
    vs_parser = subparsers.add_parser('vs', help='Run bot vs bot battles')
    vs_parser.set_defaults(func=run_bot_vs_bot)
    
    # Play format command
    format_parser = subparsers.add_parser('format', help='Run play format utility')
    format_parser.set_defaults(func=run_play_format)
    
    # Leaderboard server command
    leaderboard_parser = subparsers.add_parser('leaderboard', help='Run leaderboard server')
    leaderboard_parser.set_defaults(func=run_leaderboard_server)
    
    # Demo leaderboard command
    demo_parser = subparsers.add_parser('demo', help='Run demo leaderboard')
    demo_parser.set_defaults(func=run_demo_leaderboard)
    
    # Fix leaderboard command
    fix_parser = subparsers.add_parser('fix-leaderboard', help='Fix leaderboard sync issues')
    fix_parser.set_defaults(func=fix_leaderboard)
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run all tests')
    test_parser.set_defaults(func=run_tests)
    
    args = parser.parse_args()
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func()


def run_single_bot():
    """Run a single bot."""
    from src.bot.run_bot import main
    return main()


def run_bot_vs_bot():
    """Run bot vs bot battles."""
    from src.bot_vs_bot.run_bot_vs_bot import main
    return asyncio.run(main())


def run_play_format():
    """Run play format utility."""
    from src.bot.play_format import main
    return main()


def run_leaderboard_server():
    """Run leaderboard server."""
    from src.bot_vs_bot.leaderboard_server import main
    return main()


def run_demo_leaderboard():
    """Run demo leaderboard."""
    from src.bot_vs_bot.demo_leaderboard import main
    return main()


def fix_leaderboard():
    """Fix leaderboard sync issues."""
    from src.utils.leaderboard_utils import main
    return main()


def run_tests():
    """Run all tests."""
    from tests.test_all import main
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(main())