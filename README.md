# Matt's Peeker

A skill that helps an agent inspect videos by combining:

- downloaded/local video access
- extracted timestamped frames (one frame per second by default)
- OpenRouter vision descriptions for each frame (Gemini 2.5 Flash by default)
- transcript retrieval (free captions via `yt-dlp` first, then Deepgram on stripped audio, then Super Data)
- a clean output package for reuse

## What this project does

`peeker.py` runs an end-to-end flow:

1. Resolve source (public URL or local file).
2. Download the video for URL sources using `yt-dlp`.
3. Extract frames with `ffmpeg` (default: one frame per second; capped by `--max-frames`).
4. Optionally describe each frame via **OpenRouter** (vision) when `OPENROUTER_API_KEY` is set.
5. Pull transcript: English captions via `yt-dlp` for URLs first, then Deepgram on **ffmpeg-stripped** mono WAV, then Super Data if still empty.
6. Build a clean report package (`report.json`, `report.md`, and `agent_context.txt`).

## Requirements

- Python 3.10+
- `yt-dlp` on PATH
- `ffmpeg` on PATH

## API keys — where they go

**Do not** commit keys into this repo or paste them into skill files. The scripts only read **environment variables** when you run `peeker.py`.

### Variables

| Purpose | Environment variable | Required? |
|--------|------------------------|-----------|
| Frame image descriptions (OpenRouter / Gemini) | `OPENROUTER_API_KEY` | Optional; without it, runs still work but frames have no AI descriptions |
| Different vision model on OpenRouter | `OPENROUTER_MODEL` | Optional; default is `google/gemini-2.5-flash` |
| How many frames to send per vision API call | `OPENROUTER_VISION_BATCH_SIZE` | Optional; default `8` |
| Transcript when captions are missing or empty | `DEEPGRAM_API_KEY` | Optional |
| Deepgram model | `DEEPGRAM_MODEL` | Optional; default `nova-2` |
| Last-resort transcript API | `SUPERDATA_API_KEY` | Optional |
| Super Data base URL | `SUPERDATA_API_BASE_URL` | Optional; default `https://api.superdata.ai` |

### How to set them (Mac / zsh)

Add exports to **`~/.zshrc`**, save, then open a **new** terminal or run `source ~/.zshrc`:

```bash
export OPENROUTER_API_KEY="your-openrouter-key"
export DEEPGRAM_API_KEY="your-deepgram-key"           # if you need Deepgram
export SUPERDATA_API_KEY="your-superdata-key"       # if you need Super Data
# Optional overrides:
# export OPENROUTER_MODEL="google/gemini-2.5-flash"
# export OPENROUTER_VISION_BATCH_SIZE="8"
# export DEEPGRAM_MODEL="nova-2"
# export SUPERDATA_API_BASE_URL="https://api.superdata.ai"
```

Only set the keys you actually use. For picture descriptions alone, **`OPENROUTER_API_KEY`** is the important one.

### Claude Code / Cursor

Install or symlink this skill where your agent expects it, but **keys still come from the shell environment** of the process that runs Python. If the agent runs in a GUI without your normal shell profile, ensure those variables are defined for that environment (or run `peeker.py` from a terminal where you have already exported the keys).

## Quick start

```bash
python3 scripts/peeker.py \
  --source "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --question "What happens around 00:30?" \
  --out-dir "./runs/demo"
```

## Claude invocation

This skill is configured as user-invocable command:

- `/peek`

Example intent mapping:

- `/peek https://www.youtube.com/watch?v=... what happens at 00:30?`

Local file example:

```bash
python3 scripts/peeker.py \
  --source "~/Movies/sample.mp4" \
  --question "When does the UI break?" \
  --out-dir "./runs/local-demo"
```

## Output package

Each run creates:

- `report.json` - structured timeline + metadata (includes frame descriptions when vision ran)
- `report.md` - human-friendly summary package
- `agent_context.txt` - compact context text for AI agents
- `frames/` - extracted JPEG frames
- `transcript.json` - transcript segments with timestamps

## Notes

- For URL sources, English subtitles via `yt-dlp` are tried first (no API cost when captions exist).
- If there is still no transcript and `DEEPGRAM_API_KEY` is set, the script strips audio with `ffmpeg` and sends WAV to Deepgram.
- If there is still no transcript and `SUPERDATA_API_KEY` is set, the script asks Super Data last.
- This project is intentionally lightweight and uses Python stdlib only.
