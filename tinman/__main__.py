"""
TinMan CLI entry point.
Usage: python -m tinman [command] [options]
       tinman [command] [options]  (after pip install)
"""

import argparse
import json
import sys
from pathlib import Path

from .config import TinManConfig, PRESETS
from .heartbeat import HeartbeatRunner
from .scheduler import Scheduler


def cmd_run(args, config: TinManConfig):
    runner = HeartbeatRunner(config)
    if args.loop:
        runner.run_loop()
    else:
        result = runner.run_beat()
        sys.exit(0 if result["status"] in ("ok", "skipped_empty") else 1)


def cmd_install(args, config: TinManConfig):
    config_path = args.config or str(Path.home() / ".tinman" / "config.json")
    saved = config.save(config_path)
    print(f"[TinMan] Config saved to {saved}")

    sched = Scheduler(config_path=config_path)
    ok = sched.install()
    if ok:
        print(f"[TinMan] Heartbeat scheduler installed ({sched.system}).")
        print(f"[TinMan] Interval: every {config.interval_minutes} min.")
        print(f"[TinMan] Mode: {'notify-only' if config.notify_only else 'ACTIVE (can run commands)'}")
    else:
        print("[TinMan] Scheduler install failed. Run manually: tinman run --loop")
        sys.exit(1)


def cmd_uninstall(args, config: TinManConfig):
    config_path = args.config or str(Path.home() / ".tinman" / "config.json")
    sched = Scheduler(config_path=config_path)
    ok = sched.uninstall()
    if ok:
        print("[TinMan] Heartbeat scheduler removed.")
    else:
        print("[TinMan] Nothing to remove (or removal failed).")


def cmd_status(args, config: TinManConfig):
    config_path = args.config or str(Path.home() / ".tinman" / "config.json")
    sched = Scheduler(config_path=config_path)
    print(f"[TinMan] Scheduler: {sched.status()}")
    print(f"[TinMan] Interval: {config.interval_minutes} min")
    print(f"[TinMan] Mode: {'notify-only' if config.notify_only else 'ACTIVE'}")
    print(f"[TinMan] Preset: {config.preset}")

    log_path = Path(config.log_file).expanduser()
    if log_path.exists():
        from .logger import HeartbeatLogger
        logger = HeartbeatLogger(config)
        entries = logger.tail(5)
        if entries:
            print("\n[TinMan] Last 5 heartbeats:")
            for e in entries:
                icon = {"ok": "✓", "alert": "⚠", "error": "✗"}.get(e.get("status", ""), "?")
                print(f"  {icon} {e.get('timestamp', '?')}  status={e.get('status')}  {e.get('duration_seconds', 0)}s")
    else:
        print("[TinMan] No heartbeat log found yet.")


def cmd_logs(args, config: TinManConfig):
    from .logger import HeartbeatLogger
    logger = HeartbeatLogger(config)
    n = args.n or 20
    entries = logger.tail(n)
    if not entries:
        print("[TinMan] No log entries found.")
        return
    for e in entries:
        print(json.dumps(e))


def cmd_init(args, config: TinManConfig):
    """Interactive first-time setup."""
    print("\n╔══════════════════════════════════╗")
    print("║  TinMan Setup - Give CC a Heart  ║")
    print("╚══════════════════════════════════╝\n")

    print("Security preset:")
    print("  sane     - notify-only, 30min interval (recommended)")
    print("  paranoid - notify-only, 15min interval, max logging")
    print("  chaos    - active mode, 5min interval (you've been warned)\n")

    preset = input("Preset [sane]: ").strip().lower() or "sane"
    if preset not in PRESETS:
        print(f"Unknown preset '{preset}', using 'sane'.")
        preset = "sane"

    interval_default = PRESETS[preset]["interval_minutes"]
    interval_str = input(f"Heartbeat interval in minutes [{interval_default}]: ").strip()
    interval = int(interval_str) if interval_str.isdigit() else interval_default

    cfg = TinManConfig.from_dict({**PRESETS[preset], "preset": preset, "interval_minutes": interval})

    config_path = str(Path.home() / ".tinman" / "config.json")
    saved = cfg.save(config_path)
    print(f"\n[TinMan] Config written to {saved}")

    # Create HEARTBEAT.md
    runner = HeartbeatRunner(cfg)
    md_path = runner.ensure_heartbeat_md()
    print(f"[TinMan] Heartbeat checklist at {md_path}")

    install = input("\nInstall heartbeat scheduler now? [Y/n]: ").strip().lower()
    if install != "n":
        sched = Scheduler(config_path=config_path)
        ok = sched.install()
        if ok:
            print(f"[TinMan] Done! Heartbeat will run every {interval} min.")
        else:
            print("[TinMan] Scheduler failed. Run: tinman run --loop")
    else:
        print("[TinMan] Run manually: tinman run --loop")
        print("[TinMan] Or install later: tinman install")

    print("\n[TinMan] Edit your checklist anytime:")
    print(f"  open {md_path}\n")


def main():
    parser = argparse.ArgumentParser(
        prog="tinman",
        description="TinMan - Heartbeat for Claude Code. Give your agent a heart.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
commands:
  init        Interactive first-time setup (start here)
  run         Run one heartbeat (or --loop for continuous)
  install     Install as background scheduler (launchd/cron)
  uninstall   Remove background scheduler
  status      Show scheduler and recent heartbeat status
  logs        Print recent heartbeat log entries

examples:
  tinman init
  tinman run --once
  tinman run --loop
  tinman install --preset paranoid
  tinman status
  tinman logs --n 10
        """,
    )
    parser.add_argument("--config", "-c", help="Path to config JSON file")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    sub = parser.add_subparsers(dest="command")

    # run
    p_run = sub.add_parser("run", help="Run heartbeat")
    p_run.add_argument("--once", action="store_true", help="Run once and exit (alias for no --loop)")
    p_run.add_argument("--loop", action="store_true", help="Run continuously on interval")
    p_run.add_argument("--preset", choices=list(PRESETS), help="Security preset")

    # install
    p_install = sub.add_parser("install", help="Install as system scheduler")
    p_install.add_argument("--preset", choices=list(PRESETS), default="sane")

    # uninstall
    sub.add_parser("uninstall", help="Remove system scheduler")

    # status
    sub.add_parser("status", help="Show TinMan status")

    # logs
    p_logs = sub.add_parser("logs", help="Show recent heartbeat logs")
    p_logs.add_argument("--n", type=int, default=20, help="Number of entries to show")

    # init
    sub.add_parser("init", help="Interactive first-time setup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Load config
    config = TinManConfig.load(args.config)

    # Apply CLI preset override
    if hasattr(args, "preset") and args.preset:
        from .config import PRESETS
        config = TinManConfig.from_dict({**PRESETS[args.preset], "preset": args.preset})

    dispatch = {
        "run": cmd_run,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "status": cmd_status,
        "logs": cmd_logs,
        "init": cmd_init,
    }
    dispatch[args.command](args, config)


if __name__ == "__main__":
    main()
