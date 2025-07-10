"""
Demo script to populate leaderboard with sample data for testing.
"""

import json
import time
import random
from datetime import datetime, timedelta

from src.bot_vs_bot.leaderboard_server import LeaderboardManager, BotStats
from src.bot_vs_bot.bot_manager import BattleResult


def generate_sample_data():
    """Generate sample bot battle data for demonstration."""
    
    # Sample bot names
    bot_names = [
        "GeminiMaster", "ChatGPTBot", "ClaudeAI", "OllamaLocal",
        "RandomBot", "StrategyKing", "SpeedRunner", "TankMaster",
        "CriticalHit", "StatusQueen", "MegaEvolution", "GigantaMax"
    ]
    
    # Initialize leaderboard manager
    manager = LeaderboardManager("demo_leaderboard_data.json")
    
    # Create bot stats with varying skill levels
    elo_ranges = [
        (1000, 1200),  # Beginner bots
        (1200, 1400),  # Intermediate bots  
        (1400, 1600),  # Advanced bots
        (1600, 1800)   # Expert bots
    ]
    
    print("Creating sample bot data...")
    
    for i, bot_name in enumerate(bot_names):
        # Assign skill level
        skill_tier = i % len(elo_ranges)
        min_elo, max_elo = elo_ranges[skill_tier]
        
        # Generate random stats
        total_battles = random.randint(10, 100)
        win_rate = random.uniform(0.3, 0.8)
        
        # Calculate wins/losses based on skill tier
        if skill_tier >= 2:  # Advanced/Expert bots
            win_rate = random.uniform(0.6, 0.85)
        elif skill_tier == 1:  # Intermediate bots
            win_rate = random.uniform(0.45, 0.65)
        else:  # Beginner bots
            win_rate = random.uniform(0.25, 0.55)
        
        wins = int(total_battles * win_rate)
        losses = total_battles - wins - random.randint(0, min(3, total_battles // 10))
        draws = total_battles - wins - losses
        
        # Create bot stats
        bot_stats = BotStats(
            username=bot_name,
            elo_rating=random.uniform(min_elo, max_elo),
            wins=wins,
            losses=losses,
            draws=draws,
            total_battles=total_battles,
            win_rate=wins / total_battles if total_battles > 0 else 0,
            last_battle_time=time.time() - random.randint(0, 86400 * 7)  # Within last week
        )
        
        manager.bot_stats[bot_name] = bot_stats
        print(f"  Created {bot_name}: ELO {bot_stats.elo_rating:.0f}, "
              f"Win Rate {bot_stats.win_rate*100:.1f}% ({wins}-{losses}-{draws})")
    
    # Generate sample battle results
    print("\nGenerating sample battle history...")
    
    battle_formats = ["gen9randombattle", "gen8ou", "gen9ou", "gen9ubers", "gen9doubles"]
    
    for battle_id in range(1, 201):  # 200 sample battles
        # Pick two random bots
        bot1, bot2 = random.sample(bot_names, 2)
        
        # Determine winner based on ELO difference
        elo1 = manager.bot_stats[bot1].elo_rating
        elo2 = manager.bot_stats[bot2].elo_rating
        
        # Higher ELO has better chance to win
        elo_diff = elo1 - elo2
        win_probability = 1 / (1 + 10 ** (-elo_diff / 400))
        
        if random.random() < win_probability:
            winner = bot1
        elif random.random() < 0.05:  # 5% chance of draw
            winner = None
        else:
            winner = bot2
        
        # Generate battle result
        battle_result = BattleResult(
            battle_id=f"demo-{battle_id:03d}",
            bot1_username=bot1,
            bot2_username=bot2,
            winner=winner,
            battle_format=random.choice(battle_formats),
            duration=random.uniform(60, 600),  # 1-10 minutes
            turns=random.randint(10, 50),
            timestamp=time.time() - random.randint(0, 86400 * 30)  # Within last month
        )
        
        manager.battle_history.append(battle_result)
        
        if battle_id % 50 == 0:
            print(f"  Generated {battle_id} battles...")
    
    # Save the demo data
    manager.save_data()
    
    print(f"\n✅ Demo data saved to: {manager.data_file}")
    print(f"📊 Created {len(manager.bot_stats)} bots with {len(manager.battle_history)} battles")
    
    # Display sample leaderboard
    print("\n🏆 Sample Leaderboard (Top 10):")
    leaderboard = manager.get_leaderboard(limit=10)
    
    for entry in leaderboard:
        print(f"{entry.rank:2d}. {entry.username:15s} | "
              f"ELO: {entry.elo_rating:4.0f} | "
              f"W-L-D: {entry.wins:2d}-{entry.losses:2d}-{entry.draws:2d} | "
              f"Win Rate: {entry.win_rate:5.1f}% | "
              f"Recent: {entry.recent_form}")
    
    # Display battle stats
    print("\n📈 Battle Statistics:")
    stats = manager.get_battle_stats()
    print(f"  Total Battles: {stats['total_battles']}")
    print(f"  Average Duration: {stats['avg_duration']:.1f}s")
    print(f"  Average Turns: {stats['avg_turns']:.1f}")
    print(f"  Active Bots: {stats['active_bots']}")
    print(f"  Battles Today: {stats['battles_today']}")
    
    print(f"\n🌐 To view the leaderboard, run:")
    print(f"python leaderboard_server.py --data-file demo_leaderboard_data.json")
    print(f"Then open: http://localhost:5000")


def main():
    """Main entry point."""
    generate_sample_data()

if __name__ == "__main__":
    main()