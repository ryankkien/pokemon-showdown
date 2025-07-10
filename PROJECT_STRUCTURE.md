# Project Structure

```
pokemon-showdown/
├── src/                        # Source code
│   ├── bot/                   # Core bot functionality
│   │   ├── bot.py            # Main bot implementation (LLMPlayer)
│   │   ├── state_processor.py # Battle state → LLM prompt conversion
│   │   ├── llm_client.py     # LLM API client implementations
│   │   ├── response_parser.py # Parse LLM responses → game actions
│   │   ├── run_bot.py        # Bot runner with server management
│   │   └── play_format.py    # Format selection helper
│   │
│   ├── bot_vs_bot/           # Bot vs Bot battle system
│   │   ├── bot_manager.py    # Manages multiple bot instances
│   │   ├── bot_matchmaker.py # ELO matchmaking system
│   │   ├── bot_vs_bot_config.py # Configuration management
│   │   ├── run_bot_vs_bot.py # Main bot vs bot runner
│   │   ├── leaderboard_server.py # Web leaderboard server
│   │   └── demo_leaderboard.py # Generate demo data
│   │
│   └── utils/                # Shared utilities
│       ├── logging_config.py # Enhanced logging setup
│       └── battle_tracker.py # Battle statistics tracking
│
├── tests/                     # Test files
│   ├── test_bot.py          # Bot component tests
│   └── test_bot_vs_bot.py   # Bot vs Bot system tests
│
├── scripts/                   # Shell scripts
│   ├── run_all.sh           # All-in-one runner
│   ├── setup_server.sh      # Server setup script
│   └── start_server.sh      # Server start script
│
├── docs/                      # Documentation
│   ├── README_BOT_VS_BOT.md # Bot vs Bot documentation
│   └── leaderboardREADME.md # Leaderboard documentation
│
├── server/                    # Pokemon Showdown server (gitignored)
│   └── pokemon-showdown/    # Server files
│
├── results/                   # Battle results (gitignored)
├── battle_analysis/          # Battle analysis files (gitignored)
│
├── README.md                 # Main documentation
├── CLAUDE.md                # Claude-specific instructions
├── PROJECT_STRUCTURE.md     # This file
├── requirements.txt         # Python dependencies
├── requirements_leaderboard.txt # Leaderboard dependencies
├── package.json             # npm metadata
├── .env.example             # Environment variable template
├── .gitignore              # Git ignore file
│
└── Root wrapper scripts:     # Convenience wrappers
    ├── run_bot.py          # Wrapper for src/bot/run_bot.py
    ├── run_bot_vs_bot.py   # Wrapper for src/bot_vs_bot/run_bot_vs_bot.py
    ├── play_format.py      # Wrapper for src/bot/play_format.py
    ├── leaderboard_server.py # Wrapper for src/bot_vs_bot/leaderboard_server.py
    ├── demo_leaderboard.py # Wrapper for src/bot_vs_bot/demo_leaderboard.py
    ├── test_bot.py         # Wrapper for tests/test_bot.py
    └── test_bot_vs_bot.py  # Wrapper for tests/test_bot_vs_bot.py
```

## Quick Commands

From the root directory:

```bash
# Run single bot
python run_bot.py

# Run bot vs bot battles
python run_bot_vs_bot.py

# Run tests
python test_bot.py
python test_bot_vs_bot.py

# Run leaderboard
python leaderboard_server.py

# Play specific format
python play_format.py gen1

# All-in-one setup and run
./scripts/run_all.sh
```