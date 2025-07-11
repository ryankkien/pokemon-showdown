"""
State Processor for LLM Pokemon Showdown Bot
Converts poke-env Battle objects into detailed prompts for LLM decision making.
"""

from typing import List, Dict, Any, Optional
from poke_env.environment import Battle, Pokemon, Move, Effect, PokemonType
from poke_env.data import GenData


class StateProcessor:
    """
    Processes battle state and creates detailed prompts for LLM decision making.
    """
    
    def __init__(self):
        """Initialize the state processor."""
        self.gen_data = GenData.from_gen(8)  # Gen 8 data
        
        # Type effectiveness chart
        self.type_chart = {
            PokemonType.NORMAL: {PokemonType.ROCK: 0.5, PokemonType.GHOST: 0, PokemonType.STEEL: 0.5},
            PokemonType.FIRE: {PokemonType.FIRE: 0.5, PokemonType.WATER: 0.5, PokemonType.GRASS: 2, PokemonType.ICE: 2, PokemonType.BUG: 2, PokemonType.ROCK: 0.5, PokemonType.DRAGON: 0.5, PokemonType.STEEL: 2},
            PokemonType.WATER: {PokemonType.FIRE: 2, PokemonType.WATER: 0.5, PokemonType.GRASS: 0.5, PokemonType.GROUND: 2, PokemonType.ROCK: 2, PokemonType.DRAGON: 0.5},
            PokemonType.ELECTRIC: {PokemonType.WATER: 2, PokemonType.ELECTRIC: 0.5, PokemonType.GRASS: 0.5, PokemonType.GROUND: 0, PokemonType.FLYING: 2, PokemonType.DRAGON: 0.5},
            PokemonType.GRASS: {PokemonType.FIRE: 0.5, PokemonType.WATER: 2, PokemonType.GRASS: 0.5, PokemonType.POISON: 0.5, PokemonType.GROUND: 2, PokemonType.FLYING: 0.5, PokemonType.BUG: 0.5, PokemonType.ROCK: 2, PokemonType.DRAGON: 0.5, PokemonType.STEEL: 0.5},
            PokemonType.ICE: {PokemonType.FIRE: 0.5, PokemonType.WATER: 0.5, PokemonType.GRASS: 2, PokemonType.ICE: 0.5, PokemonType.GROUND: 2, PokemonType.FLYING: 2, PokemonType.DRAGON: 2, PokemonType.STEEL: 0.5},
            PokemonType.FIGHTING: {PokemonType.NORMAL: 2, PokemonType.ICE: 2, PokemonType.POISON: 0.5, PokemonType.FLYING: 0.5, PokemonType.PSYCHIC: 0.5, PokemonType.BUG: 0.5, PokemonType.ROCK: 2, PokemonType.GHOST: 0, PokemonType.DARK: 2, PokemonType.STEEL: 2, PokemonType.FAIRY: 0.5},
            PokemonType.POISON: {PokemonType.GRASS: 2, PokemonType.POISON: 0.5, PokemonType.GROUND: 0.5, PokemonType.ROCK: 0.5, PokemonType.GHOST: 0.5, PokemonType.STEEL: 0, PokemonType.FAIRY: 2},
            PokemonType.GROUND: {PokemonType.FIRE: 2, PokemonType.ELECTRIC: 2, PokemonType.GRASS: 0.5, PokemonType.POISON: 2, PokemonType.FLYING: 0, PokemonType.BUG: 0.5, PokemonType.ROCK: 2, PokemonType.STEEL: 2},
            PokemonType.FLYING: {PokemonType.ELECTRIC: 0.5, PokemonType.GRASS: 2, PokemonType.FIGHTING: 2, PokemonType.BUG: 2, PokemonType.ROCK: 0.5, PokemonType.STEEL: 0.5},
            PokemonType.PSYCHIC: {PokemonType.FIGHTING: 2, PokemonType.POISON: 2, PokemonType.PSYCHIC: 0.5, PokemonType.DARK: 0, PokemonType.STEEL: 0.5},
            PokemonType.BUG: {PokemonType.FIRE: 0.5, PokemonType.GRASS: 2, PokemonType.FIGHTING: 0.5, PokemonType.POISON: 0.5, PokemonType.FLYING: 0.5, PokemonType.PSYCHIC: 2, PokemonType.GHOST: 0.5, PokemonType.DARK: 2, PokemonType.STEEL: 0.5, PokemonType.FAIRY: 0.5},
            PokemonType.ROCK: {PokemonType.FIRE: 2, PokemonType.ICE: 2, PokemonType.FIGHTING: 0.5, PokemonType.GROUND: 0.5, PokemonType.FLYING: 2, PokemonType.BUG: 2, PokemonType.STEEL: 0.5},
            PokemonType.GHOST: {PokemonType.NORMAL: 0, PokemonType.PSYCHIC: 2, PokemonType.GHOST: 2, PokemonType.DARK: 0.5},
            PokemonType.DRAGON: {PokemonType.DRAGON: 2, PokemonType.STEEL: 0.5, PokemonType.FAIRY: 0},
            PokemonType.DARK: {PokemonType.FIGHTING: 0.5, PokemonType.PSYCHIC: 2, PokemonType.GHOST: 2, PokemonType.DARK: 0.5, PokemonType.FAIRY: 0.5},
            PokemonType.STEEL: {PokemonType.FIRE: 0.5, PokemonType.WATER: 0.5, PokemonType.ELECTRIC: 0.5, PokemonType.ICE: 2, PokemonType.ROCK: 2, PokemonType.STEEL: 0.5, PokemonType.FAIRY: 2},
            PokemonType.FAIRY: {PokemonType.FIRE: 0.5, PokemonType.FIGHTING: 2, PokemonType.POISON: 0.5, PokemonType.DRAGON: 2, PokemonType.DARK: 2, PokemonType.STEEL: 0.5}
        }
    
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
            "**Key Principles:**",
            "- Type advantages are crucial: 2x damage for super effective, 0.5x for not very effective, 0x for immunity",
            "- STAB (Same Type Attack Bonus) gives 1.5x damage when a Pokemon uses a move matching its type",
            "- Speed determines turn order unless priority moves are used",
            "- Consider the long-term win condition, not just immediate damage",
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
            # Add effectiveness hint if opponent is active
            if battle.opponent_active_pokemon and move.type:
                effectiveness = self._calculate_type_effectiveness(
                    move.type, 
                    battle.opponent_active_pokemon.types if battle.opponent_active_pokemon.types else []
                )
                if effectiveness != 1.0:
                    move_info += f" [vs opponent: {effectiveness}x]"
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
            info += "\nMOVES (use exact names in 'value' field):\n"
            for i, move in enumerate(battle.available_moves, 1):
                move_info = self._get_move_info(move)
                info += f"  {i}. {move_info}\n"
                # Add the exact move ID to use
                info += f"     → To use this move, set value: {move.id}\n"
        else:
            info += "\nNO MOVES AVAILABLE (might need to switch or struggle)\n"
        
        # Available switches
        if battle.available_switches:
            info += "\nSWITCHES (use exact names in 'value' field):\n"
            for i, pokemon in enumerate(battle.available_switches, 1):
                hp_str = f"{int(pokemon.current_hp_fraction * 100)}%" if pokemon.current_hp_fraction is not None else "Unknown"
                status_str = f" ({pokemon.status.name})" if pokemon.status else ""
                info += f"  {i}. {pokemon.species} (HP: {hp_str}{status_str})\n"
                # Add the exact Pokemon name to use
                info += f"     → To switch to this Pokemon, set value: {pokemon.species}\n"
        else:
            info += "\nNO SWITCHES AVAILABLE (all other Pokemon fainted or trapped)\n"
        
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
            
        # Add priority information
        if hasattr(move, 'priority') and move.priority != 0:
            info += f", priority {move.priority:+d}"
        
        if move.max_pp:
            info += f", {move.current_pp}/{move.max_pp} PP"
        
        info += ")"
        
        # Add effect description if available
        if hasattr(move, 'effect') and move.effect:
            info += f" - {move.effect}"
            
        # Add strategic notes for common moves
        strategic_notes = {
            "stealthrock": "Sets hazards, damages on switch-in",
            "uturn": "Switches out after damage, maintains momentum",
            "voltswitch": "Switches out after damage, maintains momentum", 
            "protect": "Blocks attacks this turn, scouts moves",
            "substitute": "Creates decoy, blocks status",
            "swordsdance": "Sharply raises Attack (+2)",
            "dragondance": "Raises Attack and Speed (+1 each)",
            "calmmind": "Raises Sp.Atk and Sp.Def (+1 each)",
            "recover": "Restores 50% HP",
            "roost": "Restores 50% HP, loses Flying type this turn",
            "toxic": "Badly poisons (increasing damage)",
            "thunderwave": "Paralyzes, reduces speed by 50%",
            "willowisp": "Burns, halves physical attack",
            "taunt": "Prevents status moves for 3 turns",
            "defog": "Removes hazards from both sides",
            "rapidspin": "Removes hazards from your side"
        }
        
        if move.id in strategic_notes:
            info += f" [{strategic_notes[move.id]}]"
        
        return info
    
    def _get_strategic_considerations(self) -> str:
        """Add strategic thinking prompts."""
        return """
**Type Effectiveness Chart:**
```
Super Effective (2x): Fire→Grass/Bug/Steel/Ice, Water→Fire/Ground/Rock, Grass→Water/Ground/Rock
Electric→Water/Flying, Ice→Grass/Ground/Flying/Dragon, Fighting→Normal/Ice/Rock/Dark/Steel
Poison→Grass/Fairy, Ground→Fire/Electric/Poison/Rock/Steel, Flying→Grass/Fighting/Bug
Psychic→Fighting/Poison, Bug→Grass/Psychic/Dark, Rock→Fire/Ice/Flying/Bug
Ghost→Psychic/Ghost, Dragon→Dragon, Dark→Psychic/Ghost, Steel→Ice/Rock/Fairy, Fairy→Fighting/Dragon/Dark

Not Very Effective (0.5x): Fire→Water/Rock/Dragon, Water→Grass/Dragon, Grass→Fire/Flying/Poison/Bug/Steel/Dragon
Electric→Grass/Ground/Dragon, Ice→Fire/Water/Steel, Fighting→Flying/Poison/Psychic/Bug/Fairy
Poison→Poison/Ground/Rock/Ghost, Ground→Grass/Bug, Flying→Electric/Rock/Steel
Psychic→Psychic/Steel, Bug→Fire/Fighting/Flying/Poison/Ghost/Steel/Fairy
Rock→Fighting/Ground/Steel, Ghost→Dark, Dragon→Steel, Dark→Fighting/Dark/Fairy
Steel→Fire/Water/Electric/Steel, Fairy→Fire/Poison/Steel

No Effect (0x): Normal→Ghost, Electric→Ground, Fighting→Ghost, Poison→Steel
Ground→Flying, Psychic→Dark, Ghost→Normal, Dragon→Fairy
```

**Damage Calculation Guide:**
Approximate damage = (Move Power × STAB × Type Effectiveness × Stat Ratio)
- STAB (Same Type Attack Bonus): 1.5x if move type matches Pokemon type
- Critical hits: 1.5x damage (ignore defensive boosts)
- Weather boosts: 1.5x (Sun→Fire, Rain→Water)
- Abilities can modify damage (e.g., Overgrow boosts Grass moves at low HP)

Quick KO estimation:
- 4x super effective STAB move: Usually OHKOs
- 2x super effective STAB move: ~50-70% damage
- Neutral STAB move: ~25-40% damage
- Not very effective: ~10-20% damage

**Key Game Mechanics:**
1. **Speed & Priority**: Faster Pokemon moves first. Priority moves go before normal moves:
   - +2: Extreme Speed
   - +1: Quick Attack, Aqua Jet, Bullet Punch, Mach Punch, Ice Shard, Shadow Sneak
   - -1: Vital Throw
   - -4: Trick Room reverses speed order
   - -5: Counter, Mirror Coat
   - -6: Roar, Whirlwind, Dragon Tail, Circle Throw

2. **Status Conditions:**
   - Burn: -50% physical attack, chip damage
   - Paralysis: -50% speed, 25% chance to not move
   - Sleep: Can't move for 1-3 turns (Rest: 2 turns)
   - Poison: Chip damage each turn
   - Toxic: Increasing damage (1/16, 2/16, 3/16...)
   - Freeze: Can't move until thawed

3. **Entry Hazards:**
   - Stealth Rock: Rock-type damage on switch (12.5% neutral, up to 50%)
   - Spikes: Ground damage (1 layer=12.5%, 2=16.7%, 3=25%)
   - Toxic Spikes: Poisons (1 layer) or badly poisons (2 layers)
   - Sticky Web: -1 Speed on switch

4. **Important Abilities:**
   - Intimidate: -1 Attack on switch-in
   - Levitate: Immune to Ground moves
   - Sturdy: Survive OHKO at full HP
   - Magic Guard: No indirect damage
   - Regenerator: Heal 33% on switch
   - Prankster: +1 priority to status moves

**Meta-Game Context:**
1. **Common Roles:**
   - Setup Sweeper: Boosts stats then sweeps (e.g., Dragon Dance, Swords Dance)
   - Wall: High defenses, recovery moves
   - Pivot: U-turn/Volt Switch for momentum
   - Revenge Killer: Fast/priority to KO weakened foes
   - Hazard Setter/Remover: Controls field
   - Weather Setter: Enables weather teams

2. **Win Conditions:**
   - Eliminate opponent's answers to your win condition Pokemon
   - Set up a sweeper when checks are gone
   - Chip damage + priority move finishes
   - Stall with defensive Pokemon + hazards

**Situational Strategies:**
- vs Setup Sweeper: Use status moves (Thunder Wave), Haze, or revenge kill
- vs Stall: Use Taunt, setup moves, or wallbreakers
- vs Weather: Change weather or use Pokemon that benefit
- Low HP situations: Consider if you can tank a hit or need to switch
- Speed ties: Both Pokemon same speed = 50/50 who goes first

**Prediction Guidelines:**
- Opponent has Water-type in back → they'll likely switch if you have Electric move
- Opponent's Pokemon is setup bait → they might switch to prevent your setup
- You threaten KO → opponent likely to switch to a resist/immunity
- Consider risk/reward: Safe play vs prediction

**Strategic Considerations:**
- Calculate if you can KO before making aggressive plays
- Preserve win conditions and checks to opponent's threats  
- Manage hazards - when to set, when to remove
- Track opponent's move PP for stall situations
- Consider team preview - what's their likely lead and win condition?
- Momentum is key - force switches to rack up hazard damage
- Don't reveal all moves early unless necessary"""
    
    def _get_response_format(self) -> str:
        """Specify the expected response format."""
        return """
**Instructions:**
Based on the battle state above, choose the best action. You MUST use the EXACT move names and Pokemon names from the "Available Actions" section above.

Provide your response in this EXACT format:

action: "move" or "switch"
value: "exact_move_name" or "exact_pokemon_name"
reasoning: Brief explanation of your choice

IMPORTANT RULES:
1. Use the EXACT move name as shown in Available Actions (e.g., "flamethrower" not "Flamethrower" or "flame thrower")
2. Use the EXACT Pokemon name as shown in Available Actions (e.g., "Pikachu" not "pikachu")
3. Do NOT make up moves that aren't listed
4. Do NOT try to use moves from Pokemon that aren't currently active

Example responses:
action: move
value: flamethrower
reasoning: Super effective against opponent's Grass-type Pokemon

action: switch  
value: pikachu
reasoning: Current Pokemon is at low HP and weak to opponent's attacks"""
    
    def _calculate_type_effectiveness(self, attacking_type: PokemonType, defending_types: List[PokemonType]) -> float:
        """Calculate type effectiveness multiplier."""
        effectiveness = 1.0
        
        for def_type in defending_types:
            if attacking_type in self.type_chart and def_type in self.type_chart[attacking_type]:
                effectiveness *= self.type_chart[attacking_type][def_type]
            # If not in chart, it's neutral (1x)
        
        return effectiveness