from __future__ import annotations

from pathlib import Path
import subprocess


def extract_audio_for_transcription(video_path: Path, out_wav: Path) -> Path:
    """Strip video to mono 16 kHz WAV for speech APIs (no video stream)."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(out_wav),
    ]
    subprocess.run(cmd, check=True)
    return out_wav
