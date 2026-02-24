# Module 3: Navigation + Overworld

## Goal
Build `navigation.py` — overworld navigation and progression logic for the Pokemon Blue autobot.

## Context
- Guide: `/Users/wren/nova/games/pokemon_blue_guide.txt` (read this file!)
- ROM: `/Users/wren/nova/games/gb/blueEng.gb`
- PyBoy 2.7.0 installed
- Works alongside emulator.py and memory.py (built in parallel — use stubs)

## navigation.py Requirements

### Map Waypoints
Define key waypoints for each major location. Each waypoint is a {map_id, x, y, action}.
```python
# Map IDs from memory.py
WAYPOINTS = {
    "pallet_start": {"map_id": 0x00, "x": 5, "y": 5},
    "route1_north": {"map_id": 0x0C, "x": 5, "y": 2},
    "viridian_pokecenter": {"map_id": 0x01, "x": 20, "y": 10},
    # ... fill these in using the walkthrough guide
}
```

### Direction system
```python
class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
```

### Navigator class
```python
class Navigator:
    def __init__(self, emulator, game_state)
    
    def move_one_step(self, direction: Direction) -> bool
        """Press direction button, wait for step to complete.
        Returns True if moved, False if blocked.
        Waits appropriate frames for walk animation (~12 frames/step).
        """
    
    def navigate_to(self, target_x: int, target_y: int, map_id: int = None) -> bool
        """Simple pathfinding: move towards target.
        Uses basic greedy approach: closer axis first.
        Detects if stuck (same position after 5 attempts) and tries alternate route.
        Returns True when reached target.
        """
    
    def press_a_interact(self)
        """Press A to interact with NPC/sign/door in front"""
    
    def mash_through_dialog(self, max_presses=50)
        """Press A repeatedly to advance dialog boxes.
        Stop when dialog flag clears or max presses reached.
        Wait enough frames between presses (~30 frames each).
        """
    
    def enter_door(self, door_x: int, door_y: int)
        """Walk to door position and enter (press UP or A)"""
    
    def exit_to_overworld(self)
        """Navigate to exit of current building/cave"""
```

### ProgressionManager class
This is the high-level "what to do next" brain.

```python
class ProgressionManager:
    def __init__(self, emulator, game_state, navigator, battle_ai)
    
    # Track progression state
    def load_state(self) -> dict   # Load from progression_state.json
    def save_state(self, state)    # Save to progression_state.json
    
    # Main progression steps (one method per major step)
    def step_pallet_town(self)
        """Start game, walk to Oak's lab, choose Squirtle"""
    
    def step_route1_to_viridian(self)
        """Walk north on Route 1, enter Viridian City"""
    
    def step_viridian_parcel(self)
        """Get parcel from mart, deliver to Oak, get Pokedex"""
    
    def step_viridian_forest(self)
        """Navigate through Viridian Forest to Pewter City"""
    
    def step_pewter_brock(self)
        """Heal, enter gym, beat Brock (Geodude L12, Onix L14)"""
    
    def step_mt_moon(self)
        """Navigate Route 3 and Mt. Moon to Cerulean"""
    
    def step_cerulean_misty(self)
        """Beat Misty (Staryu L18, Starmie L21)"""
    
    def step_nugget_bridge_bill(self)
        """Routes 24/25, Nugget Bridge, Bill's Cottage for SS Ticket"""
    
    def step_vermilion_ltsurge(self)
        """SS Anne (get Cut), beat Lt. Surge (Voltorb/Pikachu/Raichu)"""
    
    def step_rock_tunnel(self)
        """Route 9, Rock Tunnel (dark), Lavender Town"""
    
    def step_celadon_erika(self)
        """Rocket Hideout → Silph Scope → Erika gym"""
    
    def step_pokemon_tower(self)
        """Rescue Mr. Fuji → Poke Flute"""
    
    def step_saffron_sabrina(self)
        """Silph Co → Master Ball → Sabrina gym"""
    
    def step_fuchsia_koga(self)
        """Safari Zone (HM Surf + Strength) → Koga gym"""
    
    def step_cinnabar_blaine(self)
        """Surf to Cinnabar, Pokemon Mansion (Secret Key), Blaine gym"""
    
    def step_viridian_giovanni(self)
        """Final gym: Giovanni (Rhyhorn/Dugtrio/Nidoqueen/Nidoking/Rhydon)"""
    
    def step_elite_four(self)
        """Victory Road → Elite Four → Champion"""
    
    def get_current_step(self) -> str
        """Based on badges and flags, determine what to do next"""
    
    def run_next_step(self)
        """Execute the next progression step"""
    
    def run_full_game(self)
        """Main loop: keep running steps until game complete"""
```

### Healing logic
```python
def go_to_pokecenter(navigator, game_state)
    """Find and use nearest Pokemon Center.
    Navigate to pokecenter for current area, walk to counter, press A, mash through dialog.
    """
```

### Map ID reference (Pokemon Blue)
```python
MAP_IDS = {
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
    0x0E: "ROUTE_1",
    0x0F: "ROUTE_2",
    # ... etc
}
```

## Testing
Add `test_navigation.py` that:
1. Tests direction logic
2. Tests navigate_to with mock positions
3. Prints progression state for various badge counts

## Notes
- Read `/Users/wren/nova/games/pokemon_blue_guide.txt` for exact navigation steps
- Step animations: ~12-16 frames per tile in normal speed
- Dialog: wait ~30 frames, press A, repeat until dialog_flag = 0
- When stuck: try 3 steps in perpendicular direction, retry
- Always check `in_battle` before navigation steps
