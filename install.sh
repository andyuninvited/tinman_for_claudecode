#!/usr/bin/env bash
# TinMan one-line installer
# curl -fsSL https://raw.githubusercontent.com/andyuninvited/tinman_for_claudecode/main/install.sh | bash

set -euo pipefail

REPO="https://github.com/andyuninvited/tinman_for_claudecode"
PYPI_NAME="tinman-for-claudecode"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  TinMan Installer - CC Heartbeat     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Prereqs ───────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo "❌  python3 not found. Install Python 3.9+ first: https://python.org"
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✓  Python $PYTHON_VERSION found"

if ! command -v claude &>/dev/null; then
  echo "⚠️   claude CLI not found."
  echo "    Install Claude Code first: https://claude.ai/code"
  echo "    (TinMan will install, but heartbeats won't run until claude is available)"
fi

# ── Install ───────────────────────────────────────────────────────────────────
echo ""
echo "Installing TinMan..."

if pip3 install --quiet --upgrade "$PYPI_NAME" 2>/dev/null; then
  echo "✓  Installed from PyPI"
else
  echo "PyPI unavailable, installing from GitHub..."
  pip3 install --quiet --upgrade "git+$REPO.git"
  echo "✓  Installed from GitHub"
fi

# ── Verify ────────────────────────────────────────────────────────────────────
if ! command -v tinman &>/dev/null; then
  # Try python -m tinman as fallback
  if python3 -m tinman --version &>/dev/null; then
    echo "✓  TinMan installed (run as: python3 -m tinman)"
    TINMAN_CMD="python3 -m tinman"
  else
    echo "❌  Install succeeded but 'tinman' command not found."
    echo "    Try: pip3 install --user tinman-for-claudecode"
    echo "    And add ~/.local/bin to your PATH"
    exit 1
  fi
else
  echo "✓  tinman command available"
  TINMAN_CMD="tinman"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  TinMan installed successfully! 🤖❤️"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next step: run setup"
echo "  $TINMAN_CMD init"
echo ""
echo "Or jump straight in:"
echo "  $TINMAN_CMD run --once          # run one heartbeat now"
echo "  $TINMAN_CMD install             # install background scheduler"
echo "  $TINMAN_CMD status              # check status"
echo ""
echo "Docs: $REPO"
echo ""
