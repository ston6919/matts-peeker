from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-2.5-flash"


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


def _jpeg_data_url(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.standard_b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _extract_json_array(text: str) -> list[dict[str, Any]] | None:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            parsed = json.loads(fence.group(1).strip())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def describe_frames_openrouter(
    frame_paths: list[Path],
    question: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    batch_size: int | None = None,
) -> list[str | None]:
    """
    Returns one description string per frame (same order as frame_paths).
    Uses batched OpenRouter vision calls (multiple images per request).
    """
    if not frame_paths:
        return []

    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        return [None] * len(frame_paths)

    mdl = (model or os.getenv("OPENROUTER_MODEL") or DEFAULT_MODEL).strip()
    bs = batch_size if batch_size is not None else _env_int("OPENROUTER_VISION_BATCH_SIZE", 8)

    out: list[str | None] = [None] * len(frame_paths)
    for start in range(0, len(frame_paths), bs):
        batch = frame_paths[start : start + bs]
        batch_labels = list(range(start + 1, start + len(batch) + 1))
        descriptions = _describe_batch(key, mdl, batch, batch_labels, question)
        for i, desc in enumerate(descriptions):
            if start + i < len(out):
                out[start + i] = desc
    return out


def _describe_batch(
    api_key: str,
    model: str,
    paths: list[Path],
    global_indices_1based: list[int],
    question: str,
) -> list[str | None]:
    instruction = (
        "These images are consecutive frames from a video, sampled at one frame per second, "
        "in the order given. The viewer's question (for context only) is:\n"
        f"{question}\n\n"
        "Return ONLY valid JSON: a JSON array with exactly one object per image, in order. "
        "Each object must have keys:\n"
        '- "frame": global frame number (integer, matching the label before each image)\n'
        '- "description": a concise English description of what is visible (on-screen text, people, actions, setting).\n'
        "Example shape:\n"
        '[{"frame": 1, "description": "..."}, {"frame": 2, "description": "..."}]\n'
    )

    content: list[dict[str, Any]] = [{"type": "text", "text": instruction}]
    for idx, p in zip(global_indices_1based, paths, strict=True):
        content.append({"type": "text", "text": f"Frame {idx}:"})
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": _jpeg_data_url(p)},
            }
        )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
        "max_tokens": 8192,
    }

    req = urllib.request.Request(
        OPENROUTER_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/peeker-local",
            "X-Title": "Matt's Peeker",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        err = f"[vision error] {exc}"
        return [err] * len(paths)

    try:
        msg = body["choices"][0]["message"].get("content")
        if msg is None:
            return ["[vision error] empty model response"] * len(paths)
        if isinstance(msg, list):
            text = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in msg
            )
        else:
            text = str(msg)
    except (KeyError, IndexError, TypeError):
        return ["[vision error] unexpected API response shape"] * len(paths)

    rows = _extract_json_array(text)
    if not rows:
        return [text[:500] + ("..." if len(text) > 500 else "")] * len(paths)

    by_frame: dict[int, str] = {}
    ordered_desc: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        desc = row.get("description")
        if not isinstance(desc, str):
            continue
        text_d = desc.strip()
        ordered_desc.append(text_d)
        fi = row.get("frame")
        if isinstance(fi, int):
            by_frame[fi] = text_d

    result: list[str | None] = []
    for idx in global_indices_1based:
        result.append(by_frame.get(idx))

    if all(r is None for r in result) and len(ordered_desc) == len(paths):
        return ordered_desc

    if any(r is None for r in result) and len(ordered_desc) == len(paths):
        for i in range(len(result)):
            if result[i] is None and i < len(ordered_desc):
                result[i] = ordered_desc[i]
    return result
