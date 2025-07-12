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
from src.bot.play_format import SUPPORTED_RANDOM_BATTLE_FORMATS


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
        """Update leaderboard from matchmaker data."""
        # Simply copy the stats from matchmaker - it already has the correct cumulative stats
        for username, stats in matchmaker.bot_stats.items():
            self.bot_stats[username] = BotStats(
                username=username,
                elo_rating=stats.elo_rating,
                wins=stats.wins,
                losses=stats.losses,
                draws=stats.draws,
                total_battles=stats.total_battles,
                win_rate=stats.win_rate,
                longest_win_streak=stats.longest_win_streak,
                current_win_streak=stats.current_win_streak,
                last_battle_time=stats.last_battle_time,
                battle_formats=stats.battle_formats.copy() if stats.battle_formats else {}
            )
        
        # Add battle results from manager
        for result in matchmaker.bot_manager.battle_results:
            if result not in self.battle_history:
                self.battle_history.append(result)
        
        self.save_data()
    
    def get_leaderboard(self, sort_by: str = "elo", limit: int = 50, battle_format: str = "all") -> List[LeaderboardEntry]:
        """Generate enhanced leaderboard with detailed statistics."""
        entries = []
        
        for username, stats in self.bot_stats.items():
            # Filter battles by format if specified
            user_battles = [
                b for b in self.battle_history 
                if (b.bot1_username == username or b.bot2_username == username)
            ]
            
            if battle_format != "all":
                user_battles = [b for b in user_battles if b.battle_format == battle_format]
            
            # Skip if no battles in this format
            if battle_format != "all" and not user_battles:
                continue
            
            # Calculate recent form (last 5 battles)
            recent_battles = user_battles[-5:]
            
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
            
            # Calculate win streaks using filtered battles
            current_streak = 0
            longest_win_streak = 0
            temp_streak = 0
            
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
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pokemon Showdown - LLM Rankings</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0c0a09;
            color: #fafaf9;
            min-height: 100vh;
            line-height: 1.5;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 32px;
            padding: 40px 24px;
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 8px;
            color: #fafaf9;
            letter-spacing: -0.025em;
        }
        
        .header p {
            font-size: 1.25rem;
            color: #a1a1aa;
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .subtitle {
            font-size: 0.875rem;
            color: #71717a;
            font-weight: 400;
        }
        
        .status-bar {
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 16px;
        }
        .status-info {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #a1a1aa;
            font-size: 0.875rem;
        }
        
        .update-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .update-indicator.flash {
            background: #ef4444;
            animation: flash 0.8s ease-out;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @keyframes flash {
            0% { background: #ef4444; transform: scale(1.2); }
            50% { background: #f97316; transform: scale(1.4); }
            100% { background: #22c55e; transform: scale(1); }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        
        .stat-card {
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2.25rem;
            font-weight: 700;
            color: #fafaf9;
            margin-bottom: 4px;
        }
        
        .stat-label {
            color: #a1a1aa;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .controls {
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }
        
        .filter-controls {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .filter-controls select {
            min-width: 120px;
        }
        
        .sort-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 8px 16px;
            border: 1px solid #27272a;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            font-size: 0.875rem;
            transition: all 0.2s ease;
            background: #09090b;
            color: #a1a1aa;
        }
        
        .btn-primary {
            background: #2563eb;
            color: #f8fafc;
            border-color: #2563eb;
        }
        
        .btn-primary:hover {
            background: #1d4ed8;
            border-color: #1d4ed8;
        }
        
        .btn:hover {
            background: #27272a;
            color: #fafaf9;
        }
        
        .refresh-info {
            color: #71717a;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .leaderboard-container {
            background: #18181b;
            border: 1px solid #27272a;
            border-radius: 12px;
            overflow: hidden;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 16px 20px;
            text-align: left;
            border-bottom: 1px solid #27272a;
        }
        
        th {
            background: #09090b;
            font-weight: 600;
            color: #fafaf9;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            position: sticky;
            top: 0;
        }
        
        tbody tr {
            transition: background-color 0.2s ease;
        }
        
        tbody tr:hover {
            background: #27272a;
        }
        
        .rank {
            font-weight: 700;
            font-size: 1.125rem;
        }
        
        .rank-1 { color: #fbbf24; }
        .rank-2 { color: #94a3b8; }
        .rank-3 { color: #fb7185; }
        .rank { color: #a1a1aa; }
        
        .model-name {
            font-weight: 600;
            color: #fafaf9;
            font-size: 1rem;
        }
        
        .provider-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-left: 8px;
        }
        
        .openai { background: #065f46; color: #ecfdf5; }
        .anthropic { background: #7c2d12; color: #fef2f2; }
        .google { background: #1e40af; color: #eff6ff; }
        
        .elo {
            font-weight: 700;
            color: #22c55e;
            font-size: 1.125rem;
        }
        
        .record {
            color: #d1d5db;
            font-weight: 500;
        }
        
        .win-rate {
            font-weight: 600;
            color: #3b82f6;
        }
        
        .recent-form {
            font-family: 'JetBrains Mono', monospace;
            font-weight: 600;
            letter-spacing: 0.1em;
        }
        
        .recent-form .win { color: #22c55e; }
        .recent-form .loss { color: #ef4444; }
        .recent-form .draw { color: #f59e0b; }
        
        .streak {
            background: #22c55e;
            color: #052e16;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        
        .last-battle {
            color: #71717a;
            font-size: 0.875rem;
        }
        
        .loading {
            text-align: center;
            padding: 80px 20px;
            color: #71717a;
        }
        
        .loading-spinner {
            width: 24px;
            height: 24px;
            border: 2px solid #27272a;
            border-top-color: #2563eb;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        @media (max-width: 1024px) {
            .container {
                padding: 16px;
            }
            .header h1 {
                font-size: 2.25rem;
            }
            .stats-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
        }
        
        @media (max-width: 768px) {
            .header {
                padding: 32px 20px;
            }
            .header h1 {
                font-size: 2rem;
            }
            .header p {
                font-size: 1.125rem;
            }
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            .sort-buttons {
                justify-content: center;
            }
            th, td {
                padding: 12px 16px;
                font-size: 0.875rem;
            }
            .provider-badge {
                display: none;
            }
        }
        
        @media (max-width: 480px) {
            .header h1 {
                font-size: 1.75rem;
            }
            .header p {
                font-size: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Pokemon Showdown LLM Rankings</h1>
            <p>AI Model Performance Leaderboard</p>
            <div class="subtitle">Real-time competitive statistics</div>
        </div>
        
        <div class="status-bar">
            <div class="status-info">
                📊 Real-time rankings • Persistent across sessions
                <span class="update-indicator" title="Live updates every 3 seconds"></span>
            </div>
            <div class="status-info">
                <span id="last-update">Loading...</span>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="total-battles">-</div>
                <div class="stat-label">Total Battles</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="active-bots">-</div>
                <div class="stat-label">LLM Models</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="battles-today">-</div>
                <div class="stat-label">Battles Today</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avg-duration">-</div>
                <div class="stat-label">Avg Duration (s)</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="sort-buttons">
                <button class="btn btn-primary" onclick="sortBy('elo')">ELO Rating</button>
                <button class="btn" onclick="sortBy('wins')">Most Wins</button>
                <button class="btn" onclick="sortBy('win_rate')">Win Rate</button>
                <button class="btn" onclick="sortBy('battles')">Most Battles</button>
            </div>
            <div class="filter-controls">
                <label for="format-filter" style="color: #a1a1aa; margin-right: 8px;">Mode:</label>
                <select id="format-filter" class="btn" onchange="filterByFormat()">
                    <option value="all">All Modes</option>
                </select>
            </div>
            <div class="refresh-info">
                <button class="btn" onclick="refreshData()">↻ Refresh</button>
            </div>
        </div>
        
        <div class="leaderboard-container">
            <div id="leaderboard-content">
                <div class="loading">
                    <div class="loading-spinner"></div>
                    Loading LLM rankings...
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentSort = 'elo';
        let currentFormat = 'all';
        
        async function fetchLeaderboard(sortBy = 'elo', formatFilter = 'all') {
            try {
                const response = await fetch(`/api/leaderboard?sort=${sortBy}&format=${formatFilter}`);
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
        
        function getProviderBadge(modelName) {
            if (modelName.toLowerCase().includes('gpt') || modelName.toLowerCase().includes('openai')) {
                return '<span class="provider-badge openai">OpenAI</span>';
            } else if (modelName.toLowerCase().includes('claude') || modelName.toLowerCase().includes('anthropic')) {
                return '<span class="provider-badge anthropic">Anthropic</span>';
            } else if (modelName.toLowerCase().includes('gemini') || modelName.toLowerCase().includes('google')) {
                return '<span class="provider-badge google">Google</span>';
            }
            return '';
        }
        
        function formatModelName(username) {
            // Clean up model names for better display
            return username
                .replace(/^(GPT|Claude|Gemini)-/, '$1 ')
                .replace(/-/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());
        }
        
        function populateFormatFilter(availableFormats) {
            const select = document.getElementById('format-filter');
            select.innerHTML = '';
            
            availableFormats.forEach(format => {
                const option = document.createElement('option');
                option.value = format;
                if (format === 'all') {
                    option.textContent = 'All Modes';
                } else {
                    option.textContent = format.replace('randombattle', ' Random').replace('random', ' Random').replace('gen', 'Gen ');
                }
                if (format === currentFormat) {
                    option.selected = true;
                }
                select.appendChild(option);
            });
        }
        
        function renderLeaderboard(data) {
            if (!data || !data.leaderboard) {
                document.getElementById('leaderboard-content').innerHTML = 
                    '<div class="loading"><div class="loading-spinner"></div>No ranking data available</div>';
                return;
            }
            
            // Update format filter options
            if (data.available_formats) {
                populateFormatFilter(data.available_formats);
            }
            
            const table = `
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>LLM Model</th>
                            <th>ELO</th>
                            <th>Record</th>
                            <th>Win Rate</th>
                            <th>Form</th>
                            <th>Streak</th>
                            <th>Last Battle</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.leaderboard.map(bot => `
                            <tr>
                                <td class="rank rank-${bot.rank}">#${bot.rank}</td>
                                <td class="model-name">
                                    ${formatModelName(bot.username)}
                                    ${getProviderBadge(bot.username)}
                                </td>
                                <td class="elo">${bot.elo_rating}</td>
                                <td class="record">${bot.wins}-${bot.losses}-${bot.draws}</td>
                                <td class="win-rate">${bot.win_rate}%</td>
                                <td class="recent-form">${formatRecentForm(bot.recent_form)}</td>
                                <td>
                                    ${bot.current_streak > 0 ? 
                                        `<span class="streak">${bot.current_streak}W</span>` : 
                                        '<span class="last-battle">-</span>'
                                    }
                                </td>
                                <td class="last-battle">${bot.last_battle}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;
            
            document.getElementById('leaderboard-content').innerHTML = table;
        }
        
        let lastBattleCount = 0;
        
        function updateStats(stats) {
            if (!stats) return;
            
            const currentBattleCount = stats.total_battles || 0;
            
            // Check if battle count increased (new battle completed)
            if (currentBattleCount > lastBattleCount) {
                // Flash the update indicator
                const indicator = document.querySelector('.update-indicator');
                indicator.classList.add('flash');
                setTimeout(() => indicator.classList.remove('flash'), 800);
                
                // Show notification for new battle
                if (lastBattleCount > 0) {  // Don't show on initial load
                    console.log(`🆕 New battle completed! Total battles: ${currentBattleCount}`);
                }
            }
            lastBattleCount = currentBattleCount;
            
            document.getElementById('total-battles').textContent = currentBattleCount;
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
                btn.className = 'btn';
            });
            event.target.className = 'btn btn-primary';
            
            const data = await fetchLeaderboard(type, currentFormat);
            renderLeaderboard(data);
        }
        
        async function filterByFormat() {
            const select = document.getElementById('format-filter');
            currentFormat = select.value;
            
            const data = await fetchLeaderboard(currentSort, currentFormat);
            renderLeaderboard(data);
        }
        
        async function refreshData() {
            const [leaderboardData, statsData] = await Promise.all([
                fetchLeaderboard(currentSort, currentFormat),
                fetchStats()
            ]);
            
            renderLeaderboard(leaderboardData);
            updateStats(statsData);
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 3 seconds for more responsive updates
        setInterval(refreshData, 3000);
        
        // Also check for updates when page becomes visible again
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                refreshData();
            }
        });
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
    battle_format = request.args.get('format', 'all')
    
    leaderboard = leaderboard_manager.get_leaderboard(sort_by, limit, battle_format)
    
    return jsonify({
        'leaderboard': [asdict(entry) for entry in leaderboard],
        'sort_by': sort_by,
        'battle_format': battle_format,
        'total_bots': len(leaderboard_manager.bot_stats),
        'available_formats': ['all'] + SUPPORTED_RANDOM_BATTLE_FORMATS
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
        new_battles = 0
        updated_bots = 0
        
        if 'bot_stats' in data:
            for username, stats_data in data['bot_stats'].items():
                # Remove username from stats_data if it exists to avoid duplicate
                stats_copy = stats_data.copy()
                stats_copy.pop('username', None)
                leaderboard_manager.bot_stats[username] = BotStats(
                    username=username,
                    **stats_copy
                )
                updated_bots += 1
        
        if 'battle_results' in data:
            for result_data in data['battle_results']:
                try:
                    result = BattleResult(**result_data)
                    # Check if this battle is already recorded
                    existing_ids = {b.battle_id for b in leaderboard_manager.battle_history}
                    if result.battle_id not in existing_ids:
                        leaderboard_manager.battle_history.append(result)
                        new_battles += 1
                except Exception as e:
                    print(f"Error processing battle result: {e}")
                    continue
        
        leaderboard_manager.save_data()
        
        # Log successful update
        total_battles = data.get('total_battles', len(leaderboard_manager.battle_history))
        timestamp = data.get('timestamp', 'unknown')
        print(f"📊 Leaderboard updated: {updated_bots} bots, {new_battles} new battles (Total: {total_battles})")
        
        return jsonify({
            'status': 'success',
            'new_battles': new_battles,
            'updated_bots': updated_bots,
            'total_battles': total_battles
        })
        
    except Exception as e:
        print(f"❌ Error updating leaderboard: {e}")
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