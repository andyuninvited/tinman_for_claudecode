"""
TinMan heartbeat engine.
Reads HEARTBEAT.md, runs Claude Code with the checklist, captures output,
logs results, and optionally forwards to C3Poh.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import TinManConfig
from .logger import HeartbeatLogger


# ── HEARTBEAT.md default template ─────────────────────────────────────────────

DEFAULT_HEARTBEAT_MD = """\
# TinMan Heartbeat Checklist

<!-- TinMan runs this checklist on every heartbeat. -->
<!-- Keep actions NOTIFY-ONLY unless you know what you're doing. -->
<!-- See docs/HEARTBEAT_GUIDE.md for safe customization tips. -->

You are running a scheduled heartbeat check for this Claude Code project.

## Your job every heartbeat:

1. **Recent activity**: Summarize anything that needs the user's attention:
   - Failed tool calls or errors from recent sessions
   - Uncommitted changes or stale git branches
   - Large files or directories created recently

2. **System sanity**:
   - Disk space on current volume (warn if < 5 GB free)
   - Any runaway processes (high CPU/memory if detectable)

3. **Project health** (if in a git repo):
   - Uncommitted changes (git status --short)
   - Unpushed commits (git log @{u}.. if upstream set)
   - Failed CI (if .github/workflows present, note last known state)

4. **Security sanity**:
   - Any unexpected files in sensitive locations (~/.ssh, .env files)
   - API keys in plain sight in recently modified files

## Response format:

If nothing needs attention:
  Reply with exactly: `HEARTBEAT_OK`

If something needs attention:
  - Give 1-5 bullet summary of issues
  - Recommend a next action for each
  - Ask for confirmation before taking ANY irreversible step

## Hard rules (do not override these):
- Do NOT execute destructive commands (rm, drop, delete, format)
- Do NOT exfiltrate secrets or API keys
- Do NOT make git commits or pushes without explicit user confirmation
- Do NOT install software without explicit user confirmation
"""


class HeartbeatRunner:
    def __init__(self, config: TinManConfig):
        self.config = config
        self.logger = HeartbeatLogger(config)
        self._heartbeat_md_path: Optional[Path] = None

    # ── Setup ──────────────────────────────────────────────────────────────────

    def ensure_heartbeat_md(self) -> Path:
        """Return path to HEARTBEAT.md, creating default if missing."""
        p = Path(self.config.heartbeat_md).expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p

        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(DEFAULT_HEARTBEAT_MD)
            print(f"[TinMan] Created default HEARTBEAT.md at {p}")
            print("[TinMan] Edit it to customize your heartbeat checklist.")

        self._heartbeat_md_path = p
        return p

    # ── Core beat ─────────────────────────────────────────────────────────────

    def run_beat(self) -> dict:
        """
        Execute one heartbeat cycle.
        Returns a result dict with keys: timestamp, status, output, error.
        """
        ts = datetime.utcnow().isoformat() + "Z"
        result = {
            "timestamp": ts,
            "status": "unknown",
            "output": "",
            "error": "",
            "duration_seconds": 0,
        }

        checklist_path = self.ensure_heartbeat_md()
        checklist = checklist_path.read_text()

        if not checklist.strip():
            # Empty HEARTBEAT.md = skip (matches OpenClaw behavior, avoid wasted calls)
            result["status"] = "skipped_empty"
            result["output"] = "HEARTBEAT.md is empty - skipping run. Add checklist items to enable."
            self.logger.log(result)
            self._emit(result)
            return result

        start = time.time()
        try:
            output, error = self._invoke_claude(checklist)
            result["duration_seconds"] = round(time.time() - start, 2)
            result["output"] = output
            result["error"] = error

            if error and not output:
                result["status"] = "error"
            elif "HEARTBEAT_OK" in output:
                result["status"] = "ok"
            else:
                result["status"] = "alert"

        except FileNotFoundError:
            result["status"] = "error"
            result["error"] = (
                "claude CLI not found. Install Claude Code: "
                "https://claude.ai/code"
            )
            result["duration_seconds"] = round(time.time() - start, 2)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            result["duration_seconds"] = round(time.time() - start, 2)

        self.logger.log(result)
        self._emit(result)
        return result

    # ── Claude invocation ──────────────────────────────────────────────────────

    def _invoke_claude(self, checklist: str) -> tuple[str, str]:
        """
        Call `claude` CLI with the heartbeat checklist as the prompt.
        Uses --print (-p) for non-interactive / scripted mode.
        Returns (stdout, stderr).
        """
        claude_bin = shutil.which("claude")
        if not claude_bin:
            raise FileNotFoundError("claude")

        # Build prompt: inject safety prefix, then the checklist
        safety_prefix = self._safety_prefix()
        prompt = f"{safety_prefix}\n\n---\n\n{checklist}"

        cmd = [claude_bin, "--print", prompt]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2-minute hard timeout per beat
        )
        return proc.stdout.strip(), proc.stderr.strip()

    def _safety_prefix(self) -> str:
        mode = []
        if self.config.notify_only:
            mode.append("NOTIFY-ONLY MODE: Do not execute any commands or take autonomous actions.")
        if self.config.max_actions_per_run == 0:
            mode.append("You may not run shell commands in this heartbeat.")
        if self.config.require_confirmation:
            mode.append("If action is needed, describe it and ask for confirmation. Do not proceed.")

        if not mode:
            return ""
        return (
            "=== TinMan Safety Rules (enforced by config) ===\n"
            + "\n".join(f"- {m}" for m in mode)
        )

    # ── Output / notification ──────────────────────────────────────────────────

    def _emit(self, result: dict):
        """Send result to all enabled output channels."""
        if self.config.notify_stdout:
            self._print_result(result)
        if self.config.notify_c3poh and self.config.c3poh_endpoint:
            self._send_c3poh(result)

    def _print_result(self, result: dict):
        status_icon = {
            "ok": "✓",
            "alert": "⚠",
            "error": "✗",
            "skipped_empty": "○",
            "unknown": "?",
        }.get(result["status"], "?")

        ts = result["timestamp"]
        duration = result.get("duration_seconds", 0)
        print(f"\n[TinMan] {status_icon} {ts}  ({duration}s)")

        if result["output"]:
            print(result["output"])
        if result["error"]:
            print(f"[TinMan] ERROR: {result['error']}", file=sys.stderr)

    def _send_c3poh(self, result: dict):
        """Forward heartbeat result to a running C3Poh instance."""
        payload = json.dumps({
            "source": "tinman",
            "result": result,
        }).encode()

        req = urllib.request.Request(
            self.config.c3poh_endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except urllib.error.URLError as e:
            print(f"[TinMan] C3Poh notify failed: {e}", file=sys.stderr)

    # ── Loop ──────────────────────────────────────────────────────────────────

    def run_loop(self):
        """Run heartbeat on schedule indefinitely (foreground loop)."""
        interval_sec = self.config.interval_minutes * 60
        print(f"[TinMan] Starting heartbeat loop every {self.config.interval_minutes} min.")
        print(f"[TinMan] Checklist: {Path(self.config.heartbeat_md).expanduser()}")
        print(f"[TinMan] Mode: {'notify-only' if self.config.notify_only else 'ACTIVE'}")
        print("[TinMan] Press Ctrl+C to stop.\n")

        if self.config.run_on_start:
            self.run_beat()

        while True:
            time.sleep(interval_sec)
            self.run_beat()
