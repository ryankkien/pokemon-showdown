#!/usr/bin/env python3
"""
Debug script to check leaderboard data
"""
import json
import os

def check_leaderboard_data():
    """Check the leaderboard data file to see what's stored"""
    data_file = "leaderboard_data.json"
    
    if not os.path.exists(data_file):
        print(f"No leaderboard data file found at {data_file}")
        return
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    print("Leaderboard Data Debug")
    print("=" * 60)
    
    # Check bot stats
    print(f"\nTotal bots: {len(data.get('bot_stats', {}))}")
    print("\nBot Statistics:")
    print("-" * 60)
    
    for username, stats in data.get('bot_stats', {}).items():
        print(f"\n{username}:")
        print(f"  ELO Rating: {stats.get('elo_rating', 'N/A')}")
        print(f"  Wins: {stats.get('wins', 0)}")
        print(f"  Losses: {stats.get('losses', 0)}")
        print(f"  Draws: {stats.get('draws', 0)}")
        print(f"  Total Battles: {stats.get('total_battles', 0)}")
        print(f"  Win Rate: {stats.get('win_rate', 0) * 100:.1f}%")
        print(f"  Current Streak: {stats.get('current_win_streak', 0)}")
        print(f"  Longest Streak: {stats.get('longest_win_streak', 0)}")
    
    # Check battle history
    print(f"\n\nTotal battles in history: {len(data.get('battle_history', []))}")
    
    # Show recent battles
    recent_battles = data.get('battle_history', [])[-5:]
    if recent_battles:
        print("\nRecent Battles:")
        print("-" * 60)
        for battle in recent_battles:
            print(f"\n{battle.get('bot1_username')} vs {battle.get('bot2_username')}")
            print(f"  Winner: {battle.get('winner', 'N/A')}")
            print(f"  Duration: {battle.get('duration', 0):.1f}s")
            print(f"  Turns: {battle.get('turns', 0)}")
            print(f"  Format: {battle.get('battle_format', 'N/A')}")

if __name__ == "__main__":
    check_leaderboard_data()
    
    # Also check if there's a demo file
    if os.path.exists("demo_leaderboard_data.json"):
        print("\n\n" + "=" * 60)
        print("Demo Leaderboard Data:")
        print("=" * 60)
        data_file = "demo_leaderboard_data.json"
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        print(f"Demo file has {len(data.get('bot_stats', {}))} bots")
        for username, stats in list(data.get('bot_stats', {}).items())[:3]:
            print(f"\n{username}: ELO {stats.get('elo_rating')}, "
                  f"Record {stats.get('wins')}-{stats.get('losses')}-{stats.get('draws')}, "
                  f"Win Rate {stats.get('win_rate', 0) * 100:.1f}%")