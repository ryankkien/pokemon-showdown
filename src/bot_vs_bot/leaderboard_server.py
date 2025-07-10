"""
Web-based leaderboard server for bot vs bot battles.
Provides real-time leaderboard updates and battle statistics.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import asyncio
import threading

from flask import Flask, render_template_string, jsonify, request
from flask_cors import CORS

from src.bot_vs_bot.bot_matchmaker import BotMatchmaker, BotStats
from src.bot_vs_bot.bot_manager import BattleResult


@dataclass
class LeaderboardEntry:
    """Enhanced leaderboard entry with additional stats."""
    rank: int
    username: str
    elo_rating: float
    wins: int
    losses: int
    draws: int
    total_battles: int
    win_rate: float
    recent_form: str  # W/L/D for last 5 battles
    last_battle: str  # Time since last battle
    favorite_format: str
    longest_win_streak: int
    current_streak: int
    avg_battle_duration: float


class LeaderboardManager:
    """Manages leaderboard data and statistics."""
    
    def __init__(self, data_file: str = "leaderboard_data.json"):
        self.data_file = data_file
        self.bot_stats: Dict[str, BotStats] = {}
        self.battle_history: List[BattleResult] = []
        self.load_data()
    
    def load_data(self):
        """Load data from file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                
                # Load bot stats
                for username, stats_data in data.get('bot_stats', {}).items():
                    # Remove username from stats_data if it exists to avoid duplicate
                    stats_copy = stats_data.copy()
                    stats_copy.pop('username', None)
                    self.bot_stats[username] = BotStats(
                        username=username,
                        **stats_copy
                    )
                
                # Load battle history
                for battle_data in data.get('battle_history', []):
                    result = BattleResult(**battle_data)
                    self.battle_history.append(result)
                    
            except Exception as e:
                print(f"Error loading leaderboard data: {e}")
    
    def save_data(self):
        """Save data to file."""
        try:
            data = {
                'bot_stats': {
                    username: asdict(stats) 
                    for username, stats in self.bot_stats.items()
                },
                'battle_history': [
                    asdict(result) for result in self.battle_history
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving leaderboard data: {e}")
    
    def update_from_matchmaker(self, matchmaker: BotMatchmaker):
        """Update leaderboard from matchmaker data, accumulating stats."""
        # Merge stats instead of replacing
        for username, new_stats in matchmaker.bot_stats.items():
            if username in self.bot_stats:
                # Accumulate stats
                existing = self.bot_stats[username]
                existing.wins += new_stats.wins
                existing.losses += new_stats.losses
                existing.draws += new_stats.draws
                existing.total_battles += new_stats.total_battles
                
                # Update ELO (use latest)
                existing.elo_rating = new_stats.elo_rating
                
                # Update win rate
                if existing.total_battles > 0:
                    existing.win_rate = (existing.wins / existing.total_battles) * 100
                
                # Update longest win streak if needed
                if new_stats.longest_win_streak > existing.longest_win_streak:
                    existing.longest_win_streak = new_stats.longest_win_streak
                
                # Update current streak
                existing.current_win_streak = new_stats.current_win_streak
                
                # Update last battle time
                existing.last_battle_time = max(existing.last_battle_time, new_stats.last_battle_time)
                
                # Update favorite format (keep the one with more battles)
                if new_stats.battle_formats:
                    if not existing.battle_formats:
                        existing.battle_formats = new_stats.battle_formats.copy()
                    else:
                        for format_name, count in new_stats.battle_formats.items():
                            existing.battle_formats[format_name] = existing.battle_formats.get(format_name, 0) + count
            else:
                # New bot - add directly
                self.bot_stats[username] = BotStats(
                    username=username,
                    elo_rating=new_stats.elo_rating,
                    wins=new_stats.wins,
                    losses=new_stats.losses,
                    draws=new_stats.draws,
                    total_battles=new_stats.total_battles,
                    win_rate=new_stats.win_rate,
                    longest_win_streak=new_stats.longest_win_streak,
                    current_win_streak=new_stats.current_win_streak,
                    last_battle_time=new_stats.last_battle_time,
                    battle_formats=new_stats.battle_formats.copy() if new_stats.battle_formats else {}
                )
        
        # Add battle results from manager
        for result in matchmaker.bot_manager.battle_results:
            if result not in self.battle_history:
                self.battle_history.append(result)
        
        self.save_data()
    
    def get_leaderboard(self, sort_by: str = "elo", limit: int = 50) -> List[LeaderboardEntry]:
        """Generate enhanced leaderboard with detailed statistics."""
        entries = []
        
        for username, stats in self.bot_stats.items():
            # Calculate recent form (last 5 battles)
            recent_battles = [
                b for b in self.battle_history 
                if (b.bot1_username == username or b.bot2_username == username)
            ][-5:]
            
            recent_form = ""
            for battle in recent_battles:
                if battle.winner == username:
                    recent_form += "W"
                elif battle.winner is None:
                    recent_form += "D"
                else:
                    recent_form += "L"
            
            # Time since last battle
            last_battle_time = max(
                [b.timestamp for b in recent_battles] or [0]
            )
            if last_battle_time > 0:
                time_diff = datetime.now().timestamp() - last_battle_time
                if time_diff < 3600:  # Less than 1 hour
                    last_battle = f"{int(time_diff/60)}m ago"
                elif time_diff < 86400:  # Less than 1 day
                    last_battle = f"{int(time_diff/3600)}h ago"
                else:
                    last_battle = f"{int(time_diff/86400)}d ago"
            else:
                last_battle = "Never"
            
            # Calculate favorite format
            format_counts = {}
            for battle in recent_battles:
                fmt = battle.battle_format
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            
            favorite_format = max(format_counts.items(), key=lambda x: x[1])[0] if format_counts else "N/A"
            
            # Calculate win streaks
            current_streak = 0
            longest_win_streak = 0
            temp_streak = 0
            
            user_battles = [
                b for b in self.battle_history 
                if (b.bot1_username == username or b.bot2_username == username)
            ]
            
            for battle in reversed(user_battles):
                if battle.winner == username:
                    current_streak += 1
                    temp_streak += 1
                    longest_win_streak = max(longest_win_streak, temp_streak)
                else:
                    if current_streak == temp_streak:
                        current_streak = 0
                    temp_streak = 0
            
            # Average battle duration
            user_durations = [
                b.duration for b in user_battles if b.duration > 0
            ]
            avg_duration = sum(user_durations) / len(user_durations) if user_durations else 0
            
            entry = LeaderboardEntry(
                rank=0,  # Will be set after sorting
                username=username,
                elo_rating=round(stats.elo_rating, 1),
                wins=stats.wins,
                losses=stats.losses,
                draws=stats.draws,
                total_battles=stats.total_battles,
                win_rate=round(stats.win_rate * 100, 1),
                recent_form=recent_form or "N/A",
                last_battle=last_battle,
                favorite_format=favorite_format,
                longest_win_streak=longest_win_streak,
                current_streak=current_streak,
                avg_battle_duration=round(avg_duration, 1)
            )
            entries.append(entry)
        
        # Sort entries
        if sort_by == "elo":
            entries.sort(key=lambda e: e.elo_rating, reverse=True)
        elif sort_by == "wins":
            entries.sort(key=lambda e: e.wins, reverse=True)
        elif sort_by == "win_rate":
            entries.sort(key=lambda e: e.win_rate, reverse=True)
        elif sort_by == "battles":
            entries.sort(key=lambda e: e.total_battles, reverse=True)
        
        # Set ranks
        for i, entry in enumerate(entries[:limit], 1):
            entry.rank = i
        
        return entries[:limit]
    
    def get_battle_stats(self) -> Dict[str, Any]:
        """Get overall battle statistics."""
        total_battles = len(self.battle_history)
        if total_battles == 0:
            return {"total_battles": 0}
        
        avg_duration = sum(b.duration for b in self.battle_history) / total_battles
        total_turns = sum(b.turns for b in self.battle_history if b.turns > 0)
        avg_turns = total_turns / len([b for b in self.battle_history if b.turns > 0]) if total_turns > 0 else 0
        
        # Format distribution
        format_counts = {}
        for battle in self.battle_history:
            fmt = battle.battle_format
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
        
        # Recent activity (last 24 hours)
        day_ago = datetime.now().timestamp() - 86400
        recent_battles = [b for b in self.battle_history if b.timestamp > day_ago]
        
        return {
            "total_battles": total_battles,
            "avg_duration": round(avg_duration, 1),
            "avg_turns": round(avg_turns, 1),
            "format_distribution": format_counts,
            "battles_today": len(recent_battles),
            "active_bots": len(self.bot_stats),
            "last_updated": datetime.now().isoformat()
        }


# Flask app for web interface
app = Flask(__name__)
CORS(app)

# Global leaderboard manager
leaderboard_manager = LeaderboardManager()

# HTML template for leaderboard
LEADERBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pokemon Showdown Bot Leaderboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #ff6b6b, #ee5a24);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }
        .persistence-note {
            background: #e8f5e8;
            color: #2d5a2d;
            padding: 10px;
            text-align: center;
            font-size: 0.9rem;
            border-left: 4px solid #28a745;
            margin: 0;
        }
        .stats-bar {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        .stat {
            text-align: center;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #2d3436;
        }
        .stat-label {
            color: #636e72;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        .controls {
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f8f9fa;
        }
        .sort-buttons {
            display: flex;
            gap: 10px;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #0984e3;
            color: white;
        }
        .btn-primary:hover {
            background: #0770c2;
        }
        .btn-secondary {
            background: #ddd;
            color: #333;
        }
        .btn-secondary:hover {
            background: #ccc;
        }
        .refresh-info {
            color: #636e72;
            font-size: 0.9rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2d3436;
            position: sticky;
            top: 0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .rank {
            font-weight: bold;
            color: #e17055;
        }
        .rank-1 { color: #fdcb6e; }
        .rank-2 { color: #a29bfe; }
        .rank-3 { color: #fd79a8; }
        .username {
            font-weight: 600;
            color: #2d3436;
        }
        .elo {
            font-weight: bold;
            color: #00b894;
        }
        .win-rate {
            color: #0984e3;
        }
        .recent-form {
            font-family: monospace;
            font-weight: bold;
        }
        .recent-form .win { color: #00b894; }
        .recent-form .loss { color: #e17055; }
        .recent-form .draw { color: #fdcb6e; }
        .streak {
            background: #00b894;
            color: white;
            padding: 2px 6px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #636e72;
        }
        @media (max-width: 768px) {
            .container {
                margin: 10px;
            }
            .header h1 {
                font-size: 2rem;
            }
            .stats-bar {
                flex-wrap: wrap;
            }
            .controls {
                flex-direction: column;
                gap: 15px;
            }
            table {
                font-size: 0.9rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Bot Battle Leaderboard</h1>
            <p>Pokemon Showdown AI Tournament Rankings</p>
        </div>
        
        <div class="persistence-note">
            📊 This leaderboard accumulates statistics across all battle sessions - stats persist between runs!
        </div>
        
        <div class="stats-bar">
            <div class="stat">
                <div class="stat-value" id="total-battles">-</div>
                <div class="stat-label">Total Battles</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="active-bots">-</div>
                <div class="stat-label">Active Bots</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="battles-today">-</div>
                <div class="stat-label">Battles Today</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="avg-duration">-</div>
                <div class="stat-label">Avg Duration (s)</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="sort-buttons">
                <button class="btn btn-primary" onclick="sortBy('elo')">ELO Rating</button>
                <button class="btn btn-secondary" onclick="sortBy('wins')">Most Wins</button>
                <button class="btn btn-secondary" onclick="sortBy('win_rate')">Win Rate</button>
                <button class="btn btn-secondary" onclick="sortBy('battles')">Most Battles</button>
            </div>
            <div class="refresh-info">
                <button class="btn btn-primary" onclick="refreshData()">🔄 Refresh</button>
                <span id="last-update">Last updated: -</span>
            </div>
        </div>
        
        <div id="leaderboard-content">
            <div class="loading">Loading leaderboard...</div>
        </div>
    </div>

    <script>
        let currentSort = 'elo';
        
        async function fetchLeaderboard(sortBy = 'elo') {
            try {
                const response = await fetch(`/api/leaderboard?sort=${sortBy}`);
                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error fetching leaderboard:', error);
                return null;
            }
        }
        
        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error fetching stats:', error);
                return null;
            }
        }
        
        function formatRecentForm(form) {
            return form.split('').map(char => {
                if (char === 'W') return '<span class="win">W</span>';
                if (char === 'L') return '<span class="loss">L</span>';
                if (char === 'D') return '<span class="draw">D</span>';
                return char;
            }).join('');
        }
        
        function renderLeaderboard(data) {
            if (!data || !data.leaderboard) {
                document.getElementById('leaderboard-content').innerHTML = 
                    '<div class="loading">No data available</div>';
                return;
            }
            
            const table = `
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Bot Name</th>
                            <th>ELO Rating</th>
                            <th>Record</th>
                            <th>Win Rate</th>
                            <th>Recent Form</th>
                            <th>Current Streak</th>
                            <th>Last Battle</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.leaderboard.map(bot => `
                            <tr>
                                <td class="rank rank-${bot.rank}">#${bot.rank}</td>
                                <td class="username">${bot.username}</td>
                                <td class="elo">${bot.elo_rating}</td>
                                <td>${bot.wins}-${bot.losses}-${bot.draws}</td>
                                <td class="win-rate">${bot.win_rate}%</td>
                                <td class="recent-form">${formatRecentForm(bot.recent_form)}</td>
                                <td>
                                    ${bot.current_streak > 0 ? 
                                        `<span class="streak">${bot.current_streak}W</span>` : 
                                        '-'
                                    }
                                </td>
                                <td>${bot.last_battle}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
            document.getElementById('leaderboard-content').innerHTML = table;
        }
        
        function updateStats(stats) {
            if (!stats) return;
            
            document.getElementById('total-battles').textContent = stats.total_battles || 0;
            document.getElementById('active-bots').textContent = stats.active_bots || 0;
            document.getElementById('battles-today').textContent = stats.battles_today || 0;
            document.getElementById('avg-duration').textContent = stats.avg_duration || 0;
            
            const lastUpdate = new Date(stats.last_updated || Date.now()).toLocaleTimeString();
            document.getElementById('last-update').textContent = `Last updated: ${lastUpdate}`;
        }
        
        async function sortBy(type) {
            currentSort = type;
            
            // Update button states
            document.querySelectorAll('.sort-buttons .btn').forEach(btn => {
                btn.className = 'btn btn-secondary';
            });
            event.target.className = 'btn btn-primary';
            
            const data = await fetchLeaderboard(type);
            renderLeaderboard(data);
        }
        
        async function refreshData() {
            const [leaderboardData, statsData] = await Promise.all([
                fetchLeaderboard(currentSort),
                fetchStats()
            ]);
            
            renderLeaderboard(leaderboardData);
            updateStats(statsData);
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Serve the leaderboard web interface."""
    return render_template_string(LEADERBOARD_HTML)


@app.route('/api/leaderboard')
def api_leaderboard():
    """API endpoint for leaderboard data."""
    sort_by = request.args.get('sort', 'elo')
    limit = int(request.args.get('limit', 50))
    
    leaderboard = leaderboard_manager.get_leaderboard(sort_by, limit)
    
    return jsonify({
        'leaderboard': [asdict(entry) for entry in leaderboard],
        'sort_by': sort_by,
        'total_bots': len(leaderboard_manager.bot_stats)
    })


@app.route('/api/stats')
def api_stats():
    """API endpoint for battle statistics."""
    return jsonify(leaderboard_manager.get_battle_stats())


@app.route('/api/update', methods=['POST'])
def api_update():
    """API endpoint to update leaderboard data."""
    try:
        data = request.get_json()
        
        if 'bot_stats' in data:
            for username, stats_data in data['bot_stats'].items():
                leaderboard_manager.bot_stats[username] = BotStats(
                    username=username,
                    **stats_data
                )
        
        if 'battle_results' in data:
            for result_data in data['battle_results']:
                result = BattleResult(**result_data)
                if result not in leaderboard_manager.battle_history:
                    leaderboard_manager.battle_history.append(result)
        
        leaderboard_manager.save_data()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


def run_server(host='localhost', port=5000, debug=False):
    """Run the leaderboard server."""
    print(f"🚀 Starting leaderboard server at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


def main():
    """Main function to run the leaderboard server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pokemon Showdown Bot Leaderboard Server")
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--data-file', default='leaderboard_data.json', help='Data file path')
    
    args = parser.parse_args()
    
    # Set global data file
    global leaderboard_manager
    leaderboard_manager = LeaderboardManager(args.data_file)
    
    run_server(args.host, args.port, args.debug)


if __name__ == '__main__':
    main()