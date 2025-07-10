# LLM Pokemon Showdown Bot

An AI-powered Pokemon Showdown bot system that uses Large Language Models to make strategic decisions in Pokemon battles.

## 🚀 Quick Start

### All-in-One Setup
```bash
./scripts/run_all.sh
```

This single command will:
- Install all Python dependencies
- Set up a local Pokemon Showdown server
- Start the server
- Run the bot
- Clean up when you're done

### Single Bot Battle
```bash
python run_bot.py
```

### Bot vs Bot Battles
```bash
# Setup configuration
python run_bot_vs_bot.py --setup

# Run quick battle
python run_bot_vs_bot.py --quick --mode single

# Run tournament
python run_bot_vs_bot.py --mode tournament

# Run continuous matchmaking with leaderboard
python run_bot_vs_bot.py --mode continuous --leaderboard
```

## 📁 Project Structure

The codebase is organized into logical folders for better maintainability:

- **`src/bot/`** - Core bot functionality
- **`src/bot_vs_bot/`** - Bot vs Bot battle system  
- **`src/utils/`** - Shared utilities
- **`tests/`** - Test files
- **`scripts/`** - Shell scripts
- **`docs/`** - Documentation

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed file organization.

## 🎮 Battle Modes

### Single Bot
Play against Pokemon Showdown's ladder or other players.

### Bot vs Bot
- **Single Battle** - One-off matches
- **Tournament** - Round robin, Swiss system, elimination
- **Continuous Matchmaking** - ELO-based ladder system

## 🧠 Supported LLM Providers

- **Google Gemini** - `gemini`
- **OpenAI ChatGPT** - `openai`
- **Anthropic Claude** - `anthropic`
- **Ollama (Local)** - `ollama`
- **Custom OpenAI-compatible** - `custom`
- **Mock LLM** - `mock` (for testing)

## ⚙️ Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# LLM Configuration
LLM_PROVIDER=gemini
USE_MOCK_LLM=false
GEMINI_API_KEY=your_api_key_here

# Pokemon Showdown Configuration
PS_SERVER_URL=http://localhost:8000
PS_USERNAME=YourBotName
PS_BATTLE_FORMAT=gen9randombattle
```

### Bot vs Bot Configuration
```bash
# Generate configuration file
python run_bot_vs_bot.py --setup
```

## 📊 Features

### Real-Time Web Leaderboard
- Live ELO rankings
- Battle statistics
- Win/loss records
- Recent form tracking
- Mobile responsive

### Analytics
- Battle duration analysis
- Move effectiveness tracking
- Format performance metrics
- Tournament brackets
- Export to JSON/CSV

### Battle Formats
- Random battles (Gen 1-9)
- Competitive tiers (OU, UU, Ubers)
- Doubles battles
- Custom formats

## 🛠️ Development

### Testing
```bash
# Test single bot
python test_bot.py

# Test bot vs bot system
python test_bot_vs_bot.py
```

### Adding New LLM Providers
1. Implement client class in `llm_client.py`
2. Add provider selection logic
3. Update environment configuration

### Extending Bot Capabilities
- Modify `state_processor.py` for better prompts
- Enhance `response_parser.py` for natural language
- Add custom battle strategies

## 🐛 Troubleshooting

### Common Issues

**Import errors**
```bash
pip install -r requirements.txt
```

**API key issues**
- Check your API keys in `.env`
- Use `USE_MOCK_LLM=true` for testing

**Connection errors**
- Verify Pokemon Showdown server is running
- Check `PS_SERVER_URL` configuration

**Battle failures**
- Enable debug logging in bot files
- Check logs for parsing issues

### Debug Mode
```bash
python run_bot_vs_bot.py --mode single --verbose
```

## 📈 Performance Tips

- Use faster LLM models for time-sensitive battles
- Monitor API usage and costs
- Adjust concurrent battle limits based on resources
- Use mock LLM for development and testing

## 🤝 Contributing

1. Test changes with both single and bot vs bot modes
2. Ensure compatibility with mock and real LLMs
3. Update documentation for new features
4. Follow existing code patterns

## 📄 License

This project is for educational purposes. Please respect Pokemon Showdown's terms of service when using automated players.

---

For detailed documentation on specific features, see:
- [Bot vs Bot System](README_BOT_VS_BOT.md)
- [Leaderboard Documentation](leaderboardREADME.md)