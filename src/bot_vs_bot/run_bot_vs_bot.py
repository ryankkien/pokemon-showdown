#!/usr/bin/env python3
"""
Main runner for Pokemon Showdown bot vs bot battles.
Supports single battles, tournaments, and continuous matchmaking.
"""

import asyncio
import json
import logging
import signal
import sys
import time
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from src.bot_vs_bot.bot_vs_bot_config import BotVsBotConfigManager, TournamentType, create_quick_battle_config, create_tournament_config
from src.bot_vs_bot.bot_manager import BotManager
from src.bot_vs_bot.bot_matchmaker import BotMatchmaker, MatchRequest
from src.bot_vs_bot.leaderboard_server import LeaderboardManager

if TYPE_CHECKING:
    from src.bot_vs_bot.web_battle_server import WebBattleServer


# Global variables for graceful shutdown
running = True
manager = None
matchmaker = None
stop_event = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running, stop_event
    print(f"\nReceived signal {signum}. Shutting down gracefully...")
    running = False
    if stop_event:
        stop_event.set()


async def run_single_battle(config_manager: BotVsBotConfigManager):
    """Run a single battle between two bots."""
    if len(config_manager.config.bot_configs) < 2:
        print("Error: Need at least 2 bot configurations for a battle")
        return
    
    print("Starting single bot vs bot battle...")
    
    # Create components
    bot_manager = BotManager(config_manager.config.server_url)
    
    try:
        # Create first two bots
        bot1_config = config_manager.config.bot_configs[0]
        bot2_config = config_manager.config.bot_configs[1]
        
        print(f"Creating bots: {bot1_config.username} vs {bot2_config.username}")
        
        await bot_manager.create_bot(bot1_config)
        await bot_manager.create_bot(bot2_config)
        
        # Start battle
        battle_id = await bot_manager.start_bot_battle(
            bot1_config.username,
            bot2_config.username,
            config_manager.config.default_battle_format
        )
        
        print(f"Battle started with ID: {battle_id}")
        
        # Wait for battle completion (simplified)
        await asyncio.sleep(60)  # Wait 1 minute
        
        # Get results
        stats = bot_manager.get_battle_stats()
        print("\nBattle Results:")
        for result in stats['results']:
            print(f"  {result['bot1']} vs {result['bot2']} -> Winner: {result['winner']}")
            print(f"  Duration: {result['duration']:.1f}s")
        
        if config_manager.config.auto_save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config_manager.config.results_dir}/single_battle_{timestamp}.json"
            bot_manager.save_results(filename)
            print(f"Results saved to: {filename}")
    
    except Exception as e:
        print(f"Error in single battle: {e}")
        raise
    finally:
        await bot_manager.shutdown()


async def run_tournament(config_manager: BotVsBotConfigManager):
    """Run a tournament with the configured bots."""
    tournament_config = config_manager.config.tournament_config
    if not tournament_config:
        print("Error: No tournament configuration found")
        return
    
    if len(config_manager.config.bot_configs) < 2:
        print("Error: Need at least 2 bot configurations for tournament")
        return
    
    print(f"Starting tournament: {tournament_config.name}")
    print(f"Type: {tournament_config.tournament_type.value}")
    print(f"Participants: {[bot.username for bot in config_manager.config.bot_configs]}")
    
    # Create components
    bot_manager = BotManager(config_manager.config.server_url)
    
    try:
        if tournament_config.tournament_type == TournamentType.ROUND_ROBIN:
            # Run round-robin tournament
            results = await bot_manager.run_tournament(
                config_manager.config.bot_configs,
                tournament_config.battle_format
            )
            
            print(f"\nTournament completed! {len(results)} battles finished.")
            
            # Display results
            for result in results:
                print(f"{result.bot1_username} vs {result.bot2_username} -> Winner: {result.winner}")
            
            # Save results
            if config_manager.config.auto_save_results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{config_manager.config.results_dir}/tournament_{timestamp}.json"
                bot_manager.save_results(filename)
                print(f"Tournament results saved to: {filename}")
        
        else:
            print(f"Tournament type {tournament_config.tournament_type.value} not implemented yet")
    
    except Exception as e:
        print(f"Error in tournament: {e}")
        raise
    finally:
        await bot_manager.shutdown()


