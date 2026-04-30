from __future__ import annotations

from pathlib import Path
from typing import Any

from common import TranscriptSegment, seconds_to_timestamp, write_json
from frames import frame_index_from_filename, estimate_frame_timestamp


def build_report_package(
    out_dir: Path,
    source: str,
    question: str,
    video_path: Path,
    fps: float,
    frames: list[Path],
    transcript_segments: list[TranscriptSegment],
) -> dict[str, Any]:
    frame_rows = []
    for frame in frames:
        idx = frame_index_from_filename(frame)
        frame_rows.append(
            {
                "frame_index": idx,
                "timestamp_seconds": estimate_frame_timestamp(idx, fps),
                "timestamp": seconds_to_timestamp(estimate_frame_timestamp(idx, fps)),
                "path": str(frame.resolve()),
            }
        )

    transcript_rows = [
        {
            "start_seconds": seg.start_seconds,
            "end_seconds": seg.end_seconds,
            "start": seconds_to_timestamp(seg.start_seconds),
            "end": seconds_to_timestamp(seg.end_seconds),
            "text": seg.text,
            "source": seg.source,
        }
        for seg in transcript_segments
    ]

    report = {
        "source": source,
        "question": question,
        "video_path": str(video_path.resolve()),
        "stats": {
            "frame_count": len(frame_rows),
            "transcript_segment_count": len(transcript_rows),
            "frame_fps": fps,
        },
        "frames": frame_rows,
        "transcript_segments": transcript_rows,
    }

    write_json(out_dir / "report.json", report)
    write_json(out_dir / "transcript.json", transcript_rows)
    _write_markdown_report(out_dir / "report.md", report)
    _write_agent_context(out_dir / "agent_context.txt", report)
    return report


def _write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Video Analysis Package")
    lines.append("")
    lines.append(f"- Source: `{report['source']}`")
    lines.append(f"- Question: {report['question']}")
    lines.append(f"- Video File: `{report['video_path']}`")
    lines.append(f"- Frames: {report['stats']['frame_count']}")
    lines.append(f"- Transcript Segments: {report['stats']['transcript_segment_count']}")
    lines.append("")
    lines.append("## Timeline Snapshot")
    lines.append("")
    for row in report["frames"][:20]:
        lines.append(f"- {row['timestamp']} -> `{row['path']}`")
    if len(report["frames"]) > 20:
        lines.append("- ... additional frames omitted in markdown view ...")
    lines.append("")
    lines.append("## Transcript Excerpts")
    lines.append("")
    for seg in report["transcript_segments"][:40]:
        lines.append(f"- [{seg['start']} - {seg['end']}] {seg['text']}")
    if len(report["transcript_segments"]) > 40:
        lines.append("- ... additional transcript segments omitted in markdown view ...")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_agent_context(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("VIDEO CONTEXT PACKAGE")
    lines.append(f"QUESTION: {report['question']}")
    lines.append(f"SOURCE: {report['source']}")
    lines.append("")
    lines.append("FRAMES:")
    for row in report["frames"]:
        lines.append(f"- t={row['timestamp']} file={row['path']}")
    lines.append("")
    lines.append("TRANSCRIPT:")
    for seg in report["transcript_segments"]:
        lines.append(f"- t={seg['start']}-{seg['end']}: {seg['text']}")
    path.write_text("\n".join(lines), encoding="utf-8")
