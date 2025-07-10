"""
Battle Tracker for analyzing LLM decision-making in Pokemon battles.
Tracks moves, decisions, and battle outcomes for performance analysis.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import os

logger = logging.getLogger(__name__)

@dataclass
class BattleMove:
    """Represents a single move decision in a battle."""
    turn: int
    bot_name: str
    battle_id: str
    timestamp: str
    llm_reasoning: str
    parsed_action: str
    action_value: str
    execution_result: str
    battle_state_summary: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class BattleAnalysis:
    """Analysis of a complete battle."""
    battle_id: str
    bot1_name: str
    bot2_name: str
    winner: Optional[str]
    total_turns: int
    duration_seconds: float
    moves: List[BattleMove]
    bot1_moves: int
    bot2_moves: int
    bot1_errors: int
    bot2_errors: int
    battle_format: str
    timestamp: str

class BattleTracker:
    """Tracks battle moves and decisions for analysis."""
    
    def __init__(self, results_dir: str = "./battle_analysis"):
        self.results_dir = results_dir
        self.current_battles: Dict[str, List[BattleMove]] = {}
        self.battle_info: Dict[str, Dict[str, Any]] = {}
        
        # Create results directory if it doesn't exist
        os.makedirs(results_dir, exist_ok=True)
        
        logger.info(f"Battle tracker initialized with results directory: {results_dir}")
    
    def start_battle(self, battle_id: str, bot1_name: str, bot2_name: str, battle_format: str):
        """Start tracking a new battle."""
        self.current_battles[battle_id] = []
        self.battle_info[battle_id] = {
            'bot1_name': bot1_name,
            'bot2_name': bot2_name,
            'battle_format': battle_format,
            'start_time': datetime.now().isoformat(),
            'turn_count': 0
        }
        
        logger.info(f"Started tracking battle {battle_id}: {bot1_name} vs {bot2_name}")
    
    def log_move(self, battle_id: str, bot_name: str, turn: int, llm_reasoning: str, 
                 parsed_action: str, action_value: str, execution_result: str, 
                 battle_state_summary: str, success: bool, error_message: Optional[str] = None):
        """Log a move decision."""
        
        if battle_id not in self.current_battles:
            logger.warning(f"Battle {battle_id} not found, creating new tracking entry")
            self.current_battles[battle_id] = []
            self.battle_info[battle_id] = {
                'bot1_name': bot_name,
                'bot2_name': 'Unknown',
                'battle_format': 'unknown',
                'start_time': datetime.now().isoformat(),
                'turn_count': turn
            }
        
        move = BattleMove(
            turn=turn,
            bot_name=bot_name,
            battle_id=battle_id,
            timestamp=datetime.now().isoformat(),
            llm_reasoning=llm_reasoning[:200] + "..." if len(llm_reasoning) > 200 else llm_reasoning,
            parsed_action=parsed_action,
            action_value=action_value,
            execution_result=execution_result,
            battle_state_summary=battle_state_summary,
            success=success,
            error_message=error_message
        )
        
        self.current_battles[battle_id].append(move)
        self.battle_info[battle_id]['turn_count'] = max(self.battle_info[battle_id]['turn_count'], turn)
        
        logger.info(f"Logged move for {bot_name} in battle {battle_id}: {parsed_action}={action_value} (success: {success})")
    
    def end_battle(self, battle_id: str, winner: Optional[str], duration_seconds: float):
        """End battle tracking and generate analysis."""
        
        if battle_id not in self.current_battles:
            logger.error(f"Cannot end battle {battle_id} - not being tracked")
            return
        
        moves = self.current_battles[battle_id]
        battle_info = self.battle_info[battle_id]
        
        # Calculate statistics
        bot1_moves = sum(1 for move in moves if move.bot_name == battle_info['bot1_name'])
        bot2_moves = sum(1 for move in moves if move.bot_name == battle_info['bot2_name'])
        bot1_errors = sum(1 for move in moves if move.bot_name == battle_info['bot1_name'] and not move.success)
        bot2_errors = sum(1 for move in moves if move.bot_name == battle_info['bot2_name'] and not move.success)
        
        analysis = BattleAnalysis(
            battle_id=battle_id,
            bot1_name=battle_info['bot1_name'],
            bot2_name=battle_info['bot2_name'],
            winner=winner,
            total_turns=battle_info['turn_count'],
            duration_seconds=duration_seconds,
            moves=moves,
            bot1_moves=bot1_moves,
            bot2_moves=bot2_moves,
            bot1_errors=bot1_errors,
            bot2_errors=bot2_errors,
            battle_format=battle_info['battle_format'],
            timestamp=datetime.now().isoformat()
        )
        
        # Save analysis to file
        filename = f"battle_analysis_{battle_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(asdict(analysis), f, indent=2, default=str)
        
        logger.info(f"Battle analysis saved to {filepath}")
        logger.info(f"Battle {battle_id} summary: {bot1_moves} moves by {battle_info['bot1_name']} ({bot1_errors} errors), "
                   f"{bot2_moves} moves by {battle_info['bot2_name']} ({bot2_errors} errors), winner: {winner}")
        
        # Clean up
        del self.current_battles[battle_id]
        del self.battle_info[battle_id]
        
        return analysis
    
    def get_battle_summary(self, battle_id: str) -> Optional[Dict[str, Any]]:
        """Get current battle summary."""
        if battle_id not in self.current_battles:
            return None
        
        moves = self.current_battles[battle_id]
        battle_info = self.battle_info[battle_id]
        
        return {
            'battle_id': battle_id,
            'total_moves': len(moves),
            'current_turn': battle_info['turn_count'],
            'bot1_name': battle_info['bot1_name'],
            'bot2_name': battle_info['bot2_name'],
            'bot1_moves': sum(1 for move in moves if move.bot_name == battle_info['bot1_name']),
            'bot2_moves': sum(1 for move in moves if move.bot_name == battle_info['bot2_name']),
            'recent_moves': [asdict(move) for move in moves[-5:]]  # Last 5 moves
        }

# Global battle tracker instance
battle_tracker = BattleTracker()