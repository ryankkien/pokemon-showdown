"""
LLM-powered Pokemon Showdown Bot
Uses Large Language Models to make strategic decisions in Pokemon battles.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

from poke_env.player import Player
from poke_env.environment import Battle
from poke_env.ps_client.server_configuration import ServerConfiguration

from state_processor import StateProcessor
from llm_client import create_llm_client, LLMClient
from response_parser import ResponseParser

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMPlayer(Player):
    """
    A Pokemon Showdown player that uses an LLM for decision making.
    """
    
    def __init__(self, battle_format: str = "gen9randombattle", use_mock_llm: bool = False, **kwargs):
        """
        Initialize the LLM player.
        
        Args:
            battle_format: The Pokemon Showdown battle format
            use_mock_llm: Whether to use mock LLM for testing
            **kwargs: Additional arguments for the Player class
        """
        super().__init__(battle_format=battle_format, **kwargs)
        self.state_processor = StateProcessor()
        self.llm_client = create_llm_client(use_mock=use_mock_llm)
        self.response_parser = ResponseParser()
        
        if not self.llm_client.is_available():
            logger.error("LLM client is not available!")
            raise RuntimeError("Failed to initialize LLM client")
        
    async def choose_move(self, battle: Battle) -> str:
        """
        Choose a move using LLM decision making.
        
        Args:
            battle: The current battle state
            
        Returns:
            The chosen move order
        """
        try:
            # Generate prompt from battle state
            prompt = self._create_prompt(battle)
            logger.info(f"Generated prompt for battle {battle.battle_tag}")
            
            # Get decision from LLM
            llm_response = await self._get_llm_decision(prompt)
            logger.info(f"LLM response: {llm_response}")
            
            # Parse LLM response
            action, value = self._parse_llm_response(llm_response, battle)
            
            # Execute the chosen action
            if action == "move":
                # Find the move object by ID
                for move in battle.available_moves:
                    if move.id == value:
                        logger.info(f"Using move: {move.id}")
                        # Check if Terastallize is available before using it
                        can_tera = battle.can_tera if hasattr(battle, 'can_tera') else False
                        return self.create_order(move, terastallize=False)  # Explicitly disable terastallize for now
                logger.warning(f"Move {value} not found. Available moves: {[m.id for m in battle.available_moves]}")
                return self.choose_random_move(battle)
            elif action == "switch":
                # Find the pokemon object by species
                for pokemon in battle.available_switches:
                    if pokemon.species.lower() == value.lower():
                        logger.info(f"Switching to: {pokemon.species}")
                        return self.create_order(pokemon)
                logger.warning(f"Pokemon {value} not found. Available switches: {[p.species for p in battle.available_switches]}")
                return self.choose_random_move(battle)
            else:
                logger.warning(f"Invalid LLM decision: {action}, {value}. Using random move.")
                return self.choose_random_move(battle)
                
        except Exception as e:
            logger.error(f"Error in choose_move: {e}")
            # Fallback to random move
            return self.choose_random_move(battle)
    
    def _create_prompt(self, battle: Battle) -> str:
        """
        Create a detailed prompt for the LLM based on the battle state.
        
        Args:
            battle: The current battle state
            
        Returns:
            A formatted prompt string
        """
        return self.state_processor.create_battle_prompt(battle)
    
    async def _get_llm_decision(self, prompt: str) -> str:
        """
        Send prompt to LLM and get response.
        
        Args:
            prompt: The formatted prompt
            
        Returns:
            The LLM's response
        """
        try:
            response = await self.llm_client.get_decision(prompt)
            
            if response.success:
                return response.content
            else:
                logger.error(f"LLM API error: {response.error_message}")
                return "action: move, value: tackle"  # Fallback response
                
        except Exception as e:
            logger.error(f"Error getting LLM decision: {e}")
            return "action: move, value: tackle"  # Fallback response
    
    def _parse_llm_response(self, response: str, battle: Battle) -> Tuple[str, str]:
        """
        Parse the LLM's response to extract action and value.
        
        Args:
            response: The LLM's response
            battle: The current battle state
            
        Returns:
            Tuple of (action, value)
        """
        return self.response_parser.parse_response(response, battle)


async def main():
    """
    Main function to run the bot.
    """
    # Get configuration from environment
    username = os.getenv("PS_USERNAME", "LLMBot")
    server_url = os.getenv("PS_SERVER_URL", "http://localhost:8000")
    battle_format = os.getenv("PS_BATTLE_FORMAT", "gen9randombattle")
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    
    logger.info(f"Starting LLM bot with username: {username}")
    logger.info(f"Server URL: {server_url}")
    logger.info(f"Battle format: {battle_format}")
    logger.info(f"Using mock LLM: {use_mock}")
    
    try:
        # Create custom server configuration for local server
        server_config = ServerConfiguration(
            'ws://localhost:8000/showdown/websocket',
            'http://localhost:8000/'
        )
        
        # Create and start the bot
        player = LLMPlayer(
            battle_format=battle_format,
            max_concurrent_battles=1,
            use_mock_llm=use_mock,
            server_configuration=server_config
        )
        
        # Start the bot (this will connect to the server)
        await player.ladder(5)  # Play 5 battles
        
        logger.info("Bot finished playing battles")
        
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())