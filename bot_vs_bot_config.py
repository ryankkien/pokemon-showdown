"""
Configuration system for bot vs bot battles.
Handles tournament setups, bot configurations, and battle parameters.
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from bot_manager import BotConfig
from bot_matchmaker import MatchmakingStrategy


class TournamentType(Enum):
    """Different tournament formats."""
    ROUND_ROBIN = "round_robin"
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    SWISS = "swiss"
    LADDER = "ladder"
    CUSTOM = "custom"


@dataclass
class TournamentConfig:
    """Configuration for a tournament."""
    name: str
    tournament_type: TournamentType
    battle_format: str = "gen9randombattle"
    max_participants: int = 8
    rounds: Optional[int] = None  # For Swiss/custom tournaments
    time_limit_per_battle: int = 600  # 10 minutes
    concurrent_battles: int = 2
    save_replays: bool = True
    description: str = ""
    
    def __post_init__(self):
        if self.rounds is None:
            if self.tournament_type == TournamentType.SWISS:
                # Swiss tournaments typically have log2(n) + 1 rounds
                import math
                self.rounds = max(3, int(math.log2(self.max_participants)) + 1)
            elif self.tournament_type == TournamentType.ROUND_ROBIN:
                self.rounds = self.max_participants - 1
            else:
                self.rounds = 1


@dataclass
class BotVsBotConfig:
    """Main configuration for bot vs bot battle system."""
    
    # Server settings
    server_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8000/showdown/websocket"
    
    # Matchmaking settings
    matchmaking_strategy: MatchmakingStrategy = MatchmakingStrategy.ELO_BASED
    elo_threshold: int = 200
    min_wait_time: float = 30.0
    max_queue_size: int = 100
    
    # Battle settings
    default_battle_format: str = "gen9randombattle"
    max_concurrent_battles: int = 3
    battle_timeout: int = 600  # 10 minutes
    auto_save_results: bool = True
    
    # Bot settings
    bot_configs: List[BotConfig] = None
    
    # Tournament settings
    tournament_config: Optional[TournamentConfig] = None
    
    # File paths
    results_dir: str = "./results"
    config_file: str = "./bot_vs_bot_config.json"
    
    def __post_init__(self):
        if self.bot_configs is None:
            self.bot_configs = []
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)


class BotVsBotConfigManager:
    """Manages bot vs bot battle configurations."""
    
    def __init__(self, config_file: str = "bot_vs_bot_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> BotVsBotConfig:
        """Load configuration from file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Convert dictionaries back to dataclasses
                config = BotVsBotConfig()
                
                # Update basic fields
                for key, value in data.items():
                    if key == "matchmaking_strategy":
                        config.matchmaking_strategy = MatchmakingStrategy(value)
                    elif key == "bot_configs":
                        config.bot_configs = [
                            BotConfig(**bot_data) for bot_data in value
                        ]
                    elif key == "tournament_config" and value:
                        config.tournament_config = TournamentConfig(
                            name=value["name"],
                            tournament_type=TournamentType(value["tournament_type"]),
                            **{k: v for k, v in value.items() 
                               if k not in ["name", "tournament_type"]}
                        )
                    elif hasattr(config, key):
                        setattr(config, key, value)
                
                return config
                
            except Exception as e:
                print(f"Error loading config: {e}")
                return BotVsBotConfig()
        
        return BotVsBotConfig()
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Convert dataclasses to dictionaries
            data = asdict(self.config)
            
            # Convert enums to strings
            if "matchmaking_strategy" in data:
                data["matchmaking_strategy"] = data["matchmaking_strategy"].value
            
            if data.get("tournament_config"):
                data["tournament_config"]["tournament_type"] = data["tournament_config"]["tournament_type"].value
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def add_bot_config(self, bot_config: BotConfig):
        """Add a bot configuration."""
        self.config.bot_configs.append(bot_config)
    
    def remove_bot_config(self, username: str) -> bool:
        """Remove a bot configuration by username."""
        original_length = len(self.config.bot_configs)
        self.config.bot_configs = [
            bot for bot in self.config.bot_configs 
            if bot.username != username
        ]
        return len(self.config.bot_configs) < original_length
    
    def get_bot_config(self, username: str) -> Optional[BotConfig]:
        """Get bot configuration by username."""
        for bot in self.config.bot_configs:
            if bot.username == username:
                return bot
        return None
    
    def create_tournament_config(self, name: str, tournament_type: TournamentType, 
                               **kwargs) -> TournamentConfig:
        """Create and set tournament configuration."""
        tournament_config = TournamentConfig(
            name=name,
            tournament_type=tournament_type,
            **kwargs
        )
        self.config.tournament_config = tournament_config
        return tournament_config
    
    def get_default_bot_configs(self) -> List[BotConfig]:
        """Get default bot configurations for testing."""
        return [
            BotConfig(
                username="Gemini-1.5-Flash",
                battle_format="gen9randombattle",
                use_mock_llm=True,
                llm_provider="gemini",
                custom_config={"description": "Google Gemini 1.5 Flash model"}
            ),
            BotConfig(
                username="GPT-4-Turbo",
                battle_format="gen9randombattle", 
                use_mock_llm=True,
                llm_provider="openai",
                custom_config={"description": "OpenAI GPT-4 Turbo model"}
            ),
            BotConfig(
                username="Claude-3-Opus",
                battle_format="gen9randombattle",
                use_mock_llm=True,
                llm_provider="anthropic",
                custom_config={"description": "Anthropic Claude 3 Opus model"}
            ),
            BotConfig(
                username="Llama2-Local",
                battle_format="gen9randombattle",
                use_mock_llm=True,
                llm_provider="ollama",
                custom_config={"description": "Meta Llama 2 via Ollama"}
            )
        ]
    
    def setup_default_tournament(self) -> TournamentConfig:
        """Setup a default tournament configuration."""
        return self.create_tournament_config(
            name="Default Bot Tournament",
            tournament_type=TournamentType.ROUND_ROBIN,
            battle_format="gen9randombattle",
            max_participants=4,
            concurrent_battles=2,
            description="Default tournament with mock LLM bots"
        )
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check server settings
        if not self.config.server_url:
            issues.append("Server URL is required")
        
        # Check bot configurations
        if not self.config.bot_configs:
            issues.append("At least one bot configuration is required")
        
        usernames = [bot.username for bot in self.config.bot_configs]
        if len(usernames) != len(set(usernames)):
            issues.append("Bot usernames must be unique")
        
        # Check tournament configuration
        if self.config.tournament_config:
            if len(self.config.bot_configs) < 2:
                issues.append("Tournament requires at least 2 bots")
            
            if len(self.config.bot_configs) > self.config.tournament_config.max_participants:
                issues.append("More bots configured than tournament allows")
        
        return issues
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        issues = self.validate_config()
        
        return {
            "server_url": self.config.server_url,
            "matchmaking_strategy": self.config.matchmaking_strategy.value,
            "battle_format": self.config.default_battle_format,
            "num_bots": len(self.config.bot_configs),
            "bot_usernames": [bot.username for bot in self.config.bot_configs],
            "tournament_configured": self.config.tournament_config is not None,
            "tournament_name": self.config.tournament_config.name if self.config.tournament_config else None,
            "tournament_type": self.config.tournament_config.tournament_type.value if self.config.tournament_config else None,
            "config_valid": len(issues) == 0,
            "validation_issues": issues
        }


