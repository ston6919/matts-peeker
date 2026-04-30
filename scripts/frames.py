from __future__ import annotations

from pathlib import Path
import subprocess


def probe_duration_seconds(video_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def pick_frame_budget(duration_seconds: float, max_frames: int) -> int:
    if duration_seconds <= 30:
        return min(max_frames, 30)
    if duration_seconds <= 60:
        return min(max_frames, 40)
    if duration_seconds <= 180:
        return min(max_frames, 60)
    if duration_seconds <= 600:
        return min(max_frames, 80)
    return min(max_frames, 100)


def extract_frames(
    video_path: Path,
    frame_dir: Path,
    resolution: int,
    max_frames: int,
    fps_override: float | None = None,
) -> tuple[list[Path], float]:
    frame_dir.mkdir(parents=True, exist_ok=True)
    duration_seconds = probe_duration_seconds(video_path)
    budget = pick_frame_budget(duration_seconds, max_frames)

    if fps_override is not None:
        fps = min(2.0, max(0.1, fps_override))
    else:
        fps = min(2.0, max(0.1, budget / max(duration_seconds, 1.0)))

    output_pattern = str(frame_dir / "frame_%05d.jpg")
    vf = f"fps={fps},scale={resolution}:-1"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-q:v",
        "2",
        output_pattern,
    ]
    subprocess.run(cmd, check=True)

    frames = sorted(frame_dir.glob("frame_*.jpg"))
    return frames, fps


def estimate_frame_timestamp(index: int, fps: float) -> float:
    # ffmpeg frame extraction numbering starts at 1.
    return max(0.0, (index - 1) / max(fps, 0.0001))


def frame_index_from_filename(path: Path) -> int:
    stem = path.stem
    return int(stem.split("_")[-1])
