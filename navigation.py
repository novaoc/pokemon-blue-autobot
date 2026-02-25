"""
navigation.py — Overworld navigation and game progression for Pokemon Blue autobot.

REWRITTEN with correct map IDs from pret/pokered disassembly and event-driven
navigation (press-until-condition instead of hardcoded tile coordinates).

Depends on emulator.py (PokemonEmulator) and memory.py (GameState).
"""

import json
import logging
import os
from enum import Enum
from typing import Callable, Optional, Tuple

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MAP CONSTANTS — from pret/pokered disassembly (verified)
# ---------------------------------------------------------------------------

# Towns / Cities
PALLET_TOWN = 0x00
VIRIDIAN_CITY = 0x01
PEWTER_CITY = 0x02
CERULEAN_CITY = 0x03
LAVENDER_TOWN = 0x04
VERMILION_CITY = 0x05
CELADON_CITY = 0x06
FUCHSIA_CITY = 0x07
CINNABAR_ISLAND = 0x08
SAFFRON_CITY = 0x09
INDIGO_PLATEAU = 0x0A

# Routes
ROUTE_1 = 0x0C
ROUTE_2 = 0x0D
ROUTE_3 = 0x0E
ROUTE_4 = 0x0F
ROUTE_5 = 0x10
ROUTE_6 = 0x11
ROUTE_7 = 0x12
ROUTE_8 = 0x13
ROUTE_9 = 0x14
ROUTE_10 = 0x15
ROUTE_11 = 0x16
ROUTE_12 = 0x17
ROUTE_13 = 0x18
ROUTE_14 = 0x19
ROUTE_15 = 0x1A
ROUTE_16 = 0x1B
ROUTE_17 = 0x1C  # Cycling Road
ROUTE_18 = 0x1D
ROUTE_22 = 0x1F
ROUTE_23 = 0x20
ROUTE_24 = 0x21
ROUTE_25 = 0x22

# Buildings
REDS_HOUSE_1F = 0x25
REDS_HOUSE_2F = 0x26  # Starting point
BLUES_HOUSE = 0x27
OAKS_LAB = 0x28

# Dungeons
VIRIDIAN_FOREST = 0x33
MT_MOON_1F = 0x3B
MT_MOON_B1F = 0x3C
MT_MOON_B2F = 0x3D
ROCK_TUNNEL_1F = 0x44
ROCK_TUNNEL_B1F = 0x45
POKEMON_TOWER_1F = 0x4E
POKEMON_TOWER_2F = 0x4F
POKEMON_TOWER_3F = 0x50
POKEMON_TOWER_4F = 0x51
POKEMON_TOWER_5F = 0x52
POKEMON_TOWER_6F = 0x53
POKEMON_TOWER_7F = 0x54
SS_ANNE = 0x5C
ROCKET_HIDEOUT_B1F = 0x67
ROCKET_HIDEOUT_B2F = 0x68
ROCKET_HIDEOUT_B3F = 0x69
ROCKET_HIDEOUT_B4F = 0x6A
SILPH_CO_1F = 0x6E
POKEMON_MANSION_1F = 0x8B
VICTORY_ROAD_1F = 0x9C

# Gyms
VIRIDIAN_GYM = 0xC2
PEWTER_GYM = 0xC3
CERULEAN_GYM = 0xC4
VERMILION_GYM = 0xC5
CELADON_GYM = 0xC6
FUCHSIA_GYM = 0xC7
SAFFRON_GYM = 0xC8
CINNABAR_GYM = 0xC9

# Pokemon Centers (interiors)
VIRIDIAN_POKECENTER = 0xB5
PEWTER_POKECENTER = 0xB6
CERULEAN_POKECENTER = 0xB7
LAVENDER_POKECENTER = 0xB8
VERMILION_POKECENTER = 0xB9
CELADON_POKECENTER = 0xBA
FUCHSIA_POKECENTER = 0xBB
SAFFRON_POKECENTER = 0xBC
CINNABAR_POKECENTER = 0xBD
INDIGO_POKECENTER = 0xBE

# ---------------------------------------------------------------------------
# MAP_IDS — map_id (int) → human-readable name (reverse lookup)
# ---------------------------------------------------------------------------
MAP_IDS = {
    # Towns / Cities
    PALLET_TOWN: "PALLET_TOWN",
    VIRIDIAN_CITY: "VIRIDIAN_CITY",
    PEWTER_CITY: "PEWTER_CITY",
    CERULEAN_CITY: "CERULEAN_CITY",
    LAVENDER_TOWN: "LAVENDER_TOWN",
    VERMILION_CITY: "VERMILION_CITY",
    CELADON_CITY: "CELADON_CITY",
    FUCHSIA_CITY: "FUCHSIA_CITY",
    CINNABAR_ISLAND: "CINNABAR_ISLAND",
    SAFFRON_CITY: "SAFFRON_CITY",
    INDIGO_PLATEAU: "INDIGO_PLATEAU",
    # Routes
    ROUTE_1: "ROUTE_1",
    ROUTE_2: "ROUTE_2",
    ROUTE_3: "ROUTE_3",
    ROUTE_4: "ROUTE_4",
    ROUTE_5: "ROUTE_5",
    ROUTE_6: "ROUTE_6",
    ROUTE_7: "ROUTE_7",
    ROUTE_8: "ROUTE_8",
    ROUTE_9: "ROUTE_9",
    ROUTE_10: "ROUTE_10",
    ROUTE_11: "ROUTE_11",
    ROUTE_12: "ROUTE_12",
    ROUTE_13: "ROUTE_13",
    ROUTE_14: "ROUTE_14",
    ROUTE_15: "ROUTE_15",
    ROUTE_16: "ROUTE_16",
    ROUTE_17: "ROUTE_17",
    ROUTE_18: "ROUTE_18",
    ROUTE_22: "ROUTE_22",
    ROUTE_23: "ROUTE_23",
    ROUTE_24: "ROUTE_24",
    ROUTE_25: "ROUTE_25",
    # Buildings
    REDS_HOUSE_1F: "REDS_HOUSE_1F",
    REDS_HOUSE_2F: "REDS_HOUSE_2F",
    BLUES_HOUSE: "BLUES_HOUSE",
    OAKS_LAB: "OAKS_LAB",
    # Dungeons
    VIRIDIAN_FOREST: "VIRIDIAN_FOREST",
    MT_MOON_1F: "MT_MOON_1F",
    MT_MOON_B1F: "MT_MOON_B1F",
    MT_MOON_B2F: "MT_MOON_B2F",
    ROCK_TUNNEL_1F: "ROCK_TUNNEL_1F",
    ROCK_TUNNEL_B1F: "ROCK_TUNNEL_B1F",
    POKEMON_TOWER_1F: "POKEMON_TOWER_1F",
    POKEMON_TOWER_2F: "POKEMON_TOWER_2F",
    POKEMON_TOWER_3F: "POKEMON_TOWER_3F",
    POKEMON_TOWER_4F: "POKEMON_TOWER_4F",
    POKEMON_TOWER_5F: "POKEMON_TOWER_5F",
    POKEMON_TOWER_6F: "POKEMON_TOWER_6F",
    POKEMON_TOWER_7F: "POKEMON_TOWER_7F",
    SS_ANNE: "SS_ANNE",
    ROCKET_HIDEOUT_B1F: "ROCKET_HIDEOUT_B1F",
    ROCKET_HIDEOUT_B2F: "ROCKET_HIDEOUT_B2F",
    ROCKET_HIDEOUT_B3F: "ROCKET_HIDEOUT_B3F",
    ROCKET_HIDEOUT_B4F: "ROCKET_HIDEOUT_B4F",
    SILPH_CO_1F: "SILPH_CO_1F",
    POKEMON_MANSION_1F: "POKEMON_MANSION_1F",
    VICTORY_ROAD_1F: "VICTORY_ROAD_1F",
    # Gyms
    VIRIDIAN_GYM: "VIRIDIAN_GYM",
    PEWTER_GYM: "PEWTER_GYM",
    CERULEAN_GYM: "CERULEAN_GYM",
    VERMILION_GYM: "VERMILION_GYM",
    CELADON_GYM: "CELADON_GYM",
    FUCHSIA_GYM: "FUCHSIA_GYM",
    SAFFRON_GYM: "SAFFRON_GYM",
    CINNABAR_GYM: "CINNABAR_GYM",
    # Pokemon Centers
    VIRIDIAN_POKECENTER: "VIRIDIAN_POKECENTER",
    PEWTER_POKECENTER: "PEWTER_POKECENTER",
    CERULEAN_POKECENTER: "CERULEAN_POKECENTER",
    LAVENDER_POKECENTER: "LAVENDER_POKECENTER",
    VERMILION_POKECENTER: "VERMILION_POKECENTER",
    CELADON_POKECENTER: "CELADON_POKECENTER",
    FUCHSIA_POKECENTER: "FUCHSIA_POKECENTER",
    SAFFRON_POKECENTER: "SAFFRON_POKECENTER",
    CINNABAR_POKECENTER: "CINNABAR_POKECENTER",
    INDIGO_POKECENTER: "INDIGO_POKECENTER",
}

