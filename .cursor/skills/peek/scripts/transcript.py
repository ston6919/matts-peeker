from __future__ import annotations

from pathlib import Path
import re
import subprocess
from urllib import request, error
import json
import os

from common import TranscriptSegment
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


def _read_export_from_zshrc(var_name: str) -> str | None:
    zshrc_path = Path.home() / ".zshrc"
    if not zshrc_path.exists():
        return None

    pattern = re.compile(
        rf'^\s*export\s+{re.escape(var_name)}=(?:"([^"]*)"|\'([^\']*)\'|([^\s#]+))\s*(?:#.*)?$'
    )
    for line in zshrc_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1) or match.group(2) or match.group(3) or ""
        value = value.strip()
        if value:
            return value
    return None


def _extract_audio_mp3(video_path: Path, out_dir: Path) -> Path:
    audio_path = out_dir / "audio.mp3"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True)
    if not audio_path.exists():
        raise RuntimeError("Audio extraction did not produce an MP3 file.")
    return audio_path


def _fetch_deepgram_transcript(audio_path: Path) -> list[TranscriptSegment]:
    api_key = os.getenv("DEEPGRAM_API_KEY") or _read_export_from_zshrc("DEEPGRAM_API_KEY")
    if not api_key:
        return []

    endpoint = (
        "https://api.deepgram.com/v1/listen"
        "?model=nova-2&smart_format=true&punctuate=true&utterances=true"
    )
    audio_bytes = audio_path.read_bytes()
    req = request.Request(
        endpoint,
        method="POST",
        data=audio_bytes,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/mpeg",
        },
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []

    results = payload.get("results") or {}
    utterances = results.get("utterances") or []
    segments: list[TranscriptSegment] = []
    for utt in utterances:
        text = (utt.get("transcript") or "").strip()
        if not text:
            continue
        try:
            start = float(utt.get("start", 0.0))
            end = float(utt.get("end", start))
        except (TypeError, ValueError):
            start = 0.0
            end = 0.0
        segments.append(
            TranscriptSegment(
                start_seconds=start,
                end_seconds=end,
                text=text,
                source="deepgram",
            )
        )
    return segments


def get_transcript(video_source: str, video_path: Path, working_dir: Path) -> list[TranscriptSegment]:
    # Primary: Native/auto captions for URL sources
    if video_source.startswith("http://") or video_source.startswith("https://"):
        subtitle_dir = working_dir / "subtitle_tmp"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        try:
            vtt_files = _download_subtitles(video_source, subtitle_dir)
        except subprocess.CalledProcessError:
            vtt_files = []

        out: list[TranscriptSegment] = []
        for vtt_file in vtt_files:
            out.extend(_parse_vtt_file(vtt_file))
        if out:
            return out

    # Secondary: Deepgram from extracted MP3 audio
    audio_dir = working_dir / "audio_tmp"
    audio_dir.mkdir(parents=True, exist_ok=True)
    try:
        audio_file = _extract_audio_mp3(video_path, audio_dir)
    except subprocess.CalledProcessError:
        audio_file = None

    if audio_file is not None:
        deepgram_segments = _fetch_deepgram_transcript(audio_file)
        if deepgram_segments:
            return deepgram_segments

    # Fallback: Super Data API
    segments = fetch_superdata_transcript(video_source)
    if segments:
        return segments

    return []
