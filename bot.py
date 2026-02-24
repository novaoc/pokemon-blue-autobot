#!/usr/bin/env python3
"""
bot.py — Pokemon Blue Autobot
==============================
Main orchestrator that wires together:
  - emulator.py  (PokemonEmulator)
  - memory.py    (GameState)
  - battle.py    (BattleAI)
  - navigation.py (Navigator + ProgressionManager)

Usage:
    python bot.py --rom /Users/wren/nova/games/gb/blueEng.gb --headless --speed 0
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import Optional

# ---------------------------------------------------------------------------
# Logging — both file and stdout
# ---------------------------------------------------------------------------

def setup_logging(log_level: str = "INFO", log_file: str = "pokemon_bot.log") -> logging.Logger:
    level = getattr(logging, log_level.upper(), logging.INFO)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
    ]

    logging.basicConfig(level=level, format=fmt, handlers=handlers)
    logger = logging.getLogger("pokemon_bot")
    logger.setLevel(level)
    return logger


log = logging.getLogger("pokemon_bot")

# ---------------------------------------------------------------------------
# Module imports
# ---------------------------------------------------------------------------

from emulator import PokemonEmulator, DEFAULT_ROM
from memory import GameState
from battle import BattleAI
from navigation import Navigator, ProgressionManager, go_to_pokecenter

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

DEFAULT_SAVE_STATE = os.path.join(
    os.path.dirname(__file__), "saves", "autosave.state"
)
DEFAULT_SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
SCREENSHOT_INTERVAL = 300  # frames between auto-screenshots


# ---------------------------------------------------------------------------
# PokemonBot
# ---------------------------------------------------------------------------

class PokemonBot:
    """
    Main orchestrator for the Pokemon Blue autobot.

    Parameters
    ----------
    rom_path : str
        Path to the Game Boy ROM file.
    headless : bool
        Run without a display window.
    speed : int
        Emulation speed (0 = unlimited, 1 = normal).
    screenshot_dir : str
        Directory to save periodic screenshots.
    log_level : str
        Logging verbosity ("DEBUG", "INFO", "WARNING", etc.).
    save_state_path : str | None
        Path to load/save emulator state.  If None, no state is auto-loaded.
    screenshots : bool
        Whether to capture periodic screenshots.
    """

    def __init__(
        self,
        rom_path: str = DEFAULT_ROM,
        headless: bool = True,
        speed: int = 0,
        screenshot_dir: str = DEFAULT_SCREENSHOT_DIR,
        log_level: str = "INFO",
        save_state_path: Optional[str] = None,
        screenshots: bool = False,
    ) -> None:
        # Configure logging (idempotent — only sets up handlers once)
        setup_logging(log_level)

        self.rom_path = rom_path
        self.headless = headless
        self.speed = speed
        self.screenshot_dir = screenshot_dir
        self.save_state_path = save_state_path
        self.screenshots = screenshots

        # Subsystem instances (created here; started in start())
        self.emulator = PokemonEmulator(
            rom_path=rom_path,
            headless=headless,
            speed=speed,
        )
        self.game_state = GameState(self.emulator)

        # BattleAI takes the raw PyBoy instance (its internal API)
        # We defer creation until start() because pyboy isn't initialized yet,
        # but we can pre-create the shell now — pyboy property is lazy.
        self._battle_ai: Optional[BattleAI] = None
        self._navigator: Optional[Navigator] = None
        self._progression: Optional[ProgressionManager] = None

        # Internal counters
        self._step_count: int = 0
        self._frame_count: int = 0
        self._last_screenshot_frame: int = 0
        self._running: bool = False

        log.info(
            "PokemonBot initialized: rom=%s headless=%s speed=%s",
            os.path.basename(rom_path), headless, speed,
        )

    # ------------------------------------------------------------------
    # Lazy subsystem accessors (valid after start())
    # ------------------------------------------------------------------

    @property
    def battle_ai(self) -> BattleAI:
        if self._battle_ai is None:
            raise RuntimeError("BattleAI not ready — call start() first")
        return self._battle_ai

    @property
    def navigator(self) -> Navigator:
        if self._navigator is None:
            raise RuntimeError("Navigator not ready — call start() first")
        return self._navigator

    @property
    def progression(self) -> ProgressionManager:
        if self._progression is None:
            raise RuntimeError("ProgressionManager not ready — call start() first")
        return self._progression

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, load_state: bool = True) -> None:
        """
        Start the emulator and initialize all subsystems.

        Parameters
        ----------
        load_state : bool
            If True and save_state_path is set (and the file exists), load
            that state automatically.
        """
        log.info("Starting emulator…")
        self.emulator.start()

        # Optionally load saved state
        if load_state and self.save_state_path and os.path.exists(self.save_state_path):
            log.info("Loading save state: %s", self.save_state_path)
            try:
                self.emulator.load_state(self.save_state_path)
            except Exception as exc:
                log.warning("Failed to load save state: %s", exc)

        # Tick a few frames to let the game boot / stabilize
        log.info("Warming up emulator (60 frames)…")
        self.emulator.tick(60)

        # Initial game-state snapshot
        self.game_state.update()

        # Now that emulator is running, create subsystems that need pyboy
        self._battle_ai = BattleAI(
            pyboy=self.emulator.pyboy,
            game_state=self.game_state,
        )
        self._navigator = Navigator(
            emulator=self.emulator,
            game_state=self.game_state,
        )
        self._progression = ProgressionManager(
            emulator=self.emulator,
            game_state=self.game_state,
            navigator=self._navigator,
            battle_ai=self._battle_ai,
        )

        # Create screenshot directory if needed
        if self.screenshots:
            os.makedirs(self.screenshot_dir, exist_ok=True)

        self._running = True
        log.info("Bot started. Frame count: %d", self.emulator.frame_count)

    def stop(self) -> None:
        """Clean shutdown — save emulator state and stop PyBoy."""
        self._running = False

        if self.emulator._pyboy is not None:
            # Auto-save state before quitting
            if self.save_state_path:
                try:
                    os.makedirs(
                        os.path.dirname(os.path.abspath(self.save_state_path)),
                        exist_ok=True,
                    )
                    self.emulator.save_state(self.save_state_path)
                    log.info("Emulator state saved to: %s", self.save_state_path)
                except Exception as exc:
                    log.error("Failed to save state: %s", exc)

            # Save progression state
            if self._progression is not None:
                try:
                    self._progression.save_state()
                except Exception as exc:
                    log.warning("Failed to save progression state: %s", exc)

            self.emulator.stop()
            log.info("Emulator stopped. Total frames: %d", self._frame_count)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "PokemonBot":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
        return False  # Don't suppress exceptions

    # ------------------------------------------------------------------
    # Screenshot helper
    # ------------------------------------------------------------------

    def _maybe_screenshot(self) -> None:
        """Save a screenshot every SCREENSHOT_INTERVAL frames."""
        if not self.screenshots:
            return
        if self._frame_count - self._last_screenshot_frame >= SCREENSHOT_INTERVAL:
            fname = os.path.join(
                self.screenshot_dir,
                f"frame_{self._frame_count:08d}.png",
            )
            try:
                self.emulator.save_screenshot(fname)
                log.debug("Screenshot saved: %s", fname)
            except Exception as exc:
                log.warning("Screenshot failed: %s", exc)
            self._last_screenshot_frame = self._frame_count

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self, max_steps: Optional[int] = None) -> None:
        """
        Main bot loop.

        Each iteration:
          1. Update game state from memory
          2. If in battle → run BattleAI for one turn
          3. Else if party needs healing → go to Pokecenter
          4. Else → run ProgressionManager's next step
          5. Tick one frame
          6. Optionally save a screenshot

        Parameters
        ----------
        max_steps : int | None
            Maximum number of loop iterations.  None = run forever.
        """
        if not self._running:
            raise RuntimeError("Bot not started — call start() or use as context manager.")

        log.info("Main loop starting (max_steps=%s)…", max_steps)
        step = 0

        while max_steps is None or step < max_steps:
            try:
                # 1. Refresh game state
                self.game_state.update()
                self._step_count += 1

                # 2. Battle handling
                if self.game_state.in_battle:
                    log.info(
                        "BATTLE [step=%d]: enemy_hp=%d/%d  player_hp=%d/%d",
                        step,
                        self.game_state.enemy_hp,
                        self.game_state.enemy_max_hp,
                        self.game_state.player_hp,
                        self.game_state.player_max_hp,
                    )
                    self.battle_ai.handle_battle_turn()

                # 3. Healing check
                elif self.game_state.needs_heal:
                    log.info(
                        "HEAL [step=%d]: party needs Pokecenter  map=%s",
                        step,
                        self.game_state.map_name,
                    )
                    try:
                        go_to_pokecenter(self.navigator, self.game_state)
                    except Exception as exc:
                        log.error("go_to_pokecenter error: %s", exc)

                # 4. Progression
                else:
                    current_step = self.progression.get_current_step()
                    log.info(
                        "PROGRESS [step=%d]: map=%s  pos=(%d,%d)  badges=%d  next_step=%s",
                        step,
                        self.game_state.map_name,
                        self.game_state.player_x,
                        self.game_state.player_y,
                        self.game_state.badge_count,
                        current_step,
                    )

                    if current_step == "game_complete":
                        log.info("🎉 GAME COMPLETE after %d steps!", step)
                        break

                    try:
                        self.progression.run_next_step()
                    except Exception as exc:
                        log.error("Progression error at step '%s': %s", current_step, exc)

                # 5. Tick
                self.emulator.tick(1)
                self._frame_count += 1

                # 6. Screenshot
                self._maybe_screenshot()

                step += 1

            except KeyboardInterrupt:
                log.info("KeyboardInterrupt — stopping bot.")
                break
            except Exception as exc:
                log.exception("Unexpected error at step %d: %s", step, exc)
                # Brief pause to avoid spinning on repeated errors
                self.emulator.tick(30)
                step += 1

        log.info("Main loop ended after %d steps.", step)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pokemon Blue Autobot — plays through the game automatically.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--rom",
        default=DEFAULT_ROM,
        help="Path to the Pokemon Blue .gb ROM file.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run without display window (default: True).",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Run with display window (SDL2).",
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=0,
        metavar="N",
        help="Emulation speed multiplier (0=unlimited, 1=normal).",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        default=False,
        help="Save screenshots every 300 frames.",
    )
    parser.add_argument(
        "--screenshot-dir",
        default=DEFAULT_SCREENSHOT_DIR,
        help="Directory for screenshots.",
    )
    parser.add_argument(
        "--log",
        default="INFO",
        metavar="LEVEL",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--log-file",
        default="pokemon_bot.log",
        help="Log file path.",
    )
    parser.add_argument(
        "--save-state",
        default=None,
        metavar="PATH",
        help="Path to load/save emulator state (.state file).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        metavar="N",
        help="Stop after N loop iterations (default: run forever).",
    )
    parser.add_argument(
        "--step",
        default=None,
        metavar="STEP_NAME",
        help="Override and run a specific progression step only.",
    )

    args = parser.parse_args()

    # Configure logging before anything else
    setup_logging(args.log, args.log_file)

    log.info("=== Pokemon Blue Autobot ===")
    log.info("ROM: %s", args.rom)
    log.info("Headless: %s  Speed: %s  Screenshots: %s", args.headless, args.speed, args.screenshots)

    bot = PokemonBot(
        rom_path=args.rom,
        headless=args.headless,
        speed=args.speed,
        screenshot_dir=args.screenshot_dir,
        log_level=args.log,
        save_state_path=args.save_state,
        screenshots=args.screenshots,
    )

    with bot:
        if args.step:
            # Run a single progression step for debugging
            log.info("Running single step: %s", args.step)
            bot.game_state.update()
            bot.progression.state["step"] = args.step
            bot.progression.run_next_step()
        else:
            bot.run(max_steps=args.max_steps)


if __name__ == "__main__":
    main()
