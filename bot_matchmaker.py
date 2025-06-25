"""
Bot Matchmaking System for Pokemon Showdown bot vs bot battles.
Handles intelligent pairing, queue management, and battle scheduling.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import heapq
import json

from bot_manager import BotManager, BotConfig, BattleResult, BattleMode

logger = logging.getLogger(__name__)


class MatchmakingStrategy(Enum):
    """Different strategies for bot matchmaking."""
    ROUND_ROBIN = "round_robin"  # Every bot plays every other bot
    SWISS_SYSTEM = "swiss_system"  # Pair bots with similar records
    RANDOM_PAIRING = "random_pairing"  # Random matchups
    ELO_BASED = "elo_based"  # Match bots with similar ELO ratings
    CUSTOM = "custom"  # Custom pairing logic


@dataclass
class BotStats:
    """Statistics for a bot in the matchmaking system."""
    username: str
    elo_rating: float = 1200.0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_battles: int = 0
    win_rate: float = 0.0
    last_battle_time: float = 0.0
    
    def update_stats(self, result: BattleResult, is_winner: bool, is_draw: bool = False):
        """Update bot statistics based on battle result."""
        self.total_battles += 1
        self.last_battle_time = result.timestamp
        
        if is_draw:
            self.draws += 1
        elif is_winner:
            self.wins += 1
        else:
            self.losses += 1
        
        # Calculate win rate
        if self.total_battles > 0:
            self.win_rate = self.wins / self.total_battles
    
    def update_elo(self, opponent_elo: float, result: float, k_factor: int = 32):
        """
        Update ELO rating based on battle result.
        
        Args:
            opponent_elo: Opponent's ELO rating
            result: Battle result (1.0 = win, 0.5 = draw, 0.0 = loss)
            k_factor: ELO K-factor for rating adjustment
        """
        expected_score = 1 / (1 + 10 ** ((opponent_elo - self.elo_rating) / 400))
        self.elo_rating += k_factor * (result - expected_score)


@dataclass
class MatchRequest:
    """A request for a battle match."""
    bot_username: str
    battle_format: str
    preferred_opponents: List[str] = None
    excluded_opponents: List[str] = None
    max_wait_time: float = 300.0  # 5 minutes
    created_time: float = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = time.time()
        if self.preferred_opponents is None:
            self.preferred_opponents = []
        if self.excluded_opponents is None:
            self.excluded_opponents = []


@dataclass
class MatchPairing:
    """A matched pair of bots ready for battle."""
    bot1_username: str
    bot2_username: str
    battle_format: str
    priority: int = 0
    created_time: float = None
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = time.time()
    
    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority > other.priority  # Higher priority = lower value in heap


class BotMatchmaker:
    """
    Advanced matchmaking system for bot vs bot battles.
    """
    
    def __init__(self, bot_manager: BotManager, strategy: MatchmakingStrategy = MatchmakingStrategy.ELO_BASED):
        """
        Initialize the matchmaker.
        
        Args:
            bot_manager: BotManager instance
            strategy: Matchmaking strategy to use
        """
        self.bot_manager = bot_manager
        self.strategy = strategy
        
        # Matchmaking state
        self.bot_stats: Dict[str, BotStats] = {}
        self.match_queue: List[MatchRequest] = []
        self.active_matches: Dict[str, MatchPairing] = {}  # battle_id -> pairing
        self.match_history: List[Tuple[str, str]] = []  # (bot1, bot2) pairs
        
        # Priority queue for match pairings
        self.pairing_queue: List[MatchPairing] = []
        
        # Matchmaking parameters
        self.elo_threshold = 200  # Max ELO difference for pairing
        self.min_wait_time = 30  # Minimum wait before pairing
        self.max_queue_size = 100
        
        logger.info(f"BotMatchmaker initialized with strategy: {strategy}")
    
    def register_bot(self, username: str, initial_elo: float = 1200.0):
        """Register a bot with the matchmaking system."""
        if username not in self.bot_stats:
            self.bot_stats[username] = BotStats(username, elo_rating=initial_elo)
            logger.info(f"Registered bot: {username} (ELO: {initial_elo})")
    
    def add_match_request(self, request: MatchRequest) -> bool:
        """
        Add a match request to the queue.
        
        Args:
            request: Match request
            
        Returns:
            True if request was added successfully
        """
        if len(self.match_queue) >= self.max_queue_size:
            logger.warning("Match queue is full")
            return False
        
        # Ensure bot is registered
        self.register_bot(request.bot_username)
        
        self.match_queue.append(request)
        logger.info(f"Added match request for {request.bot_username} in {request.battle_format}")
        
        # Try to find matches immediately
        asyncio.create_task(self._process_match_queue())
        return True
    
    async def _process_match_queue(self):
        """Process the match queue and create pairings."""
        current_time = time.time()
        new_pairings = []
        
        # Remove expired requests
        self.match_queue = [
            req for req in self.match_queue 
            if current_time - req.created_time < req.max_wait_time
        ]
        
        # Group requests by format
        format_groups = {}
        for request in self.match_queue:
            if request.battle_format not in format_groups:
                format_groups[request.battle_format] = []
            format_groups[request.battle_format].append(request)
        
        # Create pairings for each format
        for battle_format, requests in format_groups.items():
            if len(requests) < 2:
                continue
            
            pairings = await self._create_pairings(requests, battle_format)
            new_pairings.extend(pairings)
        
        # Add new pairings to queue
        for pairing in new_pairings:
            heapq.heappush(self.pairing_queue, pairing)
            logger.info(f"Created pairing: {pairing.bot1_username} vs {pairing.bot2_username}")
        
        # Remove matched requests from queue
        matched_bots = {pairing.bot1_username for pairing in new_pairings}
        matched_bots.update(pairing.bot2_username for pairing in new_pairings)
        self.match_queue = [req for req in self.match_queue if req.bot_username not in matched_bots]

    async def _create_pairings(self, requests: List[MatchRequest], battle_format: str) -> List[MatchPairing]:
        """
        Create bot pairings based on the matchmaking strategy.
        
        Args:
            requests: List of match requests for the same format
            battle_format: Battle format
            
        Returns:
            List of match pairings
        """
        if self.strategy == MatchmakingStrategy.ELO_BASED:
            return self._create_elo_pairings(requests, battle_format)
        elif self.strategy == MatchmakingStrategy.RANDOM_PAIRING:
            return self._create_random_pairings(requests, battle_format)
        elif self.strategy == MatchmakingStrategy.SWISS_SYSTEM:
            return self._create_swiss_pairings(requests, battle_format)
        else:
            # Default to ELO-based
            return self._create_elo_pairings(requests, battle_format)
    
    def _create_elo_pairings(self, requests: List[MatchRequest], battle_format: str) -> List[MatchPairing]:
        """Create pairings based on ELO ratings."""
        pairings = []
        available_requests = requests.copy()
        
        # Sort by ELO rating
        available_requests.sort(key=lambda r: self.bot_stats[r.bot_username].elo_rating)
        
        while len(available_requests) >= 2:
            request1 = available_requests.pop(0)
            bot1_elo = self.bot_stats[request1.bot_username].elo_rating
            
            # Find best match within ELO threshold
            best_match_idx = None
            best_elo_diff = float('inf')
            
            for i, request2 in enumerate(available_requests):
                bot2_elo = self.bot_stats[request2.bot_username].elo_rating
                elo_diff = abs(bot1_elo - bot2_elo)
                
                # Check constraints
                if elo_diff <= self.elo_threshold and elo_diff < best_elo_diff:
                    if self._can_pair_bots(request1, request2):
                        best_match_idx = i
                        best_elo_diff = elo_diff
            
            if best_match_idx is not None:
                request2 = available_requests.pop(best_match_idx)
                
                # Calculate priority (lower ELO difference = higher priority)
                priority = int(1000 - best_elo_diff)
                
                pairing = MatchPairing(
                    bot1_username=request1.bot_username,
                    bot2_username=request2.bot_username,
                    battle_format=battle_format,
                    priority=priority
                )
                pairings.append(pairing)
        
        return pairings
    
    def _create_random_pairings(self, requests: List[MatchRequest], battle_format: str) -> List[MatchPairing]:
        """Create random pairings."""
        import random
        pairings = []
        available_requests = requests.copy()
        random.shuffle(available_requests)
        
        while len(available_requests) >= 2:
            request1 = available_requests.pop()
            request2 = available_requests.pop()
            
            if self._can_pair_bots(request1, request2):
                pairing = MatchPairing(
                    bot1_username=request1.bot_username,
                    bot2_username=request2.bot_username,
                    battle_format=battle_format,
                    priority=100  # Default priority
                )
                pairings.append(pairing)
        
        return pairings
    
    def _create_swiss_pairings(self, requests: List[MatchRequest], battle_format: str) -> List[MatchPairing]:
        """Create pairings using Swiss system (pair bots with similar records)."""
        pairings = []
        available_requests = requests.copy()
        
        # Sort by win rate and total battles
        available_requests.sort(
            key=lambda r: (self.bot_stats[r.bot_username].win_rate, 
                          self.bot_stats[r.bot_username].total_battles),
            reverse=True
        )
        
        while len(available_requests) >= 2:
            request1 = available_requests.pop(0)
            
            # Find opponent with similar record who hasn't played against this bot recently
            best_match_idx = None
            for i, request2 in enumerate(available_requests):
                if self._can_pair_bots(request1, request2):
                    if not self._have_played_recently(request1.bot_username, request2.bot_username):
                        best_match_idx = i
                        break
            
            if best_match_idx is not None:
                request2 = available_requests.pop(best_match_idx)
                
                pairing = MatchPairing(
                    bot1_username=request1.bot_username,
                    bot2_username=request2.bot_username,
                    battle_format=battle_format,
                    priority=200  # Higher priority for Swiss pairings
                )
                pairings.append(pairing)
        
        return pairings
    
    def _can_pair_bots(self, request1: MatchRequest, request2: MatchRequest) -> bool:
        """Check if two bots can be paired together."""
        # Check exclusion lists
        if request2.bot_username in request1.excluded_opponents:
            return False
        if request1.bot_username in request2.excluded_opponents:
            return False
        
        # Check if bots are the same
        if request1.bot_username == request2.bot_username:
            return False
        
        # Check if both bots are currently active
        if request1.bot_username not in self.bot_manager.active_bots:
            return False
        if request2.bot_username not in self.bot_manager.active_bots:
            return False
        
        return True
    
    def _have_played_recently(self, bot1: str, bot2: str, recent_threshold: int = 5) -> bool:
        """Check if two bots have played against each other recently."""
        recent_matches = self.match_history[-recent_threshold:]
        pair1 = (bot1, bot2)
        pair2 = (bot2, bot1)
        
        return pair1 in recent_matches or pair2 in recent_matches
    
    async def start_next_battle(self) -> Optional[str]:
        """
        Start the next battle from the pairing queue.
        
        Returns:
            Battle ID if battle started, None if no battles available
        """
        if not self.pairing_queue:
            return None
        
        pairing = heapq.heappop(self.pairing_queue)
        
        try:
            # Start the battle
            battle_id = await self.bot_manager.start_bot_battle(
                pairing.bot1_username,
                pairing.bot2_username,
                pairing.battle_format,
                BattleMode.CHALLENGE
            )
            
            # Track active match
            self.active_matches[battle_id] = pairing
            
            # Add to match history
            self.match_history.append((pairing.bot1_username, pairing.bot2_username))
            
            logger.info(f"Started battle {battle_id}: {pairing.bot1_username} vs {pairing.bot2_username}")
            return battle_id
            
        except Exception as e:
            logger.error(f"Failed to start battle: {pairing.bot1_username} vs {pairing.bot2_username}: {e}")
            return None
    
    def update_battle_result(self, battle_result: BattleResult):
        """Update bot statistics based on battle result."""
        bot1_stats = self.bot_stats.get(battle_result.bot1_username)
        bot2_stats = self.bot_stats.get(battle_result.bot2_username)
        
        if not bot1_stats or not bot2_stats:
            logger.warning(f"Bot stats not found for battle {battle_result.battle_id}")
            return
        
        # Determine results
        is_draw = battle_result.winner is None
        bot1_wins = battle_result.winner == battle_result.bot1_username
        bot2_wins = battle_result.winner == battle_result.bot2_username
        
        # Update basic stats
        bot1_stats.update_stats(battle_result, bot1_wins, is_draw)
        bot2_stats.update_stats(battle_result, bot2_wins, is_draw)
        
        # Update ELO ratings
        if is_draw:
            bot1_stats.update_elo(bot2_stats.elo_rating, 0.5)
            bot2_stats.update_elo(bot1_stats.elo_rating, 0.5)
        elif bot1_wins:
            bot1_stats.update_elo(bot2_stats.elo_rating, 1.0)
            bot2_stats.update_elo(bot1_stats.elo_rating, 0.0)
        elif bot2_wins:
            bot1_stats.update_elo(bot2_stats.elo_rating, 0.0)
            bot2_stats.update_elo(bot1_stats.elo_rating, 1.0)
        
        # Clean up active match
        if battle_result.battle_id in self.active_matches:
            del self.active_matches[battle_result.battle_id]
        
        logger.info(f"Updated stats for battle {battle_result.battle_id}")
    
    def get_leaderboard(self, sort_by: str = "elo") -> List[Dict]:
        """
        Get bot leaderboard sorted by specified metric.
        
        Args:
            sort_by: Metric to sort by (elo, win_rate, wins, total_battles)
            
        Returns:
            List of bot stats dictionaries
        """
        bots = list(self.bot_stats.values())
        
        if sort_by == "elo":
            bots.sort(key=lambda b: b.elo_rating, reverse=True)
        elif sort_by == "win_rate":
            bots.sort(key=lambda b: b.win_rate, reverse=True)
        elif sort_by == "wins":
            bots.sort(key=lambda b: b.wins, reverse=True)
        elif sort_by == "total_battles":
            bots.sort(key=lambda b: b.total_battles, reverse=True)
        
        return [
            {
                "username": bot.username,
                "elo_rating": round(bot.elo_rating, 1),
                "wins": bot.wins,
                "losses": bot.losses,
                "draws": bot.draws,
                "win_rate": round(bot.win_rate * 100, 1),
                "total_battles": bot.total_battles
            }
            for bot in bots
        ]
    
    async def run_continuous_matchmaking(self, interval: float = 10.0):
        """
        Run continuous matchmaking loop.
        
        Args:
            interval: Seconds between matchmaking cycles
        """
        logger.info("Starting continuous matchmaking...")
        
        while True:
            try:
                # Process match queue
                await self._process_match_queue()
                
                # Start battles from pairing queue
                battles_started = 0
                while battles_started < 3:  # Limit concurrent battles
                    battle_id = await self.start_next_battle()
                    if battle_id:
                        battles_started += 1
                    else:
                        break
                
                # Wait before next cycle
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in matchmaking loop: {e}")
                await asyncio.sleep(interval)
    
    def save_stats(self, filename: str):
        """Save matchmaking statistics to file."""
        stats_data = {
            "bot_stats": {
                username: {
                    "elo_rating": stats.elo_rating,
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "draws": stats.draws,
                    "total_battles": stats.total_battles,
                    "win_rate": stats.win_rate
                }
                for username, stats in self.bot_stats.items()
            },
            "leaderboard": self.get_leaderboard(),
            "total_matches": len(self.match_history),
            "active_matches": len(self.active_matches),
            "queue_size": len(self.match_queue),
            "pairing_queue_size": len(self.pairing_queue)
        }
        
        with open(filename, 'w') as f:
            json.dump(stats_data, f, indent=2)
        
        logger.info(f"Matchmaking stats saved to {filename}")


async def main():
    """Example usage of the matchmaking system."""
    logging.basicConfig(level=logging.INFO)
    
    # Create components
    bot_manager = BotManager()
    matchmaker = BotMatchmaker(bot_manager, MatchmakingStrategy.ELO_BASED)
    
    # Create some bots
    bot_configs = [
        BotConfig(username=f"TestBot{i}", use_mock_llm=True)
        for i in range(4)
    ]
    
    for config in bot_configs:
        await bot_manager.create_bot(config)
        matchmaker.register_bot(config.username)
    
    # Add match requests
    for config in bot_configs:
        request = MatchRequest(
            bot_username=config.username,
            battle_format="gen9randombattle"
        )
        matchmaker.add_match_request(request)
    
    # Run a few matchmaking cycles
    for _ in range(3):
        await asyncio.sleep(2)
        battle_id = await matchmaker.start_next_battle()
        if battle_id:
            print(f"Started battle: {battle_id}")
    
    # Print leaderboard
    leaderboard = matchmaker.get_leaderboard()
    print("\nLeaderboard:")
    for i, bot in enumerate(leaderboard, 1):
        print(f"{i}. {bot['username']}: ELO {bot['elo_rating']}, "
              f"Win Rate {bot['win_rate']}% ({bot['wins']}-{bot['losses']}-{bot['draws']})")
    
    await bot_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(main())