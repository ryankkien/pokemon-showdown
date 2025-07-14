"""
Enhanced web server that combines leaderboard, battle scheduling, and relay functionality.
"""

import json
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

from src.bot_vs_bot.leaderboard_server import LeaderboardManager, LEADERBOARD_HTML
from src.bot_vs_bot.battle_relay_server import start_relay_server, get_relay_server
from src.bot_vs_bot.bot_manager import BotManager
from src.bot_vs_bot.bot_matchmaker import BotMatchmaker, MatchRequest
from src.bot_vs_bot.bot_vs_bot_config import BotVsBotConfigManager
from src.bot.play_format import SUPPORTED_RANDOM_BATTLE_FORMATS

@dataclass 
class ScheduledBattle:
    """Represents a scheduled battle."""
    bot1: str
    bot2: str
    format: str
    scheduled_time: datetime
    battle_id: Optional[str] = None

class WebBattleServer:
    """Combined web server for battles and leaderboard."""
    
    def __init__(self, config_manager: BotVsBotConfigManager, port: int = 5000, 
                 use_external_matchmaker: bool = False):
        self.app = Flask(__name__)
        CORS(self.app)
        self.port = port
        self.config_manager = config_manager
        self.use_external_matchmaker = use_external_matchmaker
        
        # Components - only create if not using external matchmaker
        self.leaderboard_manager = LeaderboardManager()
        self.bot_manager = None
        self.matchmaker = None
        if not use_external_matchmaker:
            self.relay_server = start_relay_server(port + 1)
        else:
            self.relay_server = None
        
        # Battle management
        self.current_battle = None
        self.scheduled_battle = None
        self.battle_status = 'idle'  # idle, battling, scheduled
        self.auto_schedule_enabled = True
        self.battle_delay_minutes = 5
        
        # External matchmaker references (set by continuous mode)
        self.external_bot_manager = None
        self.external_matchmaker = None
        
        # Setup routes
        self._setup_routes()
    
    def set_external_components(self, bot_manager, matchmaker):
        """Set external bot manager and matchmaker from continuous mode."""
        self.external_bot_manager = bot_manager
        self.external_matchmaker = matchmaker
        self.use_external_matchmaker = True
        
    def _setup_routes(self):
        """Setup all HTTP routes."""
        
        # Serve main page - redirect to React app
        @self.app.route('/')
        def index():
            return '''
            <html>
            <head><title>Pokemon Showdown LLM Battle Arena</title></head>
            <body>
                <h1>Pokemon Showdown LLM Battle Arena</h1>
                <p>This is the API server running on port 5000.</p>
                <p><strong>Please visit the web interface at: <a href="http://localhost:3000">http://localhost:3000</a></strong></p>
                <p>Services:</p>
                <ul>
                    <li>Web Interface: <a href="http://localhost:3000">http://localhost:3000</a></li>
                    <li>API Server: <a href="http://localhost:5000/api/leaderboard">http://localhost:5000/api/leaderboard</a></li>
                    <li>Pokemon Showdown: <a href="http://localhost:8000">http://localhost:8000</a></li>
                </ul>
            </body>
            </html>
            '''
        
        # Leaderboard endpoints
        @self.app.route('/api/leaderboard')
        def api_leaderboard():
            sort_by = request.args.get('sort', 'elo')
            limit = int(request.args.get('limit', 50))
            battle_format = request.args.get('format', 'all')
            
            # Use external matchmaker if available
            if self.use_external_matchmaker and self.external_matchmaker:
                # Get data from external matchmaker
                leaderboard_data = self.external_matchmaker.get_leaderboard()
                leaderboard = []
                for i, bot_data in enumerate(leaderboard_data[:limit], 1):
                    from src.bot_vs_bot.leaderboard_server import LeaderboardEntry
                    entry = LeaderboardEntry(
                        rank=i,
                        username=bot_data['username'],
                        elo_rating=bot_data['elo_rating'],
                        wins=bot_data['wins'],
                        losses=bot_data['losses'],
                        draws=bot_data['draws'],
                        total_battles=bot_data['total_battles'],
                        win_rate=bot_data['win_rate'],
                        recent_form=bot_data.get('recent_form', ''),
                        longest_win_streak=bot_data.get('longest_win_streak', 0),
                        current_streak=bot_data.get('current_streak', 0),
                        avg_battle_duration=bot_data.get('avg_battle_duration', 0.0),
                        is_battling=False
                    )
                    # Check if bot is currently battling
                    if self.current_battle:
                        entry.is_battling = (
                            entry.username == self.current_battle.get('bot1') or 
                            entry.username == self.current_battle.get('bot2')
                        )
                    leaderboard.append(entry)
            else:
                # Use internal leaderboard manager
                leaderboard = self.leaderboard_manager.get_leaderboard(sort_by, limit, battle_format)
                
                # Add battling status to entries
                for entry in leaderboard:
                    if self.current_battle:
                        entry.is_battling = (
                            entry.username == self.current_battle.get('bot1') or 
                            entry.username == self.current_battle.get('bot2')
                        )
                    else:
                        entry.is_battling = False
            
            return jsonify({
                'leaderboard': [asdict(entry) for entry in leaderboard],
                'sort_by': sort_by,
                'battle_format': battle_format,
                'total_bots': len(leaderboard),
                'available_formats': ['all'] + SUPPORTED_RANDOM_BATTLE_FORMATS
            })
        
        @self.app.route('/api/stats')
        def api_stats():
            if self.use_external_matchmaker and self.external_matchmaker:
                # Get stats from external matchmaker
                total_battles = len(self.external_bot_manager.battle_results) if self.external_bot_manager else 0
                stats = {
                    'total_battles': total_battles,
                    'active_bots': len(self.external_bot_manager.active_bots) if self.external_bot_manager else 0,
                    'battles_today': total_battles,  # Simplified for now
                    'avg_duration': 120.0,  # Simplified for now
                    'battle_status': self.battle_status,
                    'current_battle': self.current_battle
                }
            else:
                # Use internal leaderboard manager
                stats = self.leaderboard_manager.get_battle_stats()
                stats['battle_status'] = self.battle_status
                stats['current_battle'] = self.current_battle
            return jsonify(stats)
        
        @self.app.route('/api/update', methods=['POST'])
        def api_update():
            """Update leaderboard data from bot system."""
            try:
                data = request.get_json()
                new_battles = 0
                updated_bots = 0
                
                # Update bot stats
                if 'bot_stats' in data:
                    for username, stats_data in data['bot_stats'].items():
                        stats_copy = stats_data.copy()
                        stats_copy.pop('username', None)
                        from src.bot_vs_bot.bot_matchmaker import BotStats
                        self.leaderboard_manager.bot_stats[username] = BotStats(
                            username=username,
                            **stats_copy
                        )
                        updated_bots += 1
                
                # Update battle history
                if 'battle_results' in data:
                    for result_data in data['battle_results']:
                        try:
                            from src.bot_vs_bot.bot_manager import BattleResult
                            result = BattleResult(**result_data)
                            existing_ids = {b.battle_id for b in self.leaderboard_manager.battle_history}
                            if result.battle_id not in existing_ids:
                                self.leaderboard_manager.battle_history.append(result)
                                new_battles += 1
                        except Exception as e:
                            print(f"Error processing battle result: {e}")
                            continue
                
                self.leaderboard_manager.save_data()
                
                return jsonify({
                    'status': 'success',
                    'new_battles': new_battles,
                    'updated_bots': updated_bots
                })
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 400
        
        # Battle control endpoints
        @self.app.route('/api/battle-status')
        def api_battle_status():
            """Get current battle status."""
            response = {
                'status': self.battle_status,
                'currentBattle': self.current_battle,
                'scheduledBattle': None,
                'autoScheduleEnabled': self.auto_schedule_enabled
            }
            
            if self.scheduled_battle:
                response['scheduledBattle'] = {
                    'bot1': self.scheduled_battle.bot1,
                    'bot2': self.scheduled_battle.bot2,
                    'format': self.scheduled_battle.format,
                    'scheduledTime': self.scheduled_battle.scheduled_time.isoformat()
                }
                response['nextBattleTime'] = self.scheduled_battle.scheduled_time.isoformat()
            
            return jsonify(response)
        
        @self.app.route('/api/start-battle', methods=['POST'])
        def api_start_battle():
            """Start a battle immediately."""
            try:
                data = request.get_json()
                battle_format = data.get('format', 'gen9randombattle')
                
                if self.use_external_matchmaker and self.external_matchmaker:
                    # Use external matchmaker - add match requests to trigger battles
                    from src.bot_vs_bot.bot_matchmaker import MatchRequest
                    import random
                    
                    # Select two random bots
                    available_bots = [config for config in self.config_manager.config.bot_configs 
                                    if config.username in self.external_bot_manager.active_bots]
                    
                    if len(available_bots) < 2:
                        return jsonify({'success': False, 'error': 'Not enough active bots'}), 400
                    
                    selected_bots = random.sample(available_bots, 2)
                    
                    # Add match requests for both bots
                    for bot_config in selected_bots:
                        request_obj = MatchRequest(
                            bot_username=bot_config.username,
                            battle_format=battle_format,
                            max_wait_time=60.0  # Shorter timeout for web-requested battles
                        )
                        self.external_matchmaker.add_match_request(request_obj)
                    
                    # Set current battle info for status tracking
                    self.current_battle = {
                        'id': f"battle_{int(time.time())}",
                        'bot1': selected_bots[0].username,
                        'bot2': selected_bots[1].username,
                        'format': battle_format,
                        'startTime': datetime.now().isoformat()
                    }
                    self.battle_status = 'battling'
                    
                    return jsonify({
                        'success': True,
                        'message': 'Battle requests added to matchmaker',
                        'format': battle_format,
                        'battle': self.current_battle
                    })
                else:
                    # Use internal battle management (original behavior)
                    # Start battle in background
                    battle_thread = threading.Thread(
                        target=self._run_battle_async,
                        args=(battle_format,),
                        daemon=True
                    )
                    battle_thread.start()
                    
                    return jsonify({
                        'success': True,
                        'message': 'Battle starting...',
                        'format': battle_format
                    })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/schedule-battle', methods=['POST'])
        def api_schedule_battle():
            """Schedule a battle for later."""
            try:
                data = request.get_json()
                battle_format = data.get('format', 'gen9randombattle')
                delay_minutes = data.get('delayMinutes', 5)
                
                if self.use_external_matchmaker and self.external_matchmaker:
                    # For external matchmaker, we just set a scheduled battle
                    # The continuous matchmaker will handle the actual scheduling
                    import random
                    
                    # Select two random bots
                    available_bots = [config for config in self.config_manager.config.bot_configs 
                                    if config.username in self.external_bot_manager.active_bots]
                    
                    if len(available_bots) < 2:
                        return jsonify({'success': False, 'error': 'Not enough active bots'}), 400
                    
                    selected_bots = random.sample(available_bots, 2)
                    
                    scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
                    
                    self.scheduled_battle = ScheduledBattle(
                        bot1=selected_bots[0].username,
                        bot2=selected_bots[1].username,
                        format=battle_format,
                        scheduled_time=scheduled_time
                    )
                    
                    self.battle_status = 'scheduled'
                    
                    # Start scheduler thread that will add match requests at the scheduled time
                    scheduler_thread = threading.Thread(
                        target=self._run_scheduled_battle_external,
                        args=(self.scheduled_battle,),
                        daemon=True
                    )
                    scheduler_thread.start()
                    
                    return jsonify({
                        'success': True,
                        'scheduledTime': scheduled_time.isoformat(),
                        'bot1': selected_bots[0].username,
                        'bot2': selected_bots[1].username,
                        'format': battle_format
                    })
                else:
                    # Use internal scheduling (original behavior)
                    # Select two random bots
                    if len(self.config_manager.config.bot_configs) < 2:
                        return jsonify({'success': False, 'error': 'Not enough bots configured'}), 400
                    
                    import random
                    bots = random.sample(self.config_manager.config.bot_configs, 2)
                    
                    scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
                    
                    self.scheduled_battle = ScheduledBattle(
                        bot1=bots[0].username,
                        bot2=bots[1].username,
                        format=battle_format,
                        scheduled_time=scheduled_time
                    )
                    
                    self.battle_status = 'scheduled'
                    
                    # Start scheduler thread
                    scheduler_thread = threading.Thread(
                        target=self._run_scheduled_battle,
                        args=(self.scheduled_battle,),
                        daemon=True
                    )
                    scheduler_thread.start()
                    
                    return jsonify({
                        'success': True,
                        'scheduledTime': scheduled_time.isoformat(),
                        'bot1': bots[0].username,
                        'bot2': bots[1].username,
                        'format': battle_format
                    })
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/toggle-auto-schedule', methods=['POST'])
        def api_toggle_auto_schedule():
            """Toggle automatic battle scheduling."""
            self.auto_schedule_enabled = not self.auto_schedule_enabled
            return jsonify({
                'success': True,
                'autoScheduleEnabled': self.auto_schedule_enabled
            })
    
    def _run_scheduled_battle(self, scheduled_battle: ScheduledBattle):
        """Run a battle at the scheduled time."""
        # Wait until scheduled time
        wait_time = (scheduled_battle.scheduled_time - datetime.now()).total_seconds()
        if wait_time > 0:
            time.sleep(wait_time)
        
        # Run the battle
        self._run_battle_async(scheduled_battle.format)
    
    def _run_scheduled_battle_external(self, scheduled_battle: ScheduledBattle):
        """Run a battle at the scheduled time using the external matchmaker."""
        # Wait until scheduled time
        wait_time = (scheduled_battle.scheduled_time - datetime.now()).total_seconds()
        if wait_time > 0:
            time.sleep(wait_time)
        
        # Add match requests for the scheduled battle
        from src.bot_vs_bot.bot_matchmaker import MatchRequest
        import random
        
        # Select two random bots
        available_bots = [config for config in self.config_manager.config.bot_configs 
                        if config.username in self.external_bot_manager.active_bots]
        
        if len(available_bots) < 2:
            print(f"Not enough active bots to schedule battle at {scheduled_battle.scheduled_time}")
            return
        
        selected_bots = random.sample(available_bots, 2)
        
        for bot_config in selected_bots:
            request_obj = MatchRequest(
                bot_username=bot_config.username,
                battle_format=scheduled_battle.format,
                max_wait_time=60.0  # Shorter timeout for web-requested battles
            )
            self.external_matchmaker.add_match_request(request_obj)
        
        # Set current battle info for status tracking
        self.current_battle = {
            'id': f"battle_{int(time.time())}",
            'bot1': selected_bots[0].username,
            'bot2': selected_bots[1].username,
            'format': scheduled_battle.format,
            'startTime': datetime.now().isoformat()
        }
        self.battle_status = 'scheduled'
        
        print(f"Scheduled battle at {scheduled_battle.scheduled_time}: {selected_bots[0].username} vs {selected_bots[1].username}")
    
    def _run_battle_async(self, battle_format: str):
        """Run a battle asynchronously."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the battle
            loop.run_until_complete(self._run_single_battle(battle_format))
            
            # Schedule next battle if auto-schedule is enabled
            if self.auto_schedule_enabled and self.battle_status != 'scheduled':
                delay_minutes = self.battle_delay_minutes
                self.api_schedule_battle()
                
        except Exception as e:
            print(f"Error running battle: {e}")
            self.battle_status = 'idle'
        finally:
            loop.close()
    
    async def _run_single_battle(self, battle_format: str):
        """Run a single battle between two random bots."""
        self.battle_status = 'battling'
        
        try:
            # Initialize components if needed
            if not self.bot_manager:
                self.bot_manager = BotManager(self.config_manager.config.server_url)
                self.matchmaker = BotMatchmaker(self.bot_manager, self.config_manager.config.matchmaking_strategy)
            
            # Select two random bots
            import random
            if len(self.config_manager.config.bot_configs) < 2:
                raise ValueError("Not enough bots configured")
            
            bot_configs = random.sample(self.config_manager.config.bot_configs, 2)
            bot1_config = bot_configs[0]
            bot2_config = bot_configs[1]
            
            # Update current battle info
            self.current_battle = {
                'id': f"battle_{int(time.time())}",
                'bot1': bot1_config.username,
                'bot2': bot2_config.username,
                'format': battle_format,
                'startTime': datetime.now().isoformat()
            }
            
            # Notify relay server about the battle
            if self.relay_server:
                self.relay_server.start_battle_relay(
                    bot1_config.username,
                    bot2_config.username,
                    battle_format,
                    self.current_battle['id']
                )
            
            print(f"Starting battle: {bot1_config.username} vs {bot2_config.username}")
            print(f"Active bots before creation: {list(self.bot_manager.active_bots.keys())}")
            
            # Create bots only if they don't exist
            if bot1_config.username not in self.bot_manager.active_bots:
                print(f"Creating bot: {bot1_config.username}")
                await self.bot_manager.create_bot(bot1_config)
            else:
                print(f"Bot {bot1_config.username} already exists")
                
            if bot2_config.username not in self.bot_manager.active_bots:
                print(f"Creating bot: {bot2_config.username}")
                await self.bot_manager.create_bot(bot2_config)
            else:
                print(f"Bot {bot2_config.username} already exists")
                
            print(f"Active bots after creation: {list(self.bot_manager.active_bots.keys())}")
            
            # Start battle directly using poke-env's battle method
            print(f"Starting direct battle between {bot1_config.username} and {bot2_config.username}")
            
            bot1 = self.bot_manager.active_bots[bot1_config.username]
            bot2 = self.bot_manager.active_bots[bot2_config.username]
            
            # Use poke-env's battle method to make them fight each other
            battle_task = asyncio.create_task(bot1.battle_against(bot2, n_battles=1))
            battle_id = f"battle_{int(time.time())}"
            
            print(f"Battle task created, waiting for completion...")
            await battle_task
            
            # Wait for battle to complete with periodic updates
            max_duration = 600  # 10 minutes max
            check_interval = 5  # Check every 5 seconds
            elapsed = 0
            
            while elapsed < max_duration:
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                
                # Check if battle is complete
                # This is a simplified check - you'd want to properly track battle state
                if len(self.bot_manager.battle_results) > 0:
                    last_result = self.bot_manager.battle_results[-1]
                    if last_result.battle_id == battle_id:
                        # Battle complete
                        break
            
            # Update stats
            if self.matchmaker:
                for result in self.bot_manager.battle_results:
                    if result.battle_id == battle_id:
                        self.matchmaker.update_battle_result(result)
                        
                        # Update leaderboard
                        self.leaderboard_manager.update_from_matchmaker(self.matchmaker)
                        
                        # End relay
                        if self.relay_server:
                            self.relay_server.end_battle_relay(
                                self.current_battle['id'],
                                result
                            )
                        
                        print(f"Battle completed: {result.winner} wins!")
                        break
            
        except Exception as e:
            print(f"Error in battle: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.current_battle = None
            self.battle_status = 'idle'
            self.scheduled_battle = None
    
    def run(self):
        """Run the web server."""
        print(f"Starting web battle server on port {self.port}")
        print(f"Battle relay server on port {self.port + 1}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)


def run_web_server(config_path: str = "bot_vs_bot_config.json", port: int = 5000):
    """Run the combined web server."""
    # Load configuration
    config_manager = BotVsBotConfigManager(config_path)
    
    # Create and run server
    server = WebBattleServer(config_manager, port)
    server.run()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="Pokemon Showdown Web Battle Server")
    parser.add_argument('--config', default='bot_vs_bot_config.json', help='Configuration file')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    
    args = parser.parse_args()
    
    run_web_server(args.config, args.port)