async def _send_update_to_web_server(matchmaker, port: int = 5001, max_retries: int = 2):
    """Send battle results to the web leaderboard server with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            import aiohttp
            from dataclasses import asdict
            
            # Prepare data to send
            bot_stats = {
                username: asdict(stats) for username, stats in matchmaker.bot_stats.items()
            }
            battle_results = [
                asdict(result) for result in matchmaker.bot_manager.battle_results
            ]
            
            data = {
                "bot_stats": bot_stats,
                "battle_results": battle_results,
                "timestamp": datetime.now().isoformat(),
                "total_battles": len(battle_results)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/api/update",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        print(f"✓ Real-time update sent to web leaderboard (Battle #{len(battle_results)})")
                        return True
                    else:
                        print(f"⚠ Web leaderboard server responded with status {response.status}")
                        if attempt < max_retries:
                            await asyncio.sleep(0.5)  # Brief retry delay
                            continue
                        return False
                        
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(0.5)  # Brief retry delay
                continue
            else:
                # Only print error on final attempt to avoid spam
                print(f"Note: Could not update web leaderboard server: {str(e)[:50]}...")
                return False
    
    return False


async def run_continuous_matchmaking(config_manager: BotVsBotConfigManager, duration_minutes: Optional[int] = None, leaderboard_port: int = 5001, web_server_instance: Optional['WebBattleServer'] = None):
    """Run continuous matchmaking system."""
    global running, manager, matchmaker, stop_event
    
    print("Starting continuous matchmaking system...")
    print(f"Bots: {[bot.username for bot in config_manager.config.bot_configs]}")
    print(f"Strategy: {config_manager.config.matchmaking_strategy.value}")
    if duration_minutes:
        print(f"Duration: {duration_minutes} minutes")
    
    # Calculate end time if duration specified
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60) if duration_minutes else None
    
    # Create components
    manager = BotManager(config_manager.config.server_url)
    matchmaker = BotMatchmaker(manager, config_manager.config.matchmaking_strategy)
    leaderboard = LeaderboardManager()
    
    # Load existing stats into matchmaker (only if they have actual battles)
    print("Loading existing leaderboard data...")
    loaded_count = 0
    for username, stats in leaderboard.bot_stats.items():
        if stats.total_battles > 0:  # Only load stats with actual battles
            matchmaker.bot_stats[username] = stats
            loaded_count += 1
    if loaded_count > 0:
        print(f"  Loaded stats for {loaded_count} bots with battle history")
    else:
        print("  No existing battle stats found - starting fresh")
    
    try:
        # Create all bots
        print("Creating bots...")
        for bot_config in config_manager.config.bot_configs:
            await manager.create_bot(bot_config)
            matchmaker.register_bot(bot_config.username)
            print(f"  Created: {bot_config.username}")
        
        # Connect web server to continuous matchmaking components
        if web_server_instance:
            web_server_instance.set_external_components(manager, matchmaker)
            print("Web server connected to continuous matchmaking")
        
        # Add initial match requests
        print("Adding initial match requests...")
        for bot_config in config_manager.config.bot_configs:
            request = MatchRequest(
                bot_username=bot_config.username,
                battle_format=config_manager.config.default_battle_format,
                max_wait_time=300.0
            )
            matchmaker.add_match_request(request)
        
        # Create stop event for coordinated shutdown
        stop_event = asyncio.Event()
        
        # Start continuous matchmaking
        print("Starting continuous matchmaking loop...")
        matchmaking_task = asyncio.create_task(
            matchmaker.run_continuous_matchmaking(interval=15.0, stop_event=stop_event)
        )
        
        # Monitor and add periodic match requests
        battle_count = 0
        last_stats_print = 0
        processed_battles = set()  # Track which battles we've already processed
        
        while running:
            # Check if duration has elapsed
            if end_time and time.time() >= end_time:
                print(f"\nDuration of {duration_minutes} minutes elapsed. Shutting down...")
                running = False
                stop_event.set()  # Signal matchmaker to stop
                break
                
            await asyncio.sleep(5)  # Check every 5 seconds for better responsiveness
            
            # Check for newly completed battles and update matchmaker
            for battle_result in manager.battle_results:
                if battle_result.battle_id not in processed_battles:
                    # This is a newly completed battle
                    matchmaker.update_battle_result(battle_result)
                    processed_battles.add(battle_result.battle_id)
                    print(f"Battle completed: {battle_result.bot1_username} vs {battle_result.bot2_username} - Winner: {battle_result.winner}")
                    
                    # Update leaderboard immediately after each battle
                    leaderboard.update_from_matchmaker(matchmaker)
                    print(f"Leaderboard updated - Total battles recorded: {len(leaderboard.battle_history)}")
                    
                    # Send data to web leaderboard server if it's running
                    await _send_update_to_web_server(matchmaker, leaderboard_port)
            
            # Print stats periodically
            current_time = asyncio.get_event_loop().time()
            if current_time - last_stats_print > 120:  # Every 2 minutes
                # Update leaderboard with latest data
                leaderboard.update_from_matchmaker(matchmaker)
                
                leaderboard_data = matchmaker.get_leaderboard()
                print(f"\n=== Leaderboard (after {len(manager.battle_results)} battles) ===")
                for i, bot in enumerate(leaderboard_data[:5], 1):  # Top 5
                    print(f"{i}. {bot['username']}: ELO {bot['elo_rating']}, "
                          f"Win Rate {bot['win_rate']}% ({bot['wins']}-{bot['losses']}-{bot['draws']})")
                
                last_stats_print = current_time
            
            # Add more match requests periodically
            if len(matchmaker.match_queue) < 2:
                for bot_config in config_manager.config.bot_configs:
                    if bot_config.username in manager.active_bots:
                        request = MatchRequest(
                            bot_username=bot_config.username,
                            battle_format=config_manager.config.default_battle_format
                        )
                        matchmaker.add_match_request(request)
        
        # Stop matchmaking gracefully
        stop_event.set()
        
        # Wait for matchmaking task to finish, with timeout
        try:
            await asyncio.wait_for(matchmaking_task, timeout=10.0)
            print("Matchmaking stopped gracefully")
        except asyncio.TimeoutError:
            print("Matchmaking task timeout, force cancelling...")
            matchmaking_task.cancel()
            try:
                await matchmaking_task
            except asyncio.CancelledError:
                pass
        
        # Final stats
        print("\n=== Final Results ===")
        # Update leaderboard with final data
        leaderboard.update_from_matchmaker(matchmaker)
        
        leaderboard_data = matchmaker.get_leaderboard()
        for i, bot in enumerate(leaderboard_data, 1):
            print(f"{i}. {bot['username']}: ELO {bot['elo_rating']}, "
                  f"Win Rate {bot['win_rate']}% ({bot['wins']}-{bot['losses']}-{bot['draws']})")
        
        # Save results
        if config_manager.config.auto_save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save battle results
            battle_filename = f"{config_manager.config.results_dir}/battles_{timestamp}.json"
            manager.save_results(battle_filename)
            
            # Save matchmaking stats
            stats_filename = f"{config_manager.config.results_dir}/matchmaking_{timestamp}.json"
            matchmaker.save_stats(stats_filename)
            
            # Save leaderboard data
            leaderboard_filename = f"{config_manager.config.results_dir}/leaderboard_{timestamp}.json"
            leaderboard.data_file = leaderboard_filename
            leaderboard.save_data()
            
            print(f"Results saved to: {battle_filename}, {stats_filename}, and {leaderboard_filename}")
    
    except Exception as e:
        print(f"Error in continuous matchmaking: {e}")
        # Make sure to stop matchmaking on error
        if 'stop_event' in locals():
            stop_event.set()
        raise
    finally:
        # Ensure matchmaking is stopped in all cases
        if 'stop_event' in locals():
            stop_event.set()
        if manager:
            await manager.shutdown()


async def main():
    """Main function with command line interface."""
    global running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Run Pokemon Showdown bot vs bot battles")
    parser.add_argument("--mode", choices=["single", "tournament", "continuous", "web"], 
                       default="single", help="Battle mode to run")
    parser.add_argument("--config", default="bot_vs_bot_config.json", 
                       help="Configuration file path")
    parser.add_argument("--setup", action="store_true", 
                       help="Setup default configuration and exit")
    parser.add_argument("--quick", action="store_true",
                       help="Use quick battle configuration")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--leaderboard", action="store_true", default=True,
                       help="Start web leaderboard server alongside battles (default: enabled)")
    parser.add_argument("--no-leaderboard", dest="leaderboard", action="store_false",
                       help="Disable web leaderboard server")
    parser.add_argument("--leaderboard-port", type=int, default=5000,
                       help="Port for leaderboard server")
    parser.add_argument("--duration", type=int, default=None,
                       help="Duration to run continuous battles (in minutes)")
    parser.add_argument("--models", nargs='+', default=None,
                       help="Filter models to use (e.g., --models gemini openai anthropic)")
    parser.add_argument("--exclude-models", nargs='+', default=None,
                       help="Exclude specific models (e.g., --exclude-models gpt-3.5-turbo)")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handle setup mode
    if args.setup:
        print("Setting up default configuration...")
        config_manager = BotVsBotConfigManager(args.config)
        config_manager.config.bot_configs = config_manager.get_default_bot_configs()
        config_manager.setup_default_tournament()
        config_manager.save_config()
        
        summary = config_manager.get_config_summary()
        print(f"Configuration saved to: {args.config}")
        print(f"Bots configured: {summary['num_bots']}")
        print(f"Tournament: {summary['tournament_name']}")
        return
    
    # Load configuration
    if args.quick:
        print("Using quick battle configuration...")
        config_manager = BotVsBotConfigManager()
        config_manager.config = create_quick_battle_config()
    else:
        print(f"Loading configuration from: {args.config}")
        config_manager = BotVsBotConfigManager(args.config)
    
    # Filter models based on command line arguments
    if args.models or args.exclude_models:
        original_count = len(config_manager.config.bot_configs)
        filtered_configs = []
        
        for bot_config in config_manager.config.bot_configs:
            # Include filtering
            if args.models:
                include = False
                for model_filter in args.models:
                    if (model_filter.lower() in bot_config.llm_provider.lower() or
                        model_filter.lower() in bot_config.username.lower()):
                        include = True
                        break
                if not include:
                    continue
            
            # Exclude filtering
            if args.exclude_models:
                exclude = False
                for exclude_filter in args.exclude_models:
                    if (exclude_filter.lower() in bot_config.username.lower() or
                        exclude_filter.lower() in bot_config.llm_provider.lower()):
                        exclude = True
                        break
                if exclude:
                    continue
            
            filtered_configs.append(bot_config)
        
        config_manager.config.bot_configs = filtered_configs
        print(f"Filtered bots: {original_count} -> {len(filtered_configs)} models")
        
        if len(filtered_configs) == 0:
            print("Error: No bots remain after filtering")
            return
        elif len(filtered_configs) == 1:
            print("Warning: Only one bot remains after filtering")
            if args.mode == "single":
                print("Cannot run single battle with only one bot")
                return
    
    # Validate configuration
    issues = config_manager.validate_config()
    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        print("Please fix configuration or run with --setup to create default config")
        return
    
    # Print configuration summary
    summary = config_manager.get_config_summary()
    print("\n=== Configuration Summary ===")
    print(f"Server: {summary['server_url']}")
    print(f"Battle Format: {summary['battle_format']}")
    print(f"Bots: {summary['num_bots']} ({', '.join(summary['bot_usernames'])})")
    print(f"Matchmaking: {summary['matchmaking_strategy']}")
    if summary['tournament_configured']:
        print(f"Tournament: {summary['tournament_name']} ({summary['tournament_type']})")
    print()
    
    try:
        # Start leaderboard/web server in background if enabled
        leaderboard_thread = None
        web_server_instance = None
        if args.leaderboard:
            import threading
            from src.bot_vs_bot.web_battle_server import run_web_server, WebBattleServer
            
            print(f"Starting web battle server on port {args.leaderboard_port}...")
            
            # Create web server instance that will integrate with continuous matchmaking
            config_manager_for_web = BotVsBotConfigManager(args.config)
            web_server_instance = WebBattleServer(
                config_manager_for_web, 
                args.leaderboard_port,
                use_external_matchmaker=True
            )
            
            leaderboard_thread = threading.Thread(
                target=web_server_instance.run,
                daemon=True
            )
            leaderboard_thread.start()
            print(f"🌐 Web interface available at: http://localhost:{args.leaderboard_port}")
            print(f"🔌 Battle relay server on port {args.leaderboard_port + 1}")
        
        # Run selected mode
        if args.mode == "single":
            await run_single_battle(config_manager)
        elif args.mode == "tournament":
            await run_tournament(config_manager)
        elif args.mode == "continuous":
            await run_continuous_matchmaking(config_manager, args.duration, args.leaderboard_port, web_server_instance)
        elif args.mode == "web":
            # Web mode - just keep the process alive for the web server
            print("Running in web-only mode. Use the web interface to start battles.")
            # Keep the main thread alive
            while True:
                await asyncio.sleep(60)
    
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    print("Bot vs bot system finished")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))