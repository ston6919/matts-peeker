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
- Samples frames at **one frame per second** (1 Hz). Override with `--fps` if needed.
- Sends JPEG frames to **OpenRouter** in **batches** (multiple images per API call) using **Google Gemini 2.5 Flash** (`google/gemini-2.5-flash` by default) for per-frame descriptions in `report.md`, `report.json`, and `agent_context.txt`.
- Supports transcript retrieval: free captions via `yt-dlp` first, then Deepgram on stripped audio, then Super Data.
- Produces a clean output package for follow-up analysis:
  - `report.json`
  - `report.md`
  - `agent_context.txt`

## OpenRouter (vision) support

Environment variables:

- `OPENROUTER_API_KEY` (for frame vision descriptions)
- `OPENROUTER_MODEL` (optional; default `google/gemini-2.5-flash`)
- `OPENROUTER_VISION_BATCH_SIZE` (optional; default `8` — frames per API request)

## Super Data API support

Environment variables:

- `SUPERDATA_API_KEY`
- `SUPERDATA_API_BASE_URL` (optional, default `https://api.superdata.ai`)

When configured, Super Data is used only if captions and Deepgram did not produce a transcript.

## Deepgram API support

Environment variables:

- `DEEPGRAM_API_KEY`
- `DEEPGRAM_MODEL` (optional, default `nova-2`)

Deepgram runs only on **audio stripped from the video** (mono 16 kHz WAV via `ffmpeg`), never on the raw video file.

## Transcript order

1. For `http`/`https` sources: English captions via `yt-dlp` when available (no API cost).
2. Deepgram on stripped audio when step 1 yields no transcript and `DEEPGRAM_API_KEY` is set.
3. Super Data when steps 1–2 yield no transcript and `SUPERDATA_API_KEY` is set.

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
- reference relevant frame descriptions and files when visual context matters

