"""
battle.py — Battle AI module for Pokemon Blue autobot.
Uses PyBoy 2.x for button input and direct memory reads.

Depends on: emulator.py (GameState stub), memory.py (memory address constants)
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Gen 1 Type constants (15 types — no Dark/Steel/Fairy in Gen 1)
# Internal type IDs match the game's byte values.
# ---------------------------------------------------------------------------
NORMAL   = "Normal"
FIGHTING = "Fighting"
FLYING   = "Flying"
POISON   = "Poison"
GROUND   = "Ground"
ROCK     = "Rock"
BUG      = "Bug"
GHOST    = "Ghost"
FIRE     = "Fire"
WATER    = "Water"
GRASS    = "Grass"
ELECTRIC = "Electric"
PSYCHIC  = "Psychic"
ICE      = "Ice"
DRAGON   = "Dragon"

ALL_TYPES = [NORMAL, FIGHTING, FLYING, POISON, GROUND, ROCK, BUG, GHOST,
             FIRE, WATER, GRASS, ELECTRIC, PSYCHIC, ICE, DRAGON]

# ---------------------------------------------------------------------------
# TYPE_CHART — Gen 1 effectiveness (attacking_type -> defending_type -> multiplier)
# Only non-1.0 entries are stored; default is 1.0.
#
# Gen 1 quirks vs later games:
#   • Ghost attacking Psychic: 0.0  (should be 2x but is a famous coding bug)
#   • Bug attacking Poison:    0.5  (became 2x in Gen 2+)
#   • Poison attacking Bug:    1.0  (was 2x in Gen 1 but treated as 1.0 per spec)
#   • Ice attacking Fire:      1.0  (Fire does NOT resist Ice in Gen 1)
#   • No Dark or Steel types
# ---------------------------------------------------------------------------
TYPE_CHART: dict[str, dict[str, float]] = {
    NORMAL: {
        ROCK: 0.5,
        GHOST: 0.0,
    },
    FIGHTING: {
        NORMAL:   2.0,
        ICE:      2.0,
        POISON:   0.5,
        FLYING:   0.5,
        PSYCHIC:  0.5,
        BUG:      0.5,
        ROCK:     2.0,
        GHOST:    0.0,
    },
    FLYING: {
        FIGHTING: 2.0,
        BUG:      2.0,
        GRASS:    2.0,
        ELECTRIC: 0.5,
        ROCK:     0.5,
    },
    POISON: {
        GRASS:    2.0,
        # Bug:    1.0 (Gen 1 quirk — Poison NOT super effective vs Bug per spec)
        POISON:   0.5,
        GROUND:   0.5,
        ROCK:     0.5,
        GHOST:    0.5,
    },
    GROUND: {
        FIRE:     2.0,
        ELECTRIC: 2.0,
        POISON:   2.0,
        ROCK:     2.0,
        GRASS:    0.5,
        BUG:      0.5,
        FLYING:   0.0,
    },
    ROCK: {
        FIRE:     2.0,
        ICE:      2.0,
        FLYING:   2.0,
        BUG:      2.0,
        FIGHTING: 0.5,
        GROUND:   0.5,
    },
    BUG: {
        PSYCHIC:  2.0,
        GRASS:    2.0,
        # Poison: 0.5 (Gen 1: Bug NOT super effective vs Poison)
        FIRE:     0.5,
        FIGHTING: 0.5,
        FLYING:   0.5,
        GHOST:    0.5,
        POISON:   0.5,
    },
    GHOST: {
        NORMAL:   0.0,
        PSYCHIC:  0.0,  # Gen 1 bug: Ghost should be 2x vs Psychic but coded as 0x
        GHOST:    2.0,
    },
    FIRE: {
        GRASS:    2.0,
        ICE:      2.0,
        BUG:      2.0,
        # Ice attacking Fire = 1.0 in Gen 1; here we list Fire attacking Ice = 2.0
        FIRE:     0.5,
        WATER:    0.5,
        ROCK:     0.5,
        DRAGON:   0.5,
    },
    WATER: {
        FIRE:     2.0,
        GROUND:   2.0,
        ROCK:     2.0,
        WATER:    0.5,
        GRASS:    0.5,
        DRAGON:   0.5,
    },
    GRASS: {
        WATER:    2.0,
        GROUND:   2.0,
        ROCK:     2.0,
        FIRE:     0.5,
        GRASS:    0.5,
        POISON:   0.5,
        FLYING:   0.5,
        BUG:      0.5,
        DRAGON:   0.5,
    },
    ELECTRIC: {
        WATER:    2.0,
        FLYING:   2.0,
        ELECTRIC: 0.5,
        GRASS:    0.5,
        GROUND:   0.0,
        DRAGON:   0.5,
    },
    PSYCHIC: {
        FIGHTING: 2.0,
        POISON:   2.0,
        PSYCHIC:  0.5,
        GHOST:    0.0,  # Psychic has no effect on Ghost in Gen 1
    },
    ICE: {
        GRASS:    2.0,
        GROUND:   2.0,
        FLYING:   2.0,
        DRAGON:   2.0,
        # Fire:   1.0  (Ice does NOT get resisted by Fire in Gen 1)
        WATER:    0.5,
        ICE:      0.5,
    },
    DRAGON: {
        DRAGON:   2.0,
    },
}


# ---------------------------------------------------------------------------
# POKEMON_TYPES — internal Gen 1 species index (NOT Pokedex number) -> (type1, type2)
# Source: pret/pokered disassembly constants/pokemon_data_constants.asm
# Single-type Pokemon have type2=None.
# ---------------------------------------------------------------------------
POKEMON_TYPES: dict[int, tuple[str, str | None]] = {
    # idx   Species           type1      type2
    0x01: ("Rhydon",        (GROUND,   ROCK)),
    0x02: ("Kangaskhan",    (NORMAL,   None)),
    0x03: ("NidoranM",      (POISON,   None)),
    0x04: ("Clefairy",      (NORMAL,   None)),
    0x05: ("Spearow",       (NORMAL,   FLYING)),
    0x06: ("Voltorb",       (ELECTRIC, None)),
    0x07: ("Nidoking",      (POISON,   GROUND)),
    0x08: ("Slowbro",       (WATER,    PSYCHIC)),
    0x09: ("Ivysaur",       (GRASS,    POISON)),
    0x0A: ("Exeggutor",     (GRASS,    PSYCHIC)),
    0x0B: ("Lickitung",     (NORMAL,   None)),
    0x0C: ("Exeggcute",     (GRASS,    PSYCHIC)),
    0x0D: ("Grimer",        (POISON,   None)),
    0x0E: ("Gengar",        (GHOST,    POISON)),
    0x0F: ("NidoranF",      (POISON,   None)),
    0x10: ("Nidoqueen",     (POISON,   GROUND)),
    0x11: ("Cubone",        (GROUND,   None)),
    0x12: ("Rhyhorn",       (GROUND,   ROCK)),
    0x13: ("Lapras",        (WATER,    ICE)),
    0x14: ("Arcanine",      (FIRE,     None)),
    0x15: ("Mew",           (PSYCHIC,  None)),
    0x16: ("Gyarados",      (WATER,    FLYING)),
    0x17: ("Shellder",      (WATER,    None)),
    0x18: ("Tentacool",     (WATER,    POISON)),
    0x19: ("Gastly",        (GHOST,    POISON)),
    0x1A: ("Scyther",       (BUG,      FLYING)),
    0x1B: ("Staryu",        (WATER,    None)),
    0x1C: ("Blastoise",     (WATER,    None)),
    0x1D: ("Pinsir",        (BUG,      None)),
    0x1E: ("Tangela",       (GRASS,    None)),
    # 0x1F unused
    0x20: ("Growlithe",     (FIRE,     None)),
    0x21: ("Onix",          (ROCK,     GROUND)),
    0x22: ("Fearow",        (NORMAL,   FLYING)),
    0x23: ("Pidgey",        (NORMAL,   FLYING)),
    0x24: ("Slowpoke",      (WATER,    PSYCHIC)),
    0x25: ("Kadabra",       (PSYCHIC,  None)),
    0x26: ("Graveler",      (ROCK,     GROUND)),
    0x27: ("Chansey",       (NORMAL,   None)),
    0x28: ("Machoke",       (FIGHTING, None)),
    0x29: ("MrMime",        (PSYCHIC,  None)),
    0x2A: ("Hitmonlee",     (FIGHTING, None)),
    0x2B: ("Hitmonchan",    (FIGHTING, None)),
    0x2C: ("Arbok",         (POISON,   None)),
    0x2D: ("Parasect",      (BUG,      GRASS)),
    0x2E: ("Psyduck",       (WATER,    None)),
    0x2F: ("Drowzee",       (PSYCHIC,  None)),
    0x30: ("Golem",         (ROCK,     GROUND)),
    # 0x31 unused
    0x32: ("Magmar",        (FIRE,     None)),
    # 0x33 unused
    0x34: ("Electabuzz",    (ELECTRIC, None)),
    0x35: ("Magneton",      (ELECTRIC, None)),
    0x36: ("Koffing",       (POISON,   None)),
    # 0x37 unused
    0x38: ("Mankey",        (FIGHTING, None)),
    0x39: ("Seel",          (WATER,    None)),
    0x3A: ("Diglett",       (GROUND,   None)),
    0x3B: ("Tauros",        (NORMAL,   None)),
    # 0x3C-0x3E unused
    0x3F: ("Farfetchd",     (NORMAL,   FLYING)),
    0x40: ("Venonat",       (BUG,      POISON)),
    0x41: ("Dragonite",     (DRAGON,   FLYING)),
    # 0x42-0x44 unused
    0x45: ("Doduo",         (NORMAL,   FLYING)),
    0x46: ("Poliwag",       (WATER,    None)),
    0x47: ("Jynx",          (ICE,      PSYCHIC)),
    0x48: ("Moltres",       (FIRE,     FLYING)),
    0x49: ("Articuno",      (ICE,      FLYING)),
    0x4A: ("Zapdos",        (ELECTRIC, FLYING)),
    0x4B: ("Ditto",         (NORMAL,   None)),
    0x4C: ("Meowth",        (NORMAL,   None)),
    0x4D: ("Krabby",        (WATER,    None)),
    # 0x4E-0x50 unused
    0x51: ("Vulpix",        (FIRE,     None)),
    0x52: ("Ninetales",     (FIRE,     None)),
    0x53: ("Pikachu",       (ELECTRIC, None)),
    0x54: ("Raichu",        (ELECTRIC, None)),
    # 0x55-0x56 unused
    0x57: ("Dratini",       (DRAGON,   None)),
    0x58: ("Dragonair",     (DRAGON,   None)),
    0x59: ("Kabuto",        (ROCK,     WATER)),
    0x5A: ("Kabutops",      (ROCK,     WATER)),
    0x5B: ("Horsea",        (WATER,    None)),
    0x5C: ("Seadra",        (WATER,    None)),
    # 0x5D-0x5E unused
    0x5F: ("Sandshrew",     (GROUND,   None)),
    0x60: ("Sandslash",     (GROUND,   None)),
    0x61: ("Omanyte",       (ROCK,     WATER)),
    0x62: ("Omastar",       (ROCK,     WATER)),
    0x63: ("Jigglypuff",    (NORMAL,   None)),
    0x64: ("Wigglytuff",    (NORMAL,   None)),
    0x65: ("Eevee",         (NORMAL,   None)),
    0x66: ("Flareon",       (FIRE,     None)),
    0x67: ("Jolteon",       (ELECTRIC, None)),
    0x68: ("Vaporeon",      (WATER,    None)),
    0x69: ("Machop",        (FIGHTING, None)),
    0x6A: ("Zubat",         (POISON,   FLYING)),
    0x6B: ("Ekans",         (POISON,   None)),
    0x6C: ("Paras",         (BUG,      GRASS)),
    0x6D: ("Poliwhirl",     (WATER,    None)),
    0x6E: ("Poliwrath",     (WATER,    FIGHTING)),
    0x6F: ("Weedle",        (BUG,      POISON)),
    0x70: ("Kakuna",        (BUG,      POISON)),
    0x71: ("Beedrill",      (BUG,      POISON)),
    # 0x72 unused
    0x73: ("Dodrio",        (NORMAL,   FLYING)),
    0x74: ("Primeape",      (FIGHTING, None)),
    0x75: ("Dugtrio",       (GROUND,   None)),
    0x76: ("Venomoth",      (BUG,      POISON)),
    0x77: ("Dewgong",       (WATER,    ICE)),
    # 0x78-0x79 unused
    0x7A: ("Caterpie",      (BUG,      None)),
    0x7B: ("Metapod",       (BUG,      None)),
    0x7C: ("Butterfree",    (BUG,      FLYING)),
    0x7D: ("Machamp",       (FIGHTING, None)),
    # 0x7E unused
    0x7F: ("Golduck",       (WATER,    None)),
    0x80: ("Hypno",         (PSYCHIC,  None)),
    0x81: ("Golbat",        (POISON,   FLYING)),
    0x82: ("Mewtwo",        (PSYCHIC,  None)),
    0x83: ("Snorlax",       (NORMAL,   None)),
    0x84: ("Magikarp",      (WATER,    None)),
    # 0x85-0x86 unused
    0x87: ("Muk",           (POISON,   None)),
    # 0x88 unused
    0x89: ("Kingler",       (WATER,    None)),
    0x8A: ("Cloyster",      (WATER,    ICE)),
    # 0x8B unused
    0x8C: ("Electrode",     (ELECTRIC, None)),
    0x8D: ("Clefable",      (NORMAL,   None)),
    0x8E: ("Weezing",       (POISON,   None)),
    0x8F: ("Persian",       (NORMAL,   None)),
    0x90: ("Marowak",       (GROUND,   None)),
    # 0x91 unused
    0x92: ("Haunter",       (GHOST,    POISON)),
    0x93: ("Abra",          (PSYCHIC,  None)),
    0x94: ("Alakazam",      (PSYCHIC,  None)),
    0x95: ("Pidgeotto",     (NORMAL,   FLYING)),
    0x96: ("Pidgeot",       (NORMAL,   FLYING)),
    0x97: ("Starmie",       (WATER,    PSYCHIC)),
    0x98: ("Bulbasaur",     (GRASS,    POISON)),
    0x99: ("Venusaur",      (GRASS,    POISON)),
    0x9A: ("Tentacruel",    (WATER,    POISON)),
    # 0x9B unused
    0x9C: ("Goldeen",       (WATER,    None)),
    0x9D: ("Seaking",       (WATER,    None)),
    # 0x9E-0xA1 unused
    0xA2: ("Ponyta",        (FIRE,     None)),
    0xA3: ("Rapidash",      (FIRE,     None)),
    0xA4: ("Rattata",       (NORMAL,   None)),
    0xA5: ("Raticate",      (NORMAL,   None)),
    0xA6: ("Nidorino",      (POISON,   None)),
    0xA7: ("Nidorina",      (POISON,   None)),
    0xA8: ("Geodude",       (ROCK,     GROUND)),
    0xA9: ("Porygon",       (NORMAL,   None)),
    0xAA: ("Aerodactyl",    (ROCK,     FLYING)),
    # 0xAB unused
    0xAC: ("Magnemite",     (ELECTRIC, None)),
    # 0xAD-0xAE unused
    0xAF: ("Charmander",    (FIRE,     None)),
    0xB0: ("Squirtle",      (WATER,    None)),
    0xB1: ("Charmeleon",    (FIRE,     None)),
    0xB2: ("Wartortle",     (WATER,    None)),
    0xB3: ("Charizard",     (FIRE,     FLYING)),
    # 0xB4-0xB9 unused
    0xBA: ("Oddish",        (GRASS,    POISON)),
    0xBB: ("Gloom",         (GRASS,    POISON)),
    0xBC: ("Vileplume",     (GRASS,    POISON)),
    0xBD: ("Bellsprout",    (GRASS,    POISON)),
    0xBE: ("Weepinbell",    (GRASS,    POISON)),
    0xBF: ("Victreebel",    (GRASS,    POISON)),
}

# Convenience lookup: index -> (type1, type2)   (drop the name field)
SPECIES_TYPES: dict[int, tuple[str, str | None]] = {
    idx: data[1] for idx, data in POKEMON_TYPES.items()
}


# ---------------------------------------------------------------------------
# MOVE_DATA — move_id -> {name, type, power, pp}
# IDs from pret/pokered disassembly (moves.asm / move_names.asm).
# power=0 means the move does no direct damage (status/special).
#
# NOTE on task description errors (corrected here):
#   Task said Water Gun=0xD1 → actual 0x37
#   Task said Surf=0x3D      → actual 0x39  (0x3D is BubbleBeam)
#   Task said Flamethrower=0x7E → actual 0x35  (0x7E is Fire Blast)
# ---------------------------------------------------------------------------
MOVE_DATA: dict[int, dict] = {
    0x01: {"name": "Pound",          "type": NORMAL,   "power": 40,  "pp": 35},
    0x02: {"name": "Karate Chop",    "type": FIGHTING, "power": 50,  "pp": 25},
    0x03: {"name": "DoubleSlap",     "type": NORMAL,   "power": 15,  "pp": 10},
    0x04: {"name": "Comet Punch",    "type": NORMAL,   "power": 18,  "pp": 15},
    0x05: {"name": "Mega Punch",     "type": NORMAL,   "power": 80,  "pp": 20},
    0x06: {"name": "Pay Day",        "type": NORMAL,   "power": 40,  "pp": 20},
    0x07: {"name": "Fire Punch",     "type": FIRE,     "power": 75,  "pp": 15},
    0x08: {"name": "Ice Punch",      "type": ICE,      "power": 75,  "pp": 15},
    0x09: {"name": "ThunderPunch",   "type": ELECTRIC, "power": 75,  "pp": 15},
    0x0A: {"name": "Scratch",        "type": NORMAL,   "power": 40,  "pp": 35},
    0x0B: {"name": "ViceGrip",       "type": NORMAL,   "power": 55,  "pp": 30},
    0x0C: {"name": "Guillotine",     "type": NORMAL,   "power": 0,   "pp": 5},   # OHKO
    0x0D: {"name": "Razor Wind",     "type": NORMAL,   "power": 80,  "pp": 10},
    0x0E: {"name": "Swords Dance",   "type": NORMAL,   "power": 0,   "pp": 30},
    0x0F: {"name": "Cut",            "type": NORMAL,   "power": 50,  "pp": 30},
    0x10: {"name": "Gust",           "type": NORMAL,   "power": 40,  "pp": 35},  # Normal in Gen 1 (not Flying)
    0x11: {"name": "Wing Attack",    "type": FLYING,   "power": 35,  "pp": 35},
    0x12: {"name": "Whirlwind",      "type": NORMAL,   "power": 0,   "pp": 20},
    0x13: {"name": "Fly",            "type": FLYING,   "power": 70,  "pp": 15},
    0x14: {"name": "Bind",           "type": NORMAL,   "power": 15,  "pp": 20},
    0x15: {"name": "Slam",           "type": NORMAL,   "power": 80,  "pp": 20},
    0x16: {"name": "Vine Whip",      "type": GRASS,    "power": 35,  "pp": 10},
    0x17: {"name": "Stomp",          "type": NORMAL,   "power": 65,  "pp": 20},
    0x18: {"name": "Double Kick",    "type": FIGHTING, "power": 30,  "pp": 30},
    0x19: {"name": "Mega Kick",      "type": NORMAL,   "power": 120, "pp": 5},
    0x1A: {"name": "Jump Kick",      "type": FIGHTING, "power": 70,  "pp": 25},
    0x1B: {"name": "Rolling Kick",   "type": FIGHTING, "power": 60,  "pp": 15},
    0x1C: {"name": "Sand Attack",    "type": NORMAL,   "power": 0,   "pp": 15},
    0x1D: {"name": "Headbutt",       "type": NORMAL,   "power": 70,  "pp": 15},
    0x1E: {"name": "Horn Attack",    "type": NORMAL,   "power": 65,  "pp": 25},
    0x1F: {"name": "Fury Attack",    "type": NORMAL,   "power": 15,  "pp": 20},
    0x20: {"name": "Horn Drill",     "type": NORMAL,   "power": 0,   "pp": 5},   # OHKO
    0x21: {"name": "Tackle",         "type": NORMAL,   "power": 35,  "pp": 35},
    0x22: {"name": "Body Slam",      "type": NORMAL,   "power": 85,  "pp": 15},
    0x23: {"name": "Wrap",           "type": NORMAL,   "power": 15,  "pp": 20},
    0x24: {"name": "Take Down",      "type": NORMAL,   "power": 90,  "pp": 20},
    0x25: {"name": "Thrash",         "type": NORMAL,   "power": 90,  "pp": 20},
    0x26: {"name": "Double-Edge",    "type": NORMAL,   "power": 100, "pp": 15},
    0x27: {"name": "Tail Whip",      "type": NORMAL,   "power": 0,   "pp": 30},
    0x28: {"name": "Poison Sting",   "type": POISON,   "power": 15,  "pp": 35},
    0x29: {"name": "Twineedle",      "type": BUG,      "power": 25,  "pp": 20},
    0x2A: {"name": "Pin Missile",    "type": BUG,      "power": 14,  "pp": 20},
    0x2B: {"name": "Leer",           "type": NORMAL,   "power": 0,   "pp": 30},
    0x2C: {"name": "Bite",           "type": NORMAL,   "power": 60,  "pp": 25},  # Normal in Gen 1 (not Dark)
    0x2D: {"name": "Growl",          "type": NORMAL,   "power": 0,   "pp": 40},
    0x2E: {"name": "Roar",           "type": NORMAL,   "power": 0,   "pp": 20},
    0x2F: {"name": "Sing",           "type": NORMAL,   "power": 0,   "pp": 15},
    0x30: {"name": "Supersonic",     "type": NORMAL,   "power": 0,   "pp": 20},
    0x31: {"name": "SonicBoom",      "type": NORMAL,   "power": 0,   "pp": 20},  # fixed 20 dmg
    0x32: {"name": "Disable",        "type": NORMAL,   "power": 0,   "pp": 20},
    0x33: {"name": "Acid",           "type": POISON,   "power": 40,  "pp": 30},
    0x34: {"name": "Ember",          "type": FIRE,     "power": 40,  "pp": 25},
    0x35: {"name": "Flamethrower",   "type": FIRE,     "power": 95,  "pp": 15},
    0x36: {"name": "Mist",           "type": ICE,      "power": 0,   "pp": 30},
    0x37: {"name": "Water Gun",      "type": WATER,    "power": 40,  "pp": 25},
    0x38: {"name": "Hydro Pump",     "type": WATER,    "power": 120, "pp": 5},
    0x39: {"name": "Surf",           "type": WATER,    "power": 95,  "pp": 15},
    0x3A: {"name": "Ice Beam",       "type": ICE,      "power": 95,  "pp": 10},
    0x3B: {"name": "Blizzard",       "type": ICE,      "power": 120, "pp": 5},
    0x3C: {"name": "Psybeam",        "type": PSYCHIC,  "power": 65,  "pp": 20},
    0x3D: {"name": "BubbleBeam",     "type": WATER,    "power": 65,  "pp": 20},
    0x3E: {"name": "Aurora Beam",    "type": ICE,      "power": 65,  "pp": 20},
    0x3F: {"name": "Hyper Beam",     "type": NORMAL,   "power": 150, "pp": 5},
    0x40: {"name": "Peck",           "type": FLYING,   "power": 35,  "pp": 35},
    0x41: {"name": "Drill Peck",     "type": FLYING,   "power": 80,  "pp": 20},
    0x42: {"name": "Submission",     "type": FIGHTING, "power": 80,  "pp": 25},
    0x43: {"name": "Low Kick",       "type": FIGHTING, "power": 50,  "pp": 20},
    0x44: {"name": "Counter",        "type": FIGHTING, "power": 0,   "pp": 20},
    0x45: {"name": "Seismic Toss",   "type": FIGHTING, "power": 0,   "pp": 20},  # level-based
    0x46: {"name": "Strength",       "type": NORMAL,   "power": 80,  "pp": 15},
    0x47: {"name": "Absorb",         "type": GRASS,    "power": 20,  "pp": 20},
    0x48: {"name": "Mega Drain",     "type": GRASS,    "power": 40,  "pp": 10},
    0x49: {"name": "Leech Seed",     "type": GRASS,    "power": 0,   "pp": 10},
    0x4A: {"name": "Growth",         "type": NORMAL,   "power": 0,   "pp": 40},
    0x4B: {"name": "Razor Leaf",     "type": GRASS,    "power": 55,  "pp": 25},
    0x4C: {"name": "SolarBeam",      "type": GRASS,    "power": 120, "pp": 10},
    0x4D: {"name": "PoisonPowder",   "type": POISON,   "power": 0,   "pp": 35},
    0x4E: {"name": "Stun Spore",     "type": GRASS,    "power": 0,   "pp": 30},
    0x4F: {"name": "Sleep Powder",   "type": GRASS,    "power": 0,   "pp": 15},
    0x50: {"name": "Petal Dance",    "type": GRASS,    "power": 70,  "pp": 20},
    0x51: {"name": "String Shot",    "type": BUG,      "power": 0,   "pp": 40},
    0x52: {"name": "Dragon Rage",    "type": DRAGON,   "power": 0,   "pp": 10},  # fixed 40 dmg
    0x53: {"name": "Fire Spin",      "type": FIRE,     "power": 15,  "pp": 15},
    0x54: {"name": "Thundershock",   "type": ELECTRIC, "power": 40,  "pp": 30},
    0x55: {"name": "Thunderbolt",    "type": ELECTRIC, "power": 95,  "pp": 15},
    0x56: {"name": "Thunder Wave",   "type": ELECTRIC, "power": 0,   "pp": 20},
    0x57: {"name": "Thunder",        "type": ELECTRIC, "power": 120, "pp": 10},
    0x58: {"name": "Rock Throw",     "type": ROCK,     "power": 50,  "pp": 15},
    0x59: {"name": "Earthquake",     "type": GROUND,   "power": 100, "pp": 10},
    0x5A: {"name": "Fissure",        "type": GROUND,   "power": 0,   "pp": 5},   # OHKO
    0x5B: {"name": "Dig",            "type": GROUND,   "power": 100, "pp": 10},
    0x5C: {"name": "Toxic",          "type": POISON,   "power": 0,   "pp": 10},
    0x5D: {"name": "Confusion",      "type": PSYCHIC,  "power": 50,  "pp": 25},
    0x5E: {"name": "Psychic",        "type": PSYCHIC,  "power": 90,  "pp": 10},
    0x5F: {"name": "Hypnosis",       "type": PSYCHIC,  "power": 0,   "pp": 20},
    0x60: {"name": "Meditate",       "type": PSYCHIC,  "power": 0,   "pp": 40},
    0x61: {"name": "Agility",        "type": PSYCHIC,  "power": 0,   "pp": 30},
    0x62: {"name": "Quick Attack",   "type": NORMAL,   "power": 40,  "pp": 30},
    0x63: {"name": "Rage",           "type": NORMAL,   "power": 20,  "pp": 20},
    0x64: {"name": "Teleport",       "type": PSYCHIC,  "power": 0,   "pp": 20},
    0x65: {"name": "Night Shade",    "type": GHOST,    "power": 0,   "pp": 15},  # level-based
    0x66: {"name": "Mimic",          "type": NORMAL,   "power": 0,   "pp": 10},
    0x67: {"name": "Screech",        "type": NORMAL,   "power": 0,   "pp": 40},
    0x68: {"name": "Double Team",    "type": NORMAL,   "power": 0,   "pp": 15},
    0x69: {"name": "Recover",        "type": NORMAL,   "power": 0,   "pp": 20},
    0x6A: {"name": "Harden",         "type": NORMAL,   "power": 0,   "pp": 30},
    0x6B: {"name": "Minimize",       "type": NORMAL,   "power": 0,   "pp": 20},
    0x6C: {"name": "Smokescreen",    "type": NORMAL,   "power": 0,   "pp": 20},
    0x6D: {"name": "Confuse Ray",    "type": GHOST,    "power": 0,   "pp": 10},
    0x6E: {"name": "Withdraw",       "type": WATER,    "power": 0,   "pp": 40},
    0x6F: {"name": "Defense Curl",   "type": NORMAL,   "power": 0,   "pp": 40},
    0x70: {"name": "Barrier",        "type": PSYCHIC,  "power": 0,   "pp": 30},
    0x71: {"name": "Light Screen",   "type": PSYCHIC,  "power": 0,   "pp": 30},
    0x72: {"name": "Haze",           "type": ICE,      "power": 0,   "pp": 30},
    0x73: {"name": "Reflect",        "type": PSYCHIC,  "power": 0,   "pp": 20},
    0x74: {"name": "Focus Energy",   "type": NORMAL,   "power": 0,   "pp": 30},
    0x75: {"name": "Bide",           "type": NORMAL,   "power": 0,   "pp": 10},
    0x76: {"name": "Metronome",      "type": NORMAL,   "power": 0,   "pp": 10},
    0x77: {"name": "Mirror Move",    "type": FLYING,   "power": 0,   "pp": 20},
    0x78: {"name": "Self-Destruct",  "type": NORMAL,   "power": 200, "pp": 5},
    0x79: {"name": "Egg Bomb",       "type": NORMAL,   "power": 100, "pp": 10},
    0x7A: {"name": "Lick",           "type": GHOST,    "power": 20,  "pp": 30},
    0x7B: {"name": "Smog",           "type": POISON,   "power": 20,  "pp": 20},
    0x7C: {"name": "Sludge",         "type": POISON,   "power": 65,  "pp": 20},
    0x7D: {"name": "Bone Club",      "type": GROUND,   "power": 65,  "pp": 20},
    0x7E: {"name": "Fire Blast",     "type": FIRE,     "power": 120, "pp": 5},
    0x7F: {"name": "Waterfall",      "type": WATER,    "power": 80,  "pp": 15},
    0x80: {"name": "Clamp",          "type": WATER,    "power": 35,  "pp": 10},
    0x81: {"name": "Swift",          "type": NORMAL,   "power": 60,  "pp": 20},
    0x82: {"name": "Skull Bash",     "type": NORMAL,   "power": 100, "pp": 15},
    0x83: {"name": "Spike Cannon",   "type": NORMAL,   "power": 20,  "pp": 15},
    0x84: {"name": "Constrict",      "type": NORMAL,   "power": 10,  "pp": 35},
    0x85: {"name": "Amnesia",        "type": PSYCHIC,  "power": 0,   "pp": 20},
    0x86: {"name": "Kinesis",        "type": PSYCHIC,  "power": 0,   "pp": 15},
    0x87: {"name": "Soft-Boiled",    "type": NORMAL,   "power": 0,   "pp": 10},
    0x88: {"name": "Hi Jump Kick",   "type": FIGHTING, "power": 85,  "pp": 20},
    0x89: {"name": "Glare",          "type": NORMAL,   "power": 0,   "pp": 30},
    0x8A: {"name": "Dream Eater",    "type": PSYCHIC,  "power": 100, "pp": 15},
    0x8B: {"name": "Poison Gas",     "type": POISON,   "power": 0,   "pp": 40},
    0x8C: {"name": "Explosion",      "type": NORMAL,   "power": 250, "pp": 5},
    0x8D: {"name": "Fury Swipes",    "type": NORMAL,   "power": 18,  "pp": 15},
    0x8E: {"name": "Bonemerang",     "type": GROUND,   "power": 50,  "pp": 10},
    0x8F: {"name": "Rest",           "type": PSYCHIC,  "power": 0,   "pp": 10},
    0x90: {"name": "Rock Slide",     "type": ROCK,     "power": 75,  "pp": 10},
    0x91: {"name": "Hyper Fang",     "type": NORMAL,   "power": 80,  "pp": 15},
    0x92: {"name": "Sharpen",        "type": NORMAL,   "power": 0,   "pp": 30},
    0x93: {"name": "Conversion",     "type": NORMAL,   "power": 0,   "pp": 30},
    0x94: {"name": "Tri Attack",     "type": NORMAL,   "power": 80,  "pp": 10},
    0x95: {"name": "Super Fang",     "type": NORMAL,   "power": 0,   "pp": 10},  # halves HP
    0x96: {"name": "Slash",          "type": NORMAL,   "power": 70,  "pp": 20},
    0x97: {"name": "Substitute",     "type": NORMAL,   "power": 0,   "pp": 10},
    0x98: {"name": "Struggle",       "type": NORMAL,   "power": 50,  "pp": 1},   # used when out of PP
}


# ---------------------------------------------------------------------------
# Memory address constants (mirrors memory.py being built in parallel)
# ---------------------------------------------------------------------------
IN_BATTLE          = 0xD057  # nonzero = in battle  (also BATTLE_TYPE: 1=wild, 2=trainer)
PLAYER_SPECIES     = 0xD014  # player active species (internal index)
PLAYER_HP_HI       = 0xD015  # player current HP high byte
PLAYER_HP_LO       = 0xD016  # player current HP low byte
PLAYER_MAX_HP_HI   = 0xD023  # player max HP high byte
PLAYER_MAX_HP_LO   = 0xD024  # player max HP low byte
PLAYER_MOVE1       = 0xD01C  # move slot 1 ID
PLAYER_MOVE2       = 0xD01D  # move slot 2 ID
PLAYER_MOVE3       = 0xD01E  # move slot 3 ID
PLAYER_MOVE4       = 0xD01F  # move slot 4 ID
PLAYER_MOVE1_PP    = 0xD02D  # PP remaining for move 1
PLAYER_MOVE2_PP    = 0xD02E  # PP remaining for move 2
PLAYER_MOVE3_PP    = 0xD02F  # PP remaining for move 3
PLAYER_MOVE4_PP    = 0xD030  # PP remaining for move 4
ENEMY_SPECIES      = 0xCFD9  # enemy species (internal index)
ENEMY_HP_HI        = 0xCFE6  # enemy current HP high byte
ENEMY_HP_LO        = 0xCFE7  # enemy current HP low byte
ENEMY_MAX_HP_HI    = 0xCFF4  # enemy max HP high byte
ENEMY_MAX_HP_LO    = 0xCFF5  # enemy max HP low byte
BATTLE_MENU_CURSOR = 0xCC26  # cursor position in battle menu


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_effectiveness(attack_type: str, defender_types: tuple) -> float:
    """
    Return the combined type-effectiveness multiplier for an attacking type
    against one or two defending types.

    Args:
        attack_type:    The type of the attacking move (e.g. WATER).
        defender_types: Tuple of (type1, type2) where type2 may be None.

    Returns:
        float: 0.0, 0.25, 0.5, 1.0, 2.0, or 4.0
    """
    chart = TYPE_CHART.get(attack_type, {})
    multiplier = 1.0
    for def_type in defender_types:
        if def_type is not None:
            multiplier *= chart.get(def_type, 1.0)
    return multiplier


# ---------------------------------------------------------------------------
# BattleAI class
# ---------------------------------------------------------------------------

class BattleAI:
    """
    Handles all battle decision-making and execution for Pokemon Blue.

    Expects a pyboy instance (PyBoy 2.x) and reads game memory directly.
    The game_state parameter is a stub for the GameState object from
    emulator.py (built in parallel); we fall back to direct pyboy reads.
    """

    def __init__(self, pyboy, game_state=None):
        """
        Args:
            pyboy:      PyBoy 2.x instance with the game running.
            game_state: Optional GameState from emulator.py (may be None).
        """
        self.pyboy = pyboy
        self.game_state = game_state

    # ------------------------------------------------------------------
    # Memory helpers
    # ------------------------------------------------------------------

    def _read(self, addr: int) -> int:
        """Read one byte from Game Boy memory."""
        return self.pyboy.memory[addr]

    def _read16(self, hi_addr: int, lo_addr: int) -> int:
        """Read a big-endian 16-bit value from two consecutive bytes."""
        return (self._read(hi_addr) << 8) | self._read(lo_addr)

    # ------------------------------------------------------------------
    # State reads
    # ------------------------------------------------------------------

    def is_in_battle(self) -> bool:
        return self._read(IN_BATTLE) != 0

    def is_wild_battle(self) -> bool:
        return self._read(IN_BATTLE) == 1

    def get_player_species(self) -> int:
        return self._read(PLAYER_SPECIES)

    def get_enemy_species(self) -> int:
        return self._read(ENEMY_SPECIES)

    def get_player_hp(self) -> int:
        return self._read16(PLAYER_HP_HI, PLAYER_HP_LO)

    def get_player_max_hp(self) -> int:
        return self._read16(PLAYER_MAX_HP_HI, PLAYER_MAX_HP_LO)

    def get_enemy_hp(self) -> int:
        return self._read16(ENEMY_HP_HI, ENEMY_HP_LO)

    def get_move_ids(self) -> list[int]:
        """Return list of 4 move IDs (0 = empty slot)."""
        return [
            self._read(PLAYER_MOVE1),
            self._read(PLAYER_MOVE2),
            self._read(PLAYER_MOVE3),
            self._read(PLAYER_MOVE4),
        ]

    def get_move_pps(self) -> list[int]:
        """Return list of 4 PP values."""
        return [
            self._read(PLAYER_MOVE1_PP),
            self._read(PLAYER_MOVE2_PP),
            self._read(PLAYER_MOVE3_PP),
            self._read(PLAYER_MOVE4_PP),
        ]

    def get_player_types(self) -> tuple[str, str | None]:
        species = self.get_player_species()
        return SPECIES_TYPES.get(species, (NORMAL, None))

    def get_enemy_types(self) -> tuple[str, str | None]:
        species = self.get_enemy_species()
        return SPECIES_TYPES.get(species, (NORMAL, None))

    # ------------------------------------------------------------------
    # AI decision methods
    # ------------------------------------------------------------------

    def get_effectiveness(self, move_type: str, defender_types: tuple) -> float:
        """Wrapper for module-level get_effectiveness."""
        return get_effectiveness(move_type, defender_types)

    def get_best_move(self) -> int:
        """
        Choose the best move slot (0-3) to use this turn.

        Strategy:
          1. Skip moves with 0 PP.
          2. Score each move: effectiveness * power.
          3. Return the slot with highest score.
          4. Fall back to slot 0 (or first move with PP) if unsure.

        Returns:
            int: move slot index 0-3.
        """
        move_ids = self.get_move_ids()
        move_pps = self.get_move_pps()
        enemy_types = self.get_enemy_types()

        best_slot = -1
        best_score = -1.0
        fallback_slot = -1

        for slot in range(4):
            move_id = move_ids[slot]
            if move_id == 0 or move_pps[slot] == 0:
                continue  # empty slot or out of PP

            if fallback_slot == -1:
                fallback_slot = slot

            move = MOVE_DATA.get(move_id)
            if move is None:
                continue

            power = move["power"]
            if power == 0:
                # Status move — low base score so we prefer damaging moves
                score = 0.1
            else:
                eff = get_effectiveness(move["type"], enemy_types)
                score = power * eff

            if score > best_score:
                best_score = score
                best_slot = slot

        if best_slot != -1:
            return best_slot
        if fallback_slot != -1:
            return fallback_slot
        return 0  # absolute fallback

    def should_use_item(self) -> str | None:
        """
        Decide whether to use a healing item.

        Returns item name string or None.
        """
        current_hp = self.get_player_hp()
        max_hp = self.get_player_max_hp()

        if max_hp == 0:
            return None

        ratio = current_hp / max_hp
        if ratio < 0.20:
            return "MAX POTION"
        if ratio < 0.50:
            return "POTION"
        return None

    def should_flee(self) -> bool:
        """
        Decide whether to flee (wild battles only).
        Flee if we have no usable moves (all PP depleted).
        """
        if not self.is_wild_battle():
            return False
        pps = self.get_move_pps()
        ids = self.get_move_ids()
        # Flee if every non-empty slot has 0 PP
        for move_id, pp in zip(ids, pps):
            if move_id != 0 and pp > 0:
                return False
        return True

    def get_action(self) -> dict:
        """
        Main decision point. Returns an action dict:
          {"action": "fight", "move": 0-3}
          {"action": "item",  "item": "POTION"}
          {"action": "flee"}
          {"action": "wait"}
        """
        if not self.is_in_battle():
            return {"action": "wait"}

        if self.should_flee():
            return {"action": "flee"}

        item = self.should_use_item()
        if item:
            return {"action": "item", "item": item}

        move_slot = self.get_best_move()
        return {"action": "fight", "move": move_slot}

    # ------------------------------------------------------------------
    # Execution helpers (PyBoy 2.x button API)
    # ------------------------------------------------------------------

    def _press(self, button: str, ticks: int = 30):
        """Press and release a button, then advance the emulator."""
        self.pyboy.button(button)
        self.pyboy.button_release(button)
        self.pyboy.tick(ticks)

    def _press_a(self, ticks: int = 30):
        self._press("a", ticks)

    def _press_b(self, ticks: int = 30):
        self._press("b", ticks)

    def _press_up(self, ticks: int = 10):
        self._press("up", ticks)

    def _press_down(self, ticks: int = 10):
        self._press("down", ticks)

    # ------------------------------------------------------------------
    # Battle menu navigation
    # ------------------------------------------------------------------

    def execute_fight(self, move_slot: int):
        """
        Navigate the battle UI to use the move at move_slot (0-3).

        Battle menu layout:
          FIGHT  PKMN
          ITEM   RUN
        Cursor starts at FIGHT (top-left). Press A to enter move list.
        Move list: 4 moves listed vertically, cursor starts at slot 0.
        Navigate with up/down, confirm with A.
        """
        # Confirm FIGHT (cursor should already be there)
        self._press_a(ticks=30)

        # Now in move selection. Cursor starts at slot 0.
        # Navigate down to target slot.
        for _ in range(move_slot):
            self._press_down(ticks=10)

        # Confirm move selection
        self._press_a(ticks=60)  # longer wait for animation start

    def execute_item(self, item_name: str):
        """
        Use a healing item from the bag during battle.
        Battle menu: FIGHT(TL) PKMN(TR) / ITEM(BL) RUN(BR)
        Navigate to ITEM by pressing down then A.
        Item bag navigation is simplified — uses first available healing item.
        """
        # Navigate to ITEM (one down from FIGHT)
        self._press_down(ticks=10)
        self._press_a(ticks=30)  # open bag

        # In Gen 1 the bag is a simple list — scroll to find the item.
        # For now: attempt to find it in the first 10 slots, skip otherwise.
        for _ in range(10):
            self._press_a(ticks=30)   # use first highlighted item
            break  # simplified; real implementation would check item name

    def execute_flee(self):
        """
        Attempt to RUN from a wild battle.
        Battle menu: FIGHT(TL) PKMN(TR) / ITEM(BL) RUN(BR)
        Navigate to RUN: right from FIGHT, then down — or: down then right.
        """
        # From FIGHT: press right to reach PKMN, then down to reach RUN
        # OR: press down to ITEM, then right to RUN
        self._press("right", ticks=10)  # FIGHT -> PKMN
        self._press_down(ticks=10)       # PKMN -> RUN
        self._press_a(ticks=60)          # confirm RUN

    def handle_battle_turn(self):
        """
        Execute one full battle turn:
          1. Read game state
          2. Decide action
          3. Execute action
          4. Wait for animations
        """
        action = self.get_action()
        act = action.get("action", "wait")

        if act == "fight":
            self.execute_fight(action["move"])
        elif act == "item":
            self.execute_item(action["item"])
        elif act == "flee":
            self.execute_flee()
        else:
            # wait — tick a few frames for animations/text
            self.pyboy.tick(60)

    def run_battle_loop(self, max_turns: int = 200):
        """
        Loop until the battle ends (enemy fainted, we fled, or lost).

        Args:
            max_turns: Safety limit to prevent infinite loops.
        """
        turn = 0
        while self.is_in_battle() and turn < max_turns:
            # Give the game time to settle (text boxes, animations)
            self.pyboy.tick(30)

            if not self.is_in_battle():
                break

            self.handle_battle_turn()
            turn += 1

            # Wait for the game to process the move (animations can be slow)
            for _ in range(10):
                self.pyboy.tick(30)
                if not self.is_in_battle():
                    break