# ---------------------------------------------------------------------------
# City → Pokecenter interior map ID mapping
# Used to know which pokecenter to enter from which city
# ---------------------------------------------------------------------------
CITY_TO_POKECENTER = {
    VIRIDIAN_CITY: VIRIDIAN_POKECENTER,
    PEWTER_CITY: PEWTER_POKECENTER,
    CERULEAN_CITY: CERULEAN_POKECENTER,
    LAVENDER_TOWN: LAVENDER_POKECENTER,
    VERMILION_CITY: VERMILION_POKECENTER,
    CELADON_CITY: CELADON_POKECENTER,
    FUCHSIA_CITY: FUCHSIA_POKECENTER,
    SAFFRON_CITY: SAFFRON_POKECENTER,
    CINNABAR_ISLAND: CINNABAR_POKECENTER,
    INDIGO_PLATEAU: INDIGO_POKECENTER,
}

# Routes that are adjacent to cities (for pokecenter routing)
ROUTE_TO_NEAREST_CITY = {
    ROUTE_1: VIRIDIAN_CITY,
    ROUTE_2: VIRIDIAN_CITY,
    ROUTE_3: PEWTER_CITY,
    ROUTE_4: CERULEAN_CITY,
    ROUTE_5: CERULEAN_CITY,
    ROUTE_6: VERMILION_CITY,
    ROUTE_7: CELADON_CITY,
    ROUTE_8: LAVENDER_TOWN,
    ROUTE_9: CERULEAN_CITY,
    ROUTE_10: LAVENDER_TOWN,
    ROUTE_11: VERMILION_CITY,
    ROUTE_12: LAVENDER_TOWN,
    ROUTE_13: FUCHSIA_CITY,
    ROUTE_14: FUCHSIA_CITY,
    ROUTE_15: FUCHSIA_CITY,
    ROUTE_16: CELADON_CITY,
    ROUTE_17: FUCHSIA_CITY,
    ROUTE_18: FUCHSIA_CITY,
    ROUTE_22: VIRIDIAN_CITY,
    ROUTE_23: VIRIDIAN_CITY,
    ROUTE_24: CERULEAN_CITY,
    ROUTE_25: CERULEAN_CITY,
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
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[self]

    @property
    def perpendiculars(self) -> Tuple["Direction", "Direction"]:
        if self in (Direction.UP, Direction.DOWN):
            return Direction.LEFT, Direction.RIGHT
        return Direction.UP, Direction.DOWN


# ---------------------------------------------------------------------------
# Navigator — event-driven movement
# ---------------------------------------------------------------------------
class Navigator:
    """
    Event-driven navigation. Instead of navigating to exact tile coordinates,
    we press directions until observable conditions change (map transitions,
    dialog opening, position reaching target, etc.).

    Expects:
        emulator   – PokemonEmulator with .button(), .button_release(), .tick()
        game_state – GameState with .player_x, .player_y, .map_id, .in_battle, .dialog_open
    """

    FRAMES_PER_STEP = 16
    FRAMES_DIALOG = 30
    FRAMES_INTERACT = 10
    MAX_STUCK_TRIES = 5
    ESCAPE_STEPS = 3

    def __init__(self, emulator, game_state):
        self.emu = emulator
        self.gs = game_state

    # ------------------------------------------------------------------
    # Low-level primitives
    # ------------------------------------------------------------------

    def _press(self, button: str, frames: int = 1):
        """Press and release a button, then tick."""
        self.emu.button(button)
        self.emu.tick(frames)
        self.emu.button_release(button)

    def _tick(self, frames: int):
        self.emu.tick(frames)

    # ------------------------------------------------------------------
    # Core movement
    # ------------------------------------------------------------------

    def move_one_step(self, direction: Direction) -> bool:
        """
        Press direction for 16 frames. Returns True if position changed.
        Refreshes game state after moving.
        """
        btn = direction.value
        x0, y0 = self.gs.player_x, self.gs.player_y

        self.emu.button(btn)
        self.emu.tick(self.FRAMES_PER_STEP)
        self.emu.button_release(btn)
        self.gs.update()

        moved = (self.gs.player_x != x0) or (self.gs.player_y != y0)
        if moved:
            log.debug(f"move({direction.name}): ({x0},{y0})→({self.gs.player_x},{self.gs.player_y})")
        else:
            log.debug(f"move({direction.name}): BLOCKED at ({x0},{y0})")
        return moved

    # ------------------------------------------------------------------
    # Event-driven movement primitives
    # ------------------------------------------------------------------

    def press_until(self, direction: Direction, condition_fn: Callable[[], bool],
                    max_steps: int = 100) -> bool:
        """Press direction until condition_fn() returns True or max_steps reached."""
        for i in range(max_steps):
            self.gs.update()
            if condition_fn():
                log.debug(f"press_until({direction.name}): condition met after {i} steps")
                return True
            if self.gs.in_battle:
                log.info("press_until: battle started — pausing navigation")
                return False
            self.move_one_step(direction)
        log.warning(f"press_until({direction.name}): max_steps ({max_steps}) reached")
        return False

    def press_until_map_change(self, direction: Direction, max_steps: int = 50) -> bool:
        """Press direction until the map ID changes."""
        start_map = self.gs.map_id
        return self.press_until(direction, lambda: self.gs.map_id != start_map, max_steps)

    def press_until_map_is(self, direction: Direction, target_map: int,
                           max_steps: int = 80) -> bool:
        """Press direction until we reach a specific map."""
        return self.press_until(direction, lambda: self.gs.map_id == target_map, max_steps)

    def press_until_dialog(self, direction: Direction, max_steps: int = 50) -> bool:
        """Press direction until dialog opens."""
        return self.press_until(direction, lambda: self.gs.dialog_open, max_steps)

    def press_until_y(self, direction: Direction, target_y: int, max_steps: int = 100) -> bool:
        """Press direction until player Y == target_y."""
        return self.press_until(direction, lambda: self.gs.player_y == target_y, max_steps)

    def press_until_x(self, direction: Direction, target_x: int, max_steps: int = 100) -> bool:
        """Press direction until player X == target_x."""
        return self.press_until(direction, lambda: self.gs.player_x == target_x, max_steps)

    # ------------------------------------------------------------------
    # Dialog helpers
    # ------------------------------------------------------------------

    def press_a_interact(self):
        """Press A to interact."""
        self.emu.button("a")
        self.emu.tick(self.FRAMES_INTERACT)
        self.emu.button_release("a")
        self.gs.update()

    def mash_through_dialog(self, max_presses: int = 50) -> int:
        """Press A repeatedly until dialog clears. Returns press count."""
        presses = 0
        for _ in range(max_presses):
            self.gs.update()
            if not self.gs.dialog_open:
                break
            self.emu.button("a")
            self.emu.tick(self.FRAMES_DIALOG)
            self.emu.button_release("a")
            presses += 1
        log.debug(f"mash_through_dialog: {presses} presses")
        return presses

    def mash_a(self, count: int = 10, frames_between: int = 30):
        """Blindly press A a fixed number of times (for menus, cutscenes)."""
        for _ in range(count):
            self.emu.button("a")
            self.emu.tick(frames_between)
            self.emu.button_release("a")
        self.gs.update()

    def press_b(self, count: int = 3, frames_between: int = 20):
        """Press B to cancel/back out of menus."""
        for _ in range(count):
            self.emu.button("b")
            self.emu.tick(frames_between)
            self.emu.button_release("b")
        self.gs.update()

    # ------------------------------------------------------------------
    # Greedy navigate_to (for when you DO know target coords)
    # ------------------------------------------------------------------

    def navigate_to(self, target_x: int, target_y: int, max_steps: int = 2000) -> bool:
        """
        Greedy pathfinding toward (target_x, target_y) on the CURRENT map.
        Uses stuck detection with perpendicular escape.
        """
        log.info(f"navigate_to({target_x}, {target_y})")
        stuck_count = 0
        last_pos = (self.gs.player_x, self.gs.player_y)

        for step in range(max_steps):
            self.gs.update()
            if self.gs.in_battle:
                log.warning("navigate_to: battle started — pausing")
                return False

            cx, cy = self.gs.player_x, self.gs.player_y
            if cx == target_x and cy == target_y:
                log.info(f"navigate_to: reached target in {step} steps")
                return True

            dx, dy = target_x - cx, target_y - cy

            # Pick primary/secondary direction
            if abs(dx) >= abs(dy):
                primary = Direction.RIGHT if dx > 0 else Direction.LEFT
                secondary = Direction.DOWN if dy > 0 else Direction.UP if dy != 0 else primary
            else:
                primary = Direction.DOWN if dy > 0 else Direction.UP
                secondary = Direction.RIGHT if dx > 0 else Direction.LEFT if dx != 0 else primary

            moved = self.move_one_step(primary)
            if not moved:
                moved = self.move_one_step(secondary)

            new_pos = (self.gs.player_x, self.gs.player_y)
            if new_pos == last_pos:
                stuck_count += 1
                if stuck_count >= self.MAX_STUCK_TRIES:
                    log.warning(f"navigate_to: stuck at {new_pos}, escaping")
                    if not self._escape_stuck(primary):
                        return False
                    stuck_count = 0
            else:
                stuck_count = 0
                last_pos = new_pos

        log.warning("navigate_to: max_steps exceeded")
        return False

    def _escape_stuck(self, blocked_direction: Direction) -> bool:
        """Try perpendicular moves to escape a stuck position."""
        for perp in blocked_direction.perpendiculars:
            for _ in range(self.ESCAPE_STEPS):
                if self.move_one_step(perp):
                    return True
        return False

    # ------------------------------------------------------------------
    # Building exit logic
    # ------------------------------------------------------------------

    def exit_players_house_2f(self) -> bool:
        """Exit from Red's House 2F → 1F → Pallet Town."""
        log.info("exit_players_house_2f")
        if self.gs.map_id == REDS_HOUSE_2F:
            # Staircase warp is at (7,1) — top-right of the room.
            # Player starts at the bottom (Y≈7). Walk UP to Y=1, then RIGHT
            # to step onto the warp tile.
            self.press_until_y(Direction.UP, target_y=1, max_steps=15)
            if not self.press_until_map_change(Direction.RIGHT, max_steps=10):
                # Fallback: shift down one row and try RIGHT again
                self.move_one_step(Direction.DOWN)
                self.press_until_map_change(Direction.RIGHT, max_steps=10)
        if self.gs.map_id == REDS_HOUSE_1F:
            # Walk out the front door (exit is at the bottom center)
            if not self.press_until_map_change(Direction.DOWN, max_steps=20):
                # Door might not be directly below — use sweep
                self._sweep_for_exit()
        return self.gs.map_id == PALLET_TOWN

    def _sweep_for_exit(self) -> bool:
        """Sweep LEFT then RIGHT along the bottom wall, trying DOWN at each position."""
        start_map = self.gs.map_id
        for direction in (Direction.LEFT, Direction.RIGHT):
            for _ in range(10):
                self.move_one_step(direction)
                self.gs.update()
                if self.gs.map_id != start_map:
                    return True
                # Try stepping DOWN into the exit from this X position
                self.move_one_step(Direction.DOWN)
                self._tick(8)  # extra frames for warp to register
                self.gs.update()
                if self.gs.map_id != start_map:
                    return True
        return False

    def exit_building(self) -> bool:
        """Generic building exit: walk DOWN to bottom wall, then sweep for exit door."""
        log.info("exit_building from map 0x%02X", self.gs.map_id)
        start_map = self.gs.map_id

        # Phase 1: Walk DOWN to reach the bottom wall
        for _ in range(15):
            old_y = self.gs.player_y
            self.move_one_step(Direction.DOWN)
            self.gs.update()
            if self.gs.map_id != start_map:
                return True  # Exited during descent
            if self.gs.player_y == old_y:
                break  # Hit the bottom wall

        # Phase 2: Sweep LEFT and RIGHT along the bottom, trying DOWN at each X
        if self._sweep_for_exit():
            return True

        log.warning("exit_building: failed to exit from map 0x%02X", start_map)
        return False

    def enter_pokecenter_and_heal(self) -> bool:
        """
        Assuming we're standing near a Pokecenter door on the overworld:
        walk UP to enter, then UP to the counter, interact, mash dialog.

        Pokecenter interiors all have the same layout:
        - Door is at bottom center
        - Nurse Joy counter is near the top center
        - Walk UP until dialog triggers = you're at the counter
        """
        # BUG-05 guard: only attempt entry when on a city map that has a pokecenter.
        # Calling this from interiors (e.g. 0x26 REDS_HOUSE_2F) would walk into the
        # wrong building or spin forever.
        current_map = self.gs.map_id
        if current_map not in CITY_TO_POKECENTER:
            log.warning(
                "enter_pokecenter_and_heal: wrong map 0x%02X (%s) — "
                "must be on a city map with a pokecenter; skipping",
                current_map, MAP_IDS.get(current_map, "?"),
            )
            return False

        start_map = self.gs.map_id
        # Enter the building (walk UP into door)
        self.press_until_map_change(Direction.UP, max_steps=10)
        if self.gs.map_id == start_map:
            log.warning("enter_pokecenter: failed to enter building")
            return False

        log.info(f"enter_pokecenter: inside map 0x{self.gs.map_id:02X}")

        # Walk UP to the counter until dialog opens
        self.press_until_dialog(Direction.UP, max_steps=10)
        # Interact and mash through healing dialog
        self.press_a_interact()
        self.mash_a(count=20, frames_between=30)
        self.mash_through_dialog(max_presses=30)

        log.info("enter_pokecenter: healing complete")
        return True


# ---------------------------------------------------------------------------
# go_to_pokecenter — find nearest pokecenter and heal
# ---------------------------------------------------------------------------

def go_to_pokecenter(navigator: Navigator, game_state) -> bool:
    """
    Determine the nearest Pokecenter for the current map and heal.
    
    Strategy: We don't hardcode exact door coordinates. Instead:
    - If already inside a pokecenter, walk up to counter
    - If in a city, we need to find the pokecenter (game-specific routing)
    - If on a route, we may need to backtrack to a city
    
    For now, this handles the "already near pokecenter" case.
    Complex routing between cities is handled by ProgressionManager steps.
    """
    current_map = game_state.map_id
    log.info(f"go_to_pokecenter: map 0x{current_map:02X} ({MAP_IDS.get(current_map, '?')})")

    # Already inside a pokecenter?
    pokecenter_maps = {
        VIRIDIAN_POKECENTER, PEWTER_POKECENTER, CERULEAN_POKECENTER,
        LAVENDER_POKECENTER, VERMILION_POKECENTER, CELADON_POKECENTER,
        FUCHSIA_POKECENTER, SAFFRON_POKECENTER, CINNABAR_POKECENTER,
        INDIGO_POKECENTER,
    }
    if current_map in pokecenter_maps:
        # Already inside — just walk to counter and heal
        navigator.press_until_dialog(Direction.UP, max_steps=10)
        navigator.press_a_interact()
        navigator.mash_a(count=20, frames_between=30)
        navigator.mash_through_dialog(max_presses=30)
        return True

    # In a city — find the pokecenter
    if current_map in CITY_TO_POKECENTER:
        # We don't know exact door coords, but pokecenters are always entered
        # by walking UP into the door. The ProgressionManager will handle
        # routing to the pokecenter area. For a generic approach, this is
        # a placeholder — real implementation needs per-city pathfinding or
        # a vision-based approach.
        log.warning(f"go_to_pokecenter: in city 0x{current_map:02X} but no pathfinding to pokecenter door yet")
        return False

    # On a route — figure out nearest city
    nearest = ROUTE_TO_NEAREST_CITY.get(current_map)
    if nearest:
        log.info(f"go_to_pokecenter: nearest city for route 0x{current_map:02X} is 0x{nearest:02X}")
        # Would need to navigate back to city first
        log.warning("go_to_pokecenter: route→city navigation not yet implemented")
        return False

    log.warning(f"go_to_pokecenter: don't know how to heal from map 0x{current_map:02X}")
    return False


# ---------------------------------------------------------------------------
# Badge constants
# ---------------------------------------------------------------------------
BADGE_BOULDER = 0   # Brock     — Pewter City
BADGE_CASCADE = 1   # Misty     — Cerulean City
BADGE_THUNDER = 2   # Lt. Surge — Vermilion City
BADGE_RAINBOW = 3   # Erika     — Celadon City
BADGE_SOUL = 4      # Koga      — Fuchsia City
BADGE_MARSH = 5     # Sabrina   — Saffron City
BADGE_VOLCANO = 6   # Blaine    — Cinnabar Island
BADGE_EARTH = 7     # Giovanni  — Viridian City


def _has_badge(badges_byte: int, badge_bit: int) -> bool:
    return bool(badges_byte & (1 << badge_bit))


# ---------------------------------------------------------------------------
# ProgressionManager — event-driven game progression
# ---------------------------------------------------------------------------

STATE_FILE = os.path.join(os.path.dirname(__file__), "progression_state.json")


class ProgressionManager:
    """
    High-level game progression using event-driven navigation.
    
    Each step uses press_until_* methods instead of hardcoded coordinates:
    - press_until_map_change: walk a direction until the map transitions
    - press_until_dialog: walk until an NPC/sign dialog opens
    - mash_through_dialog: clear dialog boxes
    - mash_a: blindly press A through cutscenes/menus
    """

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

    # Stall detector thresholds
    _STALL_WINDOW = 3       # consecutive (step, map_id) repeats that trigger a stall event
    _STALL_MAX_RETRIES = 5  # stall events before the step is forcibly skipped

    def __init__(self, emulator, game_state, navigator: Navigator, battle_ai=None):
        self.emu = emulator
        self.gs = game_state
        self.nav = navigator
        self.battle_ai = battle_ai
        self.state = self.load_state()

        # BUG-03: stall detection state
        # _stall_history: ring buffer of (step, map_id, x, y) snapshots taken at
        #   the top of each run_next_step() call.
        # _stall_retries: per-step count of stall events (cleared on success/skip).
        self._stall_history: list[tuple] = []
        self._stall_retries: dict[str, int] = {}

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def load_state(self) -> dict:
        defaults = {"step": "pallet_start", "badges": 0, "completed_steps": []}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                # Ensure all required keys exist (older state files may lack them)
                for k, v in defaults.items():
                    state.setdefault(k, v)
                log.info(f"load_state: loaded — step={state.get('step')}")
                return state
            except (json.JSONDecodeError, IOError) as e:
                log.warning(f"load_state: {e}; using defaults")
        return defaults

    def save_state(self, state: Optional[dict] = None):
        if state is None:
            state = self.state
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except IOError as e:
            log.error(f"save_state: {e}")

    def _mark_complete(self, step_name: str):
        if step_name not in self.state["completed_steps"]:
            self.state["completed_steps"].append(step_name)
        idx = self.STEP_ORDER.index(step_name) if step_name in self.STEP_ORDER else -1
        if 0 <= idx < len(self.STEP_ORDER) - 1:
            self.state["step"] = self.STEP_ORDER[idx + 1]
        self.state["badges"] = self.gs.badges
        self.save_state()

    # ------------------------------------------------------------------
    # Step detection from badges
    # ------------------------------------------------------------------

    def get_current_step(self) -> str:
        try:
            badges = self.gs.badges
        except Exception:
            return self.state.get("step", "pallet_start")

        badge_count = bin(badges).count("1")
        saved = self.state.get("step", "pallet_start")

        # Map badge count ranges to possible steps
        step_ranges = {
            0: ["pallet_start", "route1_to_viridian", "viridian_parcel",
                "viridian_forest", "pewter_brock"],
            1: ["mt_moon", "cerulean_misty"],
            2: ["nugget_bridge_bill", "vermilion_ltsurge"],
            3: ["rock_tunnel", "celadon_erika"],
            4: ["pokemon_tower", "saffron_sabrina", "celadon_erika"],
            5: ["fuchsia_koga", "saffron_sabrina"],
            6: ["cinnabar_blaine", "fuchsia_koga"],
            7: ["viridian_giovanni"],
            8: ["elite_four"],
        }

        valid_steps = step_ranges.get(badge_count, [])
        if saved in valid_steps:
            return saved
        return valid_steps[0] if valid_steps else "game_complete"

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
    # Individual progression steps — EVENT DRIVEN
    # ------------------------------------------------------------------

    def step_pallet_town(self):
        """
        Start of game: exit Red's House, get intercepted by Oak,
        choose starter Pokemon (Squirtle), fight rival.
        
        Event sequence:
        1. Press DOWN until map changes from REDS_HOUSE_2F → REDS_HOUSE_1F
        2. Press DOWN until map changes from REDS_HOUSE_1F → PALLET_TOWN
        3. Walk north — Oak will intercept you automatically
        4. Mash through Oak dialog, follow him to lab
        5. In Oak's Lab: walk to Squirtle ball (rightmost), interact
        6. Mash through selection dialog
        7. Rival battle triggers automatically — battle_ai handles
        """
        log.info("STEP: pallet_start")

        # Exit Red's House
        self.nav.exit_players_house_2f()

        # Walk north toward Route 1 — Oak will intercept
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.mash_through_dialog(max_presses=80)
        self.nav.mash_a(count=30, frames_between=30)

        # Oak takes us to his lab — wait for map transition to OAKS_LAB
        self.nav.press_until(Direction.DOWN,
                             lambda: self.gs.map_id == OAKS_LAB, max_steps=100)
        # If not in lab yet, mash A (cutscene auto-walks us)
        if self.gs.map_id != OAKS_LAB:
            self.nav.mash_a(count=50, frames_between=20)

        # Walk to the rightmost pokeball (Squirtle) and interact
        # Pokeballs are on the table at the top of the lab
        # Walk RIGHT then UP to the rightmost ball
        self.nav.press_until_x(Direction.RIGHT, target_x=9, max_steps=15)
        self.nav.press_until_dialog(Direction.UP, max_steps=10)
        self.nav.press_a_interact()
        # Confirm selection: mash A through "Do you want Squirtle?" etc.
        self.nav.mash_a(count=30, frames_between=30)
        self.nav.mash_through_dialog(max_presses=80)

        # Rival battle happens — will be handled by battle_ai in main loop
        # Mash through post-battle dialog
        self.nav.mash_a(count=50, frames_between=20)
        self.nav.mash_through_dialog(max_presses=50)

        log.info("STEP: pallet_start — complete")
        self._mark_complete("pallet_start")

    def step_route1_to_viridian(self):
        """Walk north through Route 1 to Viridian City."""
        log.info("STEP: route1_to_viridian")

        # Exit Oak's Lab if still inside
        if self.gs.map_id == OAKS_LAB:
            self.nav.exit_building()

        # Walk north until we reach Viridian City
        self.nav.press_until_map_is(Direction.UP, VIRIDIAN_CITY, max_steps=200)

        log.info("STEP: route1_to_viridian — complete")
        self._mark_complete("route1_to_viridian")

    def step_viridian_parcel(self):
        """
        Pick up Oak's Parcel from Viridian Mart, deliver to Oak,
        get Pokedex, return north.
        """
        log.info("STEP: viridian_parcel")

        # Walk north in Viridian to find the Mart (entering triggers parcel event)
        # Mart is on the east side — walk right then up to find the door
        self.nav.press_until_map_change(Direction.UP, max_steps=40)

        # If we entered a building, check if it's the mart
        # Mash through the "parcel for Prof Oak" dialog
        self.nav.mash_a(count=20, frames_between=30)
        self.nav.mash_through_dialog(max_presses=40)
        self.nav.exit_building()

        # Walk south back to Pallet Town
        self.nav.press_until_map_is(Direction.DOWN, PALLET_TOWN, max_steps=200)

        # Enter Oak's Lab
        self.nav.press_until_map_is(Direction.DOWN, OAKS_LAB, max_steps=40)
        if self.gs.map_id != OAKS_LAB:
            # Try entering from pallet — lab is south
            self.nav.press_until_map_change(Direction.UP, max_steps=20)

        # Talk to Oak — walk toward him
        self.nav.press_until_dialog(Direction.UP, max_steps=15)
        self.nav.press_a_interact()
        self.nav.mash_a(count=40, frames_between=30)
        self.nav.mash_through_dialog(max_presses=80)

        # Exit lab and head back north
        self.nav.exit_building()
        self.nav.press_until_map_is(Direction.UP, VIRIDIAN_CITY, max_steps=200)

        log.info("STEP: viridian_parcel — complete")
        self._mark_complete("viridian_parcel")

    def step_viridian_forest(self):
        """Navigate north through Route 2, Viridian Forest, to Pewter City."""
        log.info("STEP: viridian_forest")

        # Walk north from Viridian through Route 2 into Viridian Forest
        # Keep going UP until we reach Viridian Forest map
        self.nav.press_until_map_is(Direction.UP, ROUTE_2, max_steps=60)
        self.nav.press_until_map_change(Direction.UP, max_steps=40)

        # In the forest gate or forest itself — keep going north
        # Forest requires some navigation — mostly UP with detours
        steps = 0
        while self.gs.map_id != PEWTER_CITY and steps < 500:
            self.gs.update()
            if self.gs.in_battle:
                steps += 1
                continue  # battle_ai handles
            # Try UP primarily, with LEFT/RIGHT to navigate around trees
            moved = self.nav.move_one_step(Direction.UP)
            if not moved:
                # Try going around obstacles
                for lateral in (Direction.LEFT, Direction.RIGHT):
                    if self.nav.move_one_step(lateral):
                        break
            steps += 1
            # Check for map transitions (forest → gate → pewter)
            if self.gs.map_id not in (VIRIDIAN_FOREST, ROUTE_2, VIRIDIAN_CITY):
                # Might be in a gate building — walk through
                self.nav.press_until_map_change(Direction.UP, max_steps=20)

        log.info("STEP: viridian_forest — complete")
        self._mark_complete("viridian_forest")

    def step_pewter_brock(self):
        """Heal at Pewter Pokecenter, then challenge Brock's gym."""
        log.info("STEP: pewter_brock")

        # Heal first — enter pokecenter
        # Walk around Pewter looking for pokecenter door (UP enters buildings)
        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Find and enter Pewter Gym
        # Gym is in the city — walk until we enter it
        self.nav.press_until_map_is(Direction.DOWN, PEWTER_GYM, max_steps=60)
        if self.gs.map_id != PEWTER_GYM:
            # Try different approach directions
            self.nav.press_until_map_change(Direction.UP, max_steps=30)

        # Walk north to Brock
        self.nav.press_until_dialog(Direction.UP, max_steps=20)
        self.nav.press_a_interact()
        self.nav.mash_a(count=10, frames_between=30)
        # Battle triggers — handled by battle_ai in main loop
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: pewter_brock — complete")
        self._mark_complete("pewter_brock")

    def step_mt_moon(self):
        """Route 3 east to Mt. Moon, navigate through to Route 4 / Cerulean."""
        log.info("STEP: mt_moon")

        # Head east from Pewter through Route 3
        self.nav.press_until_map_is(Direction.RIGHT, ROUTE_3, max_steps=60)
        # Continue east through Route 3
        self.nav.press_until_map_change(Direction.RIGHT, max_steps=200)

        # Navigate Mt. Moon (3 floors) — go DOWN/RIGHT through cave
        floors_traversed = 0
        steps = 0
        while floors_traversed < 3 and steps < 800:
            self.gs.update()
            if self.gs.in_battle:
                steps += 1
                continue
            start_map = self.gs.map_id
            # Try going down and right through the cave
            moved = self.nav.move_one_step(Direction.DOWN)
            if not moved:
                moved = self.nav.move_one_step(Direction.RIGHT)
            if not moved:
                moved = self.nav.move_one_step(Direction.LEFT)
            if not moved:
                self.nav.move_one_step(Direction.UP)
            self.gs.update()
            if self.gs.map_id != start_map:
                floors_traversed += 1
                log.info(f"mt_moon: transitioned to map 0x{self.gs.map_id:02X} (floor {floors_traversed})")
            steps += 1

        log.info("STEP: mt_moon — complete")
        self._mark_complete("mt_moon")

    def step_cerulean_misty(self):
        """Heal, then challenge Misty in Cerulean Gym."""
        log.info("STEP: cerulean_misty")

        # Should be near Cerulean after Mt. Moon
        if self.gs.map_id != CERULEAN_CITY:
            self.nav.press_until_map_is(Direction.RIGHT, CERULEAN_CITY, max_steps=100)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Enter Cerulean Gym
        self.nav.press_until_map_is(Direction.UP, CERULEAN_GYM, max_steps=80)
        if self.gs.map_id != CERULEAN_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=30)

        self.nav.press_until_dialog(Direction.UP, max_steps=20)
        self.nav.press_a_interact()
        self.nav.mash_a(count=10, frames_between=30)
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: cerulean_misty — complete")
        self._mark_complete("cerulean_misty")

    def step_nugget_bridge_bill(self):
        """Cross Nugget Bridge (Route 24/25), visit Bill, get SS Ticket."""
        log.info("STEP: nugget_bridge_bill")

        # Head north from Cerulean across Route 24 (Nugget Bridge)
        self.nav.press_until_map_is(Direction.UP, ROUTE_24, max_steps=40)
        # Walk north through the bridge (6 trainer fights)
        self.nav.press_until_map_is(Direction.UP, ROUTE_25, max_steps=200)
        # Walk right to Bill's cottage
        self.nav.press_until_map_change(Direction.RIGHT, max_steps=100)
        # Talk to Bill
        self.nav.press_until_dialog(Direction.UP, max_steps=20)
        self.nav.press_a_interact()
        self.nav.mash_a(count=50, frames_between=30)
        self.nav.mash_through_dialog(max_presses=100)
        self.nav.exit_building()

        # Return to Cerulean
        self.nav.press_until_map_is(Direction.DOWN, CERULEAN_CITY, max_steps=300)

        log.info("STEP: nugget_bridge_bill — complete")
        self._mark_complete("nugget_bridge_bill")

    def step_vermilion_ltsurge(self):
        """
        Go south to Vermilion, board SS Anne (get HM01 Cut),
        then beat Lt. Surge.
        """
        log.info("STEP: vermilion_ltsurge")

        # South from Cerulean through Route 5 to Vermilion
        self.nav.press_until_map_is(Direction.DOWN, VERMILION_CITY, max_steps=300)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # SS Anne — dock is south of Vermilion
        # Enter the port building, show SS Ticket
        self.nav.press_until_map_change(Direction.DOWN, max_steps=40)
        self.nav.mash_a(count=20, frames_between=30)
        self.nav.mash_through_dialog(max_presses=40)
        # Navigate SS Anne to captain, get HM01 Cut
        self.nav.press_until_dialog(Direction.UP, max_steps=50)
        self.nav.press_a_interact()
        self.nav.mash_a(count=30, frames_between=30)
        self.nav.mash_through_dialog(max_presses=60)
        self.nav.exit_building()

        # Vermilion Gym (need Cut to enter)
        self.nav.press_until_map_is(Direction.UP, VERMILION_GYM, max_steps=80)
        if self.gs.map_id != VERMILION_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=30)
        # Trash can puzzle + Lt. Surge
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_a(count=10, frames_between=30)
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: vermilion_ltsurge — complete")
        self._mark_complete("vermilion_ltsurge")

    def step_rock_tunnel(self):
        """Route 9 east, heal at Route 10 center, through Rock Tunnel to Lavender."""
        log.info("STEP: rock_tunnel")

        # East from Cerulean through Route 9
        self.nav.press_until_map_is(Direction.RIGHT, ROUTE_9, max_steps=60)
        self.nav.press_until_map_is(Direction.RIGHT, ROUTE_10, max_steps=200)

        # Heal at Route 10 pokecenter
        self.nav.press_until_map_change(Direction.UP, max_steps=20)
        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Enter Rock Tunnel
        self.nav.press_until_map_change(Direction.DOWN, max_steps=40)

        # Navigate through Rock Tunnel (2 floors, dark)
        steps = 0
        while self.gs.map_id in (ROCK_TUNNEL_1F, ROCK_TUNNEL_B1F) and steps < 600:
            self.gs.update()
            if self.gs.in_battle:
                steps += 1
                continue
            moved = self.nav.move_one_step(Direction.DOWN)
            if not moved:
                moved = self.nav.move_one_step(Direction.RIGHT)
            if not moved:
                self.nav.move_one_step(Direction.LEFT)
            steps += 1

        log.info("STEP: rock_tunnel — complete")
        self._mark_complete("rock_tunnel")

    def step_celadon_erika(self):
        """Rocket Hideout under Game Corner, then Erika's gym."""
        log.info("STEP: celadon_erika")

        # Navigate to Celadon City
        if self.gs.map_id != CELADON_CITY:
            self.nav.press_until_map_is(Direction.LEFT, CELADON_CITY, max_steps=300)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Game Corner → Rocket Hideout (4 basement floors)
        self.nav.press_until_map_change(Direction.UP, max_steps=40)
        # Navigate through hideout
        self.nav.mash_a(count=30, frames_between=20)
        for _ in range(4):  # 4 floors
            self.nav.press_until_map_change(Direction.DOWN, max_steps=100)
        # Giovanni battle at B4F
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        # Get Silph Scope
        self.nav.mash_a(count=20, frames_between=30)
        self.nav.exit_building()

        # Celadon Gym
        self.nav.press_until_map_is(Direction.LEFT, CELADON_GYM, max_steps=60)
        if self.gs.map_id != CELADON_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=30)
        self.nav.press_until_dialog(Direction.UP, max_steps=20)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: celadon_erika — complete")
        self._mark_complete("celadon_erika")

    def step_pokemon_tower(self):
        """Climb Pokemon Tower in Lavender, rescue Mr. Fuji, get Poke Flute."""
        log.info("STEP: pokemon_tower")

        # Navigate to Lavender Town
        if self.gs.map_id != LAVENDER_TOWN:
            self.nav.press_until_map_is(Direction.RIGHT, LAVENDER_TOWN, max_steps=300)

        # Enter Pokemon Tower
        self.nav.press_until_map_change(Direction.UP, max_steps=40)

        # Climb 7 floors — each floor: walk to stairs, transition
        for floor in range(6):  # 6 transitions (1F→7F)
            self.gs.update()
            if self.gs.in_battle:
                continue
            self.nav.press_until_map_change(Direction.UP, max_steps=80)
            log.info(f"pokemon_tower: floor {floor + 2}, map 0x{self.gs.map_id:02X}")

        # Top floor — rescue Mr. Fuji
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_a(count=40, frames_between=30)
        self.nav.mash_through_dialog(max_presses=100)

        # Mr. Fuji teleports us to his house — mash through, get Poke Flute
        self.nav.mash_a(count=30, frames_between=30)
        self.nav.exit_building()

        log.info("STEP: pokemon_tower — complete")
        self._mark_complete("pokemon_tower")

    def step_saffron_sabrina(self):
        """Clear Silph Co., then beat Sabrina in Saffron Gym."""
        log.info("STEP: saffron_sabrina")

        # Navigate to Saffron City
        if self.gs.map_id != SAFFRON_CITY:
            self.nav.press_until_map_is(Direction.LEFT, SAFFRON_CITY, max_steps=300)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Silph Co. — tall building, navigate through floors
        self.nav.press_until_map_change(Direction.UP, max_steps=40)
        # Navigate through Silph Co. (11 floors with teleport pads)
        # This is complex — for now, keep pressing through
        for _ in range(10):
            self.nav.press_until_map_change(Direction.UP, max_steps=60)
            self.nav.mash_a(count=10, frames_between=20)
        # Giovanni on 11F
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=300)
        self.nav.exit_building()

        # Saffron Gym (teleport pad puzzle)
        self.nav.press_until_map_is(Direction.DOWN, SAFFRON_GYM, max_steps=60)
        if self.gs.map_id != SAFFRON_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=30)
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: saffron_sabrina — complete")
        self._mark_complete("saffron_sabrina")

    def step_fuchsia_koga(self):
        """Safari Zone (Surf + Strength), then Koga's gym."""
        log.info("STEP: fuchsia_koga")

        # Navigate to Fuchsia City
        if self.gs.map_id != FUCHSIA_CITY:
            self.nav.press_until_map_is(Direction.DOWN, FUCHSIA_CITY, max_steps=500)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Safari Zone — get HM03 Surf and Gold Teeth
        self.nav.press_until_map_change(Direction.UP, max_steps=40)
        # Navigate Safari Zone areas
        for _ in range(4):
            self.nav.press_until_map_change(Direction.UP, max_steps=100)
        # Secret House with Surf
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=60)
        self.nav.exit_building()

        # Warden's house — trade Gold Teeth for HM04 Strength
        self.nav.press_until_map_change(Direction.DOWN, max_steps=60)
        self.nav.press_until_dialog(Direction.UP, max_steps=15)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=40)
        self.nav.exit_building()

        # Fuchsia Gym (invisible walls)
        self.nav.press_until_map_is(Direction.DOWN, FUCHSIA_GYM, max_steps=60)
        if self.gs.map_id != FUCHSIA_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=30)
        self.nav.press_until_dialog(Direction.UP, max_steps=30)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: fuchsia_koga — complete")
        self._mark_complete("fuchsia_koga")

    def step_cinnabar_blaine(self):
        """Surf to Cinnabar, Pokemon Mansion (Secret Key), beat Blaine."""
        log.info("STEP: cinnabar_blaine")

        # Surf south from Fuchsia/Pallet to Cinnabar Island
        self.nav.press_until_map_is(Direction.DOWN, CINNABAR_ISLAND, max_steps=500)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Pokemon Mansion — get Secret Key
        self.nav.press_until_map_change(Direction.UP, max_steps=40)
        # Navigate mansion (4 floors with switches)
        for _ in range(4):
            self.nav.press_until_map_change(Direction.DOWN, max_steps=100)
        self.nav.mash_a(count=20, frames_between=20)
        self.nav.exit_building()

        # Cinnabar Gym (quiz doors)
        self.nav.press_until_map_is(Direction.RIGHT, CINNABAR_GYM, max_steps=40)
        if self.gs.map_id != CINNABAR_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=20)
        # Answer quiz questions with A to skip fights
        for _ in range(6):
            self.nav.press_until_dialog(Direction.UP, max_steps=15)
            self.nav.press_a_interact()
            self.nav.mash_a(count=5, frames_between=30)
        # Blaine battle
        self.nav.press_until_dialog(Direction.UP, max_steps=15)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: cinnabar_blaine — complete")
        self._mark_complete("cinnabar_blaine")

    def step_viridian_giovanni(self):
        """Return to Viridian City, beat Giovanni in the gym."""
        log.info("STEP: viridian_giovanni")

        # Surf/walk back to Viridian City
        if self.gs.map_id != VIRIDIAN_CITY:
            self.nav.press_until_map_is(Direction.UP, VIRIDIAN_CITY, max_steps=500)

        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Viridian Gym
        self.nav.press_until_map_is(Direction.DOWN, VIRIDIAN_GYM, max_steps=60)
        if self.gs.map_id != VIRIDIAN_GYM:
            self.nav.press_until_map_change(Direction.UP, max_steps=30)
        # Navigate spinning tiles to Giovanni
        self.nav.press_until_dialog(Direction.UP, max_steps=40)
        self.nav.press_a_interact()
        self.nav.mash_through_dialog(max_presses=200)
        self.nav.exit_building()

        log.info("STEP: viridian_giovanni — complete")
        self._mark_complete("viridian_giovanni")

    def step_elite_four(self):
        """Route 22 → 23 → Victory Road → Indigo Plateau → Elite Four → Champion."""
        log.info("STEP: elite_four")

        # Navigate west to Route 22
        self.nav.press_until_map_is(Direction.LEFT, ROUTE_22, max_steps=60)
        # North through Route 23 (badge gates)
        self.nav.press_until_map_is(Direction.UP, ROUTE_23, max_steps=100)
        self.nav.mash_a(count=30, frames_between=20)  # badge gate dialogs

        # Victory Road (3 floors with strength puzzles)
        self.nav.press_until_map_change(Direction.UP, max_steps=100)
        for _ in range(3):
            self.nav.press_until_map_change(Direction.UP, max_steps=150)

        # Indigo Plateau — heal
        self.nav.press_until_map_is(Direction.UP, INDIGO_PLATEAU, max_steps=100)
        self.nav.enter_pokecenter_and_heal()
        self.nav.exit_building()

        # Elite Four: 4 battles + Champion (5 consecutive rooms)
        for i in range(5):
            log.info(f"elite_four: battle {i + 1}/5")
            self.nav.press_until_map_change(Direction.UP, max_steps=30)
            self.nav.press_until_dialog(Direction.UP, max_steps=20)
            self.nav.press_a_interact()
            self.nav.mash_through_dialog(max_presses=500)

        # Hall of Fame
        self.nav.mash_a(count=100, frames_between=20)

        log.info("STEP: elite_four — GAME COMPLETE!")
        self._mark_complete("elite_four")
        self._mark_complete("game_complete")

    # ------------------------------------------------------------------
    # Dispatcher & main loop
    # ------------------------------------------------------------------

    def run_next_step(self):
        """Execute the next progression step."""
        step = self.get_current_step()

        # ---- BUG-03: stall detector ----------------------------------------
        # Snapshot (step, map_id, x, y) at the start of each call.
        # If the last _STALL_WINDOW snapshots all share the same step AND the same
        # map_id (no map progress), that's a stall event.  After _STALL_MAX_RETRIES
        # stall events on the same step, we force-advance to the next step so the
        # bot doesn't loop forever.
        self.gs.update()
        snap = (step, self.gs.map_id, self.gs.player_x, self.gs.player_y)
        self._stall_history.append(snap)
        if len(self._stall_history) > self._STALL_WINDOW:
            self._stall_history.pop(0)

        if len(self._stall_history) == self._STALL_WINDOW:
            all_same = all(
                h[0] == step and h[1] == snap[1]
                for h in self._stall_history
            )
            if all_same:
                retries = self._stall_retries.get(step, 0) + 1
                self._stall_retries[step] = retries
                log.warning(
                    "STALL [retry %d/%d]: step='%s' map=0x%02X pos=(%d,%d) — "
                    "same step+map for %d consecutive calls",
                    retries, self._STALL_MAX_RETRIES,
                    step, snap[1], snap[2], snap[3], self._STALL_WINDOW,
                )
                if retries >= self._STALL_MAX_RETRIES:
                    log.error(
                        "STALL SKIP: step='%s' failed after %d retries — "
                        "marking complete and advancing to next step",
                        step, retries,
                    )
                    self._stall_history.clear()
                    self._stall_retries.pop(step, None)
                    self._mark_complete(step)
                    return
        # ---- end stall detector --------------------------------------------

        log.info(f"run_next_step: '{step}'")

        dispatch = {
            "pallet_start": self.step_pallet_town,
            "route1_to_viridian": self.step_route1_to_viridian,
            "viridian_parcel": self.step_viridian_parcel,
            "viridian_forest": self.step_viridian_forest,
            "pewter_brock": self.step_pewter_brock,
            "mt_moon": self.step_mt_moon,
            "cerulean_misty": self.step_cerulean_misty,
            "nugget_bridge_bill": self.step_nugget_bridge_bill,
            "vermilion_ltsurge": self.step_vermilion_ltsurge,
            "rock_tunnel": self.step_rock_tunnel,
            "celadon_erika": self.step_celadon_erika,
            "pokemon_tower": self.step_pokemon_tower,
            "saffron_sabrina": self.step_saffron_sabrina,
            "fuchsia_koga": self.step_fuchsia_koga,
            "cinnabar_blaine": self.step_cinnabar_blaine,
            "viridian_giovanni": self.step_viridian_giovanni,
            "elite_four": self.step_elite_four,
        }

        fn = dispatch.get(step)
        if fn:
            fn()
        elif step == "game_complete":
            log.info("Game is complete!")
        else:
            log.warning(f"Unknown step: '{step}'")

    def run_full_game(self):
        """Main loop: execute steps, handle battles, heal as needed."""
        log.info("run_full_game: starting")
        while True:
            self.gs.update()

            if self.gs.in_battle:
                if self.battle_ai:
                    self.battle_ai.handle_battle_turn()
                else:
                    self.nav.mash_a(count=5, frames_between=20)
                continue

            if self.gs.needs_heal:
                go_to_pokecenter(self.nav, self.gs)
                continue

            step = self.get_current_step()
            if step == "game_complete":
                log.info("GAME COMPLETE!")
                break

            self.run_next_step()
