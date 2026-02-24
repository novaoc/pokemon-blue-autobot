"""
navigation.py — Overworld navigation and game progression for Pokemon Blue autobot.

Depends on emulator.py (PokemonEmulator) and memory.py (GameState) interfaces,
both defined in their SPEC files. Uses stubs when run in isolation/tests.
"""

import json
import logging
import os
import time
from enum import Enum
from typing import Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MAP_IDS — map_id (int) → human-readable name
# ---------------------------------------------------------------------------
MAP_IDS = {
    # Towns / Cities
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

    # Routes
    0x0E: "ROUTE_1",
    0x0F: "ROUTE_2",
    0x10: "ROUTE_3",
    0x11: "ROUTE_4",   # NOTE: 0x11 shared name — context-dependent; city takes priority
    0x16: "ROUTE_5",
    0x17: "ROUTE_6",
    0x18: "ROUTE_7",
    0x19: "ROUTE_8",
    0x1A: "ROUTE_9",
    0x1B: "ROUTE_10",
    0x1C: "ROUTE_11",
    0x1D: "ROUTE_12",
    0x1E: "ROUTE_13",
    0x1F: "ROUTE_14",
    0x20: "ROUTE_15",
    0x21: "ROUTE_16",
    0x22: "ROUTE_17",   # Cycling Road
    0x23: "ROUTE_18",
    0x2C: "ROUTE_22",
    0x41: "ROUTE_23",
    0x32: "ROUTE_24",
    0x33: "ROUTE_25",

    # Dungeons / Special
    0x3B: "VIRIDIAN_FOREST",
    0x51: "MT_MOON_1F",
    0x52: "MT_MOON_B1F",
    0x53: "MT_MOON_B2F",
    0x54: "ROCK_TUNNEL_1F",
    0x55: "ROCK_TUNNEL_B1F",
    0x61: "POKEMON_TOWER_1F",
    0x62: "POKEMON_TOWER_2F",
    0x63: "POKEMON_TOWER_3F",
    0x64: "POKEMON_TOWER_4F",
    0x65: "POKEMON_TOWER_5F",
    0x66: "POKEMON_TOWER_6F",
    0x67: "POKEMON_TOWER_7F",
    0x6E: "SAFARI_ZONE",
    0x79: "SS_ANNE",
    0x82: "SILPH_CO_1F",
    0x8B: "ROCKET_HIDEOUT_B1F",
    0x8C: "ROCKET_HIDEOUT_B2F",
    0x8D: "ROCKET_HIDEOUT_B3F",
    0x8E: "ROCKET_HIDEOUT_B4F",
    0xA4: "POKEMON_MANSION_1F",
    0xA5: "POKEMON_MANSION_2F",
    0xA6: "POKEMON_MANSION_3F",
    0xA7: "POKEMON_MANSION_B1F",
    0xAE: "VICTORY_ROAD_1F",
    0xAF: "VICTORY_ROAD_2F",
    0xB0: "VICTORY_ROAD_3F",

    # Gyms
    0xC5: "VIRIDIAN_GYM",
    0xC6: "PEWTER_GYM",
    0xC7: "CERULEAN_GYM",
    0xC8: "VERMILION_GYM",
    0xC9: "CELADON_GYM",
    0xCA: "FUCHSIA_GYM",
    0xCB: "SAFFRON_GYM",
    0xCC: "CINNABAR_GYM",

    # Pokemon Centers (interiors)
    0xD0: "VIRIDIAN_POKECENTER",
    0xD1: "PEWTER_POKECENTER",
    0xD2: "CERULEAN_POKECENTER",
    0xD3: "LAVENDER_POKECENTER",
    0xD4: "VERMILION_POKECENTER",
    0xD5: "CELADON_POKECENTER",
    0xD6: "FUCHSIA_POKECENTER",
    0xD7: "CINNABAR_POKECENTER",
    0xD8: "SAFFRON_POKECENTER",
    0xD9: "INDIGO_POKECENTER",

    # Oak's lab / player house etc.
    0xC4: "OAKS_LAB",
    0xC3: "REDS_HOUSE_1F",
    0xC2: "REDS_HOUSE_2F",
}

