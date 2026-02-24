# Pokemon Blue Autobot

An automated bot that plays through Pokemon Blue using the [PyBoy](https://github.com/Baekalfen/PyBoy) Game Boy emulator. The bot drives itself through the entire main story using memory-based game state reading, type-chart-aware battle AI, and a scripted progression system.

---

## Setup

**Requirements:** Python 3.10+

```bash
# 1. Clone / enter the project directory
cd /Users/wren/nova/pokemon-bot

# 2. (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

```bash
# Basic: headless, unlimited speed
python bot.py --rom /Users/wren/nova/games/gb/blueEng.gb

# With a display window (SDL2)
python bot.py --rom /path/to/blueEng.gb --no-headless --speed 1

# Save screenshots every 300 frames
python bot.py --rom /path/to/blueEng.gb --screenshots

# Load / save emulator state
python bot.py --rom /path/to/blueEng.gb --save-state saves/checkpoint.state

# Run only a specific progression step (debug mode)
python bot.py --rom /path/to/blueEng.gb --step pewter_brock

# Limit to N loop iterations
python bot.py --rom /path/to/blueEng.gb --max-steps 10000

# Verbose logging
python bot.py --rom /path/to/blueEng.gb --log DEBUG
```

### CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--rom PATH` | `/Users/wren/nova/games/gb/blueEng.gb` | ROM path |
| `--headless` / `--no-headless` | headless | Show window or not |
| `--speed N` | `0` | 0 = unlimited, 1 = normal speed |
| `--screenshots` | off | Save PNG every 300 frames |
| `--screenshot-dir DIR` | `./screenshots` | Screenshot output directory |
| `--log LEVEL` | `INFO` | Logging level |
| `--log-file PATH` | `pokemon_bot.log` | Log file path |
| `--save-state PATH` | none | Load/save emulator state |
| `--max-steps N` | none | Stop after N iterations |
| `--step NAME` | none | Run one specific step |

---

## Architecture

The bot is structured as five modules:

```
bot.py                   ← Orchestrator (you are here)
├── emulator.py          ← PyBoy 2.7.0 wrapper
├── memory.py            ← Gen 1 memory map + GameState reader
├── battle.py            ← Type chart + BattleAI decision engine
└── navigation.py        ← Navigator (pathfinding) + ProgressionManager
```

### Module Overview

#### `emulator.py` — `PokemonEmulator`
Thin wrapper around PyBoy 2.7.0.  Provides:
- `start()` / `stop()` lifecycle
- `tick(frames)` — advance emulator
- `press(button, frames)` — press-and-release input
- `read_memory(addr)` — single-byte memory read
- `save_state(path)` / `load_state(path)` — emulator snapshots
- `get_screen()` / `save_screenshot(path)` — screen capture

#### `memory.py` — `GameState`
Reads Gen 1 memory addresses each frame.  Exposes:
- `update()` — refresh all values from memory
- `in_battle`, `battle_type` — battle detection
- `map_id`, `map_name`, `player_x`, `player_y` — position
- `player_hp`, `player_max_hp`, `enemy_hp`, `enemy_max_hp`
- `badges`, `badge_count` — gym progress
- `party` — list of party Pokémon dicts `{slot, species, hp, max_hp}`
- `needs_heal` — True if any Pokémon is below 30% HP
- `dialog_open` — True if a text box is currently displayed

#### `battle.py` — `BattleAI`
Handles all in-battle decisions using Gen 1 type chart and move data.
- `get_action()` → `{action: fight|item|flee, move: 0-3}`
- `handle_battle_turn()` — executes one complete turn
- `run_battle_loop(max_turns)` — loops until battle ends
- Full Gen 1 type chart (with historical bugs: Ghost→Psychic = 0x, etc.)
- All 152 move entries with type / base power / PP

#### `navigation.py` — `Navigator` + `ProgressionManager`
- `Navigator.navigate_to(x, y)` — greedy pathfinding with stuck detection
- `Navigator.enter_building(door_x, door_y)` — building entry
- `Navigator.mash_through_dialog(max_presses)` — text dismissal
- `go_to_pokecenter(navigator, game_state)` — nearest Pokecenter healing
- `ProgressionManager` — 17-step scripted walkthrough from Pallet Town to the Elite Four

#### `bot.py` — `PokemonBot`
Main orchestrator.  Each loop iteration:
1. `game_state.update()` — read memory
2. If `in_battle` → `battle_ai.handle_battle_turn()`
3. Else if `needs_heal` → `go_to_pokecenter()`
4. Else → `progression.run_next_step()`
5. `emulator.tick(1)` — advance one frame

---

## Key Gen 1 Memory Addresses

| Address | Name | Description |
|---------|------|-------------|
| `0xD057` | `BATTLE_TYPE` | 0=none, 1=wild, 2=trainer battle |
| `0xD35E` | `MAP_ID` | Current map (see `MAP_NAMES` in memory.py) |
| `0xD361` | `PLAYER_X` | Player X tile coordinate |
| `0xD362` | `PLAYER_Y` | Player Y tile coordinate |
| `0xD015`–`0xD016` | `PLAYER_HP` | Active Pokémon current HP (big-endian) |
| `0xD023`–`0xD024` | `PLAYER_MAX_HP` | Active Pokémon max HP (big-endian) |
| `0xCFE6`–`0xCFE7` | `ENEMY_HP` | Enemy Pokémon current HP |
| `0xCFF4`–`0xCFF5` | `ENEMY_MAX_HP` | Enemy Pokémon max HP |
| `0xD163` | `PARTY_COUNT` | Number of Pokémon in party (0–6) |
| `0xD164` | `PARTY_MON1_SPECIES` | Species ID of party slot 1 |
| `0xD356` | `BADGES` | Badge bitfield (bit 0=Boulder … bit 7=Earth) |
| `0xD014` | `PLAYER_SPECIES` | Active battle Pokémon species index |
| `0xCFD9` | `ENEMY_SPECIES` | Enemy species index |
| `0xD01C`–`0xD01F` | `PLAYER_MOVE1–4` | Move IDs in active Pokémon's moveset |
| `0xD02D`–`0xD030` | `PLAYER_MOVE_PP` | PP remaining for each move slot |
| `0xC4F1` | `DIALOG_BOX` | Non-zero when a text dialog is open |

All addresses are for **Pokemon Blue (English)** — identical to Pokemon Red.

---

## Progression Steps

The bot follows these 17 steps in order:

1. `pallet_start` — Choose Squirtle, beat Rival
2. `route1_to_viridian` — Walk Route 1 north
3. `viridian_parcel` — Collect Oak's Parcel, get Pokédex
4. `viridian_forest` — Navigate forest to Pewter
5. `pewter_brock` — Beat Brock (Boulder Badge)
6. `mt_moon` — Navigate Mt. Moon caves
7. `cerulean_misty` — Beat Misty (Cascade Badge)
8. `nugget_bridge_bill` — Cross bridge, get S.S. Ticket
9. `vermilion_ltsurge` — S.S. Anne + Cut, beat Lt. Surge (Thunder Badge)
10. `rock_tunnel` — Navigate dark Rock Tunnel
11. `celadon_erika` — Rocket Hideout + Silph Scope, beat Erika (Rainbow Badge)
12. `pokemon_tower` — Rescue Mr. Fuji, get Pokéflute
13. `saffron_sabrina` — Silph Co. + Card Key, beat Sabrina (Marsh Badge)
14. `fuchsia_koga` — Safari Zone (Surf), beat Koga (Soul Badge)
15. `cinnabar_blaine` — Pokémon Mansion (Secret Key), beat Blaine (Volcano Badge)
16. `viridian_giovanni` — Beat Giovanni (Earth Badge)
17. `elite_four` — Victory Road + Elite Four + Champion

---

## Known Limitations

- **Navigation is greedy/approximate** — coordinates in `navigation.py` are estimates. The bot may get stuck on walls or miss exact tile positions. The stuck-detection escape helps but isn't perfect.
- **Battle menu timing** — battle UI navigation assumes the cursor is in default position. Menu lag or glitched states can cause misaligned inputs.
- **Dialog detection** — `dialog_open` reads a single flag byte (`0xC4F1`). Some cutscenes use different flags and may not be detected correctly.
- **No healing item logic** — the bag-navigation code in `BattleAI.execute_item()` is simplified and may not reliably find specific items.
- **Multi-floor dungeons** — Mt. Moon, Rock Tunnel, Silph Co. etc. have tile coordinates hard-coded as estimates; real staircase positions may differ.
- **Trainer battles mid-route** — trainers that initiate battle mid-navigation interrupt the progression step. The main loop handles them via BattleAI but may not resume the step correctly.
- **No Pokémon catching** — the bot does not catch wild Pokémon. It fights or flees from every encounter.
- **Memory addresses are for Blue (EN)** — will not work correctly with Red, Yellow, or non-English versions.
- **PyBoy 2.x API** — confirmed working with PyBoy 2.7.0. Earlier or later versions may have different APIs.
