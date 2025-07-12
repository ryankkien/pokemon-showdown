#!/usr/bin/env python3
"""
Leaderboard utilities for Pokemon Showdown bot system.
Includes functionality to sync and fix leaderboard data.
"""
import json
from src.bot_vs_bot.bot_matchmaker import BotStats


def fix_leaderboard_sync(leaderboard_file='leaderboard_data.json'):
    """Recalculate stats from battle history"""
    
    # Load current data
    with open(leaderboard_file, 'r') as f:
        data = json.load(f)
    
    print("Fixing leaderboard sync...")
    print(f"Found {len(data.get('battle_history', []))} battles")
    
    # Reset all stats
    bot_stats = {}
    
    # Recalculate from battle history
    for battle in data.get('battle_history', []):
        bot1 = battle['bot1_username']
        bot2 = battle['bot2_username']
        winner = battle.get('winner')
        
        # Initialize stats if needed
        if bot1 not in bot_stats:
            bot_stats[bot1] = {
                'username': bot1,
                'elo_rating': 1200.0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'total_battles': 0,
                'win_rate': 0.0,
                'longest_win_streak': 0,
                'current_win_streak': 0,
                'last_battle_time': 0,
                'battle_formats': {}
            }
        if bot2 not in bot_stats:
            bot_stats[bot2] = {
                'username': bot2,
                'elo_rating': 1200.0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'total_battles': 0,
                'win_rate': 0.0,
                'longest_win_streak': 0,
                'current_win_streak': 0,
                'last_battle_time': 0,
                'battle_formats': {}
            }
        
        # Update battle counts
        bot_stats[bot1]['total_battles'] += 1
        bot_stats[bot2]['total_battles'] += 1
        
        # Update wins/losses
        if winner == bot1:
            bot_stats[bot1]['wins'] += 1
            bot_stats[bot2]['losses'] += 1
            bot_stats[bot1]['current_win_streak'] += 1
            bot_stats[bot2]['current_win_streak'] = 0
            bot_stats[bot1]['longest_win_streak'] = max(
                bot_stats[bot1]['longest_win_streak'],
                bot_stats[bot1]['current_win_streak']
            )
        elif winner == bot2:
            bot_stats[bot2]['wins'] += 1
            bot_stats[bot1]['losses'] += 1
            bot_stats[bot2]['current_win_streak'] += 1
            bot_stats[bot1]['current_win_streak'] = 0
            bot_stats[bot2]['longest_win_streak'] = max(
                bot_stats[bot2]['longest_win_streak'],
                bot_stats[bot2]['current_win_streak']
            )
        else:
            # Draw
            bot_stats[bot1]['draws'] += 1
            bot_stats[bot2]['draws'] += 1
            bot_stats[bot1]['current_win_streak'] = 0
            bot_stats[bot2]['current_win_streak'] = 0
    
    # Calculate win rates and update ELO
    for username, stats in bot_stats.items():
        if stats['total_battles'] > 0:
            stats['win_rate'] = stats['wins'] / stats['total_battles']
            # Simple ELO calculation based on performance
            stats['elo_rating'] = 1200 + (stats['wins'] - stats['losses']) * 10
    
    # Update the data
    data['bot_stats'] = bot_stats
    
    # Save back
    with open(leaderboard_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print("\nFixed stats:")
    for username, stats in bot_stats.items():
        if stats['total_battles'] > 0:
            print(f"{username}: {stats['wins']}-{stats['losses']}-{stats['draws']} "
                  f"(ELO: {stats['elo_rating']}, WR: {stats['win_rate']*100:.1f}%)")


def main():
    """Command line interface for leaderboard utilities."""
    fix_leaderboard_sync()
    print("\nLeaderboard data has been fixed!")
    print("The web leaderboard should now show correct stats.")


if __name__ == "__main__":
    main()