# CLAUDE.md - Voice Memos Skill Setup Protocol for AI Assistants

This document provides comprehensive setup guidance for Claude Code and other AI assistants setting up the voice-memos skill. It addresses critical pitfalls that can cause cascade failures during installation.

## ⚠️ Critical Architecture Issue

**The primary failure pattern**: x86_64 Homebrew on Apple Silicon Macs leads to wrong Python → wrong packages → MPS unavailable → transcription failure.

Always verify native arm64 execution before proceeding.

---

## Setup Protocol

### Phase 1: Architecture Detection & Validation

**GATE CHECK 1: Verify Apple Silicon Hardware**
```bash
sysctl -n machdep.cpu.brand_string
# MUST show: "Apple M1" / "Apple M2" / "Apple M3" / "Apple M4" (any variant)
```

**GATE CHECK 2: Detect Current Execution Mode**
```bash
arch
uname -m
```
- If both show `arm64` → ✅ Native execution
- If either shows `i386` or `x86_64` → ⚠️ Running under Rosetta emulation

**GATE CHECK 3: Homebrew Architecture Detection**
```bash
# Check for native arm64 Homebrew
ls /opt/homebrew/bin/brew 2>/dev/null && echo "✅ Native Homebrew found" || echo "❌ Native Homebrew missing"

# Check for x86_64 Homebrew
ls /usr/local/bin/brew 2>/dev/null && echo "⚠️ x86_64 Homebrew found" || echo "✅ No x86_64 Homebrew"

# Verify which brew is in PATH
which brew
```

**Expected Results:**
- ✅ Native: `/opt/homebrew/bin/brew` exists and is in PATH
- ❌ Problem: Only `/usr/local/bin/brew` exists (x86_64 Homebrew)

### Phase 2: Homebrew Installation/Verification

**If native Homebrew missing:**
```bash
# Install native arm64 Homebrew (requires user sudo)
arch -arm64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add to PATH
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv zsh)"
```

**GATE CHECK 4: Homebrew Validation**
```bash
arch -arm64 /opt/homebrew/bin/brew --version
# MUST work without "Bad CPU type" error
```

### Phase 3: Python Installation & Verification

**Install Python 3.14+ via native Homebrew:**
```bash
arch -arm64 /opt/homebrew/bin/brew install python@3.14
```

**GATE CHECK 5: Python Architecture Validation**
```bash
arch -arm64 /opt/homebrew/opt/python@3.14/bin/python3.14 -c "import platform; print(f'Python {platform.python_version()} - {platform.machine()}')"
# MUST show: "Python 3.14.x - arm64"
```

### Phase 4: Virtual Environment Setup

**Create native arm64 venv:**
```bash
arch -arm64 /opt/homebrew/opt/python@3.14/bin/python3.14 -m venv ~/cohere_env
```

**CRITICAL: Fix venv symlinks (common failure point)**
```bash
# Verify venv configuration
~/cohere_env/bin/python -c "import platform; print(platform.machine())"
cat ~/cohere_env/pyvenv.cfg | grep home

# If python reports x86_64, fix symlinks:
cd ~/cohere_env/bin
rm python python3 python3.9 2>/dev/null  # Remove wrong symlinks
ln -s python3.14 python3
ln -s python3.14 python
```

**GATE CHECK 6: Virtual Environment Validation**
```bash
~/cohere_env/bin/python -c "import platform; print(f'Python {platform.python_version()} - {platform.machine()}')"
# MUST show: "Python 3.14.x - arm64"

# Verify venv points to correct Python
cat ~/cohere_env/pyvenv.cfg | grep home
# MUST show: home = /opt/homebrew/opt/python@3.14/bin
```

### Phase 5: Package Installation

**Install dependencies with correct architecture:**
```bash
~/cohere_env/bin/pip install --upgrade pip

~/cohere_env/bin/pip install \
  'torch>=2.11.0' \
  'transformers>=5.4.0' \
  'accelerate>=1.13.0' \
  'safetensors>=0.7.0' \
  'tokenizers>=0.22.2' \
  'sentencepiece>=0.2.1' \
  'numpy>=2.0.0' \
  'librosa>=0.11.0' \
  'soundfile>=0.13.0' \
  'scipy>=1.17.0' \
  'huggingface_hub[cli]>=1.8.0' \
  'hf-xet>=1.4.0' \
  'tqdm>=4.67.0'
```

**GATE CHECK 7: Package and MPS Validation**
```bash
~/cohere_env/bin/python -c "
import torch, transformers, numpy, librosa
print('✅ torch:', torch.__version__)
print('✅ transformers:', transformers.__version__)
print('✅ numpy:', numpy.__version__)
print('✅ MPS available:', torch.backends.mps.is_available())
print('✅ MPS built:', torch.backends.mps.is_built())
"
```

**Required output:**
- torch: 2.11.0 or higher
- transformers: 5.4.0 or higher
- numpy: 2.0.0 or higher
- MPS available: True
- MPS built: True

### Phase 6: HuggingFace Account, Gated Access, and Model Download

This phase has three hard prerequisites that must ALL be satisfied before the download command will succeed. A 403 error means one of them is missing.

**PREREQUISITE 1 — Active HuggingFace account**
The user must have a registered account at huggingface.co. This is free. Cannot be automated — the user must do this manually if they haven't already.

