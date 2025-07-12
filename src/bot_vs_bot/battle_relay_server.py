"""
Battle Relay Server - Proxies Pokemon Showdown battles with move delays for better viewing.
Provides Socket.IO interface for web clients to watch battles in real-time.
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import requests

from src.bot.bot import LLMPlayer
from src.bot_vs_bot.bot_manager import BotManager, BattleResult

logger = logging.getLogger(__name__)

@dataclass
class BattleState:
    """Current state of a battle for display."""
    battle_id: str
    format: str
    turn: int
    p1: Dict[str, Any]  # Player 1 info
    p2: Dict[str, Any]  # Player 2 info
    weather: Optional[str] = None
    terrain: Optional[str] = None
    last_move: Optional[str] = None
    timestamp: float = 0

@dataclass
class DelayedMove:
    """A move that's been delayed for viewing."""
    battle_id: str
    player: str
    move: str
    target: Optional[str]
    delay_seconds: float
    scheduled_time: float

class BattleRelayServer:
    """Manages battle streaming with move delays."""
    
    def __init__(self, port: int = 5001):
        self.app = Flask(__name__)
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*", async_mode='threading')
        self.port = port
        
        # Battle tracking
        self.active_battles: Dict[str, BattleState] = {}
        self.battle_logs: Dict[str, List[str]] = {}
        self.delayed_moves: List[DelayedMove] = []
        self.battle_subscribers: Dict[str, List[str]] = {}  # battle_id -> [client_ids]
        
        # Move delay configuration
        self.min_delay = 10  # seconds
        self.max_delay = 30  # seconds
        
        self._setup_routes()
        self._setup_socketio_handlers()
        
    def _setup_routes(self):
        """Setup HTTP routes."""
        
        @self.app.route('/health')
        def health():
            return {'status': 'healthy', 'active_battles': len(self.active_battles)}
        
        @self.app.route('/api/active-battles')
        def get_active_battles():
            return {
                'battles': [
                    {
                        'id': battle_id,
                        'format': state.format,
                        'turn': state.turn,
                        'p1': state.p1['name'],
                        'p2': state.p2['name']
                    }
                    for battle_id, state in self.active_battles.items()
                ]
            }
    
    def _setup_socketio_handlers(self):
        """Setup Socket.IO event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = requests.sid
            logger.info(f"Client connected: {client_id}")
            emit('connected', {'client_id': client_id})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = requests.sid
            logger.info(f"Client disconnected: {client_id}")
            # Remove from all battle subscriptions
            for battle_id, subscribers in self.battle_subscribers.items():
                if client_id in subscribers:
                    subscribers.remove(client_id)
        
        @self.socketio.on('subscribeToBattle')
        def handle_subscribe(data):
            client_id = requests.sid
            battle_id = data.get('battleId')
            
            if battle_id:
                join_room(f"battle_{battle_id}")
                
                if battle_id not in self.battle_subscribers:
                    self.battle_subscribers[battle_id] = []
                self.battle_subscribers[battle_id].append(client_id)
                
                # Send current state if available
                if battle_id in self.active_battles:
                    emit('battleUpdate', {
                        'state': asdict(self.active_battles[battle_id]),
                        'logs': self.battle_logs.get(battle_id, [])[-10:]  # Last 10 logs
                    })
                
                logger.info(f"Client {client_id} subscribed to battle {battle_id}")
        
        @self.socketio.on('unsubscribeFromBattle')
        def handle_unsubscribe(data):
            client_id = requests.sid
            battle_id = data.get('battleId')
            
            if battle_id:
                leave_room(f"battle_{battle_id}")
                if battle_id in self.battle_subscribers and client_id in self.battle_subscribers[battle_id]:
                    self.battle_subscribers[battle_id].remove(client_id)
    
    def start_battle_relay(self, bot1_username: str, bot2_username: str, battle_format: str, battle_id: str):
        """Start relaying a battle with move delays."""
        # Initialize battle state
        battle_state = BattleState(
            battle_id=battle_id,
            format=battle_format,
            turn=0,
            p1={'name': bot1_username, 'team': [], 'active': None},
            p2={'name': bot2_username, 'team': [], 'active': None},
            timestamp=time.time()
        )
        
        self.active_battles[battle_id] = battle_state
        self.battle_logs[battle_id] = []
        
        logger.info(f"Started relaying battle {battle_id}: {bot1_username} vs {bot2_username}")
        
        # Notify all clients about new battle
        self.socketio.emit('newBattle', {
            'battleId': battle_id,
            'format': battle_format,
            'p1': bot1_username,
            'p2': bot2_username
        })
    
    def update_battle_state(self, battle_id: str, update: Dict[str, Any]):
        """Update battle state and notify subscribers."""
        if battle_id not in self.active_battles:
            return
        
        state = self.active_battles[battle_id]
        
        # Update state fields
        if 'turn' in update:
            state.turn = update['turn']
        if 'p1' in update:
            state.p1.update(update['p1'])
        if 'p2' in update:
            state.p2.update(update['p2'])
        if 'weather' in update:
            state.weather = update['weather']
        if 'terrain' in update:
            state.terrain = update['terrain']
        
        state.timestamp = time.time()
        
        # Add to battle log if provided
        if 'log' in update:
            self.battle_logs[battle_id].append(update['log'])
        
        # Check if this is a move that should be delayed
        if 'move' in update and not update.get('skipDelay', False):
            delay = random.uniform(self.min_delay, self.max_delay)
            delayed_move = DelayedMove(
                battle_id=battle_id,
                player=update.get('player', 'unknown'),
                move=update['move'],
                target=update.get('target'),
                delay_seconds=delay,
                scheduled_time=time.time() + delay
            )
            self.delayed_moves.append(delayed_move)
            
            # Notify about delayed move
            self._emit_to_battle(battle_id, 'battleUpdate', {
                'state': asdict(state),
                'log': f"[Delayed] {update.get('player', 'Player')} is thinking...",
                'isDelayed': True
            })
            
            # Schedule the actual move
            self.socketio.start_background_task(self._execute_delayed_move, delayed_move, state, update)
        else:
            # Immediate update (no delay)
            self._emit_to_battle(battle_id, 'battleUpdate', {
                'state': asdict(state),
                'log': update.get('log'),
                'isDelayed': False
            })
    
    def _execute_delayed_move(self, delayed_move: DelayedMove, state: BattleState, update: Dict[str, Any]):
        """Execute a move after its delay period."""
        # Wait for the delay
        delay_remaining = delayed_move.scheduled_time - time.time()
        if delay_remaining > 0:
            time.sleep(delay_remaining)
        
        # Apply the move update
        if 'last_move' in update:
            state.last_move = update['last_move']
        
        # Emit the actual move
        self._emit_to_battle(delayed_move.battle_id, 'battleUpdate', {
            'state': asdict(state),
            'log': f"{delayed_move.player} used {delayed_move.move}!",
            'isDelayed': False
        })
    
    def end_battle_relay(self, battle_id: str, result: BattleResult):
        """End a battle relay and notify subscribers."""
        if battle_id not in self.active_battles:
            return
        
        # Notify subscribers
        self._emit_to_battle(battle_id, 'battleEnd', {
            'battleId': battle_id,
            'winner': result.winner,
            'duration': result.duration,
            'turns': result.turns,
            'timestamp': result.timestamp
        })
        
        # Clean up
        del self.active_battles[battle_id]
        if battle_id in self.battle_logs:
            del self.battle_logs[battle_id]
        if battle_id in self.battle_subscribers:
            del self.battle_subscribers[battle_id]
        
        # Remove any pending delayed moves
        self.delayed_moves = [m for m in self.delayed_moves if m.battle_id != battle_id]
        
        logger.info(f"Ended battle relay {battle_id}")
    
    def _emit_to_battle(self, battle_id: str, event: str, data: Any):
        """Emit an event to all subscribers of a battle."""
        self.socketio.emit(event, data, room=f"battle_{battle_id}")
    
    def run(self):
        """Run the relay server."""
        logger.info(f"Starting battle relay server on port {self.port}")
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False, allow_unsafe_werkzeug=True)


# Global relay server instance
relay_server = None


def start_relay_server(port: int = 5001):
    """Start the battle relay server in a separate thread."""
    global relay_server
    
    if relay_server is None:
        relay_server = BattleRelayServer(port)
        
        import threading
        server_thread = threading.Thread(
            target=relay_server.run,
            daemon=True
        )
        server_thread.start()
        
        # Give server time to start
        time.sleep(2)
        
        logger.info(f"Battle relay server started on port {port}")
    
    return relay_server


def get_relay_server() -> Optional[BattleRelayServer]:
    """Get the current relay server instance."""
    return relay_server


if __name__ == '__main__':
    # Test the relay server
    server = BattleRelayServer()
    server.run()