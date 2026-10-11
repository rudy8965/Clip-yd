"""
Reaction Layout generator for Clipper style.
Supports:
1. Top-Bottom Split (atas = wajah reactor, bawah = konten) ← style contoh user
2. PiP style (konten full + wajah kecil di pojok)
"""

import os
import tempfile
from typing import Optional, Tuple
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from moviepy import VideoFileClip, CompositeVideoClip, TextClip


def detect_face_region(video_path: str, sample_times: list = None) -> Optional[Tuple[int, int, int, int]]:
    """
    Detect the largest face across a few sample frames.
    Returns (x, y, w, h) or None.
    """
    if not HAS_CV2:
        return None

    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        if sample_times is None:
            sample_times = [0.5, duration * 0.3, duration * 0.6]

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)

        best_face = None
        best_area = 0

        for t in sample_times:
            t = min(max(0.1, t), duration - 0.1)
            frame = clip.get_frame(t)
            gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(50, 50)
            )
            for (x, y, w, h) in faces:
                area = w * h
                if area > best_area:
                    best_area = area
                    # Expand face box a bit
                    pad = int(max(w, h) * 0.4)
                    x = max(0, x - pad)
                    y = max(0, y - pad)
                    w = min(frame.shape[1] - x, w + pad * 2)
                    h = min(frame.shape[0] - y, h + pad * 2)
                    best_face = (x, y, w, h)

        clip.close()
        return best_face
    except Exception as e:
        print(f"Face detect error: {e}")
        return None


def make_split_reaction(
    video_path: str,
    output_path: str,
    face_ratio: float = 0.42,          # berapa persen tinggi untuk bagian wajah (atas)
    add_text: bool = True,
    text_content: str = "+1000 AURA",
    max_duration: float = 45.0,
) -> str:
    """
    Buat layout Top-Bottom Split (gaya Clipper Indonesia).
    Atas = crop wajah reactor, Bawah = video asli.
    """
    video = VideoFileClip(video_path)

    if video.duration > max_duration:
        video = video.subclipped(0, max_duration)

    target_w, target_h = 1080, 1920
    face_h = int(target_h * face_ratio)
    content_h = target_h - face_h

    # --- Bagian ATAS: wajah ---
    face_box = detect_face_region(video_path)

    if face_box is not None:
        fx, fy, fw, fh = face_box
        # Buat crop persegi di sekitar wajah
        side = max(fw, fh)
        cx = fx + fw // 2
        cy = fy + fh // 2
        x1 = max(0, cx - side // 2)
        y1 = max(0, cy - side // 2)
        x2 = min(video.w, x1 + side)
        y2 = min(video.h, y1 + side)
        face_clip = video.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    else:
        # Fallback: ambil bagian atas tengah (umum untuk face cam)
        side = min(video.w, int(video.h * 0.55))
        x1 = (video.w - side) // 2
        y1 = 0
        face_clip = video.cropped(x1=x1, y1=y1, x2=x1 + side, y2=y1 + side)

    face_clip = face_clip.resized((target_w, face_h))

    # --- Bagian BAWAH: konten asli (center crop ke 9:16) ---
    w, h = video.size
    target_ratio = target_w / content_h
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x1 = (w - new_w) // 2
        content = video.cropped(x1=x1, y1=0, x2=x1 + new_w, y2=h)
    else:
        new_h = int(w / target_ratio)
        y1 = (h - new_h) // 2
        content = video.cropped(x1=0, y1=y1, x2=w, y2=y1 + new_h)

    content = content.resized((target_w, content_h))
    content = content.with_position((0, face_h))

    clips = [face_clip, content]

    # --- Teks ---
    if add_text and text_content.strip():
        try:
            txt = TextClip(
                text=text_content,
                font_size=60,
                color="white",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(target_w - 80, None),
            )
            txt = txt.with_duration(video.duration).with_position(("center", face_h + 30))
            clips.append(txt)
        except Exception:
            pass

    final = CompositeVideoClip(clips, size=(target_w, target_h))
    final = final.with_duration(video.duration)
    if video.audio:
        final = final.with_audio(video.audio)

    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=min(30, video.fps or 30),
        preset="ultrafast",
        threads=2,
        logger=None,
    )

    final.close()
    video.close()
    return output_path


def make_reaction_layout(
    video_path: str,
    output_path: str,
    style: str = "split",              # "split" atau "pip"
    pip_position: str = "bottom_left",
    add_text: bool = True,
    text_content: str = "+1000 AURA",
    max_duration: float = 45.0,
) -> str:
    """
    Entry point. style="split" → top-bottom (contoh user)
                 style="pip"   → full content + wajah kecil di pojok
    """
    if style == "pip":
        return _make_pip(
            video_path, output_path, pip_position, add_text, text_content, max_duration
        )
    else:
        return make_split_reaction(
            video_path, output_path, add_text=add_text, text_content=text_content, max_duration=max_duration
        )


def _make_pip(
    video_path: str,
    output_path: str,
    pip_position: str = "bottom_left",
    add_text: bool = True,
    text_content: str = "LAUGH ON",
    max_duration: float = 45.0,
) -> str:
    """PiP style: konten full + wajah kecil di pojok."""
    video = VideoFileClip(video_path)
    if video.duration > max_duration:
        video = video.subclipped(0, max_duration)

    target_w, target_h = 1080, 1920

    # Main content center crop 9:16
    w, h = video.size
    target_ratio = 9 / 16
    current_ratio = w / h
    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x1 = (w - new_w) // 2
        main = video.cropped(x1=x1, y1=0, x2=x1 + new_w, y2=h)
    else:
        new_h = int(w / target_ratio)
        y1 = (h - new_h) // 2
        main = video.cropped(x1=0, y1=y1, x2=w, y2=y1 + new_h)
    main = main.resized((target_w, target_h))

    # Face PiP
    face_box = detect_face_region(video_path)
    if face_box is not None:
        fx, fy, fw, fh = face_box
        side = max(fw, fh)
        cx, cy = fx + fw // 2, fy + fh // 2
        x1 = max(0, cx - side // 2)
        y1 = max(0, cy - side // 2)
        x2 = min(video.w, x1 + side)
        y2 = min(video.h, y1 + side)
        pip_src = video.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    else:
        side = min(video.w, video.h) // 2
        x1 = (video.w - side) // 2
        pip_src = video.cropped(x1=x1, y1=0, x2=x1 + side, y2=side)

    pip_w = int(target_w * 0.30)
    pip = pip_src.resized((pip_w, pip_w))
    margin = 40
    if pip_position == "bottom_right":
        pos = (target_w - pip_w - margin, target_h - pip_w - margin - 60)
    else:
        pos = (margin, target_h - pip_w - margin - 60)
    pip = pip.with_position(pos)

    clips = [main, pip]

    if add_text and text_content.strip():
        try:
            txt = TextClip(
                text=text_content,
                font_size=65,
                color="white",
                stroke_color="black",
                stroke_width=3,
                method="caption",
                size=(target_w - 80, None),
            )
            txt = txt.with_duration(main.duration).with_position(("center", 60))
            clips.append(txt)
        except Exception:
            pass

    final = CompositeVideoClip(clips, size=(target_w, target_h)).with_duration(main.duration)
    if video.audio:
        final = final.with_audio(video.audio)

    final.write_videofile(
        output_path, codec="libx264", audio_codec="aac",
        fps=min(30, video.fps or 30), preset="ultrafast", threads=2, logger=None
    )
    final.close()
    video.close()
    return output_path
