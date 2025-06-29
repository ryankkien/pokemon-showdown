"""
Bot Manager for coordinating multiple Pokemon Showdown bots in battles.
Handles spawning, managing, and orchestrating bot vs bot battles.
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import time

from bot import LLMPlayer
from poke_env.ps_client.server_configuration import ServerConfiguration

logger = logging.getLogger(__name__)


class BattleMode(Enum):
    """Battle modes for bot vs bot matches."""
    CHALLENGE = "challenge"  # One bot challenges another
    PRIVATE_ROOM = "private_room"  # Create private battle room
    LADDER = "ladder"  # Use ladder matchmaking


@dataclass
class BotConfig:
    """Configuration for a single bot instance."""
    username: str
    battle_format: str = "gen9randombattle"
    use_mock_llm: bool = False
    llm_provider: Optional[str] = None
    max_concurrent_battles: int = 1
    custom_config: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_config is None:
            self.custom_config = {}


@dataclass
class BattleResult:
    """Result of a bot vs bot battle."""
    battle_id: str
    bot1_username: str
    bot2_username: str
    winner: Optional[str]
    battle_format: str
    duration: float
    turns: int
    battle_log: Optional[str] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class BotManager:
    """
    Manages multiple bot instances and coordinates bot vs bot battles.
    """

    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        Initialize the bot manager.
        
        Args:
            server_url: Pokemon Showdown server URL
        """
        self.server_url = server_url
        self.server_config = ServerConfiguration(
            f'ws://{server_url.split("://")[1]}/showdown/websocket',
            server_url
        )
        
        self.active_bots: Dict[str, LLMPlayer] = {}
        self.battle_results: List[BattleResult] = []
        self.battle_queue: List[Tuple[str, str, str]] = []  # (bot1, bot2, format)
        
        logger.info(f"BotManager initialized with server: {server_url}")

    async def create_bot(self, config: BotConfig) -> LLMPlayer:
        """
        Create and initialize a new bot instance.
        
        Args:
            config: Bot configuration
            
        Returns:
            Initialized LLMPlayer instance
        """
        try:
            # Create bot with custom configuration
            # Filter out 'description' as it's not accepted by Player.__init__
            filtered_config = {k: v for k, v in config.custom_config.items() if k != 'description'}
            bot = LLMPlayer(
                username=config.username,
                battle_format=config.battle_format,
                max_concurrent_battles=config.max_concurrent_battles,
                use_mock_llm=config.use_mock_llm,
                server_configuration=self.server_config,
                **filtered_config
            )
            
            # Store bot reference
            self.active_bots[config.username] = bot
            
            # Give the bot time to establish websocket connection
            await asyncio.sleep(1.0)
            
            logger.info(f"Created bot: {config.username} (format: {config.battle_format})")
            return bot
            
        except Exception as e:
            logger.error(f"Failed to create bot {config.username}: {e}")
            raise

    async def start_bot_battle(self, bot1_username: str, bot2_username: str, 
                             battle_format: str, mode: BattleMode = BattleMode.CHALLENGE) -> str:
        """
        Start a battle between two bots.
        
        Args:
            bot1_username: First bot username
            bot2_username: Second bot username  
            battle_format: Battle format to use
            mode: Battle mode (challenge, private room, etc.)
            
        Returns:
            Battle ID
        """
        if bot1_username not in self.active_bots:
            raise ValueError(f"Bot {bot1_username} not found")
        if bot2_username not in self.active_bots:
            raise ValueError(f"Bot {bot2_username} not found")
        
        bot1 = self.active_bots[bot1_username]
        bot2 = self.active_bots[bot2_username]
        
        battle_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        try:
            if mode == BattleMode.CHALLENGE:
                # Bot1 challenges Bot2
                logger.info(f"Starting challenge battle: {bot1_username} vs {bot2_username}")
                
                # Add a small delay to ensure both bots are ready
                await asyncio.sleep(0.5)
                
                # Create challenge and accept tasks
                challenge_task = asyncio.create_task(
                    bot1.send_challenges(bot2_username, 1)
                )
                accept_task = asyncio.create_task(
                    bot2.accept_challenges(bot1_username, 1)
                )
                
                # Wait for both tasks to complete
                await asyncio.gather(challenge_task, accept_task)
                
            elif mode == BattleMode.LADDER:
                # Both bots play on ladder (may not guarantee they fight each other)
                logger.info(f"Starting ladder battles: {bot1_username} and {bot2_username}")
                
                ladder_task1 = asyncio.create_task(bot1.ladder(1))
                ladder_task2 = asyncio.create_task(bot2.ladder(1))
                
                await asyncio.gather(ladder_task1, ladder_task2)
                
            else:
                raise NotImplementedError(f"Battle mode {mode} not implemented yet")
            
            # Calculate battle duration
            duration = time.time() - start_time
            
            # Determine winner (simplified - would need actual battle result tracking)
            winner = self._determine_winner(bot1, bot2)
            
            # Store battle result
            result = BattleResult(
                battle_id=battle_id,
                bot1_username=bot1_username,
                bot2_username=bot2_username,
                winner=winner,
                battle_format=battle_format,
                duration=duration,
                turns=0  # Would need to track actual turns
            )
            self.battle_results.append(result)
            
            logger.info(f"Battle completed: {battle_id}, Winner: {winner}")
            return battle_id
            
        except Exception as e:
            logger.error(f"Battle failed: {e}")
            raise

    def _determine_winner(self, bot1: LLMPlayer, bot2: LLMPlayer) -> Optional[str]:
        """
        Determine battle winner from bot states.
        This is a simplified implementation - real implementation would 
        need to track battle outcomes properly.
        
        Args:
            bot1: First bot
            bot2: Second bot
            
        Returns:
            Winner username or None for draw
        """
        # This is a placeholder - actual implementation would need
        # to monitor battle events and track wins/losses
        # For now, return None (draw) as we can't easily determine winner
        return None

    async def run_tournament(self, bot_configs: List[BotConfig], 
                           battle_format: str = "gen9randombattle") -> List[BattleResult]:
        """
        Run a round-robin tournament between multiple bots.
        
        Args:
            bot_configs: List of bot configurations
            battle_format: Battle format to use
            
        Returns:
            List of battle results
        """
        if len(bot_configs) < 2:
            raise ValueError("Need at least 2 bots for tournament")
        
        logger.info(f"Starting tournament with {len(bot_configs)} bots")
        
        # Create all bots
        bots = []
        for config in bot_configs:
            bot = await self.create_bot(config)
            bots.append((config.username, bot))
        
        # Generate all possible pairings
        tournament_results = []
        for i in range(len(bots)):
            for j in range(i + 1, len(bots)):
                bot1_name, _ = bots[i]
                bot2_name, _ = bots[j]
                
                try:
                    battle_id = await self.start_bot_battle(
                        bot1_name, bot2_name, battle_format
                    )
                    
                    # Find the result for this battle
                    result = next(r for r in self.battle_results if r.battle_id == battle_id)
                    tournament_results.append(result)
                    
                    logger.info(f"Tournament match completed: {bot1_name} vs {bot2_name}")
                    
                except Exception as e:
                    logger.error(f"Tournament match failed: {bot1_name} vs {bot2_name}: {e}")
        
        logger.info(f"Tournament completed. {len(tournament_results)} battles finished.")
        return tournament_results

    async def shutdown(self):
        """Shutdown all active bots and cleanup resources."""
        logger.info("Shutting down bot manager...")
        
        for username, bot in self.active_bots.items():
            try:
                # Close bot connections
                await bot.stop_listening()
                logger.info(f"Shutdown bot: {username}")
            except Exception as e:
                logger.error(f"Error shutting down bot {username}: {e}")
        
        self.active_bots.clear()
        logger.info("Bot manager shutdown complete")

    def get_battle_stats(self) -> Dict[str, Any]:
        """
        Get battle statistics and results.
        
        Returns:
            Dictionary with battle statistics
        """
        if not self.battle_results:
            return {"total_battles": 0, "results": []}
        
        # Calculate basic stats
        total_battles = len(self.battle_results)
        avg_duration = sum(r.duration for r in self.battle_results) / total_battles
        
        # Count wins per bot
        wins_by_bot = {}
        for result in self.battle_results:
            if result.winner:
                wins_by_bot[result.winner] = wins_by_bot.get(result.winner, 0) + 1
        
        return {
            "total_battles": total_battles,
            "average_duration": avg_duration,
            "wins_by_bot": wins_by_bot,
            "results": [
                {
                    "battle_id": r.battle_id,
                    "bot1": r.bot1_username,
                    "bot2": r.bot2_username,
                    "winner": r.winner,
                    "duration": r.duration,
                    "format": r.battle_format
                }
                for r in self.battle_results
            ]
        }

    def save_results(self, filename: str):
        """Save battle results to JSON file."""
        stats = self.get_battle_stats()
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"Results saved to {filename}")


async def main():
    """Example usage of the bot manager."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create bot manager
    manager = BotManager()
    
    try:
        # Define bot configurations
        bot_configs = [
            BotConfig(
                username="GeminiBot",
                battle_format="gen9randombattle",
                use_mock_llm=True,  # Use mock for testing
                custom_config={"team": None}
            ),
            BotConfig(
                username="OpenAIBot", 
                battle_format="gen9randombattle",
                use_mock_llm=True,
                custom_config={"team": None}
            )
        ]
        
        # Run a simple battle
        logger.info("Creating bots...")
        for config in bot_configs:
            await manager.create_bot(config)
        
        logger.info("Starting bot vs bot battle...")
        battle_id = await manager.start_bot_battle(
            "GeminiBot", "OpenAIBot", "gen9randombattle"
        )
        
        # Print results
        stats = manager.get_battle_stats()
        print(f"\nBattle Results:")
        print(f"Total battles: {stats['total_battles']}")
        print(f"Average duration: {stats['average_duration']:.2f}s")
        
        for result in stats['results']:
            print(f"Battle {result['battle_id']}: {result['bot1']} vs {result['bot2']} -> Winner: {result['winner']}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())