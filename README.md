# 🤖❤️ TinMan — Heartbeat for Claude Code

> *"If I only had a heart…"*
> The Tin Man wanted a heart. Now Claude Code has one.

**TinMan** adds a proactive heartbeat to your [Claude Code](https://claude.ai/code) setup. Instead of waiting for you to ask, Claude runs a scheduled health check and tells you when something needs attention — disk space, uncommitted code, stale branches, failed tool calls, whatever you care about.

Zero external dependencies. Works on macOS and Linux. Takes 2 minutes to set up.

---

## Why this exists

OpenClaw ships a built-in `heartbeat` feature that lets an AI agent proactively check in with you on a schedule. Claude Code doesn't have that — it waits for you to initiate.

TinMan fills that gap. It's a lightweight scheduler that:
1. Runs your **HEARTBEAT.md** checklist through Claude Code on a timer
2. Prints (or forwards) the result
3. Logs everything
4. Stays safely in **notify-only mode** by default — Claude tells you what's wrong, it doesn't fix things without asking

---

## Install

**One-liner:**
```bash
curl -fsSL https://raw.githubusercontent.com/andyuninvited/tinman_for_claudecode/main/install.sh | bash
```

**Or pip:**
```bash
pip install tinman-for-claudecode
```

**Requirements:**
- Python 3.9+
- [Claude Code](https://claude.ai/code) (`claude` CLI in your PATH)
- macOS or Linux

---

## Quick start

```bash
tinman init        # interactive setup (choose preset, set interval, install scheduler)
```

That's it. TinMan will:
- Create a `HEARTBEAT.md` checklist in your project (edit it to customize)
- Install a background scheduler (launchd on macOS, cron on Linux)
- Run the first heartbeat immediately

---

## Commands

```
tinman init                   Interactive first-time setup
tinman run --once             Run one heartbeat right now
tinman run --loop             Run continuously (foreground)
tinman install                Install as background scheduler
tinman install --preset paranoid
tinman uninstall              Remove scheduler
tinman status                 Show scheduler + recent results
tinman logs                   Print recent heartbeat log
tinman logs --n 50            Print last 50 entries
```

---

## Security presets

TinMan ships with three modes. Pick the one that matches your comfort level.

| Preset | Interval | Mode | Use when |
|--------|----------|------|----------|
| `sane` | 30 min | notify-only | **default** — Claude tells, never acts |
| `paranoid` | 15 min | notify-only | Extra visibility, max logging |
| `chaos` | 5 min | active | You trust Claude to take action. You've been warned ⚠️ |

```bash
tinman install --preset sane       # recommended for most people
tinman install --preset paranoid   # tighter, more frequent
tinman install --preset chaos      # Claude can act autonomously
```

> **OpenClaw users:** The default `sane` preset matches the OpenClaw pattern of `showOk: false, showAlerts: true`. TinMan is `notify-only` by default — OpenClaw users often get burned by leaving defaults that allow autonomous actions. Don't be that person.

---

## Customize your HEARTBEAT.md

TinMan creates a default `HEARTBEAT.md` when you run `tinman init`. Edit it to make the heartbeat yours:

```markdown
# My Project Heartbeat

Every heartbeat, check:
1. Any failing tests? (run pytest --co -q and report)
2. Uncommitted changes older than 24h?
3. Any TODO comments I added recently?
4. Disk space on my main volume?

If nothing needs attention: reply HEARTBEAT_OK
If something needs attention: 1-3 bullets + recommended action
Never take irreversible steps without asking me first.
```

**Hard rules baked into every run (cannot be overridden from HEARTBEAT.md):**
- No destructive commands (rm, drop, delete)
- No secret exfiltration
- No git commits/pushes without confirmation
- No software installs without confirmation

---

## Configuration

TinMan looks for config at `./tinman.json` then `~/.tinman/config.json`.

```json
{
  "preset": "sane",
  "interval_minutes": 30,
  "notify_only": true,
  "heartbeat_md": "HEARTBEAT.md",
  "log_file": "~/.tinman/heartbeat.log",
  "notify_c3poh": false,
  "c3poh_endpoint": ""
}
```

**Environment variable overrides** (useful for CI/containers):
```bash
TINMAN_INTERVAL_MINUTES=15
TINMAN_NOTIFY_ONLY=true
TINMAN_HEARTBEAT_MD=/path/to/HEARTBEAT.md
TINMAN_C3POH_ENDPOINT=http://localhost:7734/notify
```

---

## C3Poh integration

Want TinMan to send heartbeat alerts to your **Telegram** (or Slack/Discord)? Pair it with [C3Poh](https://github.com/andyuninvited/c3poh_for_claudecode):

```json
{
  "notify_c3poh": true,
  "c3poh_endpoint": "http://localhost:7734/notify"
}
```

TinMan → C3Poh → your phone. Done.

---

## How it works

```
[launchd/cron] every N minutes
      ↓
[tinman run --once]
      ↓
reads HEARTBEAT.md
      ↓
claude --print "[safety prefix]\n\n[checklist]"
      ↓
captures output
      ↓
logs result to ~/.tinman/heartbeat.log
      ↓
prints to stdout (+ C3Poh if configured)
```

No daemons. No servers. No Docker. Just Claude + a scheduler.

---

## Why not just use a cron job with a raw prompt?

You could! TinMan adds:
- **Safety rails** — enforced prefix that prevents risky actions in notify-only mode
- **Preset system** — sane/paranoid/chaos in one flag, not manual config editing
- **Log rotation** — keeps log files sane
- **C3Poh integration** — forwards alerts to messaging
- **Status command** — `tinman status` shows you exactly what's running and last N results
- **Empty HEARTBEAT.md detection** — matches OpenClaw behavior, avoids wasted API calls

---

## Run tests

```bash
pip install tinman-for-claudecode[dev]
pytest tests/ -v
```

---

## Roadmap

- [ ] v0.2: Web dashboard (local-only) to view heartbeat history
- [ ] v0.2: Slack and Discord output (via C3Poh)
- [ ] v0.3: Per-project heartbeat config (`.tinman.json` in project root)
- [ ] v0.3: GitHub Actions heartbeat mode
- [ ] v1.0: Windows support

---

## Related

- [C3Poh](https://github.com/andyuninvited/c3poh_for_claudecode) — Telegram/Slack/Discord bridge for Claude Code (the comms to TinMan's heart)
- [Claude Code](https://claude.ai/code) — the agentic CLI this is built for
- [OpenClaw](https://openclaw.ai) — the inspiration (heartbeat + messaging for a different runtime)

---

## License

GNU GPLv3 — copy-left, and let's evolve together.

See [LICENSE](LICENSE) for the full text.

---

*Built by [@andyuninvited](https://github.com/andyuninvited). Star the repo if TinMan saved you from a bad day.*
