# Real-Time Leaderboard Setup Instructions

The leaderboard website has been enhanced with real-time auto-updates that refresh every 3 seconds and show visual indicators when new battles complete.

## Quick Start

1. **Start the Leaderboard Server:**
   ```bash
   python pokemon_bot.py leaderboard
   # Or with custom port if 5000 is in use:
   python -m src.bot_vs_bot.leaderboard_server --port 5001
   ```

2. **Open the Web Interface:**
   Open your browser to http://localhost:5001 (or whatever port you used)

3. **Start Bot Battles:**
   ```bash
   python pokemon_bot.py vs
   ```

## Auto-Update Features

✅ **Every 3 seconds**: Page automatically refreshes data from server
✅ **Visual flash**: Green dot flashes red/orange when new battles complete  
✅ **Real-time stats**: Battle count, ELO changes, win streaks update immediately
✅ **Connection resilience**: Retry logic handles temporary server issues
✅ **Persistence**: All stats persist across sessions and bot restarts

## What You Should See

When battles are running, you should observe:

1. **Battle counter increasing** in real-time as fights complete
2. **ELO ratings changing** after each battle result
3. **Visual flash indicator** when new data arrives
4. **Leaderboard rankings** automatically reordering
5. **Recent form** (W/L/D) updating with latest results

## Troubleshooting

**No updates showing?**
- Check that both leaderboard server and bot battles are running
- Look for "✓ Real-time update sent to web leaderboard" messages in bot output
- Check browser developer console (F12) for any errors

**Port 5000 in use?**
- Use a different port: `--port 5001` 
- Update bot battle system to use same port
- On macOS, disable AirPlay Receiver in System Preferences > Sharing

**Data seems wrong?**
- Run: `python pokemon_bot.py fix-leaderboard` to recalculate stats
- Check `leaderboard_data.json` for any corruption

## Technical Details

The system uses:
- **HTTP POST** to `/api/update` for real-time data transmission
- **3-second polling** of `/api/stats` and `/api/leaderboard` endpoints  
- **Retry logic** with exponential backoff for failed updates
- **Battle deduplication** to prevent double-counting results
- **Persistent storage** in `leaderboard_data.json`

The leaderboard will continue showing the latest data even if bot battles stop, and new battles will immediately appear when they start again.