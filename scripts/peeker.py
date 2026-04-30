#!/usr/bin/env python3
from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import os
import shutil
import sys

from common import ensure_dir
from downloader import download_video, is_url
from frames import extract_frames
from report import build_report_package
from transcript import get_transcript


def parse_args() -> object:
    parser = ArgumentParser(description="Matt's Peeker video analysis with Super Data + packaged output.")
    parser.add_argument("--source", required=True, help="Public URL or local video path")
    parser.add_argument("--question", required=True, help="Question to guide analysis")
    parser.add_argument("--out-dir", required=True, help="Output directory for run artifacts")
    parser.add_argument("--max-frames", type=int, default=100, help="Hard cap on extracted frames")
    parser.add_argument("--resolution", type=int, default=512, help="Frame width in pixels")
    parser.add_argument("--fps", type=float, default=None, help="Optional fps override")
    return parser.parse_args()


def resolve_video_file(source: str, working_dir: Path) -> Path:
    if is_url(source):
        return download_video(source, working_dir)

    local = Path(source).expanduser().resolve()
    if not local.exists():
        raise FileNotFoundError(f"Local file not found: {local}")
    return local


def print_env_hints() -> None:
    if not os.getenv("DEEPGRAM_API_KEY"):
        print("[hint] DEEPGRAM_API_KEY not set; Deepgram step skipped after captions.")
    if not os.getenv("SUPERDATA_API_KEY"):
        print("[hint] SUPERDATA_API_KEY not set; Super Data fallback disabled.")


def main() -> int:
    args = parse_args()
    out_dir = ensure_dir(Path(args.out_dir).expanduser().resolve())
    working_dir = ensure_dir(out_dir / "working")
    frame_dir = ensure_dir(out_dir / "frames")

    print_env_hints()
    print(f"[run] source={args.source}")
    print(f"[run] out_dir={out_dir}")

    try:
        video_file = resolve_video_file(args.source, working_dir)
        print(f"[ok] video_file={video_file}")

        frames, fps = extract_frames(
            video_path=video_file,
            frame_dir=frame_dir,
            resolution=args.resolution,
            max_frames=args.max_frames,
            fps_override=args.fps,
        )
        print(f"[ok] extracted_frames={len(frames)} fps={fps:.3f}")

        transcript_segments = get_transcript(args.source, working_dir, video_file)
        print(f"[ok] transcript_segments={len(transcript_segments)}")

        report = build_report_package(
            out_dir=out_dir,
            source=args.source,
            question=args.question,
            video_path=video_file,
            fps=fps,
            frames=frames,
            transcript_segments=transcript_segments,
        )

        print("")
        print("=== Matt's Peeker Output Package ===")
        print(f"report.json: {out_dir / 'report.json'}")
        print(f"report.md: {out_dir / 'report.md'}")
        print(f"agent_context.txt: {out_dir / 'agent_context.txt'}")
        print(f"frames_dir: {frame_dir}")
        print(f"frame_count: {report['stats']['frame_count']}")
        print(f"transcript_segments: {report['stats']['transcript_segment_count']}")
        return 0
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    finally:
        if working_dir.exists():
            shutil.rmtree(working_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
