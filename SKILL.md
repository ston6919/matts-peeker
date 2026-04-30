---
name: peek
description: Matt's Peeker analyzes a video source with extracted frames and transcript data, then builds a clean output package.
argument-hint: " <video-url-or-path> [question]"
allowed-tools: Bash, Read, AskUserQuestion
user-invocable: true
---

# /peek

Use this skill when a user wants Matt's Peeker style video understanding with reusable packaged output.

## Command pattern

Run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/peeker.py" --source "<url-or-file>" --question "<user-question>" --out-dir "<output-folder>"
```

## Capabilities

- Works with public video URLs and local video files.
- Uses `yt-dlp` and `ffmpeg` for acquisition and frame extraction.
- Supports transcript retrieval from Super Data API.
- Produces a clean output package for follow-up analysis:
  - `report.json`
  - `report.md`
  - `agent_context.txt`

## Super Data API support

Environment variables:

- `SUPERDATA_API_KEY`
- `SUPERDATA_API_BASE_URL` (optional, default `https://api.superdata.ai`)

When configured, transcript retrieval uses Super Data first.

## Fallback behavior

If Super Data transcript is unavailable, the skill tries subtitle extraction via `yt-dlp`.

## Good usage examples

```bash
python3 scripts/peeker.py \
  --source "https://www.youtube.com/watch?v=abc123" \
  --question "Break down the opening hook in 3 bullets." \
  --out-dir "./runs/hook-analysis"
```

```bash
python3 scripts/peeker.py \
  --source "~/Desktop/bug-repro.mov" \
  --question "What visual issue appears first?" \
  --out-dir "./runs/bug-review"
```

## Output contract

The final answer to the user should use the report package:

- cite key timestamps
- cite transcript evidence
- reference relevant frame files when visual context matters