# Predefined configurations
def create_quick_battle_config() -> BotVsBotConfig:
    """Create configuration for quick bot vs bot battles."""
    config = BotVsBotConfig()
    config.bot_configs = [
        BotConfig(username="GPT-4-Quick", use_mock_llm=True, llm_provider="openai"),
        BotConfig(username="Claude-3-Quick", use_mock_llm=True, llm_provider="anthropic")
    ]
    return config


def create_tournament_config() -> BotVsBotConfig:
    """Create configuration for a tournament."""
    config = BotVsBotConfig()
    
    # Add multiple bots with model names
    config.bot_configs = [
        BotConfig(username="GPT-4-Turbo", use_mock_llm=True, llm_provider="openai"),
        BotConfig(username="Claude-3-Opus", use_mock_llm=True, llm_provider="anthropic"),
        BotConfig(username="Gemini-1.5-Flash", use_mock_llm=True, llm_provider="gemini"),
        BotConfig(username="Llama2-Local", use_mock_llm=True, llm_provider="ollama")
    ]
    
    # Configure tournament
    config.tournament_config = TournamentConfig(
        name="Test Tournament",
        tournament_type=TournamentType.ROUND_ROBIN,
        battle_format="gen9randombattle",
        max_participants=4,
        concurrent_battles=2
    )
    
    return config


def create_elo_ladder_config() -> BotVsBotConfig:
    """Create configuration for ELO-based ladder system."""
    config = BotVsBotConfig()
    config.matchmaking_strategy = MatchmakingStrategy.ELO_BASED
    config.elo_threshold = 150
    
    # Add bots with different initial ELO ratings
    config.bot_configs = [
        BotConfig(username="Beginner", use_mock_llm=True, custom_config={"initial_elo": 1000}),
        BotConfig(username="Intermediate", use_mock_llm=True, custom_config={"initial_elo": 1200}),
        BotConfig(username="Advanced", use_mock_llm=True, custom_config={"initial_elo": 1400}),
        BotConfig(username="Expert", use_mock_llm=True, custom_config={"initial_elo": 1600})
    ]
    
    return config


def main():
    """Example usage of configuration system."""
    # Create config manager
    config_manager = BotVsBotConfigManager()
    
    # Setup default configuration
    config_manager.config.bot_configs = config_manager.get_default_bot_configs()
    config_manager.setup_default_tournament()
    
    # Save configuration
    config_manager.save_config()
    
    # Print summary
    summary = config_manager.get_config_summary()
    print("Bot vs Bot Configuration Summary:")
    print(f"Server: {summary['server_url']}")
    print(f"Matchmaking: {summary['matchmaking_strategy']}")
    print(f"Battle Format: {summary['battle_format']}")
    print(f"Bots: {summary['num_bots']} ({', '.join(summary['bot_usernames'])})")
    print(f"Tournament: {summary['tournament_name']} ({summary['tournament_type']})")
    print(f"Valid: {summary['config_valid']}")
    
    if summary['validation_issues']:
        print("Issues:")
        for issue in summary['validation_issues']:
            print(f"  - {issue}")


if __name__ == "__main__":
    main()