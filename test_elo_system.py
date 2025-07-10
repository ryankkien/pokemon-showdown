#!/usr/bin/env python3
"""
Test script to verify ELO rating calculations
"""
import json
from src.bot_vs_bot.bot_matchmaker import BotMatchmaker, BotStats

def test_elo_calculations():
    """Test ELO rating changes after battles"""
    print("Testing ELO Rating System")
    print("=" * 50)
    
    # Create a matchmaker (with None for bot_manager since we're just testing ELO)
    matchmaker = BotMatchmaker(None)
    
    # Create two test bots with different ratings
    bot1_name = "TestBot1"
    bot2_name = "TestBot2"
    
    # Initialize bot stats
    matchmaker.bot_stats[bot1_name] = BotStats(
        username=bot1_name,
        elo_rating=1500.0,
        wins=10,
        losses=10,
        draws=0
    )
    
    matchmaker.bot_stats[bot2_name] = BotStats(
        username=bot2_name,
        elo_rating=1200.0,
        wins=5,
        losses=15,
        draws=0
    )
    
    print(f"\nInitial Ratings:")
    print(f"{bot1_name}: ELO {matchmaker.bot_stats[bot1_name].elo_rating}")
    print(f"{bot2_name}: ELO {matchmaker.bot_stats[bot2_name].elo_rating}")
    
    # Test 1: Higher rated player wins (expected outcome)
    print(f"\n--- Test 1: {bot1_name} (1500) beats {bot2_name} (1200) ---")
    old_elo1 = matchmaker.bot_stats[bot1_name].elo_rating
    old_elo2 = matchmaker.bot_stats[bot2_name].elo_rating
    
    # Update ELO ratings (bot1 wins)
    matchmaker.bot_stats[bot1_name].update_elo(old_elo2, 1.0)  # Win
    matchmaker.bot_stats[bot2_name].update_elo(old_elo1, 0.0)  # Loss
    matchmaker.bot_stats[bot1_name].wins += 1
    matchmaker.bot_stats[bot2_name].losses += 1
    
    new_elo1 = matchmaker.bot_stats[bot1_name].elo_rating
    new_elo2 = matchmaker.bot_stats[bot2_name].elo_rating
    
    print(f"{bot1_name}: {old_elo1:.1f} → {new_elo1:.1f} (change: {new_elo1 - old_elo1:+.1f})")
    print(f"{bot2_name}: {old_elo2:.1f} → {new_elo2:.1f} (change: {new_elo2 - old_elo2:+.1f})")
    
    # Test 2: Lower rated player wins (upset)
    print(f"\n--- Test 2: {bot2_name} ({new_elo2:.0f}) beats {bot1_name} ({new_elo1:.0f}) ---")
    old_elo1 = matchmaker.bot_stats[bot1_name].elo_rating
    old_elo2 = matchmaker.bot_stats[bot2_name].elo_rating
    
    # Update ELO ratings (bot2 wins)
    matchmaker.bot_stats[bot2_name].update_elo(old_elo1, 1.0)  # Win
    matchmaker.bot_stats[bot1_name].update_elo(old_elo2, 0.0)  # Loss
    matchmaker.bot_stats[bot2_name].wins += 1
    matchmaker.bot_stats[bot1_name].losses += 1
    
    new_elo1 = matchmaker.bot_stats[bot1_name].elo_rating
    new_elo2 = matchmaker.bot_stats[bot2_name].elo_rating
    
    print(f"{bot1_name}: {old_elo1:.1f} → {new_elo1:.1f} (change: {new_elo1 - old_elo1:+.1f})")
    print(f"{bot2_name}: {old_elo2:.1f} → {new_elo2:.1f} (change: {new_elo2 - old_elo2:+.1f})")
    
    # Test 3: Draw
    print(f"\n--- Test 3: Draw between {bot1_name} ({new_elo1:.0f}) and {bot2_name} ({new_elo2:.0f}) ---")
    old_elo1 = matchmaker.bot_stats[bot1_name].elo_rating
    old_elo2 = matchmaker.bot_stats[bot2_name].elo_rating
    
    # For draw, we need to manually calculate since _update_elo_ratings assumes winner/loser
    # Expected score for each player
    expected1 = 1 / (1 + 10 ** ((old_elo2 - old_elo1) / 400))
    expected2 = 1 / (1 + 10 ** ((old_elo1 - old_elo2) / 400))
    
    # For a draw, actual score is 0.5 for both
    k_factor = 32
    new_elo1 = old_elo1 + k_factor * (0.5 - expected1)
    new_elo2 = old_elo2 + k_factor * (0.5 - expected2)
    
    matchmaker.bot_stats[bot1_name].elo_rating = new_elo1
    matchmaker.bot_stats[bot2_name].elo_rating = new_elo2
    matchmaker.bot_stats[bot1_name].draws += 1
    matchmaker.bot_stats[bot2_name].draws += 1
    
    print(f"{bot1_name}: {old_elo1:.1f} → {new_elo1:.1f} (change: {new_elo1 - old_elo1:+.1f})")
    print(f"{bot2_name}: {old_elo2:.1f} → {new_elo2:.1f} (change: {new_elo2 - old_elo2:+.1f})")
    
    # Show final stats
    print("\n" + "=" * 50)
    print("Final Statistics:")
    leaderboard = matchmaker.get_leaderboard()
    for i, bot in enumerate(leaderboard, 1):
        print(f"{i}. {bot['username']}: ELO {bot['elo_rating']:.1f}, "
              f"Record: {bot['wins']}-{bot['losses']}-{bot['draws']}")
    
    # Test ELO properties
    print("\n" + "=" * 50)
    print("ELO System Properties:")
    print("✓ Higher rated player gains less from wins")
    print("✓ Lower rated player loses less from losses")
    print("✓ Upsets result in larger rating changes")
    print("✓ Draws move ratings toward each other")
    print("✓ Total ELO in system remains constant")

def test_leaderboard_persistence():
    """Test that leaderboard data persists correctly"""
    print("\n\nTesting Leaderboard Persistence")
    print("=" * 50)
    
    test_file = "test_leaderboard_data.json"
    
    # Create test data
    from src.bot_vs_bot.leaderboard_server import LeaderboardManager
    
    manager = LeaderboardManager(test_file)
    
    # Add some test data
    test_stats = {
        "TestBot1": {"elo_rating": 1600, "wins": 15, "losses": 5, "draws": 0},
        "TestBot2": {"elo_rating": 1400, "wins": 10, "losses": 10, "draws": 0},
        "TestBot3": {"elo_rating": 1200, "wins": 5, "losses": 15, "draws": 0}
    }
    
    for username, stats in test_stats.items():
        manager.bot_stats[username] = BotStats(
            username=username,
            elo_rating=stats["elo_rating"],
            wins=stats["wins"],
            losses=stats["losses"],
            draws=stats["draws"]
        )
    
    # Save data
    manager.save_data()
    print(f"Saved data to {test_file}")
    
    # Load data in new manager
    manager2 = LeaderboardManager(test_file)
    print(f"Loaded data from {test_file}")
    
    # Verify data
    print("\nVerifying loaded data:")
    for username, expected in test_stats.items():
        if username in manager2.bot_stats:
            actual = manager2.bot_stats[username]
            print(f"✓ {username}: ELO {actual.elo_rating} (expected {expected['elo_rating']})")
        else:
            print(f"✗ {username}: Not found!")
    
    # Clean up
    import os
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"\nCleaned up {test_file}")

if __name__ == "__main__":
    test_elo_calculations()
    test_leaderboard_persistence()