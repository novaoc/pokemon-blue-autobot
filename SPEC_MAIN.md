# Module 4: Main Orchestrator + Integration

## Goal
Build `bot.py` — the main entry point that wires emulator, game state, battle AI, and navigation together
into a complete Pokemon Blue autobot.

## Context
- All other modules (emulator.py, memory.py, battle.py, navigation.py) are being built in parallel
- Read all SPEC_*.md files in this directory to understand the interfaces
- ROM: `/Users/wren/nova/games/gb/blueEng.gb`
- Guide: `/Users/wren/nova/games/pokemon_blue_guide.txt`
- PyBoy 2.7.0 installed

## bot.py Requirements

```python
#!/usr/bin/env python3
"""
Pokemon Blue Autobot
Plays through Pokemon Blue automatically using PyBoy emulator.
"""

class PokemonBot:
    def __init__(self, 
                 rom_path="/Users/wren/nova/games/gb/blueEng.gb",
                 headless=True,
                 speed=0,
                 screenshot_dir="screenshots",
                 log_level="INFO"):
        """
        Initialize all subsystems.
        headless=True for automated play (no window)
        speed=0 for max speed, 1 for normal
        """
    
    def start(self)
        """Start emulator, initialize game state, load save if exists"""
    
    def stop(self)
        """Clean shutdown — save state before exit"""
    
    def run(self, max_steps=None)
        """Main loop:
        1. Update game state
        2. If in battle: run battle AI
        3. Else: run progression manager
        4. Log progress
        5. Screenshot every N frames to screenshots/
        6. Repeat
        """
    
    def __enter__(self) / __exit__()
        """Context manager support"""
```

### Main entry point
```python
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pokemon Blue Autobot")
    parser.add_argument("--rom", default="/Users/wren/nova/games/gb/blueEng.gb")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--speed", type=int, default=0, help="0=max, 1=normal")
    parser.add_argument("--screenshots", action="store_true", help="Save periodic screenshots")
    parser.add_argument("--log", default="INFO")
    parser.add_argument("--step", type=str, help="Run a specific step only (e.g. 'pallet_town')")
    args = parser.parse_args()
    
    bot = PokemonBot(rom_path=args.rom, headless=args.headless, speed=args.speed)
    with bot:
        bot.run()
```

### Logging setup
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("pokemon_bot.log"),
        logging.StreamHandler()
    ]
)
```

### State loop pseudocode
```python
def run(self):
    while True:
        self.game_state.update()
        
        if self.game_state.in_battle:
            log.info(f"BATTLE: enemy={self.game_state.enemy_species}")
            self.battle_ai.handle_battle_turn()
        
        elif self.game_state.needs_heal:
            log.info("HEALING: party needs a Pokemon Center")
            go_to_pokecenter(self.navigator, self.game_state)
        
        else:
            next_step = self.progression.get_current_step()
            log.info(f"STEP: {next_step}")
            self.progression.run_next_step()
        
        self.emulator.tick(1)
```

## Also create: requirements.txt
```
pyboy>=2.7.0
Pillow>=10.0.0
numpy>=1.24.0
```

## Also create: README.md
Document:
- Setup instructions
- How to run
- Architecture overview
- Key memory addresses
- Known issues / limitations

## Integration checklist
When integrating all modules:
1. Check that all imports work
2. Verify PyBoy 2.x API calls are correct
3. Test that emulator starts headless
4. Test memory reads return plausible values
5. Test that button presses register in game

## Notes
- This is the integration layer — import from other modules, don't reimplement
- Add proper error handling: if emulator crashes, save state and retry
- Log every major action at INFO level
- Screenshots dir: create if doesn't exist
