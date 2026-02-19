"""
TinMan scheduler - macOS (launchd) and Linux (cron) integration.
Installs/uninstalls TinMan as a system-level background job.
"""

import os
import platform
import subprocess
import sys
import textwrap
from pathlib import Path


class Scheduler:
    def __init__(self, config_path: str = ""):
        self.system = platform.system()
        self.config_path = config_path or str(Path.home() / ".tinman" / "config.json")
        self.tinman_bin = self._find_tinman()

    def _find_tinman(self) -> str:
        """Find the tinman CLI entry point."""
        # Prefer the installed script
        for candidate in ["tinman", "python3 -m tinman"]:
            if candidate.startswith("python"):
                return candidate
            path = Path(sys.prefix) / "bin" / candidate
            if path.exists():
                return str(path)
        return "python3 -m tinman"

    # ── macOS launchd ─────────────────────────────────────────────────────────

    @property
    def _plist_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / "com.tinman.heartbeat.plist"

    def _interval_minutes(self) -> int:
        """Read interval from config file (default 30)."""
        try:
            import json
            with open(self.config_path) as f:
                return int(json.load(f).get("interval_minutes", 30))
        except Exception:
            return 30

    def install_macos(self) -> bool:
        interval_sec = self._interval_minutes() * 60
        log_dir = Path.home() / ".tinman"
        log_dir.mkdir(parents=True, exist_ok=True)

        plist = textwrap.dedent(f"""\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
              "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
              <key>Label</key>
              <string>com.tinman.heartbeat</string>
              <key>ProgramArguments</key>
              <array>
                <string>{sys.executable}</string>
                <string>-m</string>
                <string>tinman</string>
                <string>run</string>
                <string>--config</string>
                <string>{self.config_path}</string>
                <string>--once</string>
              </array>
              <key>StartInterval</key>
              <integer>{interval_sec}</integer>
              <key>RunAtLoad</key>
              <true/>
              <key>StandardOutPath</key>
              <string>{log_dir}/launchd.out.log</string>
              <key>StandardErrorPath</key>
              <string>{log_dir}/launchd.err.log</string>
              <key>KeepAlive</key>
              <false/>
            </dict>
            </plist>
        """)

        self._plist_path.parent.mkdir(parents=True, exist_ok=True)
        self._plist_path.write_text(plist)

        # Unload first (in case already installed), then load
        subprocess.run(
            ["launchctl", "unload", str(self._plist_path)],
            capture_output=True,
        )
        result = subprocess.run(
            ["launchctl", "load", str(self._plist_path)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def uninstall_macos(self) -> bool:
        if not self._plist_path.exists():
            return True
        subprocess.run(
            ["launchctl", "unload", str(self._plist_path)],
            capture_output=True,
        )
        self._plist_path.unlink(missing_ok=True)
        return True

    def status_macos(self) -> str:
        result = subprocess.run(
            ["launchctl", "list", "com.tinman.heartbeat"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return f"installed (launchd)\n{result.stdout.strip()}"
        return "not installed"

    # ── Linux cron ────────────────────────────────────────────────────────────

    def install_linux(self) -> bool:
        interval = self._interval_minutes()
        # Convert minutes to cron expression
        if interval == 60:
            cron_expr = "0 * * * *"
        elif 60 % interval == 0:
            cron_expr = f"*/{interval} * * * *"
        else:
            cron_expr = f"*/{interval} * * * *"

        marker = "# tinman-heartbeat"
        new_line = (
            f"{cron_expr} {sys.executable} -m tinman run "
            f"--config {self.config_path} --once  {marker}"
        )

        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""

        # Remove old tinman lines, add new
        lines = [l for l in existing.splitlines() if marker not in l]
        lines.append(new_line)
        new_crontab = "\n".join(lines) + "\n"

        proc = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            capture_output=True,
        )
        return proc.returncode == 0

    def uninstall_linux(self) -> bool:
        marker = "# tinman-heartbeat"
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode != 0:
            return True
        lines = [l for l in result.stdout.splitlines() if marker not in l]
        new_crontab = "\n".join(lines) + "\n"
        proc = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            capture_output=True,
        )
        return proc.returncode == 0

    # ── Platform-agnostic API ─────────────────────────────────────────────────

    def install(self) -> bool:
        if self.system == "Darwin":
            return self.install_macos()
        elif self.system == "Linux":
            return self.install_linux()
        else:
            print(f"[TinMan] Scheduler: unsupported platform '{self.system}'.")
            print("[TinMan] Run manually: tinman run --loop")
            return False

    def uninstall(self) -> bool:
        if self.system == "Darwin":
            return self.uninstall_macos()
        elif self.system == "Linux":
            return self.uninstall_linux()
        return False

    def status(self) -> str:
        if self.system == "Darwin":
            return self.status_macos()
        elif self.system == "Linux":
            marker = "# tinman-heartbeat"
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            if result.returncode == 0 and marker in result.stdout:
                return "installed (cron)"
            return "not installed"
        return "unknown platform"
