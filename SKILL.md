---
name: voice-memos
description: Transcribe, summarize, and query Apple Voice Memos on macOS. Lists all memos with titles and durations, transcribes audio using Cohere Transcribe on Apple Silicon GPU (MPS), provides speaker-attributed summaries with optional Q&A section, and supports follow-up questions about memo content. Use when the user asks about their voice memos, recordings, wants a summary of a recording, or asks what they said in a voice memo.
argument-hint: <memo title or query> [--speakers "Name (role), Name2 (role)"] [--qa]
user-invocable: true
thinking: high
---

# Voice Memos — Orchestrator

Transcribe and summarize Apple Voice Memos stored on macOS. Supports listing, fuzzy title matching, transcription via Cohere Transcribe (MPS), summarization, and multi-turn follow-up questions.

## Prerequisites

- **Full Disk Access**: Terminal must have Full Disk Access in System Settings > Privacy & Security.
- **Paths**:
  - Recordings: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/`
  - DB: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db`
- **Transcription**: Uses `CohereLabs/cohere-transcribe-03-2026` via PyTorch MPS (Apple Silicon GPU, fp16). ~46x RTFx — a 78-min recording transcribes in ~2 min.
- **Python env**: `~/cohere_env/bin/python` — has `transformers>=5.4.0`, `torch>=2.11.0`, `numpy`, `librosa` installed. See `setup.sh` for environment creation.
- **Transcription script**: `~/.claude/skills/voice-memos/transcribe_cohere_mps.py` — accepts `AUDIO_PATH` and `OUTPUT_PATH` as env vars.
- **ffmpeg**: Required for audio decoding. Install via `brew install ffmpeg`.

## DB Reference

Key table: `ZCLOUDRECORDING`

| Column | Type | Notes |
|--------|------|-------|
| `ZENCRYPTEDTITLE` | VARCHAR | Human-readable memo title (despite the name, not encrypted) |
| `ZPATH` | VARCHAR | Filename only (e.g., `20250925 184559-C51B20B8.m4a`) |
| `ZDURATION` | FLOAT | Duration in seconds |
| `ZDATE` | TIMESTAMP | CoreData timestamp — add 978307200 to convert to Unix epoch |
| `ZCUSTOMLABEL` | VARCHAR | User-edited label (may be NULL; prefer `ZENCRYPTEDTITLE`) |

Convert date: `datetime(ZDATE + 978307200, 'unixepoch', 'localtime')`

Full recording path: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/<ZPATH>`

## Pre-loaded Context

The following list of memos is injected at skill load — no tool call needed for listing. Use it directly for "list my memos" or to fuzzy-match a user's query to a specific memo.

### All Voice Memos
!`sqlite3 "$HOME/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db" "SELECT COALESCE(ZENCRYPTEDTITLE, ZPATH), ZPATH, printf('%.0f', ZDURATION/60)||'m '||printf('%.0f', ZDURATION%60)||'s', datetime(ZDATE+978307200,'unixepoch','localtime') FROM ZCLOUDRECORDING ORDER BY ZDATE DESC;" 2>/dev/null | python3 -c "import sys; [print(f'{i}. {p[0]} | {p[3]} | {p[2]} | file: {p[1]}') for i,l in enumerate(sys.stdin,1) if (p:=l.strip().split('|')) and len(p)>=4]"`

## $ARGUMENTS Parsing

Parse `$ARGUMENTS` loosely — the user should be able to write naturally. Infer intent rather than requiring strict flag syntax.

### Speaker Extraction
Look for speaker names anywhere in the arguments using any of these patterns:
- `--speakers "Name (role), Name2 (role)"` — explicit flag
- `Name (panelist), Name2 (moderator)` — inline with roles
- `Harrison Chase and Max Ruderman` — names without roles (infer roles from context: who asks = moderator, who answers = panelist)
- Names embedded in the memo title itself: `"Harrison Chase chat with Max Ruderman"` → infer both as speakers

**Role inference when not specified:**
- "chat with", "interview", "conversation with" → first name = moderator/interviewer, second = panelist/guest
- "talk by", "keynote by" → single speaker = panelist
- If unsure, label both as `(speaker)` and let Claude infer from transcript

### Q&A Detection
Set `HAS_QA=true` if ANY of these appear:
- `--qa` flag
- words like "qa", "q&a", "questions", "audience questions" anywhere in args

### Memo Title Extraction
After extracting speaker and QA hints, the remaining text (or the full string if no flags found) is the memo title/query.

**Examples — all valid:**
- `/voice-memos stephen wolfram` → title only
- `/voice-memos harrison chase --qa` → title + Q&A flag
- `/voice-memos Harrison Chase chat with Max Ruderman --speakers Max Ruderman(panelist), Harrison Chase(moderator) --qa` → full explicit
- `/voice-memos Harrison Chase chat with Max Ruderman` → infer both names as speakers from title
- `/voice-memos stanford talk Max Ruderman Harrison Chase qa` → infer speakers + Q&A from loose text

Pass inferred `SPEAKER_LIST` and `HAS_QA` to the `transcribe-memo` agent when routing.

## Intent Classification

| Input Pattern | Agent File | Description |
|---|---|---|
| "list", "all memos", "what recordings" | `agents/list-memos.md` | Show all memos with titles, dates, durations |
| Memo title, date, or "recent" + "summarize"/"what did I say" | `agents/transcribe-memo.md` | Transcribe and summarize a specific memo |
| "search", "find", keyword across memos | `agents/search-memos.md` | Search transcripts for content |
| Follow-up question about a previously transcribed memo | Continue in current context | Answer using cached transcript |

### Input Detection Logic

1. **List intent**: "list", "show all", "what memos do I have", "all recordings" → route to **list-memos**
2. **Specific memo + action**: If user names a memo (by title, date, or "most recent") and says "summarize", "what did I say", "recap", "play back" → route to **transcribe-memo**
3. **Search across memos**: "find memos about X", "which recording mentions Y" → route to **search-memos**
4. **Recent/latest**: "my last recording", "most recent memo" → use the first entry from pre-loaded list above → route to **transcribe-memo**
5. **Follow-up**: If a transcript is already in context and user asks a question about it → answer directly, no re-transcription needed
6. **Ambiguous**: If unclear which memo, show the pre-loaded list and ask the user to pick one
7. **Default**: Show the list of memos

## Execution Instructions

1. Classify intent using the table above
2. `Read` the matched agent `.md` file from `~/.claude/skills/voice-memos/agents/`
3. For transcription, warn the user if the memo is long (>10 min) — it may take 1-3 minutes
4. After transcription and summarization, proactively offer follow-up options
5. Cache transcripts in the conversation context — never re-transcribe within the same session

## Duration Reference

- `ZDURATION` is in **seconds** as a float
- Convert: `floor(duration/60)` minutes, `floor(duration%60)` seconds
- Example: `1839.956` → 30m 39s
- At ~46x RTFx on MPS: 10 min audio → ~13s, 30 min → ~40s, 60 min → ~80s, 78 min → ~2 min
- No need to warn for any duration — MPS is fast enough to proceed silently for all lengths

## Transcript Caching

Once a memo is transcribed, store the full transcript text in the conversation context as:

```
[TRANSCRIPT CACHE: <filename>]
<full transcript text>
[/TRANSCRIPT CACHE]
```

Reference this cache for all follow-up questions without re-running the transcription script.
