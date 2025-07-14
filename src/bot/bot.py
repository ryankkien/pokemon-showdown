"""
LLM-powered Pokemon Showdown Bot
Uses Large Language Models to make strategic decisions in Pokemon battles.
"""

import os
import asyncio
import logging
import json
import random
from typing import Dict, Any, Tuple, Optional
from dotenv import load_dotenv

from poke_env.player import Player
from poke_env.environment import Battle
from poke_env.ps_client.server_configuration import ServerConfiguration

from src.bot.state_processor import StateProcessor
from src.bot.llm_client import create_llm_client, LLMClient
from src.bot.response_parser import ResponseParser
from src.utils.battle_tracker import battle_tracker

# Load environment variables
load_dotenv()

# Configure enhanced logging
from src.utils.logging_config import setup_enhanced_logging
setup_enhanced_logging()

logger = logging.getLogger(__name__)


class LLMPlayer(Player):
    """
    A Pokemon Showdown player that uses an LLM for decision making.
    """
    
    def __init__(self, battle_format: str = "gen9randombattle", use_mock_llm: bool = False, 
                 llm_provider: Optional[str] = None, model: Optional[str] = None, **kwargs):
        """
        Initialize the LLM player.
        
        Args:
            battle_format: The Pokemon Showdown battle format
            use_mock_llm: Whether to use mock LLM for testing
            llm_provider: LLM provider to use (gemini, openai, anthropic, etc.)
            model: Specific model to use (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')
            **kwargs: Additional arguments for the Player class
        """
        super().__init__(battle_format=battle_format, **kwargs)
        self.state_processor = StateProcessor()
        self.llm_client = create_llm_client(use_mock=use_mock_llm, provider=llm_provider, model=model)
        self.response_parser = ResponseParser()
        self.battle_tracker = battle_tracker  # Reference to global tracker
        
        if not self.llm_client.is_available():
            logger.error("LLM client is not available!")
            raise RuntimeError("Failed to initialize LLM client")
        
    async def choose_move(self, battle: Battle) -> str:
        """
        Choose a move using LLM decision making with error retry.
        
        Args:
            battle: The current battle state
            
        Returns:
            The chosen move order
        """
        max_retries = 2
        failed_attempts = []
        
        for attempt in range(max_retries + 1):
            try:
                # Generate prompt from battle state
                prompt = self._create_prompt(battle)
                if attempt > 0:
                    # Add error context to the prompt for retries
                    available_move_ids = [move.id for move in battle.available_moves] if battle.available_moves else []
                    available_switch_names = [pokemon.species for pokemon in battle.available_switches] if battle.available_switches else []
                    
                    prompt += f"\n\nIMPORTANT: Previous attempt(s) failed. Here's what went wrong:\n"
                    for i, (failed_action, failed_value, reason) in enumerate(failed_attempts, 1):
                        prompt += f"{i}. Tried {failed_action} '{failed_value}' - {reason}\n"
                    
                    prompt += f"\n**VALID OPTIONS ONLY:**\n"
                    if available_move_ids:
                        prompt += f"Available moves (use EXACT names): {', '.join(available_move_ids)}\n"
                    if available_switch_names:
                        prompt += f"Available switches (use EXACT names): {', '.join(available_switch_names)}\n"
                    prompt += "\nChoose ONLY from these exact options listed above!"
                
                logger.info(f"Making decision for battle {battle.battle_tag} (attempt {attempt + 1}/{max_retries + 1})", 
                           extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                
                # Print battle state to console
                if attempt == 0:  # Only print on first attempt to avoid spam
                    print(f"\n⚔️  Battle {battle.battle_tag} - Turn {battle.turn}")
                    
                    # Show active Pokemon
                    if battle.active_pokemon:
                        my_hp = int(battle.active_pokemon.current_hp_fraction * 100) if battle.active_pokemon.current_hp_fraction else 0
                        print(f"   My Pokemon: {battle.active_pokemon.species} (HP: {my_hp}%)")
                    
                    if battle.opponent_active_pokemon:
                        opp_hp = int(battle.opponent_active_pokemon.current_hp_fraction * 100) if battle.opponent_active_pokemon.current_hp_fraction else 0
                        print(f"   Opponent: {battle.opponent_active_pokemon.species} (HP: {opp_hp}%)")
                    
                    # Show available moves
                    if battle.available_moves:
                        move_names = [move.id for move in battle.available_moves]
                        print(f"   Available moves: {', '.join(move_names)}")
                    
                    print()
                
                # Get decision from LLM
                llm_response = await self._get_llm_decision(prompt)
                
                # Log structured decision info
                logger.info(f"LLM decision received: {llm_response[:100]}{'...' if len(llm_response) > 100 else ''}", 
                           extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                
                # Print LLM reasoning to console
                print(f"🧠 {self.username} thinking:")
                reasoning_lines = llm_response.split('\n')
                for line in reasoning_lines:
                    if line.strip().startswith('reasoning:'):
                        print(f"   💭 {line.strip()}")
                        break
                
                # Parse LLM response
                action, value = self._parse_llm_response(llm_response, battle)
                
                # Log the parsed action
                logger.info(f"Parsed action: {action}={value}", 
                           extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                
                # Print action to console for visibility
                print(f"🤖 {self.username} in battle {battle.battle_tag} (Turn {battle.turn}):")
                print(f"   Action: {action.upper()} → {value}")
                
                # Validate and execute the chosen action
                result = self._execute_validated_action(action, value, battle)
                if result:
                    logger.info(f"Action executed successfully: {result}", 
                               extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                    print(f"   ✅ Action executed successfully!")
                else:
                    print(f"   ❌ Action failed validation")
                    
                    # Track the successful move
                    self.battle_tracker.log_move(
                        battle_id=battle.battle_tag,
                        bot_name=self.username,
                        turn=battle.turn,
                        llm_reasoning=llm_response,
                        parsed_action=action,
                        action_value=value,
                        execution_result=result,
                        battle_state_summary=self._get_battle_state_summary(battle),
                        success=True
                    )
                    
                    # Add strategic delay between moves (10-15 seconds)
                    delay = random.uniform(10.0, 15.0)
                    logger.info(f"Adding strategic delay of {delay:.1f} seconds before executing move", 
                               extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                    await asyncio.sleep(delay)
                    
                    return result
                
                # If we get here, the action was invalid, try again
                if attempt < max_retries:
                    # Determine why it failed
                    failure_reason = self._get_failure_reason(action, value, battle)
                    failed_attempts.append((action, value, failure_reason))
                    
                    logger.warning(f"Invalid action on attempt {attempt + 1}: {failure_reason}", 
                                  extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                    
                    # Print failure reason to console
                    print(f"   ⚠️  Attempt {attempt + 1} failed: {failure_reason}")
                    print(f"   🔄 Retrying...")
                    
                    # Track the failed move
                    self.battle_tracker.log_move(
                        battle_id=battle.battle_tag,
                        bot_name=self.username,
                        turn=battle.turn,
                        llm_reasoning=llm_response,
                        parsed_action=action,
                        action_value=value,
                        execution_result="INVALID_ACTION",
                        battle_state_summary=self._get_battle_state_summary(battle),
                        success=False,
                        error_message=failure_reason
                    )
                    
                    continue
                else:
                    logger.error(f"All {max_retries + 1} attempts failed, using safe random move", 
                                extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                    
                    # Print fallback message to console
                    print(f"   💀 All {max_retries + 1} attempts failed!")
                    print(f"   🎲 Using safe random move as fallback...")
                    
                    # Track the final failure
                    self.battle_tracker.log_move(
                        battle_id=battle.battle_tag,
                        bot_name=self.username,
                        turn=battle.turn,
                        llm_reasoning=llm_response,
                        parsed_action=action,
                        action_value=value,
                        execution_result="FALLBACK_RANDOM",
                        battle_state_summary=self._get_battle_state_summary(battle),
                        success=False,
                        error_message=f"All attempts failed, using fallback"
                    )
                    
                    return self._choose_safe_random_move(battle)
                    
            except Exception as e:
                logger.error(f"Error in choose_move attempt {attempt + 1}: {str(e)}", 
                           extra={'battle_id': battle.battle_tag, 'bot_name': self.username, 'error_type': type(e).__name__})
                if attempt < max_retries:
                    logger.info(f"Retrying after error...", 
                               extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                    continue
                else:
                    # Final fallback
                    logger.error(f"All retry attempts exhausted, using safe random move", 
                                extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
                    return self._choose_safe_random_move(battle)
    
    def _get_failure_reason(self, action: str, value: str, battle: Battle) -> str:
        """
        Determine why an action failed validation.
        
        Returns:
            Human-readable reason for failure
        """
        if action == "move":
            available_moves = [move.id for move in battle.available_moves] if battle.available_moves else []
            if not available_moves:
                return "No moves are available (might be trapped or struggling)"
            elif value:
                # Try to find similar moves
                similar = [move for move in available_moves if value.lower() in move.lower() or move.lower() in value.lower()]
                if similar:
                    return f"Move '{value}' not found. Did you mean: {', '.join(similar)}?"
                else:
                    return f"Move '{value}' not available. Valid moves: {', '.join(available_moves)}"
            else:
                return "No move name provided"
                
        elif action == "switch":
            available_switches = [pokemon.species for pokemon in battle.available_switches] if battle.available_switches else []
            if not available_switches:
                return "No switches available (might be trapped or only one Pokemon left)"
            elif value:
                # Try to find similar Pokemon names
                similar = [poke for poke in available_switches if value.lower() in poke.lower() or poke.lower() in value.lower()]
                if similar:
                    return f"Pokemon '{value}' not found. Did you mean: {', '.join(similar)}?"
                else:
                    return f"Pokemon '{value}' not available. Valid switches: {', '.join(available_switches)}"
            else:
                return "No Pokemon name provided"
        else:
            return f"Invalid action type '{action}'. Must be 'move' or 'switch'"
    
    def _execute_validated_action(self, action: str, value: str, battle: Battle) -> Optional[str]:
        """
        Execute an action after validation.
        
        Returns:
            The battle order if valid, None if invalid
        """
        if action == "move":
            # Strict validation: only allow moves that are actually available
            for move in battle.available_moves:
                if move.id.lower() == value.lower():
                    logger.info(f"Using validated move: {move.id}")
                    return self.create_order(move, terastallize=False)
            logger.warning(f"Move '{value}' not in available moves: {[m.id for m in battle.available_moves]}")
            return None
            
        elif action == "switch":
            # Strict validation: only allow switches that are actually available
            for pokemon in battle.available_switches:
                if pokemon.species.lower() == value.lower():
                    logger.info(f"Using validated switch: {pokemon.species}")
                    return self.create_order(pokemon)
            logger.warning(f"Pokemon '{value}' not in available switches: {[p.species for p in battle.available_switches]}")
            return None
        else:
            logger.warning(f"Invalid action type: {action}")
            return None
    
    def _choose_safe_random_move(self, battle: Battle) -> str:
        """
        Choose a random move without using special mechanics like Terastallize, Mega, Dynamax, etc.
        This prevents invalid choice errors.
        """
        
        # Try to use a regular move first
        if battle.available_moves:
            move = random.choice(battle.available_moves)
            logger.info(f"Choosing safe random move: {move.id}")
            print(f"   🎲 Random move chosen: {move.id}")
            return self.create_order(move, terastallize=False, mega=False, dynamax=False, z_move=False)
        
        # If no moves available, try to switch
        if battle.available_switches:
            pokemon = random.choice(battle.available_switches)
            logger.info(f"Choosing safe random switch: {pokemon.species}")
            print(f"   🎲 Random switch chosen: {pokemon.species}")
            return self.create_order(pokemon)
        
        # Last resort - struggle
        logger.warning("No safe moves or switches available, defaulting to struggle")
        print(f"   💀 No options available, defaulting to struggle")
        return self.choose_default_move()
    
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
    
    def _get_battle_state_summary(self, battle: Battle) -> str:
        """Get a concise summary of the current battle state."""
        try:
            active_pokemon = battle.active_pokemon
            opponent_pokemon = battle.opponent_active_pokemon
            
            summary = {
                'turn': battle.turn,
                'my_pokemon': f"{active_pokemon.species} ({active_pokemon.current_hp}/{active_pokemon.max_hp} HP)" if active_pokemon else "None",
                'opponent_pokemon': f"{opponent_pokemon.species} ({opponent_pokemon.current_hp}/{opponent_pokemon.max_hp} HP)" if opponent_pokemon else "None",
                'available_moves': len(battle.available_moves),
                'available_switches': len(battle.available_switches),
                'weather': str(battle.weather) if battle.weather else "None",
                'terrain': str(battle.terrain) if battle.terrain else "None"
            }
            
            return json.dumps(summary, default=str)
        except Exception as e:
            return f"Error getting battle state: {str(e)}"
    
    async def _battle_start_callback(self, battle: Battle):
        """Called when a battle starts."""
        logger.info(f"Battle started: {battle.battle_tag}", 
                   extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
        
        # Print battle start to console
        print(f"\n🚀 NEW BATTLE STARTED: {battle.battle_tag}")
        print(f"   Player: {self.username}")
        print(f"   Format: {battle.format}")
        print(f"   Ready to battle! 🔥")
        
        # The battle_tracker.start_battle is called from bot_manager
        # so we don't need to call it here to avoid duplicates
    
    async def _battle_finished_callback(self, battle: Battle):
        """Called when a battle finishes."""
        logger.info(f"Battle finished: {battle.battle_tag}", 
                   extra={'battle_id': battle.battle_tag, 'bot_name': self.username})
        
        # Print battle result to console
        if battle.won is not None:
            result = "🏆 WON" if battle.won else "💀 LOST"
            print(f"\n🏁 Battle {battle.battle_tag} finished!")
            print(f"   {self.username}: {result}")
            if battle.won:
                print(f"   🎉 Victory for {self.username}!")
            else:
                print(f"   😔 Defeat for {self.username}")
        
        # The battle_tracker.end_battle is called from bot_manager
        # so we don't need to call it here to avoid duplicates
    
    async def send_lobby_message(self, message: str):
        """Send a message to the lobby to confirm server connection."""
        try:
            # For localhost, try to send message even if not fully authenticated
            # Send message to lobby
            await self._send_message(f'/msg lobby,{message}')
            logger.info(f"Sent lobby message: {message}")
        except Exception as e:
            logger.error(f"Failed to send lobby message: {e}")
    
    async def test_server_connection(self):
        """Test server connection by sending a lobby message."""
        try:
            # Give the bot more time to connect
            await asyncio.sleep(2.0)
            await self.send_lobby_message(f"Bot {self.username} is connected and ready for battle!")
            logger.info(f"Bot {self.username} tested server connection successfully")
        except Exception as e:
            logger.warning(f"Bot {self.username} failed to test server connection: {e}")
            # Connection might still work for battles even if lobby messaging fails


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