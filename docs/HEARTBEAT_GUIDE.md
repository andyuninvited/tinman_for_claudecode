# HEARTBEAT.md Customization Guide

TinMan runs your `HEARTBEAT.md` file as a prompt to Claude Code on every scheduled heartbeat. This guide explains how to write a good one.

---

## The golden rule

**Write your HEARTBEAT.md like you're leaving instructions for a careful, cautious assistant who will check in while you're away — not like you're writing a script for an autonomous robot.**

The best heartbeats are:
- Short (10-20 lines)
- Specific (tell Claude what to check, not what to do)
- Notify-only (describe → report → ask, never act unilaterally)

---

## Anatomy of a good HEARTBEAT.md

```markdown
# My Project Heartbeat

## Check every run:
1. [specific thing to check]
2. [another thing]
3. [etc.]

## Response format:
- Nothing urgent: reply exactly `HEARTBEAT_OK`
- Something needs attention: 1-5 bullets + recommended action per item
- Always ask before taking any irreversible action
```

---

## Examples

### Minimal / safe
```markdown
# Heartbeat

1. Any uncommitted changes? (git status --short)
2. Disk space below 5 GB? (df -h)

Nothing urgent: HEARTBEAT_OK
Something found: 1-3 bullets, ask before acting.
```

### Developer project
```markdown
# Dev Project Heartbeat

1. Uncommitted changes older than 24h in this repo
2. Failing tests (run pytest --co -q, just list failures, don't fix)
3. TODO/FIXME comments added since last commit
4. Any .env files accidentally committed (git log --all --full-history -- "**/.env")
5. Disk free on current volume (warn if < 10 GB)

Format: HEARTBEAT_OK if clean. Otherwise bullets + ask before acting.
Never run destructive commands. Never commit or push without asking.
```

### System ops
```markdown
# System Heartbeat

1. High CPU/memory processes (ps aux sorted by CPU, top 5)
2. Disk space (df -h, flag if any volume > 90% used)
3. Any crashed Docker containers (docker ps -a --filter status=exited)
4. Log errors in /var/log/syslog in the last hour

Report only. Do not restart services or kill processes without asking.
HEARTBEAT_OK if nothing needs attention.
```

### AI project monitoring
```markdown
# AI Project Heartbeat

1. Any failed Supabase edge function deployments (check supabase/functions/*.log if present)
2. .env files present in committed code (security check)
3. Stale branches (git branch --sort=-committerdate | head -10)
4. Any TODO items in the codebase related to "auth" or "payments"

Summarize any findings. Ask before modifying anything. HEARTBEAT_OK if clear.
```

---

## What NOT to put in HEARTBEAT.md

❌ Commands that delete or modify files without asking
❌ `git commit`, `git push`, `git reset` without confirmation
❌ `pip install`, `npm install` without asking
❌ Sending messages or emails
❌ Anything that touches credentials or secrets

TinMan's safety prefix enforces these in `sane` and `paranoid` modes regardless. In `chaos` mode, you're on your own.

---

## Empty file behavior

If your `HEARTBEAT.md` is empty or contains only whitespace/headers, TinMan skips the API call entirely and logs `skipped_empty`. This matches OpenClaw's behavior and avoids wasted API calls.

**Don't leave it empty if you want heartbeats to run.** TinMan creates a default if it's missing, but won't overwrite your empty file.

---

## Tips for non-devs

- You don't need to know code to write a good HEARTBEAT.md
- Think of it as a sticky note to a really capable intern who checks in every 30 minutes
- Start with 2-3 things you actually care about
- Add more as you learn what Claude spots that matters to you
- The checklist is *yours* — make it useful for your workflow, not a demo

---

## Testing your checklist

Run a single heartbeat to see what Claude produces before installing the scheduler:

```bash
tinman run --once
```

Iterate on your HEARTBEAT.md until the output is useful, then install:

```bash
tinman install
```
