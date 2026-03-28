#!/bin/bash
# setup.sh — voice-memos skill environment setup
# Requires: Apple Silicon Mac (M1/M2/M3/M4), macOS 13+, Python 3.11+, Homebrew
# Run: bash setup.sh

set -euo pipefail

VENV_DIR="$HOME/cohere_env"
SKILL_DIR="$HOME/.claude/skills/voice-memos"

echo "==> voice-memos skill setup"
echo ""

# ── 1. Check architecture ──────────────────────────────────────────────────
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
  echo "ERROR: This skill requires an Apple Silicon Mac (M1/M2/M3/M4)."
  echo "       Detected architecture: $ARCH"
  exit 1
fi
echo "[1/6] Architecture: Apple Silicon (arm64) ✓"

# ── 2. Check / install ffmpeg ──────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
  echo "[2/6] Installing ffmpeg via Homebrew..."
  brew install ffmpeg
else
  echo "[2/6] ffmpeg: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3) ✓"
fi

# ── 3. Check Python ────────────────────────────────────────────────────────
PYTHON_BIN=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" &>/dev/null; then
    PYTHON_BIN=$(command -v "$candidate")
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  echo "ERROR: Python 3.11+ not found. Install via: brew install python@3.14"
  exit 1
fi

PY_VERSION=$("$PYTHON_BIN" --version 2>&1 | cut -d' ' -f2)
echo "[3/6] Python: $PY_VERSION at $PYTHON_BIN ✓"

# ── 4. Create virtual environment ─────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
  echo "[4/6] Virtual env already exists at $VENV_DIR — skipping creation"
else
  echo "[4/6] Creating virtual env at $VENV_DIR ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  echo "      Created ✓"
fi

# ── 5. Install dependencies ────────────────────────────────────────────────
echo "[5/6] Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$(dirname "$0")/requirements.txt"
echo "      Dependencies installed ✓"

# ── 6. HuggingFace login & model download ─────────────────────────────────
echo ""
echo "[6/6] HuggingFace setup"
echo "      The CohereLabs/cohere-transcribe-03-2026 model (~3 GB) will be"
echo "      downloaded on first use and cached at ~/.cache/huggingface/"
echo ""
echo "      You need a free HuggingFace account to download the model."
echo "      Get a token at: https://huggingface.co/settings/tokens"
echo ""

if "$VENV_DIR/bin/hf" auth whoami &>/dev/null 2>&1; then
  echo "      Already logged in to HuggingFace ✓"
else
  echo "      Run the following to log in:"
  echo "        $VENV_DIR/bin/hf auth login"
  echo ""
  echo "      IMPORTANT: Before downloading, visit the model page and accept access:"
  echo "        https://huggingface.co/CohereLabs/cohere-transcribe-03-2026"
  echo "        Click 'Agree and access repository' — required, no CLI workaround"
  echo ""
  echo "      Then pre-download the model (recommended for first run speed):"
  echo "        $VENV_DIR/bin/hf download CohereLabs/cohere-transcribe-03-2026"
fi

# ── 7. Install skill into Claude Code ─────────────────────────────────────
echo ""
echo "      Installing skill to $SKILL_DIR ..."
mkdir -p "$SKILL_DIR/agents"
cp "$(dirname "$0")/SKILL.md" "$SKILL_DIR/SKILL.md"
cp "$(dirname "$0")/transcribe_cohere_mps.py" "$SKILL_DIR/transcribe_cohere_mps.py"
cp "$(dirname "$0")/agents/"*.md "$SKILL_DIR/agents/"
chmod +x "$SKILL_DIR/transcribe_cohere_mps.py"
echo "      Skill installed ✓"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo " Setup complete!"
echo ""
echo " Update SKILL.md and agents/transcribe-memo.md if your venv is"
echo " not at ~/cohere_env — replace '~/cohere_env' with your path."
echo ""
echo " Grant Terminal Full Disk Access before using:"
echo "   System Settings > Privacy & Security > Full Disk Access"
echo ""
echo " Then in Claude Code: /voice-memos"
echo "================================================================"
