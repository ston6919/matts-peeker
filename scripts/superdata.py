from __future__ import annotations

from typing import Any
from urllib import request, error
import json
import os

from common import TranscriptSegment


def _parse_seconds(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def fetch_superdata_transcript(video_source: str) -> list[TranscriptSegment]:
    """Best-effort Super Data transcript fetch.

    Expected API contract:
    POST {base_url}/v1/transcripts
    body: {"source": "<url-or-id>"}
    response: {"segments":[{"start":0.0,"end":1.2,"text":"..."}]}
    """
    api_key = os.getenv("SUPERDATA_API_KEY")
    if not api_key:
        return []

    base_url = os.getenv("SUPERDATA_API_BASE_URL", "https://api.superdata.ai").rstrip("/")
    endpoint = f"{base_url}/v1/transcripts"
    body = json.dumps({"source": video_source}).encode("utf-8")

    req = request.Request(
        endpoint,
        method="POST",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []

    segments_raw = payload.get("segments") or []
    segments: list[TranscriptSegment] = []
    for seg in segments_raw:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                start_seconds=_parse_seconds(seg.get("start")),
                end_seconds=_parse_seconds(seg.get("end")),
                text=text,
                source="superdata",
            )
        )
    return segments
