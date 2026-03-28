# voice-memos

A [Claude Code](https://claude.ai/code) skill that transcribes and summarizes Apple Voice Memos using your Mac's Apple Silicon GPU.

> **Apple Silicon Macs only (M1 / M2 / M3 / M4).** Uses PyTorch MPS backend for GPU inference.

## What it does

| Command | Result |
|---|---|
| `/voice-memos` | Lists all your Voice Memos |
| `/voice-memos <title>` | Transcribes + summarizes that memo |
| `/voice-memos <title> --qa` | Adds Q&A highlights section |
| `/voice-memos <title> --speakers "Alice (host), Bob (guest)"` | Speaker-attributed transcript |
| `/voice-memos search <keyword>` | Searches across memos |

Follow-up questions work naturally — the transcript is cached so nothing gets re-transcribed.

## Requirements

- **Apple Silicon Mac** (M1, M2, M3, or M4)
- **macOS 13+**
- **Full Disk Access** for Terminal: System Settings → Privacy & Security → Full Disk Access
- **HuggingFace account** (free) — required to download the transcription model
- **Gated model access accepted** — you must visit the [CohereLabs/cohere-transcribe-03-2026](https://huggingface.co/CohereLabs/cohere-transcribe-03-2026) model page and click **"Agree and access repository"** to share your HF username with Cohere. Without this, the download returns a 403 even with a valid token.
- **`hf` CLI installed and authenticated** (`pip install huggingface_hub[cli]` installs it) before setup runs any download

## Installation

### Before you begin — HuggingFace setup (required)

1. Create a free account at [huggingface.co](https://huggingface.co/join) if you don't have one
2. Visit [CohereLabs/cohere-transcribe-03-2026](https://huggingface.co/CohereLabs/cohere-transcribe-03-2026) and click **"Agree and access repository"** to accept the model's terms and share your HF username with Cohere
3. Create an access token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
4. Install and authenticate the CLI:
   ```bash
   pip install huggingface_hub[cli]   # or use the venv after setup.sh creates it
   hf auth login                      # paste your token when prompted
   ```

> If you skip any of these steps, the model download will fail and the skill won't be able to transcribe.

### Clone and run setup

```bash
git clone https://github.com/<your-username>/voice-memos.git
cd voice-memos
bash setup.sh
```

`setup.sh` will create the Python venv, install all dependencies, and copy the skill files into `~/.claude/skills/voice-memos/`. It will also remind you to log in if the CLI isn't authenticated.

Then in Claude Code:
```
/voice-memos
```

## Performance

~65× real-time speed on Apple Silicon with MPS:

| Recording length | Transcription time |
|---|---|
| 5 minutes | ~5 seconds |
| 15 minutes | ~14 seconds |
| 30 minutes | ~27 seconds |
| 60 minutes | ~55 seconds |

## Privacy

All processing is local. Your audio never leaves your machine.

## License

MIT