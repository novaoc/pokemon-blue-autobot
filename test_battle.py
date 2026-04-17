"""
test_battle.py — Unit tests for battle.py (Battle AI module)

Tests type effectiveness, move selection logic, and action decisions
using mock game state (no PyBoy/ROM required).
"""

import sys
import traceback
from battle import (
    get_effectiveness,
    POKEMON_TYPES, SPECIES_TYPES, MOVE_DATA, TYPE_CHART,
    BattleAI,
    NORMAL, FIGHTING, FLYING, POISON, GROUND, ROCK, BUG, GHOST,
    FIRE, WATER, GRASS, ELECTRIC, PSYCHIC, ICE, DRAGON,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

_results = []

def check(description: str, got, expected, tolerance: float = 1e-9):
    if isinstance(got, str) and isinstance(expected, str):
        ok = got == expected
    elif got is None or expected is None:
        ok = got is expected
    else:
        ok = abs(got - expected) < tolerance
    status = PASS if ok else FAIL
    print(f"  [{status}] {description}: got={got!r}, expected={expected!r}")
    _results.append(ok)
    return ok

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


# ---------------------------------------------------------------------------
# Mock PyBoy for BattleAI tests (no ROM needed)
# ---------------------------------------------------------------------------

class MockPyBoy:
    """Minimal PyBoy 2.x mock: wraps a flat memory dict."""

    def __init__(self, mem: dict):
        self._mem = mem
        self.buttons_pressed = []
        self.ticks = 0

    @property
    def memory(self):
        return self._mem

    def button(self, btn):
        self.buttons_pressed.append(f"press:{btn}")

    def button_release(self, btn):
        self.buttons_pressed.append(f"release:{btn}")

    def tick(self, n=1):
        self.ticks += n


def make_mock_state(
    *,
    battle_type: int = 1,          # 1=wild
    player_species: int = 0xB0,    # Squirtle (Water)
    player_hp: int = 100,
    player_max_hp: int = 100,
    enemy_species: int = 0xAF,     # Charmander (Fire)
    enemy_hp: int = 50,
    moves: list = None,            # list of (move_id, pp) tuples, length 4
    bag_items: list = None,        # list of (item_id, quantity) tuples; None = default potions
):
    if moves is None:
        # Squirtle starter set: Tackle, Tail Whip, Water Gun, Withdraw
        moves = [
            (0x21, 35),  # Tackle (Normal, 35 power)
            (0x27, 30),  # Tail Whip (Normal, 0 power)
            (0x37, 25),  # Water Gun (Water, 40 power)
            (0x6E, 40),  # Withdraw (Water, 0 power)
        ]

    if bag_items is None:
        # Default: give the bot some potions to use
        bag_items = [
            (0x10, 3),  # POTION x3
            (0x12, 1),  # HYPER POTION x1
        ]

    mem = {}
    mem[0xD057] = battle_type

    mem[0xD014] = player_species
    mem[0xD015] = (player_hp >> 8) & 0xFF
    mem[0xD016] = player_hp & 0xFF
    mem[0xD023] = (player_max_hp >> 8) & 0xFF
    mem[0xD024] = player_max_hp & 0xFF

    mem[0xCFD9] = enemy_species
    mem[0xCFE6] = (enemy_hp >> 8) & 0xFF
    mem[0xCFE7] = enemy_hp & 0xFF

    move_addrs = [0xD01C, 0xD01D, 0xD01E, 0xD01F]
    pp_addrs   = [0xD02D, 0xD02E, 0xD02F, 0xD030]
    for i, (mid, pp) in enumerate(moves):
        mem[move_addrs[i]] = mid
        mem[pp_addrs[i]]   = pp

    # Bag items: [count] [id, qty] [id, qty] ...
    mem[0xD31D] = len(bag_items)
    for i, (item_id, qty) in enumerate(bag_items):
        mem[0xD31E + i * 2] = item_id
        mem[0xD31E + i * 2 + 1] = qty

    return mem


# ---------------------------------------------------------------------------
# Test 1: Type Effectiveness
# ---------------------------------------------------------------------------

def test_type_effectiveness():
    section("Type Effectiveness")

    # Super effective cases (2.0x)
    check("Water vs Fire",           get_effectiveness(WATER,    (FIRE,    None)),  2.0)
    check("Fire vs Grass",            get_effectiveness(FIRE,     (GRASS,   None)),  2.0)
    check("Fire vs Ice",              get_effectiveness(FIRE,     (ICE,     None)),  2.0)
    check("Electric vs Water",        get_effectiveness(ELECTRIC, (WATER,   None)),  2.0)
    check("Electric vs Flying",       get_effectiveness(ELECTRIC, (FLYING,  None)),  2.0)
    check("Grass vs Water",           get_effectiveness(GRASS,    (WATER,   None)),  2.0)
    check("Ice vs Grass",             get_effectiveness(ICE,      (GRASS,   None)),  2.0)
    check("Ice vs Ground",            get_effectiveness(ICE,      (GROUND,  None)),  2.0)
    check("Ice vs Dragon",            get_effectiveness(ICE,      (DRAGON,  None)),  2.0)
    check("Ground vs Fire",           get_effectiveness(GROUND,   (FIRE,    None)),  2.0)
    check("Ground vs Electric",       get_effectiveness(GROUND,   (ELECTRIC,None)),  2.0)
    check("Ground vs Poison",         get_effectiveness(GROUND,   (POISON,  None)),  2.0)
    check("Ground vs Rock",           get_effectiveness(GROUND,   (ROCK,    None)),  2.0)
    check("Rock vs Fire",             get_effectiveness(ROCK,     (FIRE,    None)),  2.0)
    check("Rock vs Ice",              get_effectiveness(ROCK,     (ICE,     None)),  2.0)
    check("Rock vs Flying",           get_effectiveness(ROCK,     (FLYING,  None)),  2.0)
    check("Psychic vs Fighting",      get_effectiveness(PSYCHIC,  (FIGHTING,None)),  2.0)
    check("Psychic vs Poison",        get_effectiveness(PSYCHIC,  (POISON,  None)),  2.0)
    check("Bug vs Psychic",           get_effectiveness(BUG,      (PSYCHIC, None)),  2.0)
    check("Bug vs Grass",             get_effectiveness(BUG,      (GRASS,   None)),  2.0)
    check("Poison vs Grass",          get_effectiveness(POISON,   (GRASS,   None)),  2.0)
    check("Fighting vs Normal",       get_effectiveness(FIGHTING, (NORMAL,  None)),  2.0)
    check("Fighting vs Ice",          get_effectiveness(FIGHTING, (ICE,     None)),  2.0)
    check("Fighting vs Rock",         get_effectiveness(FIGHTING, (ROCK,    None)),  2.0)
    check("Dragon vs Dragon",         get_effectiveness(DRAGON,   (DRAGON,  None)),  2.0)
    check("Ghost vs Ghost",           get_effectiveness(GHOST,    (GHOST,   None)),  2.0)

    # Not very effective (0.5x)
    check("Normal vs Rock",           get_effectiveness(NORMAL,   (ROCK,    None)),  0.5)
    check("Fire vs Fire",             get_effectiveness(FIRE,     (FIRE,    None)),  0.5)
    check("Water vs Water",           get_effectiveness(WATER,    (WATER,   None)),  0.5)
    check("Water vs Grass",           get_effectiveness(WATER,    (GRASS,   None)),  0.5)
    check("Electric vs Grass",        get_effectiveness(ELECTRIC, (GRASS,   None)),  0.5)
    check("Electric vs Electric",     get_effectiveness(ELECTRIC, (ELECTRIC,None)),  0.5)
    check("Grass vs Fire",            get_effectiveness(GRASS,    (FIRE,    None)),  0.5)
    check("Grass vs Poison",          get_effectiveness(GRASS,    (POISON,  None)),  0.5)
    check("Ice vs Water",             get_effectiveness(ICE,      (WATER,   None)),  0.5)
    check("Ice vs Ice",               get_effectiveness(ICE,      (ICE,     None)),  0.5)
    check("Bug vs Fire",              get_effectiveness(BUG,      (FIRE,    None)),  0.5)
    check("Bug vs Flying",            get_effectiveness(BUG,      (FLYING,  None)),  0.5)
    check("Bug vs Poison",            get_effectiveness(BUG,      (POISON,  None)),  0.5)  # Gen 1
    check("Bug vs Fighting",          get_effectiveness(BUG,      (FIGHTING,None)),  0.5)
    check("Poison vs Poison",         get_effectiveness(POISON,   (POISON,  None)),  0.5)
    check("Poison vs Ground",         get_effectiveness(POISON,   (GROUND,  None)),  0.5)
    check("Poison vs Rock",           get_effectiveness(POISON,   (ROCK,    None)),  0.5)
    check("Poison vs Ghost",          get_effectiveness(POISON,   (GHOST,   None)),  0.5)
    check("Fighting vs Poison",       get_effectiveness(FIGHTING, (POISON,  None)),  0.5)
    check("Fighting vs Flying",       get_effectiveness(FIGHTING, (FLYING,  None)),  0.5)
    check("Fighting vs Psychic",      get_effectiveness(FIGHTING, (PSYCHIC, None)),  0.5)
    check("Fighting vs Bug",          get_effectiveness(FIGHTING, (BUG,     None)),  0.5)
    check("Psychic vs Psychic",       get_effectiveness(PSYCHIC,  (PSYCHIC, None)),  0.5)

    # Immune (0.0x)
    check("Normal vs Ghost",          get_effectiveness(NORMAL,   (GHOST,   None)),  0.0)
    check("Electric vs Ground",       get_effectiveness(ELECTRIC, (GROUND,  None)),  0.0)
    check("Ground vs Flying",         get_effectiveness(GROUND,   (FLYING,  None)),  0.0)
    check("Fighting vs Ghost",        get_effectiveness(FIGHTING, (GHOST,   None)),  0.0)
    check("Ghost vs Normal",          get_effectiveness(GHOST,    (NORMAL,  None)),  0.0)
    check("Ghost vs Psychic (Gen 1 bug)", get_effectiveness(GHOST, (PSYCHIC, None)), 0.0)
    check("Psychic vs Ghost",         get_effectiveness(PSYCHIC,  (GHOST,   None)),  0.0)

    # Neutral (1.0x)
    check("Normal vs Normal",         get_effectiveness(NORMAL,   (NORMAL,  None)),  1.0)
    check("Water vs Fire (1.0?)",     get_effectiveness(FIRE,     (WATER,   None)),  0.5)  # fire not eff vs water
    check("Ice vs Fire (Gen 1 neutral)", get_effectiveness(ICE,   (FIRE,    None)),  1.0)  # Gen 1 quirk
    check("Poison vs Bug (Gen 1)",    get_effectiveness(POISON,   (BUG,     None)),  1.0)  # Gen 1 quirk

    # Dual-type combinations
    # Charizard = Fire/Flying -> Water should be 2.0 * 1.0 = 2.0
    check("Water vs Charizard (Fire/Flying)", get_effectiveness(WATER, (FIRE, FLYING)), 2.0)
    # Gengar = Ghost/Poison -> Normal should be 0.0 * 0.5 = 0.0
    check("Normal vs Gengar (Ghost/Poison)", get_effectiveness(NORMAL, (GHOST, POISON)), 0.0)
    # Geodude = Rock/Ground -> Water should be 2.0 * 2.0 = 4.0
    check("Water vs Geodude (Rock/Ground)", get_effectiveness(WATER, (ROCK, GROUND)), 4.0)
    # Gyarados = Water/Flying -> Electric: Water=2.0 * Flying=2.0 = 4.0
    check("Electric vs Gyarados (Water/Flying)", get_effectiveness(ELECTRIC, (WATER, FLYING)), 4.0)
    # Gyarados = Water/Flying -> Ground should be 0.0 (Flying immune)
    check("Ground vs Gyarados (Water/Flying)", get_effectiveness(GROUND, (WATER, FLYING)), 0.0)
    # Parasect = Bug/Grass -> Fire: Fire vs Bug=2.0 * Fire vs Grass=2.0 → 4.0
    # (Note: Bug vs Fire=0.5, but here Fire is ATTACKING Bug, which is 2x)
    check("Fire vs Parasect (Bug/Grass)", get_effectiveness(FIRE, (BUG, GRASS)), 4.0)  # 2.0*2.0
    # Poliwrath = Water/Fighting -> Psychic: Psychic vs Water=1.0 * Psychic vs Fighting=2.0 → 2.0
    check("Psychic vs Poliwrath (Water/Fighting)", get_effectiveness(PSYCHIC, (WATER, FIGHTING)), 2.0)


# ---------------------------------------------------------------------------
# Test 2: POKEMON_TYPES completeness
# ---------------------------------------------------------------------------

def test_pokemon_types():
    section("Pokemon Types Data")

    # All 151 Gen 1 Pokemon should be present
    count = len(POKEMON_TYPES)
    print(f"  [{'PASS' if count >= 151 else 'FAIL'}] Pokemon count: {count} (expected >= 151)")
    _results.append(count >= 151)

    # Spot-checks for known Pokemon with correct internal indices
    spot_checks = [
        (0x01, "Rhydon",     (GROUND,   ROCK)),
        (0x0E, "Gengar",     (GHOST,    POISON)),
        (0x1C, "Blastoise",  (WATER,    None)),
        (0x35, "Magneton",   (ELECTRIC, None)),
        (0x41, "Dragonite",  (DRAGON,   FLYING)),
        (0x53, "Pikachu",    (ELECTRIC, None)),
        (0x82, "Mewtwo",     (PSYCHIC,  None)),
        (0x83, "Snorlax",    (NORMAL,   None)),
        (0x98, "Bulbasaur",  (GRASS,    POISON)),
        (0x9A, "Tentacruel", (WATER,    POISON)),
        (0xAF, "Charmander", (FIRE,     None)),
        (0xB0, "Squirtle",   (WATER,    None)),
        (0xB3, "Charizard",  (FIRE,     FLYING)),
        (0xAA, "Aerodactyl", (ROCK,     FLYING)),
        (0x15, "Mew",        (PSYCHIC,  None)),
        (0x47, "Jynx",       (ICE,      PSYCHIC)),
        (0x48, "Moltres",    (FIRE,     FLYING)),
        (0x49, "Articuno",   (ICE,      FLYING)),
        (0x4A, "Zapdos",     (ELECTRIC, FLYING)),
        (0x08, "Slowbro",    (WATER,    PSYCHIC)),
        (0x97, "Starmie",    (WATER,    PSYCHIC)),
        (0x16, "Gyarados",   (WATER,    FLYING)),
    ]
    for idx, name, expected_types in spot_checks:
        entry = POKEMON_TYPES.get(idx)
        if entry is None:
            print(f"  [{FAIL}] {name} (0x{idx:02X}): not found")
            _results.append(False)
            continue
        actual_types = entry[1]
        ok = actual_types == expected_types
        print(f"  [{'PASS' if ok else 'FAIL'}] 0x{idx:02X} {name}: {actual_types!r} == {expected_types!r}")
        _results.append(ok)


# ---------------------------------------------------------------------------
# Test 3: MOVE_DATA completeness and key moves
# ---------------------------------------------------------------------------

def test_move_data():
    section("Move Data")

    key_moves = [
        (0x16, "Vine Whip",    GRASS,    35,   10),
        (0x21, "Tackle",       NORMAL,   35,   35),
        (0x34, "Ember",        FIRE,     40,   25),
        (0x35, "Flamethrower", FIRE,     95,   15),
        (0x37, "Water Gun",    WATER,    40,   25),
        (0x38, "Hydro Pump",   WATER,   120,    5),
        (0x39, "Surf",         WATER,    95,   15),
        (0x3A, "Ice Beam",     ICE,      95,   10),
        (0x3B, "Blizzard",     ICE,     120,    5),
        (0x3F, "Hyper Beam",   NORMAL,  150,    5),
        (0x54, "Thundershock", ELECTRIC, 40,   30),
        (0x55, "Thunderbolt",  ELECTRIC, 95,   15),
        (0x57, "Thunder",      ELECTRIC,120,   10),
        (0x59, "Earthquake",   GROUND,  100,   10),
        (0x5E, "Psychic",      PSYCHIC,  90,   10),
        (0x7E, "Fire Blast",   FIRE,    120,    5),
        (0x4B, "Razor Leaf",   GRASS,    55,   25),
        (0x4C, "SolarBeam",    GRASS,   120,   10),
        (0x96, "Slash",        NORMAL,   70,   20),
        (0x98, "Struggle",     NORMAL,   50,    1),
    ]

    for mid, name, mtype, power, pp in key_moves:
        data = MOVE_DATA.get(mid)
        if data is None:
            print(f"  [{FAIL}] 0x{mid:02X} {name}: not found in MOVE_DATA")
            _results.append(False)
            continue
        ok_name  = data["name"]  == name
        ok_type  = data["type"]  == mtype
        ok_power = data["power"] == power
        ok_pp    = data["pp"]    == pp
        ok = ok_name and ok_type and ok_power and ok_pp
        _results.append(ok)
        if ok:
            print(f"  [{PASS}] 0x{mid:02X} {name}")
        else:
            print(f"  [{FAIL}] 0x{mid:02X} {name}: got {data!r}")
            if not ok_name:  print(f"          name:  got {data['name']!r}, expected {name!r}")
            if not ok_type:  print(f"          type:  got {data['type']!r}, expected {mtype!r}")
            if not ok_power: print(f"          power: got {data['power']!r}, expected {power!r}")
            if not ok_pp:    print(f"          pp:    got {data['pp']!r}, expected {pp!r}")

    total_moves = len(MOVE_DATA)
    print(f"\n  Total moves in MOVE_DATA: {total_moves} (Gen 1 has 165 moves, 0x01-0x98)")
    _results.append(total_moves >= 100)
    print(f"  [{'PASS' if total_moves >= 100 else 'FAIL'}] At least 100 moves present")


# ---------------------------------------------------------------------------
# Test 4: BattleAI — get_best_move
# ---------------------------------------------------------------------------

def test_battle_ai_move_selection():
    section("BattleAI — get_best_move()")

    # Scenario: Squirtle (Water) vs Charmander (Fire)
    # Moves: Tackle (Normal 35 pw), Tail Whip (Normal 0 pw),
    #        Water Gun (Water 40 pw), Withdraw (Water 0 pw)
    # Water Gun vs Fire = 40 * 2.0 = 80, with STAB = 80 * 1.5 = 120 → best
    mem = make_mock_state(
        player_species=0xB0,  # Squirtle (Water)
        enemy_species=0xAF,   # Charmander (Fire)
    )
    ai = BattleAI(MockPyBoy(mem))
    best = ai.get_best_move()
    check("Squirtle vs Charmander → Water Gun (slot 2)", best, 2)

    # Scenario: all moves have 0 PP except Tackle → should use Tackle (slot 0)
    mem2 = make_mock_state(
        player_species=0xB0,
        enemy_species=0xAF,
        moves=[
            (0x21, 5),  # Tackle — only move with PP
            (0x27, 0),  # Tail Whip — 0 PP
            (0x37, 0),  # Water Gun — 0 PP
            (0x6E, 0),  # Withdraw — 0 PP
        ],
    )
    ai2 = BattleAI(MockPyBoy(mem2))
    best2 = ai2.get_best_move()
    check("Only Tackle has PP → slot 0", best2, 0)

    # Scenario: Pikachu (Electric) vs Gyarados (Water/Flying)
    # Thunderbolt (Electric 95) vs Gyarados: Water=2.0, Flying=2.0 → eff=4.0, score=95*4.0*1.5=570
    mem3 = make_mock_state(
        player_species=0x53,   # Pikachu (Electric)
        enemy_species=0x16,    # Gyarados (Water/Flying)
        moves=[
            (0x21, 35),  # Tackle  Normal  35 pw → 35 * 1.0 = 35
            (0x54, 30),  # Thundershock Elec 40 pw → 40 * 4.0 * 1.5 = 240
            (0x55, 15),  # Thunderbolt Elec 95 pw → 95 * 4.0 * 1.5 = 570  (best)
            (0x00, 0),   # empty
        ],
    )
    ai3 = BattleAI(MockPyBoy(mem3))
    best3 = ai3.get_best_move()
    check("Pikachu vs Gyarados → Thunderbolt (slot 2)", best3, 2)

    # Scenario: Earthquake vs a Flying type — should be 0.0 effective,
    # prefer Tackle (Normal) which at least does 1.0
    mem4 = make_mock_state(
        player_species=0x75,   # Dugtrio (Ground)
        enemy_species=0x23,    # Pidgey (Normal/Flying)
        moves=[
            (0x59, 10),  # Earthquake Ground 100 → 0.0 vs Flying = 0
            (0x21, 35),  # Tackle Normal 35 → 35 * 1.0 = 35 (best)
            (0x00, 0),
            (0x00, 0),
        ],
    )
    ai4 = BattleAI(MockPyBoy(mem4))
    best4 = ai4.get_best_move()
    check("Earthquake 0x vs Flying → prefer Tackle (slot 1)", best4, 1)

    # Scenario: STAB test — Charizard (Fire/Flying)
    # Flamethrower (Fire 95, STAB) vs Tackle (Normal 35, no STAB)
    # vs a Grass type: Flamethrower = 95 * 2.0 * 1.5 = 285 vs Tackle = 35
    mem5 = make_mock_state(
        player_species=0xB3,   # Charizard (Fire/Flying)
        enemy_species=0x98,    # Bulbasaur (Grass/Poison)
        moves=[
            (0x21, 35),  # Tackle Normal 35 → 35 * 1.0 = 35
            (0x35, 15),  # Flamethrower Fire 95 → 95 * 2.0 * 1.5 = 285 (STAB!)
            (0x13, 15),  # Fly Flying 70 → 70 * 1.0 * 1.5 = 105 (STAB, not SE)
            (0x00, 0),
        ],
    )
    ai5 = BattleAI(MockPyBoy(mem5))
    best5 = ai5.get_best_move()
    check("Charizard STAB: Flamethrower vs Grass (slot 1)", best5, 1)


# ---------------------------------------------------------------------------
# Test 5: BattleAI — get_action / should_use_item / should_flee
# ---------------------------------------------------------------------------

def test_battle_ai_decisions():
    section("BattleAI — get_action() decisions")

    # Not in battle → wait
    mem = make_mock_state(battle_type=0)
    ai = BattleAI(MockPyBoy(mem))
    action = ai.get_action()
    ok = action["action"] == "wait"
    check("Not in battle → wait", int(ok), 1)

    # HP < 50% → item
    mem2 = make_mock_state(player_hp=40, player_max_hp=100)
    ai2 = BattleAI(MockPyBoy(mem2))
    action2 = ai2.get_action()
    ok2 = action2["action"] == "item" and "POTION" in action2.get("item", "")
    check("HP=40/100 → use item (POTION)", int(ok2), 1)

    # HP < 20% → Max Potion (if available)
    mem3 = make_mock_state(player_hp=15, player_max_hp=100,
                           bag_items=[(0x13, 1)])  # MAX POTION x1
    ai3 = BattleAI(MockPyBoy(mem3))
    action3 = ai3.get_action()
    ok3 = action3["action"] == "item" and "MAX" in action3.get("item", "")
    check("HP=15/100 → MAX POTION", int(ok3), 1)

    # Full HP → fight
    mem4 = make_mock_state(player_hp=100, player_max_hp=100)
    ai4 = BattleAI(MockPyBoy(mem4))
    action4 = ai4.get_action()
    ok4 = action4["action"] == "fight"
    check("Full HP → fight", int(ok4), 1)

    # Wild battle with all PP = 0 and empty bag → flee
    mem5 = make_mock_state(
        battle_type=1,  # wild
        player_hp=100, player_max_hp=100,
        moves=[(0x21, 0), (0x37, 0), (0x27, 0), (0x6E, 0)],
        bag_items=[],  # no items
    )
    ai5 = BattleAI(MockPyBoy(mem5))
    action5 = ai5.get_action()
    ok5 = action5["action"] == "flee"
    check("Wild battle, all PP=0 → flee", int(ok5), 1)

    # Trainer battle with all PP = 0 → should NOT flee (returns fight with fallback)
    mem6 = make_mock_state(
        battle_type=2,  # trainer
        moves=[(0x21, 0), (0x37, 0), (0x27, 0), (0x6E, 0)],
        bag_items=[],
    )
    ai6 = BattleAI(MockPyBoy(mem6))
    ok6 = not ai6.should_flee()
    check("Trainer battle → should_flee()=False", int(ok6), 1)


# ---------------------------------------------------------------------------
# Test 6: Verify POKEMON_TYPES uses internal indices (not Pokedex numbers)
# ---------------------------------------------------------------------------

def test_internal_indices():
    section("Internal Index Sanity Checks")

    # Pokedex #1 = Bulbasaur, but internal index should NOT be 0x01
    # Bulbasaur's internal index is 0x98
    not_at_1 = 0x01 not in POKEMON_TYPES or POKEMON_TYPES[0x01][0] != "Bulbasaur"
    check("Bulbasaur NOT at index 0x01 (Rhydon is)", int(not_at_1), 1)

    at_98 = 0x98 in POKEMON_TYPES and POKEMON_TYPES[0x98][0] == "Bulbasaur"
    check("Bulbasaur IS at index 0x98", int(at_98), 1)

    at_01 = 0x01 in POKEMON_TYPES and POKEMON_TYPES[0x01][0] == "Rhydon"
    check("Rhydon IS at index 0x01", int(at_01), 1)

    blastoise_correct = 0x1C in POKEMON_TYPES and POKEMON_TYPES[0x1C][0] == "Blastoise"
    check("Blastoise IS at index 0x1C", int(blastoise_correct), 1)

    charmander_correct = 0xAF in POKEMON_TYPES and POKEMON_TYPES[0xAF][0] == "Charmander"
    check("Charmander IS at index 0xAF", int(charmander_correct), 1)

    squirtle_correct = 0xB0 in POKEMON_TYPES and POKEMON_TYPES[0xB0][0] == "Squirtle"
    check("Squirtle IS at index 0xB0", int(squirtle_correct), 1)


# ---------------------------------------------------------------------------#
# Test 7: BattleAI — read_bag and find_best_heal_item
# ---------------------------------------------------------------------------#

def test_bag_reading():
    section("BattleAI — Bag Reading")

    # Default mock state has POTION and HYPER POTION
    mem = make_mock_state()
    ai = BattleAI(MockPyBoy(mem))
    bag = ai.read_bag()
    check("Default bag has 2 items", len(bag), 2)
    check("First item is POTION (0x10)", bag[0]["item_id"], 0x10)
    check("First item qty is 3", bag[0]["quantity"], 3)

    # find_best_heal_item should return best available (HYPER POTION > POTION)
    item = ai.find_best_heal_item()
    check("find_best_heal_item → HYPER POTION", item, "HYPER POTION")

    # With a FULL RESTORE in bag, should prefer that
    mem2 = make_mock_state(bag_items=[(0x19, 1)])  # FULL RESTORE
    ai2 = BattleAI(MockPyBoy(mem2))
    item2 = ai2.find_best_heal_item()
    check("find_best_heal_item → FULL RESTORE", item2, "FULL RESTORE")

    # Empty bag → None
    mem3 = make_mock_state(bag_items=[])
    ai3 = BattleAI(MockPyBoy(mem3))
    item3 = ai3.find_best_heal_item()
    check("Empty bag → None", item3, None)


# ---------------------------------------------------------------------------#
# Test 8: BattleAI — party switching when active mon faints
# ---------------------------------------------------------------------------#

def test_party_switching():
    section("BattleAI — Party Switching")

    # Helper to make a mock game_state with party
    class MockGameState:
        def __init__(self, party):
            self.party = party

    healthy_party = [
        {"slot": 1, "species": 0xB0, "hp": 0, "max_hp": 50},    # fainted
        {"slot": 2, "species": 0xAF, "hp": 30, "max_hp": 45},    # healthy
        {"slot": 3, "species": 0x98, "hp": 20, "max_hp": 40},    # healthy
    ]

    # Active mon fainted (HP=0), should switch to slot 1 (first healthy)
    mem = make_mock_state(player_hp=0, player_max_hp=50)
    ai = BattleAI(MockPyBoy(mem), game_state=MockGameState(healthy_party))
    switch = ai.should_switch()
    check("Fainted mon, healthy party → switch to slot 1", switch, 1)

    # Active mon healthy, should not switch
    mem2 = make_mock_state(player_hp=30, player_max_hp=50)
    ai2 = BattleAI(MockPyBoy(mem2), game_state=MockGameState(healthy_party))
    switch2 = ai2.should_switch()
    check("Healthy mon → no switch", switch2, None)

    # Active mon fainted, all others fainted too → no switch possible
    all_fainted = [
        {"slot": 1, "species": 0xB0, "hp": 0, "max_hp": 50},
        {"slot": 2, "species": 0xAF, "hp": 0, "max_hp": 45},
        {"slot": 3, "species": 0x98, "hp": 0, "max_hp": 40},
    ]
    mem3 = make_mock_state(player_hp=0, player_max_hp=50)
    ai3 = BattleAI(MockPyBoy(mem3), game_state=MockGameState(all_fainted))
    switch3 = ai3.should_switch()
    check("All fainted → no switch", switch3, None)

    # No game_state → no switch
    mem4 = make_mock_state(player_hp=0, player_max_hp=50)
    ai4 = BattleAI(MockPyBoy(mem4), game_state=None)
    switch4 = ai4.should_switch()
    check("No game_state → no switch", switch4, None)

    # get_action returns switch when active mon faints
    action = ai.get_action()
    check("get_action with fainted mon → switch", action["action"], "switch")
    check("get_action switch slot → 1", action["slot"], 1)


# ---------------------------------------------------------------------------#
# Test 9: StatsTracker
# ---------------------------------------------------------------------------#

def test_stats_tracker():
    section("StatsTracker")

    import os
    import tempfile
    from stats import StatsTracker

    # Use a temp file to avoid polluting real stats
    tmp = tempfile.mktemp(suffix=".json")

    try:
        s = StatsTracker(stats_file=tmp)

        # Initial state
        check("Initial battles won = 0", s.battles_won, 0)
        check("Initial total battles = 0", s.total_battles, 0)

        # Record some events
        s.record_battle_won()
        s.record_battle_won()
        s.record_battle_lost()
        s.record_pokemon_caught()
        s.record_step()
        s.record_step()
        s.record_step()
        s.record_item_used()

        check("After 2 wins + 1 loss = 3 total battles", s.total_battles, 3)
        check("Battles won = 2", s.battles_won, 2)
        check("Battles lost = 1", s.battles_lost, 1)
        check("Pokemon caught = 1", s.pokemon_caught, 1)
        check("Steps taken = 3", s.steps_taken, 3)
        check("Items used = 1", s.items_used, 1)
        check("Win rate = 2/3", s.win_rate, 2.0 / 3.0)

        # Save and reload
        s.save()
        s2 = StatsTracker(stats_file=tmp)
        check("Reload: battles won persisted", s2.battles_won, 2)
        check("Reload: pokemon caught persisted", s2.pokemon_caught, 1)
        check("Reload: sessions incremented", s2.sessions, 2)

        # Summary should not crash
        summary = s2.summary()
        check("Summary is a string", isinstance(summary, str), True)
        check("Summary contains 'Battles'", isinstance(summary, str) and "Battles" in summary, True)

    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# ---------------------------------------------------------------------------
# Test 9: Catching logic — find_best_ball
# ---------------------------------------------------------------------------

def test_find_best_ball():
    section("BattleAI — find_best_ball()")

    # Bag with POKE BALL only
    mem = make_mock_state(bag_items=[(0x04, 10)])  # POKE BALL x10
    ai = BattleAI(MockPyBoy(mem))
    check("Only Poke Ball → POKE BALL", ai.find_best_ball(), "POKE BALL")

    # Bag with GREAT BALL and POKE BALL → prefer GREAT
    mem2 = make_mock_state(bag_items=[(0x04, 5), (0x03, 3)])
    ai2 = BattleAI(MockPyBoy(mem2))
    check("Great + Poke → GREAT BALL", ai2.find_best_ball(), "GREAT BALL")

    # Bag with ULTRA, GREAT, POKE → prefer ULTRA
    mem3 = make_mock_state(bag_items=[(0x04, 5), (0x03, 3), (0x02, 2)])
    ai3 = BattleAI(MockPyBoy(mem3))
    check("Ultra + Great + Poke → ULTRA BALL", ai3.find_best_ball(), "ULTRA BALL")

    # Bag with MASTER BALL
    mem4 = make_mock_state(bag_items=[(0x01, 1), (0x02, 10)])
    ai4 = BattleAI(MockPyBoy(mem4))
    check("Master + Ultra → MASTER BALL", ai4.find_best_ball(), "MASTER BALL")

    # Empty bag → None
    mem5 = make_mock_state(bag_items=[])
    ai5 = BattleAI(MockPyBoy(mem5))
    check("Empty bag → None", ai5.find_best_ball(), None)


# ---------------------------------------------------------------------------
# Test 10: Catching logic — should_catch
# ---------------------------------------------------------------------------

class MockGameState:
    """Minimal game_state mock for catching tests."""
    def __init__(self, party_species=None):
        self._party_species = party_species or []
        self.party = [{"species": s, "hp": 100, "max_hp": 100} for s in self._party_species]

def test_should_catch():
    section("BattleAI — should_catch()")

    # Helper: make BattleAI with ball, party, and enemy HP
    def make_catch_ai(enemy_species, enemy_hp, enemy_max_hp, party_species, ball_qty=10):
        bag = [(0x04, ball_qty)]  # POKE BALL
        mem = make_mock_state(
            battle_type=1,  # wild
            enemy_species=enemy_species,
            enemy_hp=enemy_hp,
            bag_items=bag,
        )
        # Override enemy max HP
        mem[0xCFF4] = (enemy_max_hp >> 8) & 0xFF
        mem[0xCFF5] = enemy_max_hp & 0xFF
        ai = BattleAI(MockPyBoy(mem), game_state=MockGameState(party_species))
        return ai

    # New species at 50% HP → should catch
    ai1 = make_catch_ai(0x01, 50, 100, [0xB0])  # Rhydon vs party with Squirtle
    check("New species at 50% HP → POKE BALL", ai1.should_catch(), "POKE BALL")

    # New species at 30% HP → should catch
    ai2 = make_catch_ai(0xAF, 30, 100, [0xB0])  # Charmander (new) at 30%
    check("New species at 30% HP → POKE BALL", ai2.should_catch(), "POKE BALL")

    # New species at 90% HP → skip (too risky)
    ai3 = make_catch_ai(0xAF, 90, 100, [0xB0])  # Charmander (new) at 90%
    check("New species at 90% HP → None", ai3.should_catch(), None)

    # Already owned at 50% HP → skip (not easy enough)
    ai4 = make_catch_ai(0xB0, 50, 100, [0xB0])  # Squirtle (owned) at 50%
    check("Owned species at 50% HP → None", ai4.should_catch(), None)

    # Already owned at 20% HP → catch (easy)
    ai5 = make_catch_ai(0xB0, 20, 100, [0xB0])  # Squirtle (owned) at 20%
    check("Owned species at 20% HP → POKE BALL", ai5.should_catch(), "POKE BALL")

    # No balls → None
    mem6 = make_mock_state(battle_type=1, enemy_species=0xAF, enemy_hp=10, bag_items=[])
    ai6 = BattleAI(MockPyBoy(mem6), game_state=MockGameState([0xB0]))
    check("No balls → None", ai6.should_catch(), None)

    # Trainer battle → None (can't catch trainer Pokemon)
    mem7 = make_mock_state(battle_type=2, enemy_species=0xAF, enemy_hp=10,
                           bag_items=[(0x04, 10)])
    ai7 = BattleAI(MockPyBoy(mem7), game_state=MockGameState([0xB0]))
    check("Trainer battle → None", ai7.should_catch(), None)

    # get_action returns catch for new species
    mem8 = make_mock_state(
        battle_type=1, player_hp=100, player_max_hp=100,
        enemy_species=0x01,  # Rhydon (not in party)
        enemy_hp=40, bag_items=[(0x04, 10)],
    )
    mem8[0xCFF4] = 0; mem8[0xCFF5] = 100  # max HP
    ai8 = BattleAI(MockPyBoy(mem8), game_state=MockGameState([0xB0]))
    action = ai8.get_action()
    check("get_action for new species → catch", action["action"], "catch")
    check("get_action catch uses POKE BALL", action.get("item"), "POKE BALL")


# ---------------------------------------------------------------------------
# Test 11: get_party_species
# ---------------------------------------------------------------------------

def test_get_party_species():
    section("BattleAI — get_party_species()")

    mem = make_mock_state(battle_type=1)
    gs = MockGameState([0xB0, 0xAF, 0x98])  # Squirtle, Charmander, Bulbasaur
    ai = BattleAI(MockPyBoy(mem), game_state=gs)
    species = ai.get_party_species()
    check("Party species set", str(sorted(species)), str(sorted([0xB0, 0xAF, 0x98])))
    check("Party has 3 species", len(species), 3)

    # No game_state → empty set
    ai2 = BattleAI(MockPyBoy(mem))
    check("No game_state → empty", len(ai2.get_party_species()), 0)


# ---------------------------------------------------------------------------#
# Summary
# ---------------------------------------------------------------------------#

def main():
    print("\n" + "="*60)
    print("  Pokemon Blue Battle AI — Test Suite")
    print("="*60)

    try:
        test_type_effectiveness()
    except Exception as e:
        print(f"\n  ERROR in test_type_effectiveness: {e}")
        traceback.print_exc()

    try:
        test_pokemon_types()
    except Exception as e:
        print(f"\n  ERROR in test_pokemon_types: {e}")
        traceback.print_exc()

    try:
        test_move_data()
    except Exception as e:
        print(f"\n  ERROR in test_move_data: {e}")
        traceback.print_exc()

    try:
        test_battle_ai_move_selection()
    except Exception as e:
        print(f"\n  ERROR in test_battle_ai_move_selection: {e}")
        traceback.print_exc()

    try:
        test_battle_ai_decisions()
    except Exception as e:
        print(f"\n  ERROR in test_battle_ai_decisions: {e}")
        traceback.print_exc()

    try:
        test_internal_indices()
    except Exception as e:
        print(f"\n  ERROR in test_internal_indices: {e}")
        traceback.print_exc()

    try:
        test_bag_reading()
    except Exception as e:
        print(f"\n  ERROR in test_bag_reading: {e}")
        traceback.print_exc()

    try:
        test_party_switching()
    except Exception as e:
        print(f"\n  ERROR in test_party_switching: {e}")
        traceback.print_exc()

    try:
        test_stats_tracker()
    except Exception as e:
        print(f"\n  ERROR in test_stats_tracker: {e}")
        traceback.print_exc()

    try:
        test_find_best_ball()
    except Exception as e:
        print(f"\n  ERROR in test_find_best_ball: {e}")
        traceback.print_exc()

    try:
        test_should_catch()
    except Exception as e:
        print(f"\n  ERROR in test_should_catch: {e}")
        traceback.print_exc()

    try:
        test_get_party_species()
    except Exception as e:
        print(f"\n  ERROR in test_get_party_species: {e}")
        traceback.print_exc()

    # Summary
    total = len(_results)
    passed = sum(_results)
    failed = total - passed
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  (\033[31m{failed} failed\033[0m)")
    else:
        print(f"  \033[32m(all passed!)\033[0m")
    print("="*60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
