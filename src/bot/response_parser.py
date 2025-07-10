"""
Response Parser for LLM Pokemon Showdown Bot
Parses LLM responses to extract valid actions and moves.
"""

import re
import logging
from typing import Tuple, Optional, List
from poke_env.environment import Battle, Move, Pokemon

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parses LLM responses to extract valid Pokemon actions.
    """
    
    def parse_response(self, response: str, battle: Battle) -> Tuple[str, str]:
        """
        Parse LLM response to extract action and value.
        
        Args:
            response: The LLM's text response
            battle: Current battle state for validation
            
        Returns:
            Tuple of (action, value) where action is "move" or "switch"
            and value is the move ID or Pokemon species name
        """
        try:
            # First, try to parse structured response
            action, value = self._parse_structured_response(response)
            
            if action and value:
                # Validate the parsed action
                validated_action, validated_value = self._validate_action(action, value, battle)
                if validated_action and validated_value:
                    logger.info(f"Parsed and validated: {validated_action} -> {validated_value}")
                    return validated_action, validated_value
            
            # If structured parsing fails, try fuzzy parsing
            logger.warning("Structured parsing failed, trying fuzzy parsing")
            action, value = self._parse_fuzzy_response(response, battle)
            
            if action and value:
                logger.info(f"Fuzzy parsed: {action} -> {value}")
                return action, value
            
            # Final fallback
            logger.warning("All parsing attempts failed, using fallback")
            return self._get_fallback_action(battle)
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return self._get_fallback_action(battle)
    
    def _parse_structured_response(self, response: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse a structured response in the expected format.
        
        Expected format:
        action: move/switch
        value: move_name/pokemon_name
        """
        action = None
        value = None
        
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip().lower()
            
            # Look for action line
            if line.startswith('action:'):
                action_text = line.split(':', 1)[1].strip()
                if 'move' in action_text:
                    action = 'move'
                elif 'switch' in action_text:
                    action = 'switch'
            
            # Look for value line
            elif line.startswith('value:'):
                value = line.split(':', 1)[1].strip()
                # Clean up the value
                value = re.sub(r'["\']', '', value)  # Remove quotes
                value = value.replace(' ', '').replace('-', '').replace('_', '')  # Remove spaces and separators
        
        return action, value
    
    def _parse_fuzzy_response(self, response: str, battle: Battle) -> Tuple[Optional[str], Optional[str]]:
        """
        Try to parse response using fuzzy matching when structured parsing fails.
        """
        response_lower = response.lower()
        
        # Get available moves and switches for fuzzy matching
        available_moves = [move.id for move in battle.available_moves] if battle.available_moves else []
        available_switches = [pokemon.species.lower() for pokemon in battle.available_switches] if battle.available_switches else []
        
        # Look for move names in the response
        for move_id in available_moves:
            move_variations = self._get_move_variations(move_id)
            for variation in move_variations:
                if variation in response_lower:
                    return 'move', move_id
        
        # Look for Pokemon names in the response
        for pokemon_species in available_switches:
            pokemon_variations = self._get_pokemon_variations(pokemon_species)
            for variation in pokemon_variations:
                if variation in response_lower:
                    # Find the actual Pokemon object to get correct species name
                    for pokemon in battle.available_switches:
                        if pokemon.species.lower() == pokemon_species:
                            return 'switch', pokemon.species
        
        # Look for keywords suggesting moves or switches
        move_keywords = ['attack', 'move', 'use', 'cast', 'fire', 'water', 'grass', 'electric']
        switch_keywords = ['switch', 'change', 'swap', 'send out', 'retreat']
        
        has_move_keyword = any(keyword in response_lower for keyword in move_keywords)
        has_switch_keyword = any(keyword in response_lower for keyword in switch_keywords)
        
        if has_switch_keyword and available_switches:
            # Default to first available switch
            for pokemon in battle.available_switches:
                return 'switch', pokemon.species
        elif has_move_keyword and available_moves:
            # Default to first available move
            return 'move', available_moves[0]
        
        return None, None
    
    def _get_move_variations(self, move_id: str) -> List[str]:
        """Get variations of a move name for fuzzy matching."""
        variations = [move_id.lower()]
        
        # Add version with spaces
        spaced = move_id.replace('', ' ').strip()
        if spaced != move_id:
            variations.append(spaced.lower())
        
        # Add version without special characters
        clean = re.sub(r'[^a-zA-Z0-9]', '', move_id)
        if clean != move_id:
            variations.append(clean.lower())
        
        # Common move name mappings
        move_mappings = {
            'thunderbolt': ['thunder bolt', 'tbolt'],
            'earthquake': ['earth quake', 'eq'],
            'flamethrower': ['flame thrower'],
            'icebeam': ['ice beam'],
            'psychic': ['psychic move'],
            'shadowball': ['shadow ball'],
            'energyball': ['energy ball'],
            'focusblast': ['focus blast'],
            'aurasphere': ['aura sphere'],
            'airslash': ['air slash'],
            'rockslide': ['rock slide'],
            'stoneedge': ['stone edge'],
            'earthquake': ['earth quake'],
        }
        
        if move_id.lower() in move_mappings:
            variations.extend(move_mappings[move_id.lower()])
        
        return variations
    
    def _get_pokemon_variations(self, species: str) -> List[str]:
        """Get variations of a Pokemon name for fuzzy matching."""
        variations = [species.lower()]
        
        # Add version without hyphens/spaces
        clean = re.sub(r'[^a-zA-Z0-9]', '', species)
        if clean != species:
            variations.append(clean.lower())
        
        return variations
    
    def _validate_action(self, action: str, value: str, battle: Battle) -> Tuple[Optional[str], Optional[str]]:
        """
        Validate that the parsed action is legal in the current battle state.
        """
        if action == 'move':
            return self._validate_move(value, battle)
        elif action == 'switch':
            return self._validate_switch(value, battle)
        else:
            return None, None
    
    def _validate_move(self, move_value: str, battle: Battle) -> Tuple[Optional[str], Optional[str]]:
        """Validate a move action."""
        if not battle.available_moves:
            return None, None
        
        # Direct ID match
        for move in battle.available_moves:
            if move.id.lower() == move_value.lower():
                return 'move', move.id
        
        # Fuzzy match with variations
        for move in battle.available_moves:
            variations = self._get_move_variations(move.id)
            if move_value.lower() in variations:
                return 'move', move.id
        
        return None, None
    
    def _validate_switch(self, pokemon_value: str, battle: Battle) -> Tuple[Optional[str], Optional[str]]:
        """Validate a switch action."""
        if not battle.available_switches:
            return None, None
        
        # Direct species match
        for pokemon in battle.available_switches:
            if pokemon.species.lower() == pokemon_value.lower():
                return 'switch', pokemon.species
        
        # Fuzzy match with variations
        for pokemon in battle.available_switches:
            variations = self._get_pokemon_variations(pokemon.species)
            if pokemon_value.lower() in variations:
                return 'switch', pokemon.species
        
        return None, None
    
    def _get_fallback_action(self, battle: Battle) -> Tuple[str, str]:
        """
        Get a fallback action when parsing fails.
        Prioritizes moves over switches.
        """
        # Try to use the first available move
        if battle.available_moves:
            return 'move', battle.available_moves[0].id
        
        # If no moves available, try to switch
        if battle.available_switches:
            return 'switch', battle.available_switches[0].species
        
        # This should never happen in a normal battle, but just in case
        logger.error("No available moves or switches!")
        return 'move', 'struggle'  # Pokemon will struggle if no other moves