# ---------------------------------------------------------------------------
# POKECENTER_LOCATIONS — map_id → (counter_x, counter_y) of the Nurse Joy counter
# These are approximate tile coords for the reception desk.
# ---------------------------------------------------------------------------
POKECENTER_LOCATIONS = {
    0x01: (7, 4),    # Viridian City Pokecenter
    0x02: (7, 4),    # Pewter City Pokecenter
    0x03: (7, 4),    # Cerulean City Pokecenter
    0x0D: (7, 4),    # Lavender Town Pokecenter
    0x0C: (7, 4),    # Vermilion City Pokecenter
    0x11: (7, 4),    # Celadon City Pokecenter
    0x12: (7, 4),    # Fuchsia City Pokecenter
    0x13: (7, 4),    # Cinnabar Island Pokecenter
    0x15: (7, 4),    # Saffron City Pokecenter
    0x14: (7, 4),    # Indigo Plateau Pokecenter
    # Route 10 Pokecenter (before Rock Tunnel)
    0x1B: (7, 4),    # Route 10 Pokecenter (approximate)
}

# Pokecenter building entrance tiles (overworld) per city map_id
# (x, y) of the door tile on the overworld map
POKECENTER_DOORS = {
    0x01: (19, 19),   # Viridian City
    0x02: (10, 11),   # Pewter City
    0x03: (16, 17),   # Cerulean City
    0x0D: (5, 3),     # Lavender Town
    0x0C: (15, 5),    # Vermilion City
    0x11: (28, 11),   # Celadon City
    0x12: (18, 3),    # Fuchsia City
    0x13: (11, 7),    # Cinnabar Island
    0x15: (17, 20),   # Saffron City
    0x14: (7, 9),     # Indigo Plateau
}


# ---------------------------------------------------------------------------
# Direction enum
# ---------------------------------------------------------------------------
class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"

    @property
    def opposite(self) -> "Direction":
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposites[self]

    @property
    def perpendiculars(self) -> Tuple["Direction", "Direction"]:
        if self in (Direction.UP, Direction.DOWN):
            return Direction.LEFT, Direction.RIGHT
        return Direction.UP, Direction.DOWN


