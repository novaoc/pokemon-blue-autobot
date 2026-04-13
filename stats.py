"""
stats.py — Stats tracking for Pokemon Blue Autobot.

Tracks battles won/lost, Pokemon caught, items used, steps taken,
and elapsed time. Persists to a JSON file between sessions.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

log = logging.getLogger("pokemon_bot")

DEFAULT_STATS_FILE = os.path.join(os.path.dirname(__file__), "bot_stats.json")


class StatsTracker:
    """
    Tracks gameplay statistics across sessions.

    Stats are persisted to a JSON file so they survive restarts.
    Call ``save()`` periodically or on shutdown to write to disk.
    """

    def __init__(self, stats_file: str = DEFAULT_STATS_FILE) -> None:
        self._file = stats_file
        self._start_time = time.monotonic()

        # Core counters
        self.battles_won: int = 0
        self.battles_lost: int = 0
        self.battles_fled: int = 0
        self.pokemon_caught: int = 0
        self.items_used: int = 0
        self.steps_taken: int = 0
        self.badges_earned: int = 0
        self.pokecenter_visits: int = 0
        self.total_damage_dealt: int = 0
        self.total_damage_taken: int = 0

        # Session tracking
        self.sessions: int = 0
        self.total_play_time_s: float = 0.0

        # Load existing stats
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load stats from the JSON file if it exists."""
        if not os.path.exists(self._file):
            self.sessions = 1
            log.info("StatsTracker: no existing stats file — starting fresh")
            return

        try:
            with open(self._file, "r") as f:
                data = json.load(f)
            self.battles_won = data.get("battles_won", 0)
            self.battles_lost = data.get("battles_lost", 0)
            self.battles_fled = data.get("battles_fled", 0)
            self.pokemon_caught = data.get("pokemon_caught", 0)
            self.items_used = data.get("items_used", 0)
            self.steps_taken = data.get("steps_taken", 0)
            self.badges_earned = data.get("badges_earned", 0)
            self.pokecenter_visits = data.get("pokecenter_visits", 0)
            self.total_damage_dealt = data.get("total_damage_dealt", 0)
            self.total_damage_taken = data.get("total_damage_taken", 0)
            self.sessions = data.get("sessions", 0) + 1
            self.total_play_time_s = data.get("total_play_time_s", 0.0)
            log.info("StatsTracker: loaded stats from %s (session %d)", self._file, self.sessions)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("StatsTracker: failed to load %s — %s", self._file, exc)
            self.sessions = 1

    def save(self) -> None:
        """Write current stats to the JSON file."""
        elapsed = time.monotonic() - self._start_time
        data = {
            "battles_won": self.battles_won,
            "battles_lost": self.battles_lost,
            "battles_fled": self.battles_fled,
            "pokemon_caught": self.pokemon_caught,
            "items_used": self.items_used,
            "steps_taken": self.steps_taken,
            "badges_earned": self.badges_earned,
            "pokecenter_visits": self.pokecenter_visits,
            "total_damage_dealt": self.total_damage_dealt,
            "total_damage_taken": self.total_damage_taken,
            "sessions": self.sessions,
            "total_play_time_s": self.total_play_time_s + elapsed,
            "last_saved": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._file)), exist_ok=True)
            with open(self._file, "w") as f:
                json.dump(data, f, indent=2)
            log.debug("StatsTracker: saved to %s", self._file)
        except OSError as exc:
            log.error("StatsTracker: failed to save — %s", exc)

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------

    def record_battle_won(self) -> None:
        self.battles_won += 1

    def record_battle_lost(self) -> None:
        self.battles_lost += 1

    def record_battle_fled(self) -> None:
        self.battles_fled += 1

    def record_pokemon_caught(self) -> None:
        self.pokemon_caught += 1

    def record_item_used(self) -> None:
        self.items_used += 1

    def record_step(self) -> None:
        self.steps_taken += 1

    def record_pokecenter_visit(self) -> None:
        self.pokecenter_visits += 1

    def record_damage_dealt(self, amount: int) -> None:
        self.total_damage_dealt += max(0, amount)

    def record_damage_taken(self, amount: int) -> None:
        self.total_damage_taken += max(0, amount)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @property
    def total_battles(self) -> int:
        return self.battles_won + self.battles_lost + self.battles_fled

    @property
    def win_rate(self) -> float:
        total = self.battles_won + self.battles_lost
        if total == 0:
            return 0.0
        return self.battles_won / total

    @property
    def session_elapsed_s(self) -> float:
        return time.monotonic() - self._start_time

    @property
    def total_play_time_display(self) -> str:
        total = self.total_play_time_s + self.session_elapsed_s
        hours, remainder = divmod(int(total), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable stats summary."""
        lines = [
            "=== Bot Stats ===",
            f"  Battles:  {self.total_battles} total — {self.battles_won} won, {self.battles_lost} lost, {self.battles_fled} fled",
            f"  Win rate: {self.win_rate:.0%}",
            f"  Caught:   {self.pokemon_caught} Pokemon",
            f"  Items:    {self.items_used} used",
            f"  Steps:    {self.steps_taken}",
            f"  Badges:   {self.badges_earned}",
            f"  Centers:  {self.pokecenter_visits} visits",
            f"  Damage:   dealt {self.total_damage_dealt} / taken {self.total_damage_taken}",
            f"  Play time: {self.total_play_time_display} (session {self.sessions})",
            "================",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.summary()
