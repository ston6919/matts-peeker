from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess

from audio import extract_audio_for_transcription
from common import TranscriptSegment
from deepgram import transcribe_wav_with_deepgram
from superdata import fetch_superdata_transcript


VTT_TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
)


def _parse_hhmmss(value: str) -> float:
    hh, mm, ss = value.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


def _parse_vtt_file(path: Path) -> list[TranscriptSegment]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    segments: list[TranscriptSegment] = []
    i = 0
    while i < len(lines):
        match = VTT_TIME_RE.search(lines[i])
        if not match:
            i += 1
            continue

        start = _parse_hhmmss(match.group("start"))
        end = _parse_hhmmss(match.group("end"))
        i += 1

        buffer: list[str] = []
        while i < len(lines) and lines[i].strip():
            buffer.append(lines[i].strip())
            i += 1

        text = " ".join(buffer).strip()
        if text:
            segments.append(
                TranscriptSegment(
                    start_seconds=start,
                    end_seconds=end,
                    text=text,
                    source="captions",
                )
            )
    return segments


def _download_subtitles(url: str, out_dir: Path) -> list[Path]:
    out_tpl = str(out_dir / "subs")
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-sub",
        "--write-auto-sub",
        "--sub-langs",
        "en.*",
        "--sub-format",
        "vtt",
        "-o",
        out_tpl,
        url,
    ]
    subprocess.run(cmd, check=True)
    return sorted(out_dir.glob("subs*.vtt"))


def _transcribe_via_deepgram(video_file: Path, working_dir: Path) -> list[TranscriptSegment]:
    """Always strip audio with ffmpeg, then send WAV to Deepgram."""
    if not os.getenv("DEEPGRAM_API_KEY"):
        return []

    audio_path = working_dir / "peeker_transcription_audio.wav"
    try:
        extract_audio_for_transcription(video_file, audio_path)
        return transcribe_wav_with_deepgram(audio_path)
    except subprocess.CalledProcessError:
        return []


def get_transcript(video_source: str, working_dir: Path, video_file: Path) -> list[TranscriptSegment]:
    # 1) Free path first: English captions via yt-dlp (URL sources only).
    if video_source.startswith("http://") or video_source.startswith("https://"):
        subtitle_dir = working_dir / "subtitle_tmp"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        try:
            vtt_files = _download_subtitles(video_source, subtitle_dir)
        except subprocess.CalledProcessError:
            vtt_files = []

        caption_segments: list[TranscriptSegment] = []
        for vtt_file in vtt_files:
            caption_segments.extend(_parse_vtt_file(vtt_file))
        if caption_segments:
            return caption_segments

    # 2) Deepgram on ffmpeg-stripped audio (mono WAV, no video).
    deepgram_segments = _transcribe_via_deepgram(video_file, working_dir)
    if deepgram_segments:
        return deepgram_segments

    # 3) Super Data last.
    return fetch_superdata_transcript(video_source)
