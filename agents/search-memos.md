---
name: search-memos
description: Search across all Apple Voice Memos for specific topics, keywords, or content
color: purple
---

# Search Memos Agent

Search across multiple voice memos to find content matching a keyword or topic. Requires transcribing multiple memos in parallel.

## When to Use

- User asks "which of my recordings mentions X?"
- User asks "find the memo where I talked about [topic]"
- User asks "do I have any recordings about [subject]?"

## Workflow

### Step 1: Get All Memos

```bash
RECDB="$HOME/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db"
sqlite3 "$RECDB" "
SELECT
  COALESCE(ZENCRYPTEDTITLE, ZCUSTOMLABEL, ZPATH) as title,
  ZPATH as filename,
  ZDURATION,
  datetime(ZDATE + 978307200, 'unixepoch', 'localtime') as recorded_at
FROM ZCLOUDRECORDING
ORDER BY ZDATE DESC;
"
```

### Step 2: Prioritize by Size

For a keyword search, don't transcribe everything blindly. Instead:

1. **Title scan first**: Check if any memo title contains the keyword — if yes, transcribe those first
2. **By recency**: If unclear, start with the most recent 5 memos
3. **User confirmation**: For broad searches that would require transcribing many large files, ask: "This would require transcribing X recordings. Want me to start with the most recent ones, or a specific date range?"

### Step 3: Parallel Transcription (small memos only)

For memos under 5 minutes, spawn parallel subagents via the Agent tool to transcribe multiple memos simultaneously:

```
Agent 1: transcribe /path/to/memo1.m4a
Agent 2: transcribe /path/to/memo2.m4a
...
```

For memos over 5 minutes, transcribe sequentially to avoid overwhelming system resources.

**Transcription command per memo:**
```bash
INFILE="$HOME/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/<ZPATH>"
OUT_PATH="/tmp/voice_memo_transcript.txt"

AUDIO_PATH="$INFILE" OUTPUT_PATH="$OUT_PATH" \
  ~/cohere_env/bin/python \
  ~/.claude/skills/voice-memos/transcribe_cohere_mps.py
```

### Step 4: Search Transcripts

After transcription, search each transcript for the keyword:

```bash
grep -i "<keyword>" /tmp/*.txt
```

Present matches with:
- Memo title and date
- Surrounding context (1-2 sentences around the match)
- Timestamp if available

### Step 5: Cache All Transcripts

Store each transcript in context using the same `[TRANSCRIPT CACHE: <filename>]` format as `transcribe-memo.md`. This allows immediate follow-up questions without re-running the transcription.

## Output Format

```
## Search Results: "<keyword>"

Found in 2 of 5 searched memos:

### 1. Project brainstorm (Jan 14, 2026)
> "...mentioned the **keyword** in the context of..."
→ Found at approximately 12:30 into the recording

### 2. Team standup notes (Jan 15, 2026)
> "...they will revisit the **keyword** again next week..."
→ Found at approximately 5:15 into the recording

---
Searched: 5 memos | Remaining: 13 not yet transcribed
Want me to search the remaining recordings as well?
```