# ---------------------------------------------------------------------------
# Navigator class
# ---------------------------------------------------------------------------
class Navigator:
    """
    Handles low-level movement and interaction with the overworld.

    Expects:
        emulator  – PokemonEmulator (or stub) with .button(), .button_release(), .tick()
        game_state – GameState (or stub) with .player_x, .player_y, .map_id, .in_battle, .dialog_open
    """

    FRAMES_PER_STEP = 16       # frames to wait after pressing a direction
    FRAMES_DIALOG = 30         # frames between dialog A presses
    FRAMES_INTERACT = 10       # frames to hold A for interaction
    MAX_STUCK_TRIES = 5        # consecutive same-position attempts before "stuck"
    ESCAPE_STEPS = 3           # perpendicular steps when escaping stuck

    def __init__(self, emulator, game_state):
        self.emu = emulator
        self.gs = game_state

    # ------------------------------------------------------------------
    # Low-level primitives
    # ------------------------------------------------------------------

    def _press(self, button: str, frames: int = 1):
        """Press and immediately release a button, then tick."""
        self.emu.button(button)
        self.emu.tick(frames)
        self.emu.button_release(button)

    def _tick(self, frames: int):
        self.emu.tick(frames)

    # ------------------------------------------------------------------
    # move_one_step
    # ------------------------------------------------------------------

    def move_one_step(self, direction: Direction) -> bool:
        """
        Press direction button, wait ~16 frames for walk animation, then check
        whether the player's position actually changed.

        Returns True if moved successfully, False if blocked.
        """
        btn = direction.value
        x_before = self.gs.player_x
        y_before = self.gs.player_y

        self.emu.button(btn)
        self.emu.tick(self.FRAMES_PER_STEP)
        self.emu.button_release(btn)
        self.gs.update()  # refresh memory snapshot so position reads are fresh

        x_after = self.gs.player_x
        y_after = self.gs.player_y

        moved = (x_after != x_before) or (y_after != y_before)
        if not moved:
            log.debug(f"move_one_step({direction.name}): BLOCKED at ({x_before},{y_before})")
        else:
            log.debug(f"move_one_step({direction.name}): ({x_before},{y_before}) → ({x_after},{y_after})")
        return moved

    # ------------------------------------------------------------------
    # navigate_to
    # ------------------------------------------------------------------

    def navigate_to(
        self,
        target_x: int,
        target_y: int,
        map_id: Optional[int] = None,
        max_steps: int = 2000,
    ) -> bool:
        """
        Greedy pathfinding toward (target_x, target_y).

        Strategy:
        - Each iteration, move along whichever axis has the larger delta.
        - If stuck (same position after MAX_STUCK_TRIES consecutive attempts),
          try ESCAPE_STEPS perpendicular moves then resume.
        - Returns True when position matches target, False if max_steps exceeded.
        """
        log.info(f"navigate_to({target_x}, {target_y})")

        stuck_count = 0
        last_pos = (self.gs.player_x, self.gs.player_y)

        for step in range(max_steps):
            if self.gs.in_battle:
                log.warning("navigate_to: battle started mid-navigation — pausing")
                return False

            cur_x = self.gs.player_x
            cur_y = self.gs.player_y

            if cur_x == target_x and cur_y == target_y:
                log.info(f"navigate_to: reached ({target_x},{target_y}) in {step} steps")
                return True

            # Determine primary direction
            dx = target_x - cur_x
            dy = target_y - cur_y

            if abs(dx) >= abs(dy):
                primary = Direction.RIGHT if dx > 0 else Direction.LEFT
                secondary = Direction.DOWN if dy > 0 else Direction.UP
            else:
                primary = Direction.DOWN if dy > 0 else Direction.UP
                secondary = Direction.RIGHT if dx > 0 else Direction.LEFT

            moved = self.move_one_step(primary)
            if not moved and (dx != 0):
                moved = self.move_one_step(secondary)

            # Stuck detection
            new_pos = (self.gs.player_x, self.gs.player_y)
            if new_pos == last_pos:
                stuck_count += 1
                log.debug(f"navigate_to: stuck count {stuck_count} at {new_pos}")
                if stuck_count >= self.MAX_STUCK_TRIES:
                    log.warning(f"navigate_to: stuck at {new_pos}, attempting escape")
                    escaped = self._escape_stuck(primary)
                    stuck_count = 0
                    if not escaped:
                        log.error("navigate_to: escape failed — aborting")
                        return False
            else:
                stuck_count = 0
                last_pos = new_pos

        log.warning(f"navigate_to: max_steps ({max_steps}) exceeded — target not reached")
        return False

    def _escape_stuck(self, blocked_direction: Direction) -> bool:
        """
        Attempt to escape a stuck position by moving perpendicular
        ESCAPE_STEPS times, then try resuming.
        Tries both perpendicular directions.
        """
        perp1, perp2 = blocked_direction.perpendiculars
        for perp in (perp1, perp2):
            for _ in range(self.ESCAPE_STEPS):
                moved = self.move_one_step(perp)
                if moved:
                    log.debug(f"escape_stuck: moved {perp.name}")
                    return True
        return False

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------

    def press_a_interact(self):
        """Press A to interact with whatever is in front of the player."""
        log.debug("press_a_interact")
        self.emu.button("a")
        self.emu.tick(self.FRAMES_INTERACT)
        self.emu.button_release("a")

    def mash_through_dialog(self, max_presses: int = 50) -> int:
        """
        Repeatedly press A every FRAMES_DIALOG frames until:
          - dialog_open flag clears, or
          - max_presses reached.
        Returns number of presses made.
        """
        log.debug(f"mash_through_dialog(max={max_presses})")
        presses = 0
        for _ in range(max_presses):
            if not self.gs.dialog_open:
                log.debug(f"mash_through_dialog: dialog cleared after {presses} presses")
                break
            self.emu.button("a")
            self.emu.tick(self.FRAMES_DIALOG)
            self.emu.button_release("a")
            presses += 1
        return presses

    # ------------------------------------------------------------------
    # Building entry
    # ------------------------------------------------------------------

    def enter_building(self, door_x: int, door_y: int):
        """
        Navigate to the tile just in front of a building door, then press UP
        to walk through. The target tile is the door itself; we stand one
        tile south of it and press UP.
        """
        log.info(f"enter_building: door at ({door_x},{door_y})")
        # Stand directly on the door tile (one step south of it so UP triggers entry)
        approach_y = door_y + 1
        self.navigate_to(door_x, approach_y)
        # Walk UP into the door
        self.emu.button("up")
        self.emu.tick(32)   # give time for map transition
        self.emu.button_release("up")
        log.info("enter_building: entered (map transition expected)")

    def exit_to_overworld(self):
        """
        Navigate to an exit. Most buildings exit southward from the bottom row.
        We simply walk DOWN until the map changes or max steps reached.
        """
        log.info("exit_to_overworld: walking toward exit")
        start_map = self.gs.map_id
        for _ in range(30):
            self.move_one_step(Direction.DOWN)
            if self.gs.map_id != start_map:
                log.info("exit_to_overworld: map changed — exited successfully")
                return
        log.warning("exit_to_overworld: map did not change after 30 DOWN steps")


# ---------------------------------------------------------------------------
# go_to_pokecenter helper
# ---------------------------------------------------------------------------

