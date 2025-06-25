"""
Test script for the LLM Pokemon Showdown Bot
Tests individual components without requiring a Pokemon Showdown server.
"""

import asyncio
import logging
from unittest.mock import MagicMock

from state_processor import StateProcessor
from llm_client import MockLLMClient
from response_parser import ResponseParser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mock_battle():
    """Create a mock battle object for testing."""
    battle = MagicMock()
    battle.battle_tag = "test-battle"
    battle.turn = 1
    
    # Mock active Pokemon
    battle.active_pokemon = MagicMock()
    battle.active_pokemon.species = "Charizard"
    battle.active_pokemon.level = 100
    battle.active_pokemon.current_hp_fraction = 0.85
    battle.active_pokemon.status = None
    # Create proper type mocks
    fire_type = MagicMock()
    fire_type.name = "FIRE"
    flying_type = MagicMock()
    flying_type.name = "FLYING"
    battle.active_pokemon.types = [fire_type, flying_type]
    battle.active_pokemon.ability = "Blaze"
    battle.active_pokemon.moves = {}
    battle.active_pokemon.boosts = {}
    
    # Mock opponent Pokemon
    battle.opponent_active_pokemon = MagicMock()
    battle.opponent_active_pokemon.species = "Blastoise"
    battle.opponent_active_pokemon.level = 100
    battle.opponent_active_pokemon.current_hp_fraction = 0.70
    battle.opponent_active_pokemon.status = None
    # Create proper type mock
    water_type = MagicMock()
    water_type.name = "WATER"
    battle.opponent_active_pokemon.types = [water_type]
    battle.opponent_active_pokemon.ability = "Torrent"
    battle.opponent_active_pokemon.moves = {}
    battle.opponent_active_pokemon.boosts = {}
    
    # Mock available moves
    mock_move = MagicMock()
    mock_move.id = "flamethrower"
    # Create proper move type and category mocks
    move_type = MagicMock()
    move_type.name = "FIRE"
    move_category = MagicMock()
    move_category.name = "SPECIAL"
    mock_move.type = move_type
    mock_move.category = move_category
    mock_move.base_power = 90
    mock_move.accuracy = 100
    mock_move.pp = 15
    mock_move.current_pp = 15
    mock_move.effect = "May burn the target"
    
    battle.available_moves = [mock_move]
    
    # Mock available switches
    mock_switch = MagicMock()
    mock_switch.species = "Pikachu"
    mock_switch.current_hp_fraction = 1.0
    mock_switch.status = None
    
    battle.available_switches = [mock_switch]
    
    # Mock team and field conditions
    battle.team = {}
    battle.opponent_team = {}
    battle.weather = None
    battle.fields = []
    battle.side_conditions = []
    battle.opponent_side_conditions = []
    
    return battle


async def test_state_processor():
    """Test the state processor."""
    logger.info("Testing State Processor...")
    
    processor = StateProcessor()
    battle = create_mock_battle()
    
    prompt = processor.create_battle_prompt(battle)
    
    logger.info("Generated prompt:")
    logger.info("=" * 50)
    logger.info(prompt)
    logger.info("=" * 50)
    
    assert "Charizard" in prompt
    assert "Blastoise" in prompt
    assert "flamethrower" in prompt.lower()
    assert "action:" in prompt.lower()
    
    logger.info("State Processor test passed!")


async def test_llm_client():
    """Test the LLM client."""
    logger.info("Testing LLM Client...")
    
    client = MockLLMClient()
    
    test_prompt = "Test prompt with charizard"
    response = await client.get_decision(test_prompt)
    
    logger.info(f"LLM Response: {response}")
    
    assert response.success
    assert "action:" in response.content
    assert "flamethrower" in response.content.lower()
    
    logger.info("LLM Client test passed!")


async def test_response_parser():
    """Test the response parser."""
    logger.info("Testing Response Parser...")
    
    parser = ResponseParser()
    battle = create_mock_battle()
    
    # Test structured response
    structured_response = """action: move
value: flamethrower
reasoning: Super effective against opponent"""
    
    action, value = parser.parse_response(structured_response, battle)
    logger.info(f"Structured parsing result: {action} -> {value}")
    
    assert action == "move"
    assert value == "flamethrower"
    
    # Test fuzzy response
    fuzzy_response = "I think we should use flamethrower to attack the opponent"
    action, value = parser.parse_response(fuzzy_response, battle)
    logger.info(f"Fuzzy parsing result: {action} -> {value}")
    
    assert action == "move"
    assert value == "flamethrower"
    
    # Test switch response
    switch_response = """action: switch
value: pikachu
reasoning: Current Pokemon is weak"""
    
    action, value = parser.parse_response(switch_response, battle)
    logger.info(f"Switch parsing result: {action} -> {value}")
    
    assert action == "switch"
    assert value == "Pikachu"
    
    logger.info("Response Parser test passed!")


async def test_full_pipeline():
    """Test the full pipeline integration."""
    logger.info("Testing Full Pipeline...")
    
    # Create components
    processor = StateProcessor()
    llm_client = MockLLMClient()
    parser = ResponseParser()
    battle = create_mock_battle()
    
    # Generate prompt
    prompt = processor.create_battle_prompt(battle)
    logger.info("Generated prompt (truncated):")
    logger.info(prompt[:200] + "...")
    
    # Get LLM response
    llm_response = await llm_client.get_decision(prompt)
    logger.info(f"LLM response: {llm_response.content}")
    
    # Parse response
    action, value = parser.parse_response(llm_response.content, battle)
    logger.info(f"Final decision: {action} -> {value}")
    
    assert action in ["move", "switch"]
    assert value is not None
    
    logger.info("Full Pipeline test passed!")


async def main():
    """Run all tests."""
    logger.info("Starting Bot Component Tests...")
    
    try:
        await test_state_processor()
        await test_llm_client()
        await test_response_parser()
        await test_full_pipeline()
        
        logger.info("All tests passed! Bot components are working correctly.")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())