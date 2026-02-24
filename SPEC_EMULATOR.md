# Module 1: Emulator Core + Memory Reader

## Goal
Build `emulator.py` and `memory.py` — the foundation layer for the Pokemon Blue autobot.

## Context
- ROM: `/Users/wren/nova/games/gb/blueEng.gb`
- Save: `/Users/wren/nova/games/gb/blueEng.sav`
- PyBoy 2.7.0 is installed (`import pyboy` works)
- Game: Pokemon Blue (GameBoy)
- Guide: `/Users/wren/nova/games/pokemon_blue_guide.txt`

## emulator.py Requirements

Create `emulator.py` with class `PokemonEmulator`:
```python
class PokemonEmulator:
    def __init__(self, rom_path, headless=True, speed=0)
    def start(self)                    # Initialize PyBoy, load ROM
    def stop(self)                     # Cleanly shut down
    def tick(self, frames=1)           # Advance N frames
    def press(self, button, frames=10) # Press button and release (UP/DOWN/LEFT/RIGHT/A/B/START/SELECT)
    def get_screen(self)               # Returns PIL Image of current screen
    def get_screen_array(self)         # Returns numpy array (160x144 RGB)
    def save_screenshot(self, path)    # Save screen to file
    def read_memory(self, addr)        # Read 1 byte from Game Boy memory
    def read_memory_range(self, addr, length)  # Read N bytes
    def load_state(self, path)         # Load a save state
    def save_state(self, path)         # Save current state
```

Button mapping for PyBoy 2.x:
- Use `pyboy.button("up")` / `pyboy.button_release("up")` or check PyBoy 2.x API
- Valid buttons: "up", "down", "left", "right", "a", "b", "start", "select"
- Speed: 0 = unlimited, 1 = normal speed

## memory.py Requirements

Create `memory.py` with Pokemon Blue Gen 1 memory addresses and `GameState` class:

### Key Memory Addresses (Pokemon Blue / Red shared layout)
```python
# Player
PLAYER_X = 0xD361          # X position on current map
PLAYER_Y = 0xD362          # Y position
MAP_ID = 0xD35E            # Current map ID

# Battle
BATTLE_TYPE = 0xD057       # 0=no battle, 1=wild, 2=trainer
IN_BATTLE = 0xD057         # nonzero = in battle
PLAYER_CURRENT_HP = 0xD015 # Current HP of active Pokemon
PLAYER_MAX_HP = 0xD023     # Max HP
ENEMY_CURRENT_HP = 0xCFE6  # Enemy HP
ENEMY_MAX_HP = 0xCFF4      # Enemy max HP

# Party
PARTY_COUNT = 0xD163       # Number of Pokemon in party
PARTY_MON1_HP = 0xD16C     # Party slot 1 current HP (2 bytes, big-endian)
PARTY_MON1_MAXHP = 0xD18D  # Party slot 1 max HP (2 bytes)
PARTY_MON1_SPECIES = 0xD164 # Species ID of slot 1
# Slots 2-6 offset by 0x2C each from slot 1

# Battle menu
BATTLE_CURSOR = 0xCC26     # Battle menu cursor position
CURRENT_MENU = 0xCC24      # Current menu type
DIALOG_BOX = 0xC4F1        # Dialog open flag

# Text / Dialog
TEXT_ID = 0xCFC4           # Current text message ID
OVERWORLD_TEXT = 0xC3A0    # Text display flag

# Flags / Progression
BADGES = 0xD356            # Bitfield: badge 0=Boulder, 1=Cascade, etc.
HM_MOVES_LEARNED = 0xD730  # HM flags

# Items
ITEM_COUNT = 0xD31D        # Number of items in bag
MONEY = 0xD347             # Money (3 bytes BCD)

# Map names (key map IDs)
MAP_NAMES = {
    0x00: "PALLET_TOWN",
    0x01: "VIRIDIAN_CITY",
    0x02: "PEWTER_CITY",
    0x03: "CERULEAN_CITY",
    0x0C: "VERMILION_CITY",
    0x0D: "LAVENDER_TOWN",
    0x11: "CELADON_CITY",
    0x12: "FUCHSIA_CITY",
    0x13: "CINNABAR_ISLAND",
    0x14: "INDIGO_PLATEAU",
    0x15: "SAFFRON_CITY",
    # etc.
}
```

### GameState class
```python
class GameState:
    def __init__(self, emu: PokemonEmulator)
    
    def update(self)          # Read all relevant memory, update internal state
    
    # Properties:
    @property
    def in_battle(self) -> bool
    @property
    def map_id(self) -> int
    @property
    def map_name(self) -> str
    @property
    def player_x(self) -> int
    @property
    def player_y(self) -> int
    @property
    def player_hp(self) -> int
    @property
    def player_max_hp(self) -> int
    @property
    def enemy_hp(self) -> int
    @property
    def badges(self) -> int   # bitfield
    @property
    def party(self) -> list[dict]  # list of {species, hp, max_hp}
    @property
    def party_healthy(self) -> bool  # any pokemon with >0 HP
    @property
    def needs_heal(self) -> bool   # any pokemon at <30% HP
    
    def __str__(self)  # Nice debug string
```

## Testing
Add a `test_emulator.py` that:
1. Starts the emulator headless
2. Advances 60 frames
3. Reads player position and map ID
4. Prints GameState
5. Saves a screenshot to `screenshots/init.png`

## Notes
- PyBoy 2.x API: `pyboy = PyBoy(rom_path, window="null")` for headless
- Use `pyboy.memory[addr]` for memory reads in PyBoy 2.x
- Research the correct PyBoy 2.x API if unsure — don't guess
- All addresses are for Pokemon Blue English (same as Red)
