---
name: list-memos
description: List all Apple Voice Memos with titles, dates, and durations
color: blue
---

# List Memos Agent

Display all voice memos from the CloudRecordings database with clean formatting.

## When to Use

- User asks "what voice memos do I have?"
- User asks "list my recordings"
- User wants to browse before picking one to summarize
- Disambiguation: when user query is ambiguous, show list first

## Workflow

### Step 1: Query All Memos

```bash
RECDB="$HOME/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db"
sqlite3 "$RECDB" "
SELECT
  COALESCE(ZENCRYPTEDTITLE, ZCUSTOMLABEL, ZPATH) as title,
  ZPATH as filename,
  printf('%.0f', ZDURATION/60) || 'm ' || printf('%.0f', ZDURATION%60) || 's' as duration,
  datetime(ZDATE + 978307200, 'unixepoch', 'localtime') as recorded_at
FROM ZCLOUDRECORDING
ORDER BY ZDATE DESC;
"
```

### Step 2: Format Output

Present as a clean numbered list with index, title, date, and duration. Example:

```
## Your Voice Memos (18 total)

| # | Title | Recorded | Duration |
|---|-------|----------|----------|
| 1 | Team standup notes | Jan 15, 2026 9:05 AM | 12m 30s |
| 2 | Project brainstorm | Jan 14, 2026 3:22 PM | 28m 11s |
| 3 | Conference keynote | Jan 12, 2026 10:37 AM | 50m 3s |
...
```

## Follow-Up Suggestions

After displaying the list, always ask:
> "Which memo would you like me to summarize? I can transcribe any of these and give you the key points."
