# Pokemon Showdown Bot vs Bot Battle System

A comprehensive system for running AI model battles in Pokemon Showdown with real-time leaderboard tracking.

## Overview

This system allows multiple AI models from different providers (Anthropic, OpenAI, Google) to battle against each other in Pokemon Showdown, with ELO ratings, tournament modes, and a web-based leaderboard.

## Prerequisites

- Python 3.8+
- Node.js (for Pokemon Showdown server)
- API keys for AI providers (Anthropic, OpenAI, Google)

## Setup

### 1. Environment Configuration

Create/update your `.env` file with API keys:

```env
# Gemini Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Pokemon Showdown Server Configuration
PS_SERVER_URL=http://localhost:8000
PS_BATTLE_FORMAT=gen9randombattle
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Pokemon Showdown Server

```bash
# Setup the server (first time only)
./setup_server.sh

# Start the server
./start_server.sh
```

### 4. Initialize Bot Configuration

```bash
python run_bot_vs_bot.py --setup
```

## Current Bot Configuration

The system is configured with 9 AI models:

### Anthropic Models
- **Claude3Opus** (`claude-3-opus-20240229`) - Most capable
- **Claude3Sonnet** (`claude-3-sonnet-20240229`) - Balanced
- **Claude3Haiku** (`claude-3-haiku-20240307`) - Fast

### OpenAI Models
- **GPT4Turbo** (`gpt-4-turbo-preview`) - Latest
- **GPT4** (`gpt-4`) - Standard
- **GPT35Turbo** (`gpt-3.5-turbo`) - Fast

### Google Gemini Models
- **GeminiPro** (`gemini-pro`) - Advanced
- **Gemini15Pro** (`gemini-1.5-pro`) - Latest
- **Gemini15Flash** (`gemini-1.5-flash`) - Fast

## Running Battles

### Quick Single Battle

```bash
python run_bot_vs_bot.py --quick --mode single
```

### Tournament Mode (Recommended)

Run a complete round-robin tournament with all 9 models:

```bash
python run_bot_vs_bot.py --mode tournament
```

### Continuous Matchmaking with ELO Ladder

```bash
python run_bot_vs_bot.py --mode continuous
```

### With Web Leaderboard

```bash
python run_bot_vs_bot.py --mode continuous --leaderboard
```

Access the leaderboard at: `http://localhost:5000`

### Standalone Leaderboard Server

```bash
python leaderboard_server.py --data-file demo_leaderboard_data.json
```

## Battle Results

Results are automatically saved to the `results/` directory with timestamps:

- Battle logs with detailed match information
- ELO ratings and statistics
- Leaderboard data
- Matchmaking history

## Web Leaderboard Features

- **Real-time Updates**: Live battle results and rankings
- **ELO Tracking**: Dynamic rating system
- **Battle History**: Detailed match logs
- **Model Statistics**: Win rates, average battle duration
- **Interactive Interface**: Sort by different metrics

## Tournament Configuration

The system supports various tournament types:

- **Round Robin**: Every bot plays every other bot
- **Swiss System**: Pairing based on current standings
- **Elimination**: Single/double elimination brackets

Current settings:
- Max participants: 9
- Concurrent battles: 3
- Battle timeout: 600 seconds
- Auto-save results: enabled

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all API keys are valid in `.env`
2. **Server Connection**: Verify Pokemon Showdown server is running on localhost:8000
3. **Model Availability**: Check that specified models are available for your API keys

### Verbose Output

Add `--verbose` flag to any command for detailed logging:

```bash
python run_bot_vs_bot.py --mode tournament --verbose
```

### Server Restart

If battles hang or fail:

```bash
# Stop server
pkill -f "node pokemon-showdown"

# Restart server
./start_server.sh
```

## Configuration Files

- `bot_vs_bot_config.json`: Main configuration
- `.env`: API keys and environment variables
- `requirements.txt`: Python dependencies

## Advanced Usage

### Custom Battle Formats

Edit `bot_vs_bot_config.json` to change battle format:

```json
{
  "default_battle_format": "gen9ou",
  "bot_configs": [
    {
      "battle_format": "gen9ou"
    }
  ]
}
```

### ELO System Configuration

Modify ELO settings in configuration:

```json
{
  "matchmaking_strategy": "elo_based",
  "elo_threshold": 200,
  "min_wait_time": 30.0
}
```

### Adding New Models

Add new bot configurations:

```json
{
  "username": "NewModel",
  "battle_format": "gen9randombattle",
  "use_mock_llm": false,
  "llm_provider": "openai",
  "model": "gpt-4o",
  "max_concurrent_battles": 1,
  "custom_config": {
    "description": "New GPT-4o model"
  }
}
```

## Performance Optimization

- Adjust `max_concurrent_battles` based on API rate limits
- Use faster models for continuous matchmaking
- Monitor API usage to avoid quota limits

## Results Analysis

Battle results include:
- Winner determination
- Battle duration
- Move choices and reasoning
- ELO rating changes
- Statistical summaries

## Support

For issues or questions:
1. Check verbose output for detailed error messages
2. Verify API key validity and quotas
3. Ensure server connectivity
4. Review configuration file syntax