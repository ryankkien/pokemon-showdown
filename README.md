# LLM Pokemon Showdown Bot

An AI-powered Pokemon Showdown bot that uses Large Language Models to make strategic decisions in Pokemon battles.

## Architecture

The bot consists of four main components:
1. **State Processor**: Converts battle state into detailed prompts for the LLM
2. **LLM Client**: Communicates with various LLM APIs (OpenAI, Anthropic, Google Gemini, Ollama, etc.)
3. **Response Parser**: Parses LLM responses into valid game actions
4. **LLMPlayer**: Main bot class that coordinates everything

## Quick Start (All-in-One)

The easiest way to get started:

```bash
./run_all.sh
```

This single command will:
- Install all Python dependencies
- Set up a local Pokemon Showdown server
- Start the server
- Run the bot
- Clean up when you're done

## Manual Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- `LLM_PROVIDER`: Choose your LLM provider (gemini, openai, anthropic, ollama, custom)
- `USE_MOCK_LLM`: Set to "false" to use real LLM, "true" for testing
- `PS_SERVER_URL`: Pokemon Showdown server URL (default: http://localhost:8000)
- `PS_USERNAME`: Your bot's username

### 3. Run with Integrated Server Management

```bash
python run_bot.py
```

This will automatically:
- Set up a local Pokemon Showdown server if needed
- Start the server
- Run the bot
- Stop the server when done

### Alternative: Run Components Separately

If you prefer to manage the server yourself:

```bash
# Terminal 1: Start server
./start_server.sh

# Terminal 2: Run bot
python bot.py
```

### With Real LLM

Choose your preferred LLM provider and configure accordingly:

#### OpenAI (GPT-4, GPT-3.5)
```bash
LLM_PROVIDER=openai
USE_MOCK_LLM=false
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview  # or gpt-3.5-turbo
```

#### Anthropic (Claude)
```bash
LLM_PROVIDER=anthropic  
USE_MOCK_LLM=false
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229  # or claude-3-sonnet-20240229
```

#### Google Gemini
```bash
LLM_PROVIDER=gemini
USE_MOCK_LLM=false
GEMINI_API_KEY=your_gemini_api_key_here
```

#### Ollama (Local Models)
First, install and run Ollama:
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Configure bot
LLM_PROVIDER=ollama
USE_MOCK_LLM=false
OLLAMA_MODEL=llama2  # or any model you've pulled
```

#### Custom OpenAI-Compatible API
For any service that provides an OpenAI-compatible API:
```bash
LLM_PROVIDER=custom
USE_MOCK_LLM=false
LLM_API_KEY=your_api_key
LLM_MODEL=your_model_name
LLM_BASE_URL=https://your-api-endpoint.com/v1
```

After configuring your provider, run:
```bash
python bot.py
```

### Testing Components

Test individual components without connecting to a server:
```bash
python test_bot.py
```

## How It Works

### 1. State Processing
The bot analyzes the current battle state and creates a detailed prompt including:
- Your active Pokemon's stats, moves, HP, and status
- Opponent's known information
- Available moves and switches
- Field conditions (weather, terrain, hazards)
- Strategic considerations

### 2. LLM Decision Making
The prompt is sent to the LLM which analyzes the situation and suggests the best action in a structured format:

```
action: move
value: flamethrower
reasoning: Super effective against opponent's Grass-type Pokemon
```

### 3. Response Parsing
The bot parses the LLM response using:
- Structured parsing for the expected format
- Fuzzy parsing for natural language responses
- Validation against available actions
- Fallback to safe moves if parsing fails

### 4. Action Execution
The validated action is converted to a poke-env command and sent to the Pokemon Showdown server.

## File Structure

- `bot.py` - Main bot implementation with LLMPlayer class
- `state_processor.py` - Converts battle state to LLM prompts
- `llm_client.py` - Handles LLM API communication
- `response_parser.py` - Parses LLM responses into actions
- `test_bot.py` - Component testing script
- `requirements.txt` - Python dependencies
- `.env.example` - Environment configuration template

## Configuration Options

### LLM Settings
- **Temperature**: Controls randomness (0.0 = deterministic, 1.0 = creative)
- **Max Tokens**: Maximum response length
- **Top-p/Top-k**: Controls response diversity

### Bot Settings
- **Battle Format**: Currently supports "gen8randombattle"
- **Concurrent Battles**: Number of simultaneous battles (recommended: 1)
- **Ladder Games**: Number of games to play in ladder mode

## Extending the Bot

### Adding New LLM Providers
1. Implement a new client class in `llm_client.py`
2. Add provider selection logic in `create_llm_client()`
3. Update environment configuration

### Improving Prompts
Modify `state_processor.py` to include additional battle information:
- Move effectiveness calculations
- Advanced stat calculations
- Historical battle data
- Team composition analysis

### Enhanced Parsing
Extend `response_parser.py` to handle:
- More natural language variations
- Multi-step strategies
- Conditional actions

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'google.generativeai'**
   - Run: `pip install google-generativeai`

2. **LLM client is not available**
   - Check your `GEMINI_API_KEY` in `.env`
   - Or set `USE_MOCK_LLM=true` for testing

3. **Connection errors**
   - Verify `PS_SERVER_URL` is correct
   - Check if Pokemon Showdown server is running

4. **Invalid moves**
   - The bot includes fallback logic for invalid actions
   - Check logs for parsing issues

### Debug Mode

Enable detailed logging by modifying the logging level in `bot.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Performance Considerations

- LLM API calls add latency (~1-3 seconds per decision)
- Consider using faster models for time-sensitive battles
- Monitor API usage and costs
- The mock LLM is much faster for development/testing

## Contributing

To contribute:
1. Test your changes with `python test_bot.py`
2. Ensure the bot works with both mock and real LLM
3. Update documentation for new features
4. Follow the existing code structure and patterns

## License

This project is for educational purposes. Please respect Pokemon Showdown's terms of service when using automated players.