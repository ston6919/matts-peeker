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

From this repository’s root directory, run:

```bash
python3 .cursor/skills/peek/scripts/peeker.py --source "<url-or-file>" --question "<user-question>" --out-dir "<output-folder>"
```

In Claude Code (when `CLAUDE_SKILL_DIR` is set to this skill’s folder):

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/peeker.py" --source "<url-or-file>" --question "<user-question>" --out-dir "<output-folder>"
```

If the shell’s working directory is not the repo root, use the absolute path to `scripts/peeker.py` next to this `SKILL.md`.

## Capabilities

- Works with public video URLs and local video files.
- Uses `yt-dlp` and `ffmpeg` for acquisition and frame extraction.
- Samples frames at **one frame per second** (1 Hz). Override with `--fps` if needed.
- Sends JPEG frames to **OpenRouter** in **batches** (multiple images per API call) using **Google Gemini 2.5 Flash** (`google/gemini-2.5-flash` by default) to produce per-frame descriptions stored in `report.md`, `report.json`, and `agent_context.txt`.
- Supports transcript retrieval with this order:
  1. `yt-dlp` captions/subtitles (URL sources)
  2. Deepgram transcription from extracted MP3
  3. Super Data API fallback
- Produces a clean output package for follow-up analysis:
  - `report.json`
  - `report.md`
  - `agent_context.txt`

## Transcript provider configuration

Environment variables:

- `OPENROUTER_API_KEY` (required for frame vision descriptions via OpenRouter)
- `OPENROUTER_MODEL` (optional; default `google/gemini-2.5-flash` — Gemini 2.5 Flash on OpenRouter)
- `OPENROUTER_VISION_BATCH_SIZE` (optional; default `8` — how many frames per vision API request)
- `DEEPGRAM_API_KEY` (used for MP3 transcription)
- `SUPERDATA_API_KEY`
- `SUPERDATA_API_BASE_URL` (optional, default `https://api.superdata.ai`)

Deepgram key lookup behavior:

- First checks `DEEPGRAM_API_KEY` in the current environment.
- If not found, checks `~/.zshrc` for `export DEEPGRAM_API_KEY="..."`.

When configured, transcript retrieval tries providers in this order:

1. `yt-dlp` subtitles/captions
2. Deepgram from extracted audio
3. Super Data fallback

## Fallback behavior

If subtitle extraction fails or returns no transcript, the skill tries Deepgram from extracted audio.

If Deepgram is unavailable or returns no transcript, the skill falls back to Super Data.

If video acquisition fails (download blocked, private/geo-restricted source, missing local file, or extraction failure), stop and return a failure message. Do **not** answer the user’s question from memory, web search, or generic reasoning.

Required failure message pattern:

- "I could not access the video source, so I cannot verify what happens at that timestamp."
- Include the blocking reason from the tool error.
- Ask the user for a direct video file or a source that is accessible from this environment.

## Good usage examples

```bash
python3 .cursor/skills/peek/scripts/peeker.py \
  --source "https://www.youtube.com/watch?v=abc123" \
  --question "Break down the opening hook in 3 bullets." \
  --out-dir "./runs/hook-analysis"
```

```bash
python3 .cursor/skills/peek/scripts/peeker.py \
  --source "~/Desktop/bug-repro.mov" \
  --question "What visual issue appears first?" \
  --out-dir "./runs/bug-review"
```

## Output contract

The final answer to the user should use the report package:

- cite key timestamps
- cite transcript evidence
- reference relevant frame descriptions and files when visual context matters

If `report.json` and extracted frames are not produced, do not provide a content answer about the video.

