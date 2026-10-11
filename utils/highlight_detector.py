"""
Advanced highlight / viral moment detector.
Combines audio energy peaks + optional Whisper transcription + keyword boost.
"""

import numpy as np
from pydub import AudioSegment
from moviepy import VideoFileClip
import tempfile
import os
import re
from typing import List, Dict, Tuple, Optional

# Viral keywords (ID + EN) that often indicate high-engagement moments
VIRAL_KEYWORDS = [
    # Indonesian
    r"\bgila\b", r"\banjir\b", r"\bwtf\b", r"\bomg\b", r"\basu\b", r"\bbangsat\b",
    r"\bgokil\b", r"\bkocak\b", r"\bparah\b", r"\bgila sih\b", r"\bngakak\b",
    r"\bwkwk\b", r"\bwkwkwk\b", r"\bhaha\b", r"\bhahaha\b", r"\blmao\b",
    r"\bno way\b", r"\bwhat the\b", r"\bsialan\b", r"\bamput\b", r"\baduh\b",
    r"\bwow\b", r"\bwahh\b", r"\bgila banget\b", r"\bclutch\b",
    # English
    r"\binsane\b", r"\bcrazy\b", r"\bholy\b", r"\bfuck\b", r"\bshit\b",
    r"\bomg\b", r"\bno way\b", r"\bwhat\b", r"\bunbelievable\b", r"\blets go\b",
    r"\bgg\b", r"\bace\b", r"\bclutch\b", r"\bnice\b", r"\bbro\b",
]

VIRAL_KEYWORDS_RE = [re.compile(k, re.IGNORECASE) for k in VIRAL_KEYWORDS]


