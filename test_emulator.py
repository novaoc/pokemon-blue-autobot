"""
test_emulator.py — Quick smoke-test for emulator.py and memory.py.

Usage:
    python3 test_emulator.py

What it does:
    1. Starts PyBoy headless with the Pokemon Blue ROM
    2. Advances 300 frames (~5 seconds of game time)
    3. Reads the full GameState from memory
    4. Prints the GameState to stdout
    5. Saves a screenshot to screenshots/init.png
    6. Reports frame count and exits cleanly
"""

import os
import sys
import traceback

# Ensure we can import from this project directory
sys.path.insert(0, os.path.dirname(__file__))

from emulator import PokemonEmulator, DEFAULT_ROM
from memory import GameState

SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "screenshots", "init.png")
FRAMES_TO_ADVANCE = 300


def main() -> int:
    print(f"[test] ROM: {DEFAULT_ROM}")
    print(f"[test] Advancing {FRAMES_TO_ADVANCE} frames headless …\n")

    try:
        with PokemonEmulator(rom_path=DEFAULT_ROM, headless=True, speed=0) as emu:
            # --- Advance frames -------------------------------------------
            emu.tick(FRAMES_TO_ADVANCE)
            print(f"[test] Frame count: {emu.frame_count}")

            # --- Read GameState -------------------------------------------
            state = GameState(emu)
            state.update()
            print(state)

            # --- Low-level memory spot-checks -----------------------------
            print("\n[test] Raw memory spot-checks:")
            print(f"  MAP_ID    (0xD35E) = 0x{emu.read_memory(0xD35E):02X}")
            print(f"  PLAYER_X  (0xD361) = {emu.read_memory(0xD361)}")
            print(f"  PLAYER_Y  (0xD362) = {emu.read_memory(0xD362)}")
            print(f"  BATTLE    (0xD057) = {emu.read_memory(0xD057)}")
            print(f"  BADGES    (0xD356) = 0b{emu.read_memory(0xD356):08b}")

            # --- Read 8-byte range example --------------------------------
            block = emu.read_memory_range(0xD163, 8)
            print(f"  PARTY block [0xD163..0xD16A] = {block.hex()}")

            # --- Screenshot -----------------------------------------------
            emu.save_screenshot(SCREENSHOT_PATH)
            print(f"\n[test] Screenshot saved → {SCREENSHOT_PATH}")

            # --- Verify screenshot exists and has size --------------------
            size = os.path.getsize(SCREENSHOT_PATH)
            print(f"[test] Screenshot size: {size} bytes")
            if size < 100:
                print("[WARN] Screenshot is suspiciously small!")

            print("\n[test] ✅  All checks passed.")
            return 0

    except Exception:
        print("\n[test] ❌  Test FAILED with exception:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
