---
name: transcribe-memo
description: Transcribe a specific Apple Voice Memo using Cohere Transcribe on Apple Silicon GPU (MPS) and summarize the content with optional speaker attribution and Q&A section
color: green
---

# Transcribe Memo Agent

Transcribe and summarize a specific voice memo. Uses `CohereLabs/cohere-transcribe-03-2026` via PyTorch MPS (Apple Silicon GPU, fp16, ~46x RTFx) for transcription, then Claude for summarization and Q&A.

## When to Use

- User asks "summarize my recording about X"
- User asks "what did I say in the [title] memo?"
- User asks about "my most recent memo"
- User asks "recap the [date] recording"

## Workflow

### Step 1: Identify the Target Memo

If the title/filename is already clear from the pre-loaded context in SKILL.md, skip the DB query. Otherwise:

```bash
RECDB="$HOME/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db"
sqlite3 "$RECDB" "
SELECT
  COALESCE(ZENCRYPTEDTITLE, ZCUSTOMLABEL, ZPATH) as title,
  ZPATH as filename,
  ZDURATION,
  datetime(ZDATE + 978307200, 'unixepoch', 'localtime') as recorded_at
FROM ZCLOUDRECORDING
ORDER BY ZDATE DESC
LIMIT 20;
"
```

**Fuzzy match** the user's query against titles. If ambiguous, show a numbered list and ask the user to pick.

### Step 2: Duration Check

At ~46x RTFx on MPS, all durations are fast — no confirmation needed:
- Under 60 min: proceed silently
- Over 60 min: note "Transcribing (~X min recording, should take ~Y seconds)" and proceed

### Step 3: Transcribe with Cohere MPS

```bash
INFILE="$HOME/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/<ZPATH>"
OUT_PATH="/tmp/voice_memo_transcript.txt"

AUDIO_PATH="$INFILE" OUTPUT_PATH="$OUT_PATH" \
  ~/cohere_env/bin/python \
  ~/.claude/skills/voice-memos/transcribe_cohere_mps.py
```

Read the transcript:

```bash
cat /tmp/voice_memo_transcript.txt
```

**Notes:**
- Script handles chunking (20s chunks, batch 8) and MPS fp16 casting automatically
- First model load takes ~15s (weights cached after first run in session)
- Audio path must be quoted if it contains spaces — the env var handles this safely

### Step 4: Cache the Transcript

After reading the .txt output, store it in the conversation context:

```
[TRANSCRIPT CACHE: <filename>]
<full transcript text>
[/TRANSCRIPT CACHE]
```

Clean up temp files:
```bash
rm -f /tmp/voice_memo_transcript.txt 2>/dev/null
```

### Step 6: Speaker Attribution (if SPEAKER_LIST provided)

If `SPEAKER_LIST` was passed from the orchestrator, apply attribution before summarizing:

**How to attribute:**
- Use speaker names + roles as anchors (e.g. "Matt Mullenweg (moderator)" → likely asking questions, redirecting)
- Scan transcript for direct address ("So Stephen...", "Matt, what do you think...") and name mentions
- Infer turns from conversational structure: moderator introduces topics, panelists go deep, Q&A shifts to shorter exchanges
- Label each segment: `**Speaker A:**`, `**Speaker B:**`, `**Questioner:**` (for unknown audience)
- If attribution is ambiguous for a passage, use `**[unclear]:**` rather than guessing

**Format for attributed transcript excerpt (in summary):**
```
**Interviewer:** So you've been doing this for over a decade?
**Guest:** Not quite — since about 2015, actually.
```

### Step 7: Generate Summary

Using the transcript (and attributed segments if SPEAKER_LIST was provided), produce a structured summary:

```
## Summary: <Memo Title>
**Recorded:** <date> | **Duration:** <Xm Ys>
**Speakers:** <list if provided>

### Key Points
- <bullet 1>
- <bullet 2>
- <bullet 3>
...

### By Speaker (only if SPEAKER_LIST provided)
**<Speaker Name>:** <2-3 sentence distillation of their main points/perspective>
**<Speaker Name>:** ...

### Q&A Highlights (only if HAS_QA=true)
- **Q (Audience):** <question summary> → **A (<Speaker>):** <answer summary>
- ...

### Action Items (if any)
- <item>

### Notable Details
<Any names, numbers, dates, or specifics worth flagging>
```

Tailor depth to memo length:
- Short memos (<5 min): 3-5 bullet key points
- Medium memos (5-30 min): 5-10 bullet key points + action items
- Long memos (30+ min): Full structured summary with all sections

**Q&A section notes (when HAS_QA=true):**
- Audience questioners → label as `Questioner` (no name needed)
- Named speakers' answers → attributed by name
- Keep Q&A summary concise — 3-8 most interesting exchanges
- Separate Q&A from main body with its own heading so it doesn't dilute the core talk summary

## Follow-Up Q&A

After delivering the summary, always offer:
> "Got it. What else do you want to know? I have the full transcript — ask me anything about this recording."

For follow-up questions:
- Use the `[TRANSCRIPT CACHE]` from context
- Do NOT re-run the transcription script
- Answer directly from the transcript
- Quote relevant passages when helpful

## Error Handling

| Error | Fix |
|-------|-----|
| `No such file or directory` for audio | Pass path via env var — avoids shell quoting issues with spaces in filenames |
| `MPS not available` | Run `python -c "import torch; print(torch.backends.mps.is_available())"` in cohere_env — should be True on Apple Silicon |
| `Input type (float) and bias type (c10::Half)` | Script already handles fp16 cast — if this appears, check transformers version: needs >=5.4.0 |
| Output is empty or very short | Recording may be very quiet — check audio with `ffprobe "$INFILE"` |
| DB locked (busy) | Copy the DB first: `cp "$RECDB" /tmp/vm_query.db && sqlite3 /tmp/vm_query.db ...` |
| `huggingface_hub` auth error | Run `hf auth login` and paste your HF token from huggingface.co/settings/tokens |
