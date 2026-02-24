"""
emulator.py - PokemonEmulator: thin wrapper around PyBoy 2.7.0

Provides a clean interface for the Pokemon Blue autobot:
  - headless / windowed startup
  - frame stepping
  - button input (press-and-release or manual)
  - memory reads
  - screenshot capture
  - save/load emulator state
"""

from __future__ import annotations

import io
import os
import warnings
from typing import Optional

# Suppress SDL2 / Cython noisy warnings at import time
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pyboy import PyBoy

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# Default ROM / save paths
DEFAULT_ROM  = "/Users/wren/nova/games/gb/blueEng.gb"
DEFAULT_SAVE = "/Users/wren/nova/games/gb/blueEng.sav"

# Buttons accepted by PyBoy 2.x
VALID_BUTTONS = {"up", "down", "left", "right", "a", "b", "start", "select"}


class PokemonEmulator:
    """
    Wraps PyBoy 2.7.0 for Pokemon Blue automation.

    Parameters
    ----------
    rom_path : str
        Path to the Game Boy ROM file.
    headless : bool
        If True (default), run without a display (window="null").
    speed : int
        Emulation speed multiplier.  0 = unlimited, 1 = normal.
    """

    def __init__(
        self,
        rom_path: str = DEFAULT_ROM,
        headless: bool = True,
        speed: int = 0,
    ) -> None:
        self.rom_path  = rom_path
        self.headless  = headless
        self.speed     = speed
        self._pyboy: Optional[PyBoy] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Initialize PyBoy and load the ROM.  Must be called before anything else."""
        window = "null" if self.headless else "SDL2"
        self._pyboy = PyBoy(self.rom_path, window=window)
        if self.speed != 1:
            self._pyboy.set_emulation_speed(self.speed)

    def stop(self) -> None:
        """Cleanly shut down PyBoy (flushes battery save, etc.)."""
        if self._pyboy is not None:
            self._pyboy.stop(save=False)  # We manage saves explicitly
            self._pyboy = None

    # Context-manager support so you can use `with PokemonEmulator() as emu:`
    def __enter__(self) -> "PokemonEmulator":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # Internal guard
    # ------------------------------------------------------------------

    @property
    def pyboy(self) -> PyBoy:
        if self._pyboy is None:
            raise RuntimeError("Emulator not started — call start() first.")
        return self._pyboy

    # ------------------------------------------------------------------
    # Frame stepping
    # ------------------------------------------------------------------

    def tick(self, frames: int = 1) -> None:
        """Advance the emulator by *frames* Game Boy frames (each ~16.7 ms)."""
        self.pyboy.tick(frames, render=True)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def press(self, button: str, frames: int = 10) -> None:
        """
        Press *button* for *frames* frames, then release automatically.

        The button string must be one of: up / down / left / right / a / b / start / select
        (case-insensitive).  After calling press(), the emulator advances *frames* ticks so
        the button hold registers in-game.
        """
        btn = button.lower()
        if btn not in VALID_BUTTONS:
            raise ValueError(f"Unknown button '{button}'. Valid: {VALID_BUTTONS}")
        # PyBoy.button(btn, delay) queues a release event after `delay` ticks
        self.pyboy.button(btn, delay=frames)
        # Advance the requested number of frames so the game sees the input
        self.tick(frames)

    def button_down(self, button: str) -> None:
        """Hold a button until button_up() is called."""
        self.pyboy.button_press(button.lower())

    def button_up(self, button: str) -> None:
        """Release a previously held button."""
        self.pyboy.button_release(button.lower())

    # ------------------------------------------------------------------
    # PyBoy-compatible proxy methods (used by Navigator / BattleAI)
    # These allow Navigator to call emu.button() / emu.button_release()
    # directly on the PokemonEmulator object.
    # ------------------------------------------------------------------

    def button(self, button: str, delay: int = 0) -> None:
        """
        Proxy for pyboy.button(). Presses and queues a release after *delay*
        ticks.  If delay == 0, just registers the press (caller must release).
        """
        btn = button.lower()
        if delay > 0:
            self.pyboy.button(btn, delay=delay)
        else:
            self.pyboy.button_press(btn)

    def button_release(self, button: str) -> None:
        """Proxy for pyboy.button_release(). Releases a held button."""
        self.pyboy.button_release(button.lower())

    # ------------------------------------------------------------------
    # Screen / Screenshot
    # ------------------------------------------------------------------

    def get_screen(self):
        """
        Return the current screen as a PIL Image (160 × 144, RGB).
        Requires Pillow to be installed.
        """
        return self.pyboy.screen.image.copy()

    def get_screen_array(self):
        """
        Return the current screen as a NumPy array.

        Shape: (144, 160, 4) — dtype uint8, RGBA channel order.
        Slicing: [row, col, channel]  e.g. ndarray[0, 0, :3] → first pixel RGB.
        """
        if not _HAS_NUMPY:
            raise ImportError("numpy is required for get_screen_array()")
        # PyBoy returns a read-only view backed by its internal buffer;
        # copy() makes it writable and stable beyond the next tick.
        return self.pyboy.screen.ndarray.copy()

    def save_screenshot(self, path: str) -> None:
        """
        Save the current screen to *path* as a PNG (or whatever Pillow infers
        from the extension).
        """
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        img = self.get_screen()
        img.save(path)

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def read_memory(self, addr: int) -> int:
        """Read one byte from Game Boy address *addr*."""
        return self.pyboy.memory[addr]

    def read_memory_range(self, addr: int, length: int) -> bytes:
        """Read *length* bytes starting at *addr* and return as bytes."""
        return bytes(self.pyboy.memory[addr : addr + length])

    def write_memory(self, addr: int, value: int) -> None:
        """Write one byte to Game Boy address *addr* (use with care!)."""
        self.pyboy.memory[addr] = value

    # ------------------------------------------------------------------
    # Save / Load emulator state
    # ------------------------------------------------------------------

    def save_state(self, path: str) -> None:
        """
        Save the full emulator state to *path*.

        This is a PyBoy save-state (not a Game Boy battery save / .sav file).
        """
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "wb") as f:
            self.pyboy.save_state(f)

    def load_state(self, path: str) -> None:
        """Load a previously saved emulator state from *path*."""
        with open(path, "rb") as f:
            self.pyboy.load_state(f)

    def save_state_memory(self) -> bytes:
        """Save emulator state into memory and return as bytes (useful for rollbacks)."""
        buf = io.BytesIO()
        self.pyboy.save_state(buf)
        return buf.getvalue()

    def load_state_memory(self, data: bytes) -> None:
        """Restore emulator state from a bytes object produced by save_state_memory()."""
        buf = io.BytesIO(data)
        self.pyboy.load_state(buf)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def frame_count(self) -> int:
        """Total number of ticks processed since start()."""
        return self.pyboy.frame_count

    def __repr__(self) -> str:
        status = "running" if self._pyboy else "stopped"
        return (
            f"<PokemonEmulator rom={os.path.basename(self.rom_path)!r} "
            f"headless={self.headless} status={status}>"
        )
