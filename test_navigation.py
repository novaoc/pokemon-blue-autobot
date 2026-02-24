"""
test_navigation.py — Unit tests for navigation.py

Tests run without a real emulator or ROM by using mock stubs.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch, call

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from navigation import (
    MAP_IDS,
    POKECENTER_LOCATIONS,
    POKECENTER_DOORS,
    Direction,
    Navigator,
    ProgressionManager,
    go_to_pokecenter,
    _has_badge,
    BADGE_BOULDER,
    BADGE_CASCADE,
    BADGE_THUNDER,
    BADGE_RAINBOW,
    BADGE_SOUL,
    BADGE_MARSH,
    BADGE_VOLCANO,
    BADGE_EARTH,
    STATE_FILE,
)


# ---------------------------------------------------------------------------
# Helpers / Stubs
# ---------------------------------------------------------------------------

def make_emulator():
    """Return a MagicMock that looks like PokemonEmulator."""
    emu = MagicMock()
    emu.button = MagicMock()
    emu.button_release = MagicMock()
    emu.tick = MagicMock()
    return emu


def make_game_state(x=5, y=5, map_id=0x00, badges=0,
                    in_battle=False, dialog_open=False, needs_heal=False):
    """Return a MagicMock GameState with given properties."""
    gs = MagicMock()
    gs.player_x = x
    gs.player_y = y
    gs.map_id = map_id
    gs.badges = badges
    gs.in_battle = in_battle
    gs.dialog_open = dialog_open
    gs.needs_heal = needs_heal
    gs.update = MagicMock()
    return gs


# ---------------------------------------------------------------------------
# Test: MAP_IDS
# ---------------------------------------------------------------------------

class TestMapIds(unittest.TestCase):

    def test_all_required_towns_present(self):
        required = {
            0x00: "PALLET_TOWN",
            0x01: "VIRIDIAN_CITY",
            0x02: "PEWTER_CITY",
            0x03: "CERULEAN_CITY",
            0x0C: "VERMILION_CITY",
            0x0D: "LAVENDER_TOWN",
            0x12: "FUCHSIA_CITY",
            0x13: "CINNABAR_ISLAND",
            0x14: "INDIGO_PLATEAU",
            0x15: "SAFFRON_CITY",
        }
        for map_id, name in required.items():
            self.assertIn(map_id, MAP_IDS,
                          f"0x{map_id:02X} missing from MAP_IDS")
            self.assertEqual(MAP_IDS[map_id], name,
                             f"0x{map_id:02X}: expected {name}, got {MAP_IDS[map_id]}")

    def test_routes_present(self):
        routes = {0x0E: "ROUTE_1", 0x0F: "ROUTE_2", 0x10: "ROUTE_3"}
        for map_id, name in routes.items():
            self.assertIn(map_id, MAP_IDS, f"Route 0x{map_id:02X} missing")

    def test_no_negative_ids(self):
        for k in MAP_IDS:
            self.assertGreaterEqual(k, 0, f"Negative map_id: {k}")

    def test_all_values_are_strings(self):
        for k, v in MAP_IDS.items():
            self.assertIsInstance(v, str, f"MAP_IDS[0x{k:02X}] is not a string")


# ---------------------------------------------------------------------------
# Test: POKECENTER_LOCATIONS
# ---------------------------------------------------------------------------

class TestPokecenterLocations(unittest.TestCase):

    def test_major_cities_have_centers(self):
        cities = [0x01, 0x02, 0x03, 0x0C, 0x11, 0x12, 0x13, 0x15]
        for city in cities:
            self.assertIn(city, POKECENTER_LOCATIONS,
                          f"City 0x{city:02X} missing from POKECENTER_LOCATIONS")

    def test_locations_are_2tuples(self):
        for k, v in POKECENTER_LOCATIONS.items():
            self.assertIsInstance(v, tuple, f"POKECENTER_LOCATIONS[0x{k:02X}] not a tuple")
            self.assertEqual(len(v), 2, f"POKECENTER_LOCATIONS[0x{k:02X}] not a 2-tuple")
            self.assertIsInstance(v[0], int)
            self.assertIsInstance(v[1], int)


# ---------------------------------------------------------------------------
# Test: Direction enum
# ---------------------------------------------------------------------------

class TestDirection(unittest.TestCase):

    def test_values(self):
        self.assertEqual(Direction.UP.value, "up")
        self.assertEqual(Direction.DOWN.value, "down")
        self.assertEqual(Direction.LEFT.value, "left")
        self.assertEqual(Direction.RIGHT.value, "right")

    def test_opposites(self):
        self.assertEqual(Direction.UP.opposite, Direction.DOWN)
        self.assertEqual(Direction.DOWN.opposite, Direction.UP)
        self.assertEqual(Direction.LEFT.opposite, Direction.RIGHT)
        self.assertEqual(Direction.RIGHT.opposite, Direction.LEFT)

    def test_perpendiculars(self):
        up_perps = Direction.UP.perpendiculars
        self.assertIn(Direction.LEFT, up_perps)
        self.assertIn(Direction.RIGHT, up_perps)

        left_perps = Direction.LEFT.perpendiculars
        self.assertIn(Direction.UP, left_perps)
        self.assertIn(Direction.DOWN, left_perps)

    def test_all_members(self):
        members = {d.name for d in Direction}
        self.assertEqual(members, {"UP", "DOWN", "LEFT", "RIGHT"})


# ---------------------------------------------------------------------------
# Test: Navigator.move_one_step
# ---------------------------------------------------------------------------

class TestNavigatorMoveOneStep(unittest.TestCase):

    def _make_nav(self, x=5, y=5, new_x=None, new_y=None):
        emu = make_emulator()
        gs = make_game_state(x=x, y=y)
        nav = Navigator(emu, gs)

        # Simulate position changing after button press by side-effecting tick
        if new_x is not None or new_y is not None:
            def _tick_effect(frames):
                gs.player_x = new_x if new_x is not None else x
                gs.player_y = new_y if new_y is not None else y
            emu.tick.side_effect = _tick_effect

        return nav, emu, gs

    def test_move_up_success(self):
        nav, emu, gs = self._make_nav(x=5, y=5, new_y=4)
        result = nav.move_one_step(Direction.UP)
        self.assertTrue(result)
        emu.button.assert_called_once_with("up")
        emu.button_release.assert_called_once_with("up")
        emu.tick.assert_called_once_with(Navigator.FRAMES_PER_STEP)

    def test_move_down_success(self):
        nav, emu, gs = self._make_nav(x=5, y=5, new_y=6)
        result = nav.move_one_step(Direction.DOWN)
        self.assertTrue(result)
        emu.button.assert_called_with("down")

    def test_move_left_success(self):
        nav, emu, gs = self._make_nav(x=5, y=5, new_x=4)
        result = nav.move_one_step(Direction.LEFT)
        self.assertTrue(result)
        emu.button.assert_called_with("left")

    def test_move_right_success(self):
        nav, emu, gs = self._make_nav(x=5, y=5, new_x=6)
        result = nav.move_one_step(Direction.RIGHT)
        self.assertTrue(result)
        emu.button.assert_called_with("right")

    def test_blocked_returns_false(self):
        # Position does not change → blocked
        nav, emu, gs = self._make_nav(x=5, y=5, new_x=5, new_y=5)
        result = nav.move_one_step(Direction.UP)
        self.assertFalse(result)

    def test_blocked_still_calls_button_and_release(self):
        nav, emu, gs = self._make_nav(x=5, y=5)
        nav.move_one_step(Direction.LEFT)
        emu.button.assert_called_with("left")
        emu.button_release.assert_called_with("left")


# ---------------------------------------------------------------------------
# Test: Navigator.navigate_to
# ---------------------------------------------------------------------------

class TestNavigatorNavigateTo(unittest.TestCase):

    def test_already_at_target(self):
        emu = make_emulator()
        gs = make_game_state(x=5, y=5)
        nav = Navigator(emu, gs)
        result = nav.navigate_to(5, 5)
        self.assertTrue(result)
        # No button presses needed
        emu.button.assert_not_called()

    def test_navigate_right(self):
        emu = make_emulator()
        gs = make_game_state(x=0, y=5)
        nav = Navigator(emu, gs)

        call_count = [0]
        def tick_side_effect(frames):
            call_count[0] += 1
            gs.player_x = min(gs.player_x + 1, 3)  # move right each tick
        emu.tick.side_effect = tick_side_effect

        result = nav.navigate_to(3, 5)
        self.assertTrue(result)

    def test_navigate_up(self):
        emu = make_emulator()
        gs = make_game_state(x=5, y=5)
        nav = Navigator(emu, gs)

        def tick_side_effect(frames):
            gs.player_y = max(gs.player_y - 1, 2)
        emu.tick.side_effect = tick_side_effect

        result = nav.navigate_to(5, 2)
        self.assertTrue(result)

    def test_stops_when_in_battle(self):
        emu = make_emulator()
        gs = make_game_state(x=0, y=0)
        gs.in_battle = True
        nav = Navigator(emu, gs)

        result = nav.navigate_to(10, 10)
        self.assertFalse(result)

    def test_stuck_detection_tries_perpendicular(self):
        """If position never changes, escape logic should be triggered."""
        emu = make_emulator()
        gs = make_game_state(x=5, y=5)  # Position NEVER changes → stuck
        nav = Navigator(emu, gs)
        nav.MAX_STUCK_TRIES = 3
        nav.ESCAPE_STEPS = 1

        # Will hit max_steps; we just verify it doesn't infinite loop
        result = nav.navigate_to(10, 5, max_steps=20)
        self.assertFalse(result)  # Never reaches target because position stuck


# ---------------------------------------------------------------------------
# Test: Navigator.press_a_interact
# ---------------------------------------------------------------------------

class TestNavigatorPressA(unittest.TestCase):

    def test_press_a_calls_button_and_release(self):
        emu = make_emulator()
        gs = make_game_state()
        nav = Navigator(emu, gs)

        nav.press_a_interact()

        emu.button.assert_called_once_with("a")
        emu.button_release.assert_called_once_with("a")
        emu.tick.assert_called_once_with(Navigator.FRAMES_INTERACT)


# ---------------------------------------------------------------------------
# Test: Navigator.mash_through_dialog
# ---------------------------------------------------------------------------

class TestNavigatorMashDialog(unittest.TestCase):

    def test_stops_when_dialog_clears(self):
        emu = make_emulator()
        gs = make_game_state(dialog_open=True)
        nav = Navigator(emu, gs)

        press_count = [0]
        def tick_side_effect(frames):
            press_count[0] += 1
            if press_count[0] >= 3:
                gs.dialog_open = False
        emu.tick.side_effect = tick_side_effect

        presses = nav.mash_through_dialog(max_presses=50)
        self.assertLessEqual(presses, 50)
        self.assertEqual(presses, 3)

    def test_respects_max_presses(self):
        emu = make_emulator()
        gs = make_game_state(dialog_open=True)
        nav = Navigator(emu, gs)
        # dialog_open stays True always → should stop at max
        presses = nav.mash_through_dialog(max_presses=5)
        self.assertEqual(presses, 5)

    def test_no_presses_if_dialog_closed(self):
        emu = make_emulator()
        gs = make_game_state(dialog_open=False)
        nav = Navigator(emu, gs)
        presses = nav.mash_through_dialog(max_presses=50)
        self.assertEqual(presses, 0)
        emu.button.assert_not_called()

    def test_uses_correct_frame_timing(self):
        emu = make_emulator()
        gs = make_game_state(dialog_open=True)
        nav = Navigator(emu, gs)
        nav.mash_through_dialog(max_presses=1)
        emu.tick.assert_called_with(Navigator.FRAMES_DIALOG)


# ---------------------------------------------------------------------------
# Test: Navigator.enter_building
# ---------------------------------------------------------------------------

class TestNavigatorEnterBuilding(unittest.TestCase):

    def test_enter_building_navigates_then_presses_up(self):
        emu = make_emulator()
        gs = make_game_state(x=5, y=5)
        nav = Navigator(emu, gs)

        # Patch navigate_to so it doesn't actually loop
        nav.navigate_to = MagicMock(return_value=True)

        nav.enter_building(7, 4)

        # Should navigate to one tile south of door (y+1)
        nav.navigate_to.assert_called_once_with(7, 5)
        # Should press "up" to enter
        emu.button.assert_called_with("up")
        emu.button_release.assert_called_with("up")


# ---------------------------------------------------------------------------
# Test: _has_badge helper
# ---------------------------------------------------------------------------

class TestHasBadge(unittest.TestCase):

    def test_no_badges(self):
        for bit in range(8):
            self.assertFalse(_has_badge(0x00, bit))

    def test_all_badges(self):
        for bit in range(8):
            self.assertTrue(_has_badge(0xFF, bit))

    def test_boulder_only(self):
        badges = 0x01  # bit 0 = Boulder
        self.assertTrue(_has_badge(badges, BADGE_BOULDER))
        self.assertFalse(_has_badge(badges, BADGE_CASCADE))

    def test_first_four_badges(self):
        badges = 0x0F  # bits 0-3
        for bit in range(4):
            self.assertTrue(_has_badge(badges, bit))
        for bit in range(4, 8):
            self.assertFalse(_has_badge(badges, bit))

    def test_all_eight_badges_individually(self):
        for bit in range(8):
            badges = 1 << bit
            self.assertTrue(_has_badge(badges, bit))
            for other in range(8):
                if other != bit:
                    self.assertFalse(_has_badge(badges, other))


# ---------------------------------------------------------------------------
# Test: ProgressionManager.get_current_step
# ---------------------------------------------------------------------------

class TestProgressionManagerGetCurrentStep(unittest.TestCase):

    def _make_pm(self, badges=0, step="pallet_start"):
        emu = make_emulator()
        gs = make_game_state(badges=badges)
        nav = Navigator(emu, gs)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"step": step, "badges": badges, "completed_steps": []}, f)
            state_path = f.name

        pm = ProgressionManager.__new__(ProgressionManager)
        pm.emu = emu
        pm.gs = gs
        pm.nav = nav
        pm.battle_ai = None
        pm.state = {"step": step, "badges": badges, "completed_steps": []}
        pm._state_file = state_path
        return pm, state_path

    def tearDown(self):
        pass  # temp files cleaned up per-test

    def test_no_badges_returns_pallet_or_early_step(self):
        pm, f = self._make_pm(badges=0, step="pallet_start")
        step = pm.get_current_step()
        self.assertEqual(step, "pallet_start")
        os.unlink(f)

    def test_no_badges_viridian_parcel_preserved(self):
        pm, f = self._make_pm(badges=0, step="viridian_parcel")
        step = pm.get_current_step()
        self.assertEqual(step, "viridian_parcel")
        os.unlink(f)

    def test_one_badge_routes_to_mt_moon_area(self):
        pm, f = self._make_pm(badges=0x01, step="mt_moon")
        step = pm.get_current_step()
        self.assertIn(step, ("mt_moon", "cerulean_misty"))
        os.unlink(f)

    def test_two_badges_routes_to_vermilion_area(self):
        pm, f = self._make_pm(badges=0x03, step="vermilion_ltsurge")
        step = pm.get_current_step()
        self.assertIn(step, ("nugget_bridge_bill", "vermilion_ltsurge"))
        os.unlink(f)

    def test_three_badges_routes_to_celadon_area(self):
        pm, f = self._make_pm(badges=0x07, step="celadon_erika")
        step = pm.get_current_step()
        self.assertIn(step, ("rock_tunnel", "celadon_erika"))
        os.unlink(f)

    def test_four_badges_routes_to_pokemon_tower(self):
        pm, f = self._make_pm(badges=0x0F, step="pokemon_tower")
        step = pm.get_current_step()
        self.assertIn(step, ("pokemon_tower", "saffron_sabrina", "celadon_erika"))
        os.unlink(f)

    def test_five_badges_routes_to_fuchsia(self):
        pm, f = self._make_pm(badges=0x1F, step="fuchsia_koga")
        step = pm.get_current_step()
        self.assertIn(step, ("fuchsia_koga", "saffron_sabrina"))
        os.unlink(f)

    def test_six_badges_routes_to_cinnabar(self):
        pm, f = self._make_pm(badges=0x3F, step="cinnabar_blaine")
        step = pm.get_current_step()
        self.assertIn(step, ("cinnabar_blaine", "fuchsia_koga"))
        os.unlink(f)

    def test_seven_badges_routes_to_giovanni(self):
        pm, f = self._make_pm(badges=0x7F, step="viridian_giovanni")
        step = pm.get_current_step()
        self.assertEqual(step, "viridian_giovanni")
        os.unlink(f)

    def test_eight_badges_routes_to_elite_four(self):
        pm, f = self._make_pm(badges=0xFF, step="elite_four")
        step = pm.get_current_step()
        self.assertEqual(step, "elite_four")
        os.unlink(f)


# ---------------------------------------------------------------------------
# Test: ProgressionManager.load_state / save_state
# ---------------------------------------------------------------------------

class TestProgressionManagerState(unittest.TestCase):

    def test_load_state_from_file(self):
        initial = {"step": "pewter_brock", "badges": 1, "completed_steps": ["pallet_start"]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(initial, f)
            fname = f.name

        emu = make_emulator()
        gs = make_game_state()
        nav = Navigator(emu, gs)

        with patch('navigation.STATE_FILE', fname):
            pm = ProgressionManager(emu, gs, nav)

        self.assertEqual(pm.state["step"], "pewter_brock")
        self.assertEqual(pm.state["badges"], 1)
        self.assertIn("pallet_start", pm.state["completed_steps"])
        os.unlink(fname)

    def test_save_state_writes_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"step": "pallet_start", "badges": 0, "completed_steps": []}, f)
            fname = f.name

        emu = make_emulator()
        gs = make_game_state()
        nav = Navigator(emu, gs)

        with patch('navigation.STATE_FILE', fname):
            pm = ProgressionManager(emu, gs, nav)
            pm.state["step"] = "celadon_erika"
            pm.state["badges"] = 7
            pm.save_state()

        with open(fname) as f:
            saved = json.load(f)
        self.assertEqual(saved["step"], "celadon_erika")
        self.assertEqual(saved["badges"], 7)
        os.unlink(fname)

    def test_load_state_defaults_when_file_missing(self):
        emu = make_emulator()
        gs = make_game_state()
        nav = Navigator(emu, gs)

        with patch('navigation.STATE_FILE', '/tmp/no_such_file_xyz_123.json'):
            pm = ProgressionManager(emu, gs, nav)

        self.assertEqual(pm.state["step"], "pallet_start")
        self.assertEqual(pm.state["badges"], 0)
        self.assertEqual(pm.state["completed_steps"], [])

    def test_load_state_defaults_on_corrupt_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("NOT VALID JSON{{{{")
            fname = f.name

        emu = make_emulator()
        gs = make_game_state()
        nav = Navigator(emu, gs)

        with patch('navigation.STATE_FILE', fname):
            pm = ProgressionManager(emu, gs, nav)

        self.assertEqual(pm.state["step"], "pallet_start")
        os.unlink(fname)


# ---------------------------------------------------------------------------
# Test: ProgressionManager.run_next_step dispatcher
# ---------------------------------------------------------------------------

class TestProgressionManagerDispatch(unittest.TestCase):

    def _make_pm_with_step(self, step, badges=0):
        emu = make_emulator()
        gs = make_game_state(badges=badges)
        nav = Navigator(emu, gs)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"step": step, "badges": badges, "completed_steps": []}, f)
            fname = f.name

        with patch('navigation.STATE_FILE', fname):
            pm = ProgressionManager(emu, gs, nav)

        os.unlink(fname)
        return pm

    def test_dispatches_pallet_start(self):
        pm = self._make_pm_with_step("pallet_start")
        pm.step_pallet_town = MagicMock()
        pm.get_current_step = MagicMock(return_value="pallet_start")
        pm.run_next_step()
        pm.step_pallet_town.assert_called_once()

    def test_dispatches_pewter_brock(self):
        pm = self._make_pm_with_step("pewter_brock", badges=0)
        pm.step_pewter_brock = MagicMock()
        pm.get_current_step = MagicMock(return_value="pewter_brock")
        pm.run_next_step()
        pm.step_pewter_brock.assert_called_once()

    def test_dispatches_elite_four(self):
        pm = self._make_pm_with_step("elite_four", badges=0xFF)
        pm.step_elite_four = MagicMock()
        pm.get_current_step = MagicMock(return_value="elite_four")
        pm.run_next_step()
        pm.step_elite_four.assert_called_once()

    def test_all_steps_have_dispatch_entry(self):
        from navigation import ProgressionManager as PM
        steps = PM.STEP_ORDER[:-1]  # exclude 'game_complete' (no method)
        pm = self._make_pm_with_step("pallet_start")
        for step in steps:
            pm.get_current_step = MagicMock(return_value=step)
            # Patch the corresponding method
            method_map = {
                "pallet_start":       "step_pallet_town",
                "route1_to_viridian": "step_route1_to_viridian",
                "viridian_parcel":    "step_viridian_parcel",
                "viridian_forest":    "step_viridian_forest",
                "pewter_brock":       "step_pewter_brock",
                "mt_moon":            "step_mt_moon",
                "cerulean_misty":     "step_cerulean_misty",
                "nugget_bridge_bill": "step_nugget_bridge_bill",
                "vermilion_ltsurge":  "step_vermilion_ltsurge",
                "rock_tunnel":        "step_rock_tunnel",
                "celadon_erika":      "step_celadon_erika",
                "pokemon_tower":      "step_pokemon_tower",
                "saffron_sabrina":    "step_saffron_sabrina",
                "fuchsia_koga":       "step_fuchsia_koga",
                "cinnabar_blaine":    "step_cinnabar_blaine",
                "viridian_giovanni":  "step_viridian_giovanni",
                "elite_four":         "step_elite_four",
            }
            if step in method_map:
                mocked = MagicMock()
                setattr(pm, method_map[step], mocked)
                pm.run_next_step()
                mocked.assert_called_once(), f"run_next_step didn't dispatch '{step}'"


# ---------------------------------------------------------------------------
# Test: go_to_pokecenter helper
# ---------------------------------------------------------------------------

class TestGotoPokecenter(unittest.TestCase):

    def test_no_door_returns_false(self):
        emu = make_emulator()
        gs = make_game_state(map_id=0xFF)  # Unknown map, no door
        nav = Navigator(emu, gs)
        result = go_to_pokecenter(nav, gs)
        self.assertFalse(result)

    def test_known_city_returns_true(self):
        emu = make_emulator()
        gs = make_game_state(map_id=0x01, dialog_open=False)  # Viridian City
        nav = Navigator(emu, gs)
        nav.enter_building = MagicMock()
        nav.navigate_to = MagicMock(return_value=True)
        nav.press_a_interact = MagicMock()
        nav.mash_through_dialog = MagicMock(return_value=5)

        result = go_to_pokecenter(nav, gs)
        self.assertTrue(result)
        nav.enter_building.assert_called_once()
        nav.press_a_interact.assert_called_once()


# ---------------------------------------------------------------------------
# Test: STEP_ORDER completeness
# ---------------------------------------------------------------------------

class TestStepOrder(unittest.TestCase):

    def test_step_order_is_list(self):
        self.assertIsInstance(ProgressionManager.STEP_ORDER, list)

    def test_step_order_starts_with_pallet(self):
        self.assertEqual(ProgressionManager.STEP_ORDER[0], "pallet_start")

    def test_step_order_ends_with_game_complete(self):
        self.assertEqual(ProgressionManager.STEP_ORDER[-1], "game_complete")

    def test_step_order_has_all_gyms(self):
        gyms = ["pewter_brock", "cerulean_misty", "vermilion_ltsurge",
                "celadon_erika", "fuchsia_koga", "saffron_sabrina",
                "cinnabar_blaine", "viridian_giovanni"]
        for gym in gyms:
            self.assertIn(gym, ProgressionManager.STEP_ORDER,
                          f"Gym step '{gym}' missing from STEP_ORDER")

    def test_step_order_has_no_duplicates(self):
        self.assertEqual(len(ProgressionManager.STEP_ORDER),
                         len(set(ProgressionManager.STEP_ORDER)))

    def test_badge_driven_order(self):
        """Gyms should appear in correct badge order."""
        order = ProgressionManager.STEP_ORDER
        brock_idx   = order.index("pewter_brock")
        misty_idx   = order.index("cerulean_misty")
        surge_idx   = order.index("vermilion_ltsurge")
        erika_idx   = order.index("celadon_erika")
        koga_idx    = order.index("fuchsia_koga")
        sabrina_idx = order.index("saffron_sabrina")
        blaine_idx  = order.index("cinnabar_blaine")
        giovanni_idx = order.index("viridian_giovanni")
        elite_idx   = order.index("elite_four")

        self.assertLess(brock_idx,    misty_idx)
        self.assertLess(misty_idx,    surge_idx)
        self.assertLess(surge_idx,    erika_idx)
        # Koga and Sabrina can be in either order in the guide, but both before Blaine
        self.assertLess(max(koga_idx, sabrina_idx), blaine_idx)
        self.assertLess(blaine_idx,   giovanni_idx)
        self.assertLess(giovanni_idx, elite_idx)


# ---------------------------------------------------------------------------
# Progression state: badge count mapping summary
# ---------------------------------------------------------------------------

class TestBadgeCountMapping(unittest.TestCase):
    """Verify that badge bit counts map to sensible step names."""

    def _step_for_badges(self, badges, saved_step):
        emu = make_emulator()
        gs = make_game_state(badges=badges)
        nav = Navigator(emu, gs)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"step": saved_step, "badges": badges, "completed_steps": []}, f)
            fname = f.name

        with patch('navigation.STATE_FILE', fname):
            pm = ProgressionManager(emu, gs, nav)

        os.unlink(fname)
        return pm.get_current_step()

    def test_badge_table(self):
        """Print a badge → step mapping table for visual verification."""
        cases = [
            (0x00, "pallet_start",       "pallet_start"),
            (0x00, "viridian_parcel",     "viridian_parcel"),
            (0x01, "mt_moon",             "mt_moon"),
            (0x01, "cerulean_misty",      "cerulean_misty"),
            (0x03, "nugget_bridge_bill",  "nugget_bridge_bill"),
            (0x03, "vermilion_ltsurge",   "vermilion_ltsurge"),
            (0x07, "rock_tunnel",         "rock_tunnel"),
            (0x07, "celadon_erika",       "celadon_erika"),
            (0x0F, "pokemon_tower",       "pokemon_tower"),
            (0x1F, "fuchsia_koga",        "fuchsia_koga"),
            (0x3F, "cinnabar_blaine",     "cinnabar_blaine"),
            (0x7F, "viridian_giovanni",   "viridian_giovanni"),
            (0xFF, "elite_four",          "elite_four"),
        ]
        print("\n\n=== Badge → Step Mapping Table ===")
        print(f"{'Badges':>8}  {'Count':>5}  {'Expected Step':<25}  {'Got'}")
        print("-" * 70)
        for badges, saved_step, expected in cases:
            got = self._step_for_badges(badges, saved_step)
            match = "✓" if got == expected else "✗"
            badge_count = bin(badges).count("1")
            print(f"0x{badges:02X}      {badge_count:>5}  {expected:<25}  {got}  {match}")
            self.assertEqual(got, expected,
                             f"badges=0x{badges:02X}, saved='{saved_step}': expected '{expected}', got '{got}'")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Configure basic logging so test output is informative
    import logging
    logging.basicConfig(
        level=logging.WARNING,  # suppress DEBUG/INFO during tests
        format="%(levelname)s: %(message)s"
    )
    unittest.main(verbosity=2)
