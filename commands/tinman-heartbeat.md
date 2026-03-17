# TinMan Heartbeat

Run a TinMan heartbeat check on the current project.

## Usage

```
/tinman-heartbeat
```

## Instructions

Run a one-time TinMan heartbeat against the current project. TinMan must be installed (`pip install tinman-for-claudecode`).

Execute `tinman run --once` in the project root. If TinMan is not installed, offer to install it first. If no HEARTBEAT.md exists, offer to run `tinman init` to create one with the user's preferred preset (sane, paranoid, or chaos).

Report the heartbeat results to the user.
