from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib import request, error
from urllib.parse import urlencode
import json
import os

from common import TranscriptSegment


def transcribe_wav_with_deepgram(wav_path: Path) -> list[TranscriptSegment]:
    """Send stripped WAV to Deepgram prerecorded listen API."""
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key or not wav_path.is_file():
        return []

    model = os.getenv("DEEPGRAM_MODEL", "nova-2")
    query = urlencode(
        {
            "model": model,
            "smart_format": "true",
            "punctuate": "true",
        }
    )
    url = f"https://api.deepgram.com/v1/listen?{query}"
    body = wav_path.read_bytes()
    req = request.Request(
        url,
        method="POST",
        data=body,
        headers={
            "Authorization": f"Token {api_key}",
            "Content-Type": "audio/wav",
        },
    )

    try:
        with request.urlopen(req, timeout=120) as resp:
            payload: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []

    try:
        alt = payload["results"]["channels"][0]["alternatives"][0]
    except (KeyError, IndexError, TypeError):
        return []

    return _alternative_to_segments(alt)


def _alternative_to_segments(alt: dict[str, Any]) -> list[TranscriptSegment]:
    out: list[TranscriptSegment] = []

    paragraphs = (alt.get("paragraphs") or {}).get("paragraphs") or []
    for para in paragraphs:
        for sent in para.get("sentences") or []:
            text = (sent.get("text") or "").strip()
            if not text:
                continue
            out.append(
                TranscriptSegment(
                    start_seconds=float(sent.get("start", 0)),
                    end_seconds=float(sent.get("end", 0)),
                    text=text,
                    source="deepgram",
                )
            )
    if out:
        return out

    words = alt.get("words") or []
    if words:
        return _words_to_segments(words)

    full = (alt.get("transcript") or "").strip()
    if full:
        return [TranscriptSegment(0.0, 0.0, full, "deepgram")]
    return []


def _words_to_segments(words: list[dict[str, Any]], max_span_seconds: float = 10.0) -> list[TranscriptSegment]:
    out: list[TranscriptSegment] = []
    chunk: list[dict[str, Any]] = []
    chunk_start: float | None = None

    for w in words:
        piece = (w.get("punctuated_word") or w.get("word") or "").strip()
        if not piece:
            continue
        start = float(w.get("start", 0))
        end = float(w.get("end", start))

        if chunk_start is None:
            chunk_start = start
            chunk = [w]
            continue

        if end - chunk_start > max_span_seconds:
            _flush_word_chunk(out, chunk)
            chunk_start = start
            chunk = [w]
        else:
            chunk.append(w)

    _flush_word_chunk(out, chunk)
    return out


def _flush_word_chunk(out: list[TranscriptSegment], chunk: list[dict[str, Any]]) -> None:
    if not chunk:
        return
    parts: list[str] = []
    for w in chunk:
        t = (w.get("punctuated_word") or w.get("word") or "").strip()
        if t:
            parts.append(t)
    text = " ".join(parts).strip()
    if not text:
        return
    start = float(chunk[0].get("start", 0))
    end = float(chunk[-1].get("end", start))
    out.append(TranscriptSegment(start, end, text, "deepgram"))
