#!/usr/bin/env python3
"""
Clean up leaderboard by removing test bots and bots without proper model names.
"""
import json
import re
from datetime import datetime


def cleanup_leaderboard(leaderboard_file='leaderboard_data.json', backup=True):
    """Remove test bots and generic bot names from leaderboard."""
    
    # Load current data
    with open(leaderboard_file, 'r') as f:
        data = json.load(f)
    
    print(f"Cleaning up leaderboard from {leaderboard_file}")
    print(f"Current bots: {len(data.get('bot_stats', {}))}")
    print(f"Current battles: {len(data.get('battle_history', []))}")
    
    # Create backup if requested
    if backup:
        backup_file = f"{leaderboard_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"✅ Backup created: {backup_file}")
    
    # Define bots to remove
    bots_to_remove = set()
    
    # Remove test bots and generic names
    for username in data.get('bot_stats', {}).keys():
        if (
            username.startswith('TestBot') or
            username.startswith('IntegrationBot') or
            username in ['GeminiBot', 'OpenAIBot', 'AnthropicBot', 'OllamaBot'] or
            re.match(r'^Bot\d*$', username) or  # Bot, Bot1, Bot2, etc.
            username.lower() in ['test', 'demo', 'example']
        ):
            bots_to_remove.add(username)
    
    print(f"\nBots to remove: {sorted(bots_to_remove)}")
    
    if not bots_to_remove:
        print("✅ No bots need to be removed!")
        return
    
    # Remove bot stats
    original_bot_count = len(data['bot_stats'])
    for username in bots_to_remove:
        if username in data['bot_stats']:
            del data['bot_stats'][username]
    
    # Remove battles involving these bots
    original_battle_count = len(data['battle_history'])
    cleaned_battles = []
    
    for battle in data['battle_history']:
        if (battle['bot1_username'] not in bots_to_remove and 
            battle['bot2_username'] not in bots_to_remove):
            cleaned_battles.append(battle)
    
    data['battle_history'] = cleaned_battles
    
    # Update timestamp
    data['last_updated'] = datetime.now().isoformat()
    
    # Save cleaned data
    with open(leaderboard_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Summary
    removed_bots = original_bot_count - len(data['bot_stats'])
    removed_battles = original_battle_count - len(data['battle_history'])
    
    print(f"\n✅ Cleanup completed!")
    print(f"   Removed {removed_bots} bots")
    print(f"   Removed {removed_battles} battles")
    print(f"   Remaining: {len(data['bot_stats'])} bots, {len(data['battle_history'])} battles")
    
    # Show remaining bots
    if data['bot_stats']:
        print(f"\nRemaining bots:")
        for username, stats in sorted(data['bot_stats'].items()):
            battles = stats['total_battles']
            record = f"{stats['wins']}-{stats['losses']}-{stats['draws']}"
            elo = stats['elo_rating']
            print(f"   {username}: {battles} battles ({record}) ELO: {elo}")


def main():
    """Command line interface for leaderboard cleanup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up Pokemon Showdown bot leaderboard")
    parser.add_argument('--file', default='leaderboard_data.json', help='Leaderboard file to clean')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without actually doing it')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        
        with open(args.file, 'r') as f:
            data = json.load(f)
        
        bots_to_remove = set()
        for username in data.get('bot_stats', {}).keys():
            if (
                username.startswith('TestBot') or
                username.startswith('IntegrationBot') or
                username in ['GeminiBot', 'OpenAIBot', 'AnthropicBot', 'OllamaBot'] or
                re.match(r'^Bot\d*$', username) or
                username.lower() in ['test', 'demo', 'example']
            ):
                bots_to_remove.add(username)
        
        print(f"Would remove these bots: {sorted(bots_to_remove) if bots_to_remove else 'None'}")
        
        battles_to_remove = 0
        for battle in data.get('battle_history', []):
            if (battle['bot1_username'] in bots_to_remove or 
                battle['bot2_username'] in bots_to_remove):
                battles_to_remove += 1
        
        print(f"Would remove {battles_to_remove} battles involving these bots")
        
    else:
        cleanup_leaderboard(args.file, backup=not args.no_backup)


if __name__ == "__main__":
    main()