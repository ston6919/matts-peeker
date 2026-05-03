from __future__ import annotations

from pathlib import Path
import subprocess


def is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def download_video(source: str, working_dir: Path) -> Path:
    """Download video for URL sources and return local path."""
    output_template = str(working_dir / "video.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        source,
    ]
    subprocess.run(cmd, check=True)

    matches = sorted(working_dir.glob("video.*"))
    if not matches:
        raise RuntimeError("Video download did not produce an output file.")
    return matches[0]