def go_to_pokecenter(navigator: Navigator, game_state) -> bool:
    """
    Find the nearest Pokemon Center for the current map, navigate to it,
    walk to the counter, and mash through the healing dialog.

    Returns True if healing was initiated.
    """
    current_map = game_state.map_id
    log.info(f"go_to_pokecenter: current map 0x{current_map:02X} ({MAP_IDS.get(current_map, '?')})")

    # Find pokecenter door for current map
    door = POKECENTER_DOORS.get(current_map)
    if door is None:
        log.warning(f"go_to_pokecenter: no pokecenter door known for map 0x{current_map:02X}")
        return False

    door_x, door_y = door
    navigator.enter_building(door_x, door_y)

    # Once inside, walk to the counter
    # Counter is typically at (7, 4) inside the pokecenter interior
    counter_x, counter_y = POKECENTER_LOCATIONS.get(current_map, (7, 4))
    navigator.navigate_to(counter_x, counter_y - 1)  # stand one tile south of counter

    # Interact with nurse Joy
    navigator.press_a_interact()
    navigator.mash_through_dialog(max_presses=60)

    log.info("go_to_pokecenter: healing dialog completed")
    return True


# ---------------------------------------------------------------------------
# ProgressionManager
# ---------------------------------------------------------------------------

STATE_FILE = os.path.join(os.path.dirname(__file__), "progression_state.json")

# Badge bit positions in BADGES byte (0xD356)
BADGE_BOULDER   = 0   # Brock     — Pewter City
BADGE_CASCADE   = 1   # Misty     — Cerulean City
BADGE_THUNDER   = 2   # Lt. Surge — Vermilion City
BADGE_RAINBOW   = 3   # Erika     — Celadon City
BADGE_SOUL      = 4   # Koga      — Fuchsia City
BADGE_MARSH     = 5   # Sabrina   — Saffron City
BADGE_VOLCANO   = 6   # Blaine    — Cinnabar Island
BADGE_EARTH     = 7   # Giovanni  — Viridian City

# Key item flags — addresses in SPEC_EMULATOR.md / memory.py
# These are illustrative; exact addresses from memory map
ITEM_SS_TICKET   = 0x3F   # SS Ticket item ID in Pokemon Blue
ITEM_SILPH_SCOPE = 0x48   # Silph Scope
ITEM_POKE_FLUTE  = 0x49   # Poke Flute
ITEM_CARD_KEY    = 0x60   # Card Key


def _has_badge(badges_byte: int, badge_bit: int) -> bool:
    return bool(badges_byte & (1 << badge_bit))


