# Matt's Peeker

A fresh skill that helps an agent inspect videos by combining:

- downloaded/local video access
- extracted timestamped frames
- transcript retrieval (free captions via `yt-dlp` first, then Deepgram on stripped audio, then Super Data)
- a clean output package for reuse

## What this project does

`peeker.py` runs an end-to-end flow:

1. Resolve source (public URL or local file).
2. Download the video for URL sources using `yt-dlp`.
3. Extract representative frames with `ffmpeg`.
4. Pull transcript: English captions via `yt-dlp` for URLs first, then Deepgram on **ffmpeg-stripped** mono WAV, then Super Data if still empty.
5. Build a clean report package (`report.json`, `report.md`, and `agent_context.txt`).

## Requirements

- Python 3.10+
- `yt-dlp` on PATH
- `ffmpeg` on PATH

Optional:

- `SUPERDATA_API_KEY`
- `SUPERDATA_API_BASE_URL` (defaults to `https://api.superdata.ai`)
- `DEEPGRAM_API_KEY` (speech-to-text when captions do not yield a transcript)
- `DEEPGRAM_MODEL` (optional, default `nova-2`)

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

## Super Data API key

Set environment variables before running:

```bash
export SUPERDATA_API_KEY="your_key_here"
export SUPERDATA_API_BASE_URL="https://api.superdata.ai"   # optional
export DEEPGRAM_API_KEY="your_deepgram_key_here"           # optional
# export DEEPGRAM_MODEL="nova-2"                           # optional
```

To persist in zsh, put those exports in `~/.zshrc` and run `source ~/.zshrc`.

Local file example:

```bash
python3 scripts/peeker.py \
  --source "~/Movies/sample.mp4" \
  --question "When does the UI break?" \
  --out-dir "./runs/local-demo"
```

## Output package

Each run creates:

- `report.json` - structured timeline + metadata
- `report.md` - human-friendly summary package
- `agent_context.txt` - compact context text for AI agents
- `frames/` - extracted JPEG frames
- `transcript.json` - transcript segments with timestamps

## Notes

- For URL sources, English subtitles via `yt-dlp` are tried first (no API cost when captions exist).
- If there is still no transcript and `DEEPGRAM_API_KEY` is set, the script strips audio with `ffmpeg` and sends WAV to Deepgram.
- If there is still no transcript and `SUPERDATA_API_KEY` is set, the script asks Super Data last.
- This project is intentionally lightweight and uses Python stdlib only.

