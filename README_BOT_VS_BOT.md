# Bot vs Bot Battle System

A comprehensive system for running Pokemon Showdown bot battles with advanced matchmaking, tournaments, and analytics.

## 🚀 Quick Start

### 1. Setup Configuration
```bash
python run_bot_vs_bot.py --setup
```

### 2. Run Quick Battle
```bash
python run_bot_vs_bot.py --quick --mode single
```

### 3. Run Tournament
```bash
python run_bot_vs_bot.py --mode tournament
```

### 4. Run Continuous Matchmaking
```bash
python run_bot_vs_bot.py --mode continuous
```

## 📁 System Components

### Core Files
- **`bot_manager.py`** - Manages multiple bot instances and coordinates battles
- **`bot_matchmaker.py`** - Advanced matchmaking with ELO ratings and multiple strategies
- **`bot_vs_bot_config.py`** - Configuration management for tournaments and battles
- **`run_bot_vs_bot.py`** - Main script with CLI interface
- **`test_bot_vs_bot.py`** - Test suite for all components

### Configuration
- **`bot_vs_bot_config.json`** - Main configuration file (created by --setup)
- **`results/`** - Directory for battle results and statistics

## 🎮 Battle Modes

### Single Battle
Run a one-off battle between two bots:
```bash
python run_bot_vs_bot.py --mode single
```

### Tournament
Run structured tournaments with multiple bots:
- **Round Robin** - Every bot plays every other bot
- **Swiss System** - Pair bots with similar records
- **Single/Double Elimination** - Bracket-style tournaments

### Continuous Matchmaking
Run an ongoing ladder system with ELO ratings:
```bash
python run_bot_vs_bot.py --mode continuous
```

## 🧠 Bot Types

The system supports multiple LLM-powered bots:

- **GeminiBot** - Google Gemini powered
- **OpenAIBot** - ChatGPT powered  
- **AnthropicBot** - Claude powered
- **OllamaBot** - Local Ollama models
- **MockBot** - Testing without API calls

## ⚙️ Configuration

### Bot Configuration
```python
BotConfig(
    username="MyBot",
    battle_format="gen9randombattle", 
    use_mock_llm=True,
    llm_provider="gemini",
    max_concurrent_battles=1,
    custom_config={"initial_elo": 1200}
)
```

### Tournament Configuration
```python
TournamentConfig(
    name="My Tournament",
    tournament_type=TournamentType.ROUND_ROBIN,
    battle_format="gen9randombattle",
    max_participants=8,
    concurrent_battles=2,
    save_replays=True
)
```

### Matchmaking Strategies
- **ELO_BASED** - Match bots with similar ratings
- **SWISS_SYSTEM** - Pair by win/loss record
- **RANDOM_PAIRING** - Random matchups
- **ROUND_ROBIN** - Systematic all-vs-all

## 📊 Analytics & Results

### Battle Statistics
- Win/Loss records
- ELO ratings
- Battle duration
- Move analysis
- Format performance

### Leaderboards
Real-time rankings by:
- ELO rating
- Win percentage
- Total battles
- Recent performance

### Export Formats
- JSON battle logs
- CSV statistics
- Tournament brackets
- Performance graphs

## 🔧 Advanced Features

### Multi-Format Support
- Random battles (Gen 1-9)
- OU/Ubers/UU tiers
- Doubles battles
- Custom formats

### Battle Coordination
- Challenge system
- Private rooms
- Ladder integration
- Queue management

### Resource Management
- Concurrent battle limits
- API rate limiting
- Memory optimization
- Graceful shutdown

## 🛠️ Development

### Running Tests
```bash
python test_bot_vs_bot.py
```

### Adding New Bots
1. Create `BotConfig` with unique username
2. Set LLM provider and parameters
3. Add to configuration
4. Register with matchmaker

### Custom Matchmaking
Extend `BotMatchmaker` class:
```python
def _create_custom_pairings(self, requests, battle_format):
    # Your custom pairing logic
    return pairings
```

## 🚦 Usage Examples

### Quick 2-Bot Battle
```bash
# Setup and run quick battle
python run_bot_vs_bot.py --quick --mode single --verbose
```

### 4-Bot Tournament
```bash
# Setup configuration
python run_bot_vs_bot.py --setup

# Run tournament
python run_bot_vs_bot.py --mode tournament
```

### ELO Ladder System
```bash
# Continuous matchmaking with ELO
python run_bot_vs_bot.py --mode continuous --verbose
```

### Custom Configuration
```python
from bot_vs_bot_config import BotVsBotConfigManager, BotConfig

config = BotVsBotConfigManager()
config.add_bot_config(BotConfig(
    username="CustomBot",
    battle_format="gen8ou",
    use_mock_llm=False,
    llm_provider="openai"
))
config.save_config()
```

## 📈 Performance Tuning

### Concurrent Battles
Adjust `max_concurrent_battles` based on:
- Server capacity
- API rate limits
- Memory usage

### Matchmaking Intervals
Balance between:
- Quick pairing (fast battles)
- Quality matches (better ELO matching)

### Battle Timeouts
Set appropriate limits:
- Fast formats: 300-600 seconds
- Complex formats: 900-1800 seconds

## 🐛 Troubleshooting

### Common Issues

**Bot Connection Fails**
- Check Pokemon Showdown server is running
- Verify websocket URL configuration
- Check firewall/network settings

**No Battles Starting**
- Ensure 2+ bots configured
- Check bot usernames are unique
- Verify battle format is valid

**LLM API Errors**
- Use `use_mock_llm=True` for testing
- Check API keys and rate limits
- Monitor error logs

### Debug Mode
```bash
python run_bot_vs_bot.py --mode single --verbose
```

## 🤝 Contributing

1. Run tests: `python test_bot_vs_bot.py`
2. Add new features to appropriate modules
3. Update configuration schemas
4. Document new functionality
5. Test with multiple bot types

## 📄 License

Same as Pokemon Showdown project license.