#!/usr/bin/env python3
"""
test_boot.py — Verify the bot boots to the overworld correctly.

Checks:
  1. Bot starts headless without errors
  2. map_id is non-zero OR position is non-zero (we're actually in the game)
  3. Pressing a direction actually moves the player (not stuck in a menu)
  4. Screenshot is saved for manual inspection

Usage:
    cd /Users/wren/nova/games/gb
    python /Users/wren/nova/pokemon-bot/test_boot.py
"""

import sys
import os

# Allow running from anywhere
sys.path.insert(0, '/Users/wren/nova/pokemon-bot')
os.chdir('/Users/wren/nova/games/gb')

from bot import PokemonBot, detect_menu_state

SCREENSHOT_PATH = '/Users/wren/nova/pokemon-bot/screenshots/boot_test.png'

def main():
    print("=" * 60)
    print("test_boot.py — Pokemon Blue boot sequence test")
    print("=" * 60)

    bot = PokemonBot(rom_path='blueEng.gb', headless=True, speed=0)
    bot.start()
    bot.game_state.update()

    map_id = bot.game_state.map_id
    px     = bot.game_state.player_x
    py     = bot.game_state.player_y
    badges = bot.game_state.badges
    party  = bot.game_state.party

    print(f"\n--- Post-boot state ---")
    print(f"Map:      0x{map_id:02X}")
    print(f"Position: ({px}, {py})")
    print(f"Badges:   {bin(badges)} ({bin(badges).count('1')} total)")
    print(f"Party:    {party}")

    menu_state = detect_menu_state(bot.emulator.pyboy)
    print(f"Menu state: {menu_state}")

    # --- Test 1: Are we in the game? ---
    in_game = (map_id != 0) or (px != 0) or (py != 0)
    print(f"\n[TEST 1] In game (map or pos non-zero): {'PASS' if in_game else 'FAIL'}")
    if not in_game:
        print("  ERROR: map=0x00, position=(0,0) — still on title screen?")

    # --- Test 2: Movement test (try all 4 directions) ---
    old_x, old_y = px, py
    moved = False
    for btn in ("right", "left", "up", "down"):
        pre_x, pre_y = bot.game_state.player_x, bot.game_state.player_y
        bot.emulator.button_down(btn)
        bot.emulator.tick(20)
        bot.emulator.button_up(btn)
        bot.emulator.tick(10)
        bot.game_state.update()
        new_x, new_y = bot.game_state.player_x, bot.game_state.player_y
        if new_x != pre_x or new_y != pre_y:
            print(f"[TEST 2] Movement ({btn}): ({pre_x},{pre_y}) → ({new_x},{new_y}): PASS")
            moved = True
            break
        else:
            print(f"[TEST 2] Movement ({btn}): ({pre_x},{pre_y}) — blocked")

    if not moved:
        print("[TEST 2] Movement: FAIL — all 4 directions blocked")

    # --- Screenshot ---
    os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)
    bot.emulator.save_screenshot(SCREENSHOT_PATH)
    print(f"\nScreenshot saved: {SCREENSHOT_PATH}")

    bot.stop()

    print("\n--- Summary ---")
    all_passed = in_game and moved
    if all_passed:
        print("✅ All tests PASSED — boot sequence working correctly!")
    else:
        print("❌ Some tests FAILED — see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