def extract_audio_from_video(video_path: str) -> AudioSegment:
    """Extract audio track as pydub AudioSegment."""
    clip = VideoFileClip(video_path)
    if clip.audio is None:
        clip.close()
        raise ValueError("Video tidak memiliki audio track.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    clip.audio.write_audiofile(tmp_path, logger=None)
    clip.close()

    audio = AudioSegment.from_wav(tmp_path)
    os.unlink(tmp_path)
    return audio


def compute_energy_profile(audio: AudioSegment, window_ms: int = 150) -> Tuple[np.ndarray, np.ndarray]:
    """Compute RMS energy over sliding windows. Returns times (sec), energies."""
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    sample_rate = audio.frame_rate
    window_size = int(sample_rate * window_ms / 1000)
    hop = max(window_size // 2, 1)

    energies = []
    times = []
    for i in range(0, len(samples) - window_size, hop):
        window = samples[i : i + window_size]
        rms = np.sqrt(np.mean(window ** 2))
        energies.append(rms)
        times.append(i / sample_rate)

    return np.array(times), np.array(energies)


def find_peaks(
    times: np.ndarray,
    energies: np.ndarray,
    min_distance_sec: float = 3.0,
    prominence_factor: float = 1.4,
    top_k: int = 15,
) -> List[Dict]:
    """Find significant energy peaks."""
    if len(energies) == 0:
        return []

    mean_e = np.mean(energies)
    std_e = np.std(energies) + 1e-6
    threshold = mean_e + prominence_factor * std_e

    candidates = []
    for i in range(1, len(energies) - 1):
        if energies[i] > energies[i - 1] and energies[i] > energies[i + 1] and energies[i] > threshold:
            candidates.append((times[i], energies[i], i))

    candidates.sort(key=lambda x: x[1], reverse=True)

    selected = []
    for t, e, idx in candidates:
        if all(abs(t - s["time"]) >= min_distance_sec for s in selected):
            selected.append({"time": float(t), "energy": float(e), "index": idx})
        if len(selected) >= top_k:
            break

    selected.sort(key=lambda x: x["time"])
    return selected


def score_from_energy(energy: float, all_energies: np.ndarray) -> float:
    """Base viral score 0-100 from energy percentile + relative strength."""
    if len(all_energies) == 0:
        return 40.0
    percentile = (np.sum(all_energies < energy) / len(all_energies)) * 100
    relative = energy / (np.mean(all_energies) + 1e-6)
    score = min(95.0, percentile * 0.55 + min(relative * 12, 35))
    return float(score)


def transcribe_with_whisper(video_path: str, model_size: str = "tiny") -> List[Dict]:
    """
    Transcribe video with Whisper.
    Returns list of segments: [{"start": float, "end": float, "text": str}, ...]
    """
    try:
        import whisper
        model = whisper.load_model(model_size)
        result = model.transcribe(video_path, language=None, verbose=False, fp16=False)
        segments = []
        for seg in result.get("segments", []):
            segments.append({
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "text": seg["text"].strip(),
            })
        return segments
    except Exception as e:
        print(f"Whisper error: {e}")
        return []


def find_keyword_hits(segments: List[Dict]) -> List[Dict]:
    """Find timestamps where viral keywords appear."""
    hits = []
    for seg in segments:
        text = seg["text"]
        for pattern in VIRAL_KEYWORDS_RE:
            if pattern.search(text):
                hits.append({
                    "time": (seg["start"] + seg["end"]) / 2,
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "keyword": pattern.pattern,
                })
                break
    return hits


def detect_highlights(
    video_path: str,
    top_k: int = 10,
    min_distance_sec: float = 4.0,
    clip_padding: float = 2.5,
    use_whisper: bool = False,
    whisper_model: str = "tiny",
) -> List[Dict]:
    """
    Main detection pipeline.
    Returns list of highlight dicts sorted by viral_score desc.
    """
    audio = extract_audio_from_video(video_path)
    times, energies = compute_energy_profile(audio, window_ms=150)
    peaks = find_peaks(times, energies, min_distance_sec=min_distance_sec, top_k=top_k * 2)

    video_duration = times[-1] if len(times) > 0 else 0.0

    keyword_hits = []
    all_segments = []
    if use_whisper:
        all_segments = transcribe_with_whisper(video_path, model_size=whisper_model)
        keyword_hits = find_keyword_hits(all_segments)

    highlights = []

    # 1. From audio peaks
    for p in peaks:
        peak_t = p["time"]
        start = max(0.0, peak_t - clip_padding)
        end = min(video_duration, peak_t + clip_padding + 1.8)
        base_score = score_from_energy(p["energy"], energies)

        matched_text = None
        for hit in keyword_hits:
            if abs(hit["time"] - peak_t) < 4.0:
                base_score = min(100.0, base_score + 18)
                matched_text = hit["text"]
                break

        highlights.append({
            "peak_time": round(peak_t, 2),
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "energy": round(p["energy"], 2),
            "viral_score": round(base_score, 1),
            "label": f"Audio Peak @ {peak_t:.1f}s",
            "source": "audio",
            "transcript": matched_text,
            "keywords_found": bool(matched_text),
        })

    # 2. Extra highlights from strong keyword hits
    for hit in keyword_hits:
        if any(abs(h["peak_time"] - hit["time"]) < min_distance_sec for h in highlights):
            continue
        peak_t = hit["time"]
        start = max(0.0, hit["start"] - 1.5)
        end = min(video_duration, hit["end"] + 2.5)
        score = 72.0

        highlights.append({
            "peak_time": round(peak_t, 2),
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "energy": 0.0,
            "viral_score": round(score, 1),
            "label": f"Keyword @ {peak_t:.1f}s",
            "source": "keyword",
            "transcript": hit["text"],
            "keywords_found": True,
        })

    # Deduplicate keeping highest score
    highlights.sort(key=lambda x: x["viral_score"], reverse=True)
    final = []
    for h in highlights:
        if all(abs(h["peak_time"] - f["peak_time"]) >= min_distance_sec for f in final):
            final.append(h)
        if len(final) >= top_k:
            break

    # Attach transcript snippet for the clip range
    if all_segments:
        for h in final:
            texts = [
                s["text"] for s in all_segments
                if s["end"] >= h["start"] and s["start"] <= h["end"]
            ]
            if texts and not h.get("transcript"):
                h["transcript"] = " ".join(texts)

    return final


def generate_viral_titles(highlight: Dict, max_titles: int = 5) -> List[str]:
    """Generate clickbait-style title suggestions."""
    score = highlight.get("viral_score", 50)
    transcript = (highlight.get("transcript") or "").lower()

    templates = [
        "Momen ini bikin gue ngakak 😂",
        "GILA BANGET SIH INI 🔥",
        "Nggak nyangka bakalan begini...",
        "Clutch of the year??",
        "Reaksi paling jujur 😭",
        "Ini yang bikin viral!",
        "Waduh parah banget 💀",
        "OMG moment yang wajib ditonton",
        "Sampai kaget sendiri 😳",
        "Highlight terlucu hari ini",
    ]

    if any(w in transcript for w in ["gila", "anjir", "parah", "gokil"]):
        templates.insert(0, "ANJIR GILA BANGET 🔥🔥")
    if any(w in transcript for w in ["clutch", "ace", "gg"]):
        templates.insert(0, "CLUTCH TERBAIK 👑")
    if score >= 85:
        templates.insert(0, "MOMEN VIRAL POTENTIAL 100% 🚀")

    return templates[:max_titles]
