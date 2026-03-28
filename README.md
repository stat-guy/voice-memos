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

## Why this exists

Voice memos are a great capture tool — but they're a terrible retrieval tool. You record something, forget about it, and the insight is gone. This skill closes that loop.

The whole point is to turn a raw audio file into something you can actually *use*: a structured summary you can skim in 30 seconds, action items you can drop into your task manager, a speaker-by-speaker breakdown of who said what in a meeting, or a searchable record of every conversation you've recorded.

Because transcription runs locally on your Mac's GPU — not in the cloud — it's also fast enough to be part of a real workflow. A 30-minute meeting is ready in under a minute. You can ask follow-up questions about the transcript without re-running anything.

## What a summary looks like

Below is a fictional example showing what `/voice-memos "product sync" --speakers "Jordan (PM), Alex (engineer)" --qa` might produce. **This is illustrative — your actual output will reflect your real recording.**

---

> **Summary: Product Sync — March 28**
> **Recorded:** Mar 28, 2026 2:04 PM | **Duration:** 22m 14s
> **Speakers:** Jordan (PM), Alex (engineer)
>
> ### Key Points
> - Decided to cut the bulk-export feature from the v2 launch to hit the April 10 deadline
> - Auth token refresh bug is the top blocker — Alex estimates 2 days to fix
> - Onboarding flow redesign approved; Jordan will share updated mocks by EOD Friday
> - Next sync moved to Tuesday at 10 AM; async update expected Monday if blockers clear early
>
> ### By Speaker
> **Jordan:** Focused on scope reduction to protect the launch date. Pushed back on adding new API endpoints before the deadline and flagged that the customer success team needs a heads-up about the export cut.
>
> **Alex:** Raised concerns about the token refresh issue surfacing under load, noted the fix is straightforward but needs QA time. Supportive of cutting export as long as it's documented on the roadmap.
>
> ### Q&A Highlights
> - **Q (Jordan):** Can we ship export as a fast-follow in v2.1? → **A (Alex):** Yes, the backend work is 80% done — it's a UI and testing problem, not an infra one.
>
> ### Action Items
> - Alex: fix auth token refresh bug by Monday EOD
> - Jordan: share onboarding mocks by Friday EOD
> - Jordan: notify customer success about export feature delay
>
> ### Notable Details
> April 10 hard deadline confirmed. v2.1 tentatively scoped for 3 weeks post-launch.

---

Once the summary is delivered you can keep asking questions in the same session — "what did Alex say about the timeline?", "list every decision made", "was anything left unresolved?" — and Claude answers directly from the transcript without re-transcribing.

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