**PREREQUISITE 2 — Accept gated model access (cannot be skipped)**
`CohereLabs/cohere-transcribe-03-2026` is a gated model. The user must visit the model page in a browser and click "Agree and access repository". This shares their HF username with Cohere and grants download permission.
```
URL: https://huggingface.co/CohereLabs/cohere-transcribe-03-2026
Action: Click "Agree and access repository"
```
Without this step, the download returns HTTP 403 even with a valid token. There is no CLI workaround for this — it must be done in the browser.

**PREREQUISITE 3 — `hf` CLI installed and authenticated**
The CLI tool is `hf` (from `huggingface_hub[cli]`). Always use the venv's binary — not a system-level path which may be absent or authenticated to the wrong account:
```bash
# Verify CLI is installed in venv (it is, from Phase 5's huggingface_hub[cli])
~/cohere_env/bin/hf version

# Authenticate — user pastes their token from huggingface.co/settings/tokens
~/cohere_env/bin/hf auth login
```

**GATE CHECK: confirm login succeeded**
```bash
~/cohere_env/bin/hf auth whoami
# Must return a username — NOT "Not logged in"
```

**Download the model (~3 GB, cached to ~/.cache/huggingface/)**
```bash
~/cohere_env/bin/hf download CohereLabs/cohere-transcribe-03-2026
```
Expected: progress bars to 100%, then "Successfully downloaded model to ~/.cache/huggingface/hub/models--CohereLabs--cohere-transcribe-03-2026/"

If download fails with 403: user has not completed PREREQUISITE 2. Direct them to the model page URL above.

### Phase 7: Skill Installation

**Copy skill files to Claude Code directory:**
```bash
mkdir -p ~/.claude/skills/voice-memos/agents
cp SKILL.md transcribe_cohere_mps.py ~/.claude/skills/voice-memos/
cp agents/*.md ~/.claude/skills/voice-memos/agents/
chmod +x ~/.claude/skills/voice-memos/transcribe_cohere_mps.py
```

**GATE CHECK 8: Smoke Test**
```bash
AUDIO_PATH="$(ls ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/*.m4a 2>/dev/null | head -1)" \
OUTPUT_PATH=/tmp/test_transcript.txt \
~/cohere_env/bin/python ~/.claude/skills/voice-memos/transcribe_cohere_mps.py
```

Expected: Model loads → transcribes → "RTFx: ~65x"

---

## Common Failure Patterns & Solutions

### Error: "Bad CPU type in executable"
**Cause:** x86_64 binary on arm64 system
**Solution:** Use `arch -arm64` prefix and native Homebrew

### Error: "MPS not available" (MPS built: False)
**Cause:** PyTorch installed for wrong architecture
**Solution:** Recreate venv with native Python, reinstall torch

### Error: "value cannot be converted to type c10::Half without overflow"
**Cause:** Model architecture mismatch (red herring - real issue is wrong PyTorch)
**Solution:** Fix underlying architecture issues, not the model code

### Error: Virtual environment shows wrong Python version
**Cause:** Broken symlinks in venv/bin/
**Solution:** Fix symlinks to point to correct python3.14

### Error: "Permission denied" during Homebrew install
**Cause:** Needs sudo access
**Solution:** Ask user to run installation command manually

### Error: "sqlite3: unable to open database"
**Cause:** Terminal lacks Full Disk Access permission
**Solution:** System Settings → Privacy & Security → Full Disk Access

---

## Working Reference Configuration

**Known-good setup (macbook-pro reference):**
- Hardware: Apple M2 Ultra
- Python: 3.14.3 from `/opt/homebrew/opt/python@3.14`
- Homebrew: Native arm64 at `/opt/homebrew`
- PyTorch: 2.11.0 (arm64 native)
- Virtual env: `~/cohere_env` with correct symlinks
- Model cached: `~/.cache/huggingface/hub/models--CohereLabs--cohere-transcribe-03-2026/`

**Validation commands for working state:**
```bash
arch                                    # → arm64
which brew                             # → /opt/homebrew/bin/brew
~/cohere_env/bin/python --version     # → Python 3.14.3
~/cohere_env/bin/python -c "import torch; print(torch.backends.mps.is_available())"  # → True
```

---

## Emergency Remediation

**If everything is broken, nuclear reset:**
```bash
# 1. Remove broken environment
rm -rf ~/cohere_env

# 2. Install native Homebrew (ask user for sudo)
arch -arm64 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 3. Follow setup protocol from Phase 2
```

**Migration from x86_64 to arm64 Homebrew:**
1. Document existing packages: `brew list --formula > /tmp/x86_packages.txt`
2. Install native Homebrew
3. Reinstall packages with native brew
4. Remove old Homebrew: `sudo rm -rf /usr/local/Homebrew`

---

## Key Success Principles

1. **Always verify architecture** before proceeding
2. **Use `arch -arm64` prefix** for critical commands
3. **Validate at each phase** before continuing
4. **Fix symlinks** in virtual environments
5. **Don't modify original skill files** - use them as-is
6. **When in doubt, start fresh** with native tools
7. **HuggingFace gated access must be accepted in browser** — no CLI flag bypasses the 403; user must click "Agree" on the model page before any download attempt
8. **Always use `~/cohere_env/bin/hf`** — the CLI is `hf`, not `huggingface-cli`; always use the venv path, not a system-level one which may be absent or wrong

This protocol prevents the cascade failures that occur when wrong architecture components interact with each other.