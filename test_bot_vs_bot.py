"""
Test script for bot vs bot battle system.
Validates components individually before running full system.
"""

import asyncio
import logging
import sys
from unittest.mock import Mock

from bot_manager import BotManager, BotConfig
from bot_matchmaker import BotMatchmaker, MatchRequest, MatchmakingStrategy
from bot_vs_bot_config import BotVsBotConfigManager


async def test_bot_manager():
    """Test basic bot manager functionality."""
    print("Testing BotManager...")
    
    try:
        # Create bot manager
        manager = BotManager("http://localhost:8000")
        
        # Create bot configurations
        config1 = BotConfig(username="TestBot1", use_mock_llm=True)
        config2 = BotConfig(username="TestBot2", use_mock_llm=True)
        
        # This would normally create actual bots, but we'll mock it for testing
        print("✓ BotManager created successfully")
        print("✓ Bot configurations created")
        
        # Test configuration validation
        assert config1.username == "TestBot1"
        assert config1.use_mock_llm == True
        print("✓ Bot configurations validated")
        
        print("BotManager tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ BotManager test failed: {e}")
        return False


def test_matchmaker():
    """Test matchmaker functionality without actual bots."""
    print("\nTesting BotMatchmaker...")
    
    try:
        # Create mock bot manager
        mock_manager = Mock()
        mock_manager.active_bots = {"TestBot1": Mock(), "TestBot2": Mock()}
        
        # Create matchmaker
        matchmaker = BotMatchmaker(mock_manager, MatchmakingStrategy.ELO_BASED)
        
        # Register bots
        matchmaker.register_bot("TestBot1", 1200)
        matchmaker.register_bot("TestBot2", 1250)
        
        # Test bot registration
        assert "TestBot1" in matchmaker.bot_stats
        assert "TestBot2" in matchmaker.bot_stats
        assert matchmaker.bot_stats["TestBot1"].elo_rating == 1200
        print("✓ Bot registration works")
        
        # Test match request creation
        request1 = MatchRequest("TestBot1", "gen9randombattle")
        request2 = MatchRequest("TestBot2", "gen9randombattle")
        
        assert request1.bot_username == "TestBot1"
        assert request2.battle_format == "gen9randombattle"
        print("✓ Match request creation works")
        
        # Test pairing logic
        requests = [request1, request2]
        pairings = matchmaker._create_elo_pairings(requests, "gen9randombattle")
        
        assert len(pairings) == 1
        pairing = pairings[0]
        assert pairing.bot1_username in ["TestBot1", "TestBot2"]
        assert pairing.bot2_username in ["TestBot1", "TestBot2"]
        assert pairing.bot1_username != pairing.bot2_username
        print("✓ ELO pairing logic works")
        
        # Test leaderboard
        leaderboard = matchmaker.get_leaderboard()
        assert len(leaderboard) == 2
        assert leaderboard[0]["elo_rating"] >= leaderboard[1]["elo_rating"]
        print("✓ Leaderboard generation works")
        
        print("BotMatchmaker tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ BotMatchmaker test failed: {e}")
        return False


def test_config_manager():
    """Test configuration management."""
    print("\nTesting BotVsBotConfigManager...")
    
    try:
        # Create config manager
        config_manager = BotVsBotConfigManager("test_config.json")
        
        # Test default configuration
        config = config_manager.config
        assert config.server_url == "http://localhost:8000"
        assert config.matchmaking_strategy == MatchmakingStrategy.ELO_BASED
        print("✓ Default configuration loaded")
        
        # Test bot configuration
        bot_config = BotConfig(username="TestBot", use_mock_llm=True)
        config_manager.add_bot_config(bot_config)
        
        assert len(config_manager.config.bot_configs) == 1
        assert config_manager.config.bot_configs[0].username == "TestBot"
        print("✓ Bot configuration management works")
        
        # Test tournament configuration
        tournament = config_manager.setup_default_tournament()
        assert tournament.name == "Default Bot Tournament"
        assert config_manager.config.tournament_config is not None
        print("✓ Tournament configuration works")
        
        # Test validation
        config_manager.config.bot_configs.append(
            BotConfig(username="TestBot2", use_mock_llm=True)
        )
        issues = config_manager.validate_config()
        assert len(issues) == 0  # Should be valid with 2 bots
        print("✓ Configuration validation works")
        
        # Test summary
        summary = config_manager.get_config_summary()
        assert summary["num_bots"] == 2
        assert summary["config_valid"] == True
        print("✓ Configuration summary works")
        
        print("BotVsBotConfigManager tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ BotVsBotConfigManager test failed: {e}")
        return False


def test_integration():
    """Test integration between components."""
    print("\nTesting component integration...")
    
    try:
        # Create configuration
        config_manager = BotVsBotConfigManager()
        config_manager.config.bot_configs = [
            BotConfig(username="IntegrationBot1", use_mock_llm=True),
            BotConfig(username="IntegrationBot2", use_mock_llm=True)
        ]
        
        # Validate configuration
        issues = config_manager.validate_config()
        assert len(issues) == 0
        print("✓ Configuration validation passed")
        
        # Create mock manager and matchmaker
        mock_manager = Mock()
        mock_manager.active_bots = {
            "IntegrationBot1": Mock(),
            "IntegrationBot2": Mock()
        }
        
        matchmaker = BotMatchmaker(mock_manager, config_manager.config.matchmaking_strategy)
        
        # Register bots
        for bot_config in config_manager.config.bot_configs:
            matchmaker.register_bot(bot_config.username)
        
        assert len(matchmaker.bot_stats) == 2
        print("✓ Bot registration integration works")
        
        # Test match request workflow
        for bot_config in config_manager.config.bot_configs:
            request = MatchRequest(
                bot_username=bot_config.username,
                battle_format=config_manager.config.default_battle_format
            )
            success = matchmaker.add_match_request(request)
            assert success == True
        
        assert len(matchmaker.match_queue) == 2
        print("✓ Match request integration works")
        
        print("Integration tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=== Bot vs Bot System Tests ===\n")
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests
    
    # Run tests
    tests = [
        test_bot_manager,
        test_matchmaker,
        test_config_manager,
        test_integration
    ]
    
    results = []
    for test in tests:
        if asyncio.iscoroutinefunction(test):
            result = await test()
        else:
            result = test()
        results.append(result)
    
    # Summary
    print(f"\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Bot vs bot system is ready.")
        return 0
    else:
        print("✗ Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))