class ProgressionManager:
    """
    High-level game progression brain.

    Tracks which major story step to execute next, based on:
    - BADGES byte (0xD356)
    - Key item flags
    - progression_state.json on disk
    """

    # Ordered list of step names
    STEP_ORDER = [
        "pallet_start",
        "route1_to_viridian",
        "viridian_parcel",
        "viridian_forest",
        "pewter_brock",
        "mt_moon",
        "cerulean_misty",
        "nugget_bridge_bill",
        "vermilion_ltsurge",
        "rock_tunnel",
        "celadon_erika",
        "pokemon_tower",
        "saffron_sabrina",
        "fuchsia_koga",
        "cinnabar_blaine",
        "viridian_giovanni",
        "elite_four",
        "game_complete",
    ]

    def __init__(self, emulator, game_state, navigator: Navigator, battle_ai=None):
        self.emu = emulator
        self.gs = game_state
        self.nav = navigator
        self.battle_ai = battle_ai
        self.state = self.load_state()

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                log.info(f"load_state: loaded from {STATE_FILE} — step={state.get('step')}")
                return state
            except (json.JSONDecodeError, IOError) as e:
                log.warning(f"load_state: failed to read {STATE_FILE}: {e}; using defaults")
        return {"step": "pallet_start", "badges": 0, "completed_steps": []}

    def save_state(self, state: Optional[dict] = None):
        if state is None:
            state = self.state
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
            log.info(f"save_state: saved to {STATE_FILE}")
        except IOError as e:
            log.error(f"save_state: failed: {e}")

    def _mark_complete(self, step_name: str):
        if step_name not in self.state["completed_steps"]:
            self.state["completed_steps"].append(step_name)
        # Advance to next step
        idx = self.STEP_ORDER.index(step_name) if step_name in self.STEP_ORDER else -1
        if idx >= 0 and idx + 1 < len(self.STEP_ORDER):
            self.state["step"] = self.STEP_ORDER[idx + 1]
        self.state["badges"] = self.gs.badges
        self.save_state()

    # ------------------------------------------------------------------
    # get_current_step — badge/flag-based detection
    # ------------------------------------------------------------------

    def get_current_step(self) -> str:
        """
        Determine the current progression step from game memory (badges byte).
        Falls back to saved state if memory is unavailable.
        """
        try:
            badges = self.gs.badges
        except Exception:
            return self.state.get("step", "pallet_start")

        # Map badge count → expected next step
        badge_count = bin(badges).count("1")

        if badge_count == 0:
            # Pre-Boulder: are we past the parcel?
            saved = self.state.get("step", "pallet_start")
            # Trust the saved step within pre-boulder range
            if saved in ("pallet_start", "route1_to_viridian", "viridian_parcel",
                         "viridian_forest", "pewter_brock"):
                return saved
            return "pallet_start"
        elif badge_count == 1:
            # Have Boulder, heading to Cerulean
            saved = self.state.get("step", "mt_moon")
            if saved in ("mt_moon", "cerulean_misty"):
                return saved
            return "mt_moon"
        elif badge_count == 2:
            saved = self.state.get("step", "nugget_bridge_bill")
            if saved in ("nugget_bridge_bill", "vermilion_ltsurge"):
                return saved
            return "nugget_bridge_bill"
        elif badge_count == 3:
            saved = self.state.get("step", "rock_tunnel")
            if saved in ("rock_tunnel", "celadon_erika"):
                return saved
            return "rock_tunnel"
        elif badge_count == 4:
            saved = self.state.get("step", "pokemon_tower")
            if saved in ("pokemon_tower", "saffron_sabrina", "celadon_erika"):
                return saved
            return "pokemon_tower"
        elif badge_count == 5:
            saved = self.state.get("step", "fuchsia_koga")
            if saved in ("fuchsia_koga", "saffron_sabrina"):
                return saved
            return "fuchsia_koga"
        elif badge_count == 6:
            saved = self.state.get("step", "cinnabar_blaine")
            if saved in ("cinnabar_blaine", "fuchsia_koga"):
                return saved
            return "cinnabar_blaine"
        elif badge_count == 7:
            return "viridian_giovanni"
        elif badge_count == 8:
            return "elite_four"
        return "game_complete"

    def sync_with_badges(self, badges: int) -> None:
        """
        Reset the progression step to match the actual badge count in memory.

        If the saved step is behind what badges imply (e.g. state says
        "pallet_start" but 5 badges are present), advances the saved step
        to the correct minimum for the badge count.
        """
        badge_count = bin(badges).count("1")

        # Map badge count → minimum expected step name
        badge_to_step = {
            0: None,           # Trust saved state for 0 badges
            1: "mt_moon",
            2: "nugget_bridge_bill",
            3: "rock_tunnel",
            4: "pokemon_tower",
            5: "fuchsia_koga",
            6: "cinnabar_blaine",
            7: "viridian_giovanni",
            8: "elite_four",
        }

        expected_step = badge_to_step.get(badge_count)
        current_step  = self.state.get("step", "pallet_start")

        if expected_step is None:
            log.debug("sync_with_badges: 0 badges — keeping saved step '%s'", current_step)
            return

        try:
            saved_idx    = self.STEP_ORDER.index(current_step)
            expected_idx = self.STEP_ORDER.index(expected_step)
        except ValueError:
            log.warning(
                "sync_with_badges: unknown step '%s' or '%s' — resetting to '%s'",
                current_step, expected_step, expected_step,
            )
            self.state["step"] = expected_step
            self.state["badges"] = badges
            self.save_state()
            return

        if saved_idx < expected_idx:
            log.warning(
                "sync_with_badges: mismatch! badges=%d but step='%s' — "
                "advancing to '%s'",
                badge_count, current_step, expected_step,
            )
            self.state["step"] = expected_step
            self.state["badges"] = badges
            self.save_state()
        else:
            log.info(
                "sync_with_badges: OK — badges=%d step='%s' (min expected: '%s')",
                badge_count, current_step, expected_step,
            )

    # ------------------------------------------------------------------
    # Individual step methods
    # ------------------------------------------------------------------

    def step_pallet_town(self):
        """
        Start of game. Walk to Oak's Lab, choose Squirtle.
        After choosing, fight rival, then head north to Route 1.
        """
        log.info("STEP: pallet_start")
        # Oak's Lab is south of the start — coordinates are approximate
        # Player starts in Red's House 2F; walk down and out
        self.nav.navigate_to(5, 7)   # Exit Red's house door area
        # Walk south toward Oak's lab on overworld
        # Pallet Town: Oak's Lab at roughly (5, 13) on map 0x00
        self.nav.navigate_to(5, 13)
        self.nav.enter_building(5, 13)
        # Walk to pokeball table (Squirtle = rightmost)
        self.nav.navigate_to(9, 5)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=80)
        # Rival battle happens automatically; mash through it
        self.nav.mash_through_dialog(max_presses=200)
        log.info("STEP: pallet_start — complete")
        self._mark_complete("pallet_start")

    def step_route1_to_viridian(self):
        """Walk north through Route 1 to Viridian City."""
        log.info("STEP: route1_to_viridian")
        # Exit Oak's lab, head north
        self.nav.exit_to_overworld()
        # Navigate north across Route 1 (map 0x0E)
        # Route 1 is a straight corridor north
        self.nav.navigate_to(5, 0)    # Aim for north edge of Route 1
        log.info("STEP: route1_to_viridian — complete")
        self._mark_complete("route1_to_viridian")

    def step_viridian_parcel(self):
        """
        Pick up parcel from Viridian Mart, deliver to Oak in Pallet Town,
        receive Pokedex. Return to Viridian City.
        """
        log.info("STEP: viridian_parcel")
        # Enter Viridian Mart (approximate door coords on Viridian map 0x01)
        self.nav.enter_building(20, 8)
        # Talk to the mart clerk (top-left counter)
        self.nav.navigate_to(4, 4)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=40)
        self.nav.exit_to_overworld()
        # Head south back to Pallet Town
        self.nav.navigate_to(5, 20)   # south toward Route 1 / Pallet
        # Deliver to Oak
        self.nav.enter_building(5, 13)
        self.nav.navigate_to(5, 5)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=80)
        # Receive Pokedex
        self.nav.mash_through_dialog(max_presses=40)
        self.nav.exit_to_overworld()
        log.info("STEP: viridian_parcel — complete")
        self._mark_complete("viridian_parcel")

    def step_viridian_forest(self):
        """Navigate through Viridian Forest to Pewter City."""
        log.info("STEP: viridian_forest")
        # Head north from Viridian through Route 2 into Viridian Forest
        # General direction: keep going north; handle trainers via battle_ai
        self.nav.navigate_to(10, 0)   # north edge of Viridian City
        # Forest navigation: mostly north with some detours
        # We navigate by pressing UP repeatedly until we exit the forest
        start_map = self.gs.map_id
        steps = 0
        while self.gs.map_id == start_map or MAP_IDS.get(self.gs.map_id, "").startswith("VIRIDIAN_FOREST"):
            if steps > 1000:
                log.warning("step_viridian_forest: timeout after 1000 steps")
                break
            self.nav.move_one_step(Direction.UP)
            steps += 1
        log.info("STEP: viridian_forest — complete")
        self._mark_complete("viridian_forest")

    def step_pewter_brock(self):
        """Heal at Pokecenter, enter Pewter Gym, beat Brock."""
        log.info("STEP: pewter_brock")
        go_to_pokecenter(self.nav, self.gs)
        # Pewter Gym: approx door at (10, 5) on Pewter City map
        self.nav.exit_to_overworld()
        self.nav.enter_building(10, 5)
        # Walk to Brock (at top of gym)
        self.nav.navigate_to(9, 3)
        self.nav.press_a_interact()
        # Battle handled by battle_ai
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: pewter_brock — complete")
        self._mark_complete("pewter_brock")

    def step_mt_moon(self):
        """
        Head east from Pewter along Route 3.
        Navigate through Mt. Moon cave (3 floors) to Route 4 and Cerulean.
        """
        log.info("STEP: mt_moon")
        # Go east through Route 3
        self.nav.navigate_to(30, 8)   # eastern edge of Route 3 (approx)
        # Enter Mt. Moon
        self.nav.enter_building(2, 5)
        # Navigate south-east through the cave floors
        self.nav.navigate_to(25, 15)  # B1F exit area
        self.nav.navigate_to(10, 5)   # B2F exit to Route 4
        log.info("STEP: mt_moon — complete")
        self._mark_complete("mt_moon")

    def step_cerulean_misty(self):
        """Heal, challenge Misty's gym in Cerulean City."""
        log.info("STEP: cerulean_misty")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Cerulean Gym door approx at (16, 5)
        self.nav.enter_building(16, 5)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: cerulean_misty — complete")
        self._mark_complete("cerulean_misty")

    def step_nugget_bridge_bill(self):
        """
        Cross Nugget Bridge (Routes 24/25), reach Bill's Cottage,
        get SS Ticket, return to Cerulean.
        """
        log.info("STEP: nugget_bridge_bill")
        # Head north from Cerulean
        self.nav.navigate_to(15, 0)
        # Cross Nugget Bridge — fight 6 trainers (battle_ai handles)
        self.nav.navigate_to(15, -20)  # Route 24 north
        # Bill's Cottage (Route 25 end)
        self.nav.enter_building(25, 5)
        self.nav.navigate_to(5, 5)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=100)
        self.nav.exit_to_overworld()
        log.info("STEP: nugget_bridge_bill — complete")
        self._mark_complete("nugget_bridge_bill")

    def step_vermilion_ltsurge(self):
        """
        Board SS Anne (get HM01 Cut), then beat Lt. Surge.
        """
        log.info("STEP: vermilion_ltsurge")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # SS Anne dock (approx)
        self.nav.navigate_to(20, 18)
        self.nav.enter_building(20, 18)
        # Get Cut from captain (navigate to top)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=60)
        self.nav.exit_to_overworld()
        # Vermilion Gym
        self.nav.enter_building(15, 8)
        # Solve trash can puzzle (battle_ai or dedicated logic handles)
        self.nav.navigate_to(8, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: vermilion_ltsurge — complete")
        self._mark_complete("vermilion_ltsurge")

    def step_rock_tunnel(self):
        """
        Route 9 east from Cerulean, heal at Route 10 Pokecenter,
        navigate Rock Tunnel (dark cave), exit to Lavender Town.
        """
        log.info("STEP: rock_tunnel")
        # Head east then south
        self.nav.navigate_to(30, 5)
        # Route 10 Pokecenter (heal before dark cave)
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Enter Rock Tunnel
        self.nav.navigate_to(2, 20)
        self.nav.enter_building(2, 20)
        # Navigate through tunnel (down through 2 floors)
        self.nav.navigate_to(15, 25)
        self.nav.navigate_to(5, 10)
        log.info("STEP: rock_tunnel — complete")
        self._mark_complete("rock_tunnel")

    def step_celadon_erika(self):
        """
        Rocket Hideout (get Silph Scope), then Erika's gym.
        """
        log.info("STEP: celadon_erika")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Game Corner (Rocket Hideout entrance)
        self.nav.enter_building(20, 15)
        self.nav.navigate_to(15, 20)
        self.nav.press_a_interact()   # poster switch
        # Navigate basement floors B1-B4
        self.nav.navigate_to(10, 10)
        self.nav.mash_through_dialog(max_presses=200)  # Giovanni battle
        self.nav.exit_to_overworld()
        # Celadon Gym
        self.nav.enter_building(10, 8)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: celadon_erika — complete")
        self._mark_complete("celadon_erika")

    def step_pokemon_tower(self):
        """
        Return to Lavender Town, climb Pokemon Tower (7F),
        rescue Mr. Fuji, receive Poke Flute.
        """
        log.info("STEP: pokemon_tower")
        # Navigate to Pokemon Tower
        self.nav.enter_building(10, 5)
        # Climb 7 floors
        for floor in range(7):
            self.nav.navigate_to(5, 0)  # climb to staircase (approx)
        # Mr. Fuji at top
        self.nav.navigate_to(5, 5)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=100)
        self.nav.exit_to_overworld()
        log.info("STEP: pokemon_tower — complete")
        self._mark_complete("pokemon_tower")

    def step_saffron_sabrina(self):
        """
        Enter Saffron City (give drink to guard),
        clear Silph Co. (get Master Ball), beat Sabrina.
        """
        log.info("STEP: saffron_sabrina")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Silph Co.
        self.nav.enter_building(15, 10)
        # Navigate to 5F Card Key, then 11F Giovanni
        self.nav.navigate_to(10, 5)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=300)
        self.nav.exit_to_overworld()
        # Saffron Gym
        self.nav.enter_building(17, 5)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: saffron_sabrina — complete")
        self._mark_complete("saffron_sabrina")

    def step_fuchsia_koga(self):
        """
        Travel to Fuchsia City (Routes 12-15 or Cycling Road),
        do Safari Zone (get Surf + Strength), beat Koga.
        """
        log.info("STEP: fuchsia_koga")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Safari Zone (get HMs)
        self.nav.enter_building(10, 5)
        self.nav.navigate_to(20, 20)  # Secret House with Surf
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=60)
        self.nav.exit_to_overworld()
        # Give Gold Teeth to Warden → get Strength
        self.nav.enter_building(8, 15)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=40)
        self.nav.exit_to_overworld()
        # Fuchsia Gym
        self.nav.enter_building(15, 5)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: fuchsia_koga — complete")
        self._mark_complete("fuchsia_koga")

    def step_cinnabar_blaine(self):
        """
        Surf south to Cinnabar Island,
        explore Pokemon Mansion (get Secret Key), beat Blaine.
        """
        log.info("STEP: cinnabar_blaine")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Pokemon Mansion
        self.nav.enter_building(10, 8)
        # Navigate 4 floors for Secret Key
        self.nav.navigate_to(10, 10)
        self.nav.mash_through_dialog(max_presses=60)
        self.nav.exit_to_overworld()
        # Cinnabar Gym
        self.nav.enter_building(12, 8)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: cinnabar_blaine — complete")
        self._mark_complete("cinnabar_blaine")

    def step_viridian_giovanni(self):
        """
        Return to Viridian City (gym now unlocked),
        navigate the gym and beat Giovanni.
        """
        log.info("STEP: viridian_giovanni")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Viridian Gym
        self.nav.enter_building(15, 5)
        self.nav.navigate_to(10, 3)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_to_overworld()
        log.info("STEP: viridian_giovanni — complete")
        self._mark_complete("viridian_giovanni")

    def step_elite_four(self):
        """
        Route 22 → Route 23 → Victory Road → Indigo Plateau → Elite Four → Champion.
        """
        log.info("STEP: elite_four")
        go_to_pokecenter(self.nav, self.gs)
        self.nav.exit_to_overworld()
        # Victory Road
        self.nav.navigate_to(5, 5)    # Route 22 entrance
        self.nav.navigate_to(5, 0)    # Route 23 north
        self.nav.enter_building(5, 0) # Victory Road
        # Navigate 3 floors
        for _ in range(3):
            self.nav.navigate_to(15, 15)
        self.nav.exit_to_overworld()
        # Elite Four (4 consecutive battles + Champion)
        self.nav.enter_building(10, 5)
        for i in range(5):
            self.nav.navigate_to(5, 3)
            self.nav.press_a_interact()
            self.nav.mash_through_dialog(max_presses=500)
        log.info("STEP: elite_four — GAME COMPLETE!")
        self._mark_complete("elite_four")
        self._mark_complete("game_complete")

    # ------------------------------------------------------------------
    # Dispatcher & main loop
    # ------------------------------------------------------------------

    def run_next_step(self):
        """Execute the next progression step based on current game state."""
        step = self.get_current_step()
        log.info(f"run_next_step: executing '{step}'")

        dispatch = {
            "pallet_start":       self.step_pallet_town,
            "route1_to_viridian": self.step_route1_to_viridian,
            "viridian_parcel":    self.step_viridian_parcel,
            "viridian_forest":    self.step_viridian_forest,
            "pewter_brock":       self.step_pewter_brock,
            "mt_moon":            self.step_mt_moon,
            "cerulean_misty":     self.step_cerulean_misty,
            "nugget_bridge_bill": self.step_nugget_bridge_bill,
            "vermilion_ltsurge":  self.step_vermilion_ltsurge,
            "rock_tunnel":        self.step_rock_tunnel,
            "celadon_erika":      self.step_celadon_erika,
            "pokemon_tower":      self.step_pokemon_tower,
            "saffron_sabrina":    self.step_saffron_sabrina,
            "fuchsia_koga":       self.step_fuchsia_koga,
            "cinnabar_blaine":    self.step_cinnabar_blaine,
            "viridian_giovanni":  self.step_viridian_giovanni,
            "elite_four":         self.step_elite_four,
        }

        fn = dispatch.get(step)
        if fn:
            fn()
        elif step == "game_complete":
            log.info("run_next_step: game is complete!")
        else:
            log.warning(f"run_next_step: unknown step '{step}'")

    def run_full_game(self):
        """
        Main loop: keep executing steps until the game is complete or
        an unrecoverable error occurs.
        """
        log.info("run_full_game: starting full game run")
        while True:
            self.gs.update()

            if self.gs.in_battle:
                if self.battle_ai:
                    log.info("run_full_game: in battle — handing off to battle_ai")
                    self.battle_ai.handle_battle_turn()
                else:
                    log.warning("run_full_game: in battle but no battle_ai configured")
                    self.nav.mash_through_dialog(max_presses=10)
                continue

            if self.gs.needs_heal:
                log.info("run_full_game: party needs healing")
                go_to_pokecenter(self.nav, self.gs)
                continue

            step = self.get_current_step()
            if step == "game_complete":
                log.info("run_full_game: GAME COMPLETE! Exiting loop.")
                break

            self.run_next_step()
