"""
TinMan heartbeat logger.
Appends structured JSON lines to a rotating log file.
"""

import json
from pathlib import Path

from .config import TinManConfig


class HeartbeatLogger:
    def __init__(self, config: TinManConfig):
        self.config = config
        self.log_path = Path(config.log_file).expanduser()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, result: dict):
        if not self.config.log_heartbeats:
            return

        # Append JSON line
        with open(self.log_path, "a") as f:
            f.write(json.dumps(result) + "\n")

        self._rotate_if_needed()

    def _rotate_if_needed(self):
        """Keep log under max_log_lines by trimming oldest entries."""
        try:
            lines = self.log_path.read_text().splitlines(keepends=True)
            if len(lines) > self.config.max_log_lines:
                keep = lines[-self.config.max_log_lines:]
                self.log_path.write_text("".join(keep))
        except Exception:
            pass  # log rotation is best-effort, never crash the main loop

    def tail(self, n: int = 20) -> list[dict]:
        """Return last n log entries as dicts."""
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text().splitlines()
        entries = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries
