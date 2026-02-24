"""
memory.py - Gen 1 Pokemon Blue memory map and GameState reader.

All addresses are for Pokemon Blue English (same layout as Pokemon Red).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from emulator import PokemonEmulator

# ---------------------------------------------------------------------------
# Player / Map
# ---------------------------------------------------------------------------
MAP_ID         = 0xD35E   # Current map ID (1 byte)
PLAYER_Y       = 0xD361   # Player Y tile position (wYCoord in disassembly)
PLAYER_X       = 0xD362   # Player X tile position (wXCoord in disassembly)

# ---------------------------------------------------------------------------
# Battle
# ---------------------------------------------------------------------------
BATTLE_TYPE    = 0xD057   # 0 = no battle, 1 = wild, 2 = trainer
IN_BATTLE      = 0xD057   # Alias — nonzero means in battle

# Active (battle-slot) Pokemon HP
PLAYER_CURRENT_HP_HI = 0xD015   # High byte of active Pokemon current HP
PLAYER_CURRENT_HP_LO = 0xD016   # Low byte
PLAYER_MAX_HP_HI     = 0xD023   # High byte of active Pokemon max HP
PLAYER_MAX_HP_LO     = 0xD024   # Low byte

ENEMY_CURRENT_HP_HI  = 0xCFE6   # High byte of enemy current HP
ENEMY_CURRENT_HP_LO  = 0xCFE7
ENEMY_MAX_HP_HI      = 0xCFF4   # High byte of enemy max HP
ENEMY_MAX_HP_LO      = 0xCFF5

# ---------------------------------------------------------------------------
# Party
# ---------------------------------------------------------------------------
PARTY_COUNT         = 0xD163   # Number of Pokemon in party (0–6)
PARTY_MON1_SPECIES  = 0xD164   # Species ID of slot 1
PARTY_MON1_HP_HI    = 0xD16C   # Current HP high byte, slot 1
PARTY_MON1_HP_LO    = 0xD16D
PARTY_MON1_MAXHP_HI = 0xD18D  # Max HP high byte, slot 1
PARTY_MON1_MAXHP_LO = 0xD18E

# Slots 2–6 are offset by 0x2C each from slot 1 base (0xD16B structure start)
PARTY_SLOT_STRIDE   = 0x2C

# ---------------------------------------------------------------------------
# Battle / Menu
# ---------------------------------------------------------------------------
BATTLE_CURSOR  = 0xCC26   # Battle menu cursor position
CURRENT_MENU   = 0xCC24   # Current menu type
DIALOG_BOX     = 0xC4F1   # Dialog open flag
TEXT_ID        = 0xCFC4   # Current text message ID
OVERWORLD_TEXT = 0xC3A0   # Text display flag

# ---------------------------------------------------------------------------
# Progression / Flags
# ---------------------------------------------------------------------------
BADGES         = 0xD356   # Badge bitfield (bit 0=Boulder, 1=Cascade, …)
HM_MOVES       = 0xD730   # HM flags learned

# ---------------------------------------------------------------------------
# Items / Money
# ---------------------------------------------------------------------------
ITEM_COUNT     = 0xD31D   # Number of items in bag
MONEY          = 0xD347   # Money (3 bytes BCD)

# ---------------------------------------------------------------------------
# Map name lookup
# ---------------------------------------------------------------------------
MAP_NAMES: dict[int, str] = {
    0x00: "PALLET_TOWN",
    0x01: "VIRIDIAN_CITY",
    0x02: "PEWTER_CITY",
    0x03: "CERULEAN_CITY",
    0x04: "VERMILION_CITY",        # (various sources differ; adjust as needed)
    0x05: "CERULEAN_CAVE",
    0x06: "ROCK_TUNNEL",
    0x0C: "VERMILION_CITY",
    0x0D: "LAVENDER_TOWN",
    0x0E: "FUCHSIA_CITY",
    0x11: "CELADON_CITY",
    0x12: "FUCHSIA_CITY",
    0x13: "CINNABAR_ISLAND",
    0x14: "INDIGO_PLATEAU",
    0x15: "SAFFRON_CITY",
    0x28: "VIRIDIAN_FOREST",
    0x33: "MT_MOON",
    0x59: "SAFARI_ZONE",
    0xED: "UNDERGROUND_PATH",
    0xFF: "UNKNOWN",
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _read16(emu: "PokemonEmulator", hi_addr: int, lo_addr: int) -> int:
    """Read a big-endian 2-byte value from two adjacent addresses."""
    hi = emu.read_memory(hi_addr)
    lo = emu.read_memory(lo_addr)
    return (hi << 8) | lo


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------

class GameState:
    """
    Reads and caches relevant Game Boy memory values for one frame.
    Call ``update()`` once per decision step to refresh.
    """

    def __init__(self, emu: "PokemonEmulator") -> None:
        self._emu = emu

        # Raw cached values (populated by update())
        self._map_id:        int = 0
        self._player_x:      int = 0
        self._player_y:      int = 0
        self._battle_type:   int = 0
        self._player_hp:     int = 0
        self._player_max_hp: int = 0
        self._enemy_hp:      int = 0
        self._enemy_max_hp:  int = 0
        self._badges:        int = 0
        self._party: list[dict] = []
        self._dialog_open:   bool = False

    # ------------------------------------------------------------------
    # Core refresh
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Read all relevant memory addresses and update internal state."""
        e = self._emu

        self._map_id        = e.read_memory(MAP_ID)
        self._player_x      = e.read_memory(PLAYER_X)
        self._player_y      = e.read_memory(PLAYER_Y)
        self._battle_type   = e.read_memory(BATTLE_TYPE)
        self._player_hp     = _read16(e, PLAYER_CURRENT_HP_HI, PLAYER_CURRENT_HP_LO)
        self._player_max_hp = _read16(e, PLAYER_MAX_HP_HI,     PLAYER_MAX_HP_LO)
        self._enemy_hp      = _read16(e, ENEMY_CURRENT_HP_HI,  ENEMY_CURRENT_HP_LO)
        self._enemy_max_hp  = _read16(e, ENEMY_MAX_HP_HI,      ENEMY_MAX_HP_LO)
        self._badges        = e.read_memory(BADGES)
        self._dialog_open   = bool(e.read_memory(DIALOG_BOX))
        self._party         = self._read_party()

    def _read_party(self) -> list[dict]:
        """Read up to 6 party Pokemon from memory."""
        e = self._emu
        count = e.read_memory(PARTY_COUNT)
        count = min(count, 6)  # Sanity cap

        party = []
        for slot in range(count):
            offset = slot * PARTY_SLOT_STRIDE
            species = e.read_memory(PARTY_MON1_SPECIES + slot)  # Species list is contiguous
            hp     = _read16(e, PARTY_MON1_HP_HI    + offset, PARTY_MON1_HP_LO    + offset)
            max_hp = _read16(e, PARTY_MON1_MAXHP_HI + offset, PARTY_MON1_MAXHP_LO + offset)
            party.append({
                "slot":    slot + 1,
                "species": species,
                "hp":      hp,
                "max_hp":  max_hp,
            })
        return party

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def in_battle(self) -> bool:
        return self._battle_type != 0

    @property
    def battle_type(self) -> int:
        """0=none, 1=wild, 2=trainer"""
        return self._battle_type

    @property
    def map_id(self) -> int:
        return self._map_id

    @property
    def map_name(self) -> str:
        return MAP_NAMES.get(self._map_id, f"MAP_0x{self._map_id:02X}")

    @property
    def player_x(self) -> int:
        return self._player_x

    @property
    def player_y(self) -> int:
        return self._player_y

    @property
    def player_hp(self) -> int:
        return self._player_hp

    @property
    def player_max_hp(self) -> int:
        return self._player_max_hp

    @property
    def enemy_hp(self) -> int:
        return self._enemy_hp

    @property
    def enemy_max_hp(self) -> int:
        return self._enemy_max_hp

    @property
    def badges(self) -> int:
        return self._badges

    @property
    def badge_count(self) -> int:
        return bin(self._badges).count("1")

    @property
    def party(self) -> list[dict]:
        return list(self._party)

    @property
    def dialog_open(self) -> bool:
        """True if a text/dialog box is currently displayed."""
        return self._dialog_open

    @property
    def party_healthy(self) -> bool:
        """True if at least one party Pokemon has HP > 0."""
        return any(mon["hp"] > 0 for mon in self._party)

    @property
    def needs_heal(self) -> bool:
        """True if any party Pokemon is at < 30 % of max HP."""
        for mon in self._party:
            if mon["max_hp"] > 0 and (mon["hp"] / mon["max_hp"]) < 0.30:
                return True
        return False

    # ------------------------------------------------------------------
    # Debug string
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        lines = [
            "=== GameState ===",
            f"  Map:      {self.map_name} (0x{self.map_id:02X})",
            f"  Position: ({self.player_x}, {self.player_y})",
            f"  Badges:   {self.badge_count} ({self._badges:08b})",
            f"  Battle:   {['none', 'wild', 'trainer'][min(self._battle_type, 2)]} "
            f"(type={self._battle_type})",
            f"  HP:       {self.player_hp}/{self.player_max_hp}  "
            f"(enemy: {self.enemy_hp}/{self.enemy_max_hp})",
            f"  Needs heal: {self.needs_heal}",
            f"  Party ({len(self._party)}):",
        ]
        for mon in self._party:
            pct = (mon["hp"] / mon["max_hp"] * 100) if mon["max_hp"] else 0
            lines.append(
                f"    Slot {mon['slot']}: species=#{mon['species']:03d}  "
                f"HP {mon['hp']}/{mon['max_hp']} ({pct:.0f}%)"
            )
        if not self._party:
            lines.append("    (empty)")
        lines.append("=================")
        return "\n".join(lines)
