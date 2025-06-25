"""
State Processor for LLM Pokemon Showdown Bot
Converts poke-env Battle objects into detailed prompts for LLM decision making.
"""

from typing import List, Dict, Any, Optional
from poke_env.environment import Battle, Pokemon, Move, Effect
from poke_env.data import GenData


class StateProcessor:
    """
    Processes battle state and creates detailed prompts for LLM decision making.
    """
    
    def __init__(self):
        """Initialize the state processor."""
        self.gen_data = GenData.from_gen(8)  # Gen 8 data
    
    def create_battle_prompt(self, battle: Battle) -> str:
        """
        Create a comprehensive prompt describing the current battle state.
        
        Args:
            battle: The current battle object
            
        Returns:
            A detailed prompt string for the LLM
        """
        prompt_parts = [
            "You are a master Pokémon strategist. Your goal is to win this Pokémon battle.",
            "Analyze the current battle state carefully and choose the best action.",
            "",
            self._get_active_pokemon_info(battle),
            self._get_opponent_info(battle),
            self._get_team_info(battle),
            self._get_field_conditions(battle),
            self._get_recent_battle_log(battle),
            self._get_available_actions(battle),
            self._get_strategic_considerations(),
            self._get_response_format()
        ]
        
        return "\n".join(filter(None, prompt_parts))
    
    def _get_active_pokemon_info(self, battle: Battle) -> str:
        """Get detailed information about the player's active Pokemon."""
        if not battle.active_pokemon:
            return "**Your Active Pokémon:** None (need to send out a Pokemon)"
        
        pokemon = battle.active_pokemon
        
        info = f"**Your Active Pokémon:**\n"
        info += f"- {pokemon.species} (Level {pokemon.level}"
        
        if pokemon.gender:
            info += f", {pokemon.gender}"
        
        # HP information
        if pokemon.current_hp_fraction is not None:
            hp_percent = int(pokemon.current_hp_fraction * 100)
            info += f", HP: {hp_percent}%"
        else:
            info += f", HP: Unknown"
        
        # Status condition
        status = pokemon.status if pokemon.status else "None"
        info += f", Status: {status.name if hasattr(status, 'name') else status})\n"
        
        # Type information
        types = "/".join([t.name for t in pokemon.types])
        info += f"  - Type: {types}\n"
        
        # Ability
        if pokemon.ability:
            info += f"  - Ability: {pokemon.ability}\n"
        
        # Stats (if known)
        if pokemon.stats:
            stats_str = ", ".join([f"{stat}: {value}" for stat, value in pokemon.stats.items()])
            info += f"  - Stats: {{{stats_str}}}\n"
        
        # Moves
        info += f"  - Moves:\n"
        for i, move in enumerate(pokemon.moves.values(), 1):
            move_info = self._get_move_info(move)
            info += f"    {i}. {move_info}\n"
        
        # Boosts/stat changes
        if pokemon.boosts:
            boosts_str = ", ".join([f"{stat}: {boost:+d}" for stat, boost in pokemon.boosts.items() if boost != 0])
            if boosts_str:
                info += f"  - Stat Changes: {boosts_str}\n"
        
        return info
    
    def _get_opponent_info(self, battle: Battle) -> str:
        """Get information about the opponent's active Pokemon."""
        if not battle.opponent_active_pokemon:
            return "**Opponent's Active Pokémon:** None"
        
        pokemon = battle.opponent_active_pokemon
        
        info = f"**Opponent's Active Pokémon:**\n"
        info += f"- {pokemon.species} (Level {pokemon.level}"
        
        # HP information
        if pokemon.current_hp_fraction is not None:
            hp_percent = int(pokemon.current_hp_fraction * 100)
            info += f", HP: {hp_percent}%"
        else:
            info += f", HP: Unknown"
        
        # Status condition
        status = pokemon.status if pokemon.status else "None"
        info += f", Status: {status.name if hasattr(status, 'name') else status})\n"
        
        # Type information
        if pokemon.types:
            types = "/".join([t.name for t in pokemon.types])
            info += f"  - Type: {types}\n"
        
        # Known ability
        if pokemon.ability:
            info += f"  - Ability: {pokemon.ability}\n"
        
        # Revealed moves
        if pokemon.moves:
            info += f"  - Known Moves:\n"
            for move_id, move in pokemon.moves.items():
                if move:  # Move has been revealed
                    move_info = self._get_move_info(move)
                    info += f"    - {move_info}\n"
        
        # Boosts/stat changes
        if pokemon.boosts:
            boosts_str = ", ".join([f"{stat}: {boost:+d}" for stat, boost in pokemon.boosts.items() if boost != 0])
            if boosts_str:
                info += f"  - Stat Changes: {boosts_str}\n"
        
        return info
    
    def _get_team_info(self, battle: Battle) -> str:
        """Get information about team members."""
        info = "**Your Team:**\n"
        
        for pokemon in battle.team.values():
            if pokemon == battle.active_pokemon:
                continue  # Skip active pokemon as it's already detailed above
            
            status_str = f" ({pokemon.status.name})" if pokemon.status else ""
            hp_str = f"{int(pokemon.current_hp_fraction * 100)}%" if pokemon.current_hp_fraction is not None else "Unknown"
            
            info += f"- {pokemon.species} (HP: {hp_str}{status_str})\n"
        
        # Opponent team info (what we know)
        info += "\n**Opponent's Team (Known):**\n"
        known_count = len([p for p in battle.opponent_team.values() if p.species])
        total_count = 6  # Standard team size
        
        for pokemon in battle.opponent_team.values():
            if pokemon == battle.opponent_active_pokemon:
                continue
            if pokemon.species:  # We've seen this pokemon
                status_str = f" ({pokemon.status.name})" if pokemon.status else ""
                hp_str = f"{int(pokemon.current_hp_fraction * 100)}%" if pokemon.current_hp_fraction is not None else "Unknown"
                
                info += f"- {pokemon.species} (HP: {hp_str}{status_str})\n"
        
        remaining = total_count - known_count
        if remaining > 0:
            info += f"- {remaining} unknown Pokémon remaining\n"
        
        return info
    
    def _get_field_conditions(self, battle: Battle) -> str:
        """Get information about field conditions, weather, terrain, etc."""
        conditions = []
        
        # Weather
        if battle.weather:
            conditions.append(f"Weather: {battle.weather}")
        
        # Terrain
        if hasattr(battle, 'terrain') and battle.terrain:
            conditions.append(f"Terrain: {battle.terrain}")
        
        # Field effects
        if battle.fields:
            for field in battle.fields:
                conditions.append(f"Field: {field}")
        
        # Side conditions (hazards, etc.)
        if battle.side_conditions:
            conditions.append("Your side:")
            for condition in battle.side_conditions:
                conditions.append(f"  - {condition}")
        
        if battle.opponent_side_conditions:
            conditions.append("Opponent's side:")
            for condition in battle.opponent_side_conditions:
                conditions.append(f"  - {condition}")
        
        if conditions:
            return "**Field Conditions:**\n" + "\n".join(conditions)
        else:
            return "**Field Conditions:** None"
    
    def _get_recent_battle_log(self, battle: Battle) -> str:
        """Get recent battle events for context."""
        # This is simplified - poke-env doesn't provide easy access to battle log
        # In a full implementation, you might track recent events yourself
        turn_info = f"**Current Turn:** {battle.turn}"
        
        if hasattr(battle, 'battle_log') and battle.battle_log:
            # Get last few entries if available
            recent_log = battle.battle_log[-3:] if len(battle.battle_log) > 3 else battle.battle_log
            log_str = "\n".join([f"- {entry}" for entry in recent_log])
            return f"{turn_info}\n\n**Recent Battle Log:**\n{log_str}"
        
        return turn_info
    
    def _get_available_actions(self, battle: Battle) -> str:
        """Get available moves and switches."""
        info = "**Available Actions:**\n"
        
        # Available moves
        if battle.available_moves:
            info += "Moves:\n"
            for i, move in enumerate(battle.available_moves, 1):
                move_info = self._get_move_info(move)
                info += f"  {i}. {move_info}\n"
        
        # Available switches
        if battle.available_switches:
            info += "Switches:\n"
            for i, pokemon in enumerate(battle.available_switches, 1):
                hp_str = f"{int(pokemon.current_hp_fraction * 100)}%" if pokemon.current_hp_fraction is not None else "Unknown"
                status_str = f" ({pokemon.status.name})" if pokemon.status else ""
                info += f"  {i}. {pokemon.species} (HP: {hp_str}{status_str})\n"
        
        return info
    
    def _get_move_info(self, move: Move) -> str:
        """Get detailed information about a move."""
        info = f"{move.id}"
        
        if move.type:
            info += f" ({move.type.name} type"
        
        if move.category:
            info += f", {move.category.name}"
        
        if move.base_power:
            info += f", {move.base_power} power"
        
        if move.accuracy and move.accuracy < 100:
            info += f", {move.accuracy}% accuracy"
        
        if move.pp:
            info += f", {move.current_pp}/{move.pp} PP"
        
        info += ")"
        
        # Add effect description if available
        if move.effect:
            info += f" - {move.effect}"
        
        return info
    
    def _get_strategic_considerations(self) -> str:
        """Add strategic thinking prompts."""
        return """
**Strategic Considerations:**
- Consider type effectiveness and STAB (Same Type Attack Bonus)
- Think about stat changes, abilities, and status conditions
- Evaluate speed tiers and priority moves
- Consider switching if your current Pokemon is at a disadvantage
- Think about preserving key team members for later
- Consider hazards, weather, and field effects
- Plan for the opponent's likely next move"""
    
    def _get_response_format(self) -> str:
        """Specify the expected response format."""
        return """
**Instructions:**
Based on the battle state above, choose the best action. Provide your response in this exact format:

action: "move" or "switch"
value: "move_name" or "pokemon_name"
reasoning: Brief explanation of your choice

Example responses:
action: move
value: flamethrower
reasoning: Super effective against opponent's Grass-type Pokemon

action: switch  
value: pikachu
reasoning: Current Pokemon is at low HP and weak to opponent's attacks"""