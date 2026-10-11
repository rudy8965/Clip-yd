"""
Simple caption / subtitle helpers.
Generate SRT and optionally burn text into video (basic).
"""

from typing import List, Dict
import tempfile
import os


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp HH:MM:SS,mmm"""
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt_from_segments(segments: List[Dict], start_offset: float = 0.0) -> str:
    """
    Create SRT content from Whisper-style segments.
    start_offset: shift all times (useful when clipping).
    """
    lines = []
    idx = 1
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        start = max(0.0, seg["start"] - start_offset)
        end = max(start + 0.3, seg["end"] - start_offset)
        lines.append(str(idx))
        lines.append(f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}")
        lines.append(text)
        lines.append("")
        idx += 1
    return "\n".join(lines)


def save_srt(content: str, prefix: str = "caption") -> str:
    """Save SRT to temp file and return path."""
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".srt", prefix=prefix).name
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def get_clip_segments(all_segments: List[Dict], clip_start: float, clip_end: float) -> List[Dict]:
    """Filter segments that overlap with [clip_start, clip_end] and shift times."""
    result = []
    for seg in all_segments:
        if seg["end"] < clip_start or seg["start"] > clip_end:
            continue
        result.append({
            "start": max(0.0, seg["start"] - clip_start),
            "end": min(clip_end - clip_start, seg["end"] - clip_start),
            "text": seg["text"],
        })
    return result
