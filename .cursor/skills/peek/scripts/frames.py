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


def extract_frames(
    video_path: Path,
    frame_dir: Path,
    resolution: int,
    max_frames: int,
    fps_override: float | None = None,
) -> tuple[list[Path], float]:
    frame_dir.mkdir(parents=True, exist_ok=True)

    # Default: one frame per second ("every second"). Override with --fps.
    if fps_override is not None:
        fps = max(0.1, fps_override)
    else:
        fps = 1.0

    output_pattern = str(frame_dir / "frame_%05d.jpg")
    vf = f"fps={fps},scale={resolution}:-1"
    cap = max(1, max_frames)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-frames:v",
        str(cap),
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
