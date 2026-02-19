"""
TinMan configuration management.
Reads from tinman.json, env vars, and CLI flags.
Supports three security presets: sane (default), paranoid, chaos.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── Security presets ──────────────────────────────────────────────────────────

PRESET_SANE = {
    "interval_minutes": 30,
    "notify_only": True,
    "max_actions_per_run": 0,          # 0 = no autonomous actions
    "require_confirmation": True,
    "log_heartbeats": True,
    "max_log_lines": 1000,
    "run_on_start": True,
}

PRESET_PARANOID = {
    "interval_minutes": 15,
    "notify_only": True,
    "max_actions_per_run": 0,
    "require_confirmation": True,
    "log_heartbeats": True,
    "max_log_lines": 5000,
    "run_on_start": True,
    "allowed_commands": [],            # empty = no shell commands allowed
    "block_internet_checks": False,    # still checks, just won't browse
}

PRESET_CHAOS = {
    "interval_minutes": 5,
    "notify_only": False,
    "max_actions_per_run": 10,
    "require_confirmation": False,
    "log_heartbeats": True,
    "max_log_lines": 10000,
    "run_on_start": True,
    # ⚠️  chaos mode: agent can take actions. You've been warned.
}

PRESETS = {
    "sane": PRESET_SANE,
    "paranoid": PRESET_PARANOID,
    "chaos": PRESET_CHAOS,
}


@dataclass
class TinManConfig:
    # Core timing
    interval_minutes: int = 30           # how often heartbeat runs
    run_on_start: bool = True            # run once immediately on launch

    # Safety rails (sane defaults)
    notify_only: bool = True             # True = heartbeat never executes actions
    max_actions_per_run: int = 0         # max autonomous actions per beat (0 = none)
    require_confirmation: bool = True    # prompt before any action

    # Logging
    log_heartbeats: bool = True
    log_file: str = "~/.tinman/heartbeat.log"
    max_log_lines: int = 1000

    # Notification output channels (c3poh integration)
    notify_stdout: bool = True           # always print to terminal
    notify_c3poh: bool = False           # set True + c3poh_endpoint to use C3Poh
    c3poh_endpoint: str = ""            # e.g. http://localhost:7734/notify

    # Heartbeat checklist file
    heartbeat_md: str = "HEARTBEAT.md"  # path to checklist (relative or absolute)

    # Allowed shell commands for non-notify-only mode
    allowed_commands: list = field(default_factory=list)

    # Preset name (informational)
    preset: str = "sane"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TinManConfig":
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "TinManConfig":
        """
        Load config with priority:
          1. CLI-provided path
          2. ./tinman.json
          3. ~/.tinman/config.json
          4. built-in sane defaults
        Then overlay env vars on top.
        """
        # Find config file
        search_paths = []
        if config_path:
            search_paths.append(Path(config_path).expanduser())
        search_paths.extend([
            Path("tinman.json"),
            Path.home() / ".tinman" / "config.json",
        ])

        data = dict(PRESET_SANE)  # start from sane defaults

        for p in search_paths:
            if p.exists():
                with open(p) as f:
                    file_data = json.load(f)
                # Apply preset first if specified
                preset_name = file_data.get("preset", "sane")
                if preset_name in PRESETS:
                    data.update(PRESETS[preset_name])
                data.update(file_data)
                break

        # Env var overrides (TINMAN_* prefix)
        env_map = {
            "TINMAN_INTERVAL_MINUTES": ("interval_minutes", int),
            "TINMAN_NOTIFY_ONLY": ("notify_only", lambda v: v.lower() in ("1", "true", "yes")),
            "TINMAN_LOG_FILE": ("log_file", str),
            "TINMAN_HEARTBEAT_MD": ("heartbeat_md", str),
            "TINMAN_C3POH_ENDPOINT": ("c3poh_endpoint", str),
            "TINMAN_NOTIFY_C3POH": ("notify_c3poh", lambda v: v.lower() in ("1", "true", "yes")),
        }
        for env_key, (field_name, cast) in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                data[field_name] = cast(val)

        return cls.from_dict(data)

    def save(self, path: Optional[str] = None) -> Path:
        """Write current config to JSON."""
        target = Path(path).expanduser() if path else Path.home() / ".tinman" / "config.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return target
