# Module 2: Battle AI

## Goal
Build `battle.py` — the battle decision-making module for Pokemon Blue autobot.

## Context
- ROM: `/Users/wren/nova/games/gb/blueEng.gb`
- PyBoy 2.7.0 installed
- Works alongside `emulator.py` and `memory.py` (those are being built in parallel)
- Use stub/interface comments where those modules are referenced

## battle.py Requirements

### Type Chart (Gen 1 — note: some types differ from later gens)
```python
# Gen 1 type effectiveness (no Dark/Steel types)
# Bug is NOT super effective on Poison in Gen 1
# Ghost has NO EFFECT on Psychic in Gen 1 (bug)
# Ice is neutral to Fire in Gen 1
TYPE_CHART = { ... }  # Build the complete Gen 1 chart
```

### Pokemon species data
Include a dict `POKEMON_TYPES` with species ID -> (type1, type2) for at least the ~151 Gen 1 Pokemon.
Use actual species IDs (internal Gen 1 IDs, NOT Pokedex numbers):
- 0x99=Rhydon, 0x09=Blastoise, etc. 
  (Reference: https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_index_number_(Generation_I))

### Move data
Include `MOVE_DATA` dict: move_id -> {name, type, power, pp, category}
For at least the most common moves (Tackle, Scratch, Pound, Ember, Water Gun, Thundershock, Vine Whip, Gust, etc.) and all HM/TM moves.

### BattleAI class
```python
class BattleAI:
    def __init__(self, game_state)  # Takes a GameState instance
    
    def get_best_move(self) -> int
        """Returns move slot (0-3) to use based on:
        - Type effectiveness against enemy
        - Move power
        - Remaining PP
        Returns 0 if unsure (use first move)
        """
    
    def should_use_item(self) -> str | None
        """Returns item to use or None.
        Use Potion if HP < 50%. Use Max Potion if HP < 20%.
        Returns None if no healing needed.
        """
    
    def should_flee(self) -> bool
        """Wild battles only: flee if badly outleveled or stuck"""
    
    def get_action(self) -> dict
        """Main decision point. Returns:
        {"action": "fight", "move": 0-3}
        {"action": "item", "item": "POTION"}
        {"action": "flee"}
        {"action": "wait"}  # wait for text/animation
        """
    
    def execute_fight(self, move_slot: int)
        """Navigate battle menu to use specified move slot.
        Battle menu: FIGHT/PKMN/ITEM/RUN
        After FIGHT: move list (4 moves)
        Use emulator button presses to navigate.
        """
    
    def execute_item(self, item_name: str)
        """Use item from bag during battle"""
    
    def execute_flee(self)
        """Attempt to run from wild battle"""
    
    def handle_battle_turn(self)
        """Full turn: read state -> decide -> execute -> wait for animation"""
    
    def run_battle_loop(self)
        """Loop until battle ends (enemy fainted or fled)"""
```

### Battle menu navigation
The Gen 1 battle menu structure:
```
FIGHT  PKMN
ITEM   RUN
```
- Start at FIGHT
- Press A to select
- In move menu: 4 moves listed vertically
- Navigate with UP/DOWN arrows
- Press A to confirm, B to go back

### Memory addresses for battle (reference from memory.py being built in parallel):
```python
IN_BATTLE = 0xD057          # nonzero = in battle
BATTLE_TYPE = 0xD057        # 1=wild, 2=trainer
CURRENT_ENEMY_SPECIES = 0xCFD9  # Enemy species ID
PLAYER_ACTIVE_SPECIES = 0xD014  # Player's active species
PLAYER_CURRENT_HP = 0xD015  # Current HP (2 bytes big-endian)
PLAYER_MAX_HP = 0xD023      # Max HP (2 bytes)
ENEMY_CURRENT_HP = 0xCFE6   # Enemy current HP
ENEMY_MAX_HP = 0xCFF4       # Enemy max HP
PLAYER_MOVE1 = 0xD01C       # Move slot 1 ID
PLAYER_MOVE2 = 0xD01D       # Move slot 2 ID
PLAYER_MOVE3 = 0xD01E       # Move slot 3 ID
PLAYER_MOVE4 = 0xD01F       # Move slot 4 ID
PLAYER_MOVE1_PP = 0xD02D    # Move 1 PP remaining
BATTLE_MENU_CURSOR = 0xCC26 # Current cursor in battle menu
```

## Testing
Add `test_battle.py` that:
1. Tests type effectiveness calculation (Water vs Fire = 2x, etc.)
2. Tests move selection logic with mock game state
3. Prints expected actions for sample scenarios

## Notes
- Gen 1 bugs to account for: Ghost moves don't affect Psychic (0x damage), Focus Energy halves crit rate (inverted bug)
- Priority: type advantage > move power
- Don't use a move with 0 PP
