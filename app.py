"""
ViralClipper 🔥 - Full Featured MVP
Auto-detect momen viral + Whisper keywords + captions + batch + titles
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
from moviepy import VideoFileClip
import time

from utils.highlight_detector import detect_highlights, generate_viral_titles, transcribe_with_whisper
from utils.caption import generate_srt_from_segments, save_srt, get_clip_segments
from utils.reaction_layout import make_reaction_layout

# ---------------------- PAGE CONFIG ----------------------
st.set_page_config(
    page_title="ViralClipper 🔥",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------- CUSTOM CSS ----------------------
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #ff4b4b, #ff8c00, #ffcc00);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .sub-header { color: #999; font-size: 1.05rem; margin-bottom: 1.2rem; }
    .score-high { color: #00e676; font-weight: 700; font-size: 1.25rem; }
    .score-mid  { color: #ffab00; font-weight: 700; font-size: 1.25rem; }
    .score-low  { color: #ff5252; font-weight: 700; font-size: 1.25rem; }
    div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------- HEADER ----------------------
st.markdown('<div class="main-header">ViralClipper 🔥</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Upload video → Deteksi momen viral (Audio + AI Keyword) → Generate clip + caption + judul siap upload</div>',
    unsafe_allow_html=True,
)

# ---------------------- SIDEBAR ----------------------
with st.sidebar:
    st.header("⚙️ Pengaturan Deteksi")
    top_k = st.slider("Jumlah momen maksimal", 3, 20, 8)
    min_distance = st.slider("Jarak minimal antar momen (detik)", 2.0, 12.0, 4.0, 0.5)
    padding = st.slider("Padding sebelum/sesudah peak (detik)", 1.0, 6.0, 2.8, 0.5)

    st.markdown("---")
    st.header("🧠 AI Features")
    use_whisper = st.checkbox(
        "Gunakan Whisper (deteksi kata kunci + transcript)",
        value=False,
        help="Lebih akurat tapi lebih lambat (terutama di CPU). Model 'tiny' cukup cepat.",
    )
    whisper_model = st.selectbox(
        "Ukuran model Whisper",
        ["tiny", "base", "small"],
        index=0,
        disabled=not use_whisper,
        help="tiny = tercepat, small = lebih akurat",
    )

    st.markdown("---")
    st.header("🎬 Output")
    make_vertical = st.checkbox("Crop vertikal 9:16 (TikTok/Reels/Shorts)", value=True)
    generate_captions = st.checkbox("Generate file subtitle (.srt)", value=True)
    show_titles = st.checkbox("Tampilkan saran judul viral", value=True)

    st.markdown("---")
    st.header("😂 Reaction Mode")
    reaction_mode = st.selectbox(
        "Layout Reaction",
        ["Tidak aktif", "Split Atas-Bawah (contoh Clipper)", "PiP (wajah kecil di pojok)"],
        index=0,
        help="Ubah 1 video biasa jadi gaya reaction seperti contoh"
    )
    reaction_text = st.text_input("Teks overlay", value="+1000 AURA")
    add_reaction_text = st.checkbox("Tampilkan teks overlay", value=True)

    st.markdown("---")
    st.caption("Gratis • Open Source • Offline-first")
    st.caption("Whisper model di-download otomatis saat pertama kali dipakai.")

# ---------------------- MAIN: UPLOAD ----------------------
st.subheader("📁 Upload Video")
uploaded_files = st.file_uploader(
    "Pilih satu atau beberapa video (MP4, MOV, MKV, WebM, AVI)",
    type=["mp4", "mov", "mkv", "webm", "avi"],
    accept_multiple_files=True,
    help="Bisa batch! Disarankan video < 8-10 menit per file untuk proses nyaman.",
)

if not uploaded_files:
    st.info("👆 Upload minimal 1 video untuk mulai.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**🎮 Gaming**\nClutch • Ace • Fail • Rage")
    with col2:
        st.markdown("**🎙️ Stream / Podcast**\nTawa • Kontroversi • Drop")
    with col3:
        st.markdown("**😂 Reaction**\nKaget • Emosi tinggi")
    with col4:
        st.markdown("**📱 Short Content**\nSiap TikTok / Reels")
    st.stop()

# Process each uploaded file
for file_idx, uploaded_file in enumerate(uploaded_files):
    st.markdown("---")
    st.markdown(f"### 🎥 Video {file_idx + 1}: `{uploaded_file.name}`")

    # Save temp
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        video_path = tmp.name

    # Video info
    try:
        clip = VideoFileClip(video_path)
        duration = clip.duration
        fps = clip.fps or 30
        size = clip.size
        clip.close()
    except Exception as e:
        st.error(f"Gagal membaca video: {e}")
        if os.path.exists(video_path):
            os.unlink(video_path)
        continue

    st.caption(f"Durasi: **{duration:.1f}s** • Resolusi: {size[0]}x{size[1]} • FPS: {fps:.1f}")

    # Preview
    with st.expander("Preview video asli", expanded=False):
        st.video(video_path)

    # --- Reaction Layout Button ---
    if reaction_mode != "Tidak aktif":
        style = "split" if "Split" in reaction_mode else "pip"
        react_key = f"react_{file_idx}"
        if st.button(f"😂 Buat Reaction Layout — {uploaded_file.name}", key=react_key, type="secondary"):
            with st.spinner("Sedang membuat layout reaction (deteksi wajah + compose)..."):
                try:
                    out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    make_reaction_layout(
                        video_path,
                        out_path,
                        style=style,
                        add_text=add_reaction_text,
                        text_content=reaction_text,
                        max_duration=45.0,
                    )
                    st.session_state[f"reaction_out_{file_idx}"] = out_path
                    st.success("Reaction layout siap!")
                except Exception as e:
                    st.error(f"Gagal buat reaction layout: {e}")

        rkey = f"reaction_out_{file_idx}"
        if rkey in st.session_state and os.path.exists(st.session_state[rkey]):
            with open(st.session_state[rkey], "rb") as f:
                st.download_button(
                    label="⬇️ Download Reaction Clip",
                    data=f,
                    file_name=f"reaction_{Path(uploaded_file.name).stem}.mp4",
                    mime="video/mp4",
                    key=f"dl_react_{file_idx}",
                )
            st.video(st.session_state[rkey])

    detect_key = f"detect_{file_idx}"
    if st.button(f"🚀 Deteksi Momen Viral — {uploaded_file.name}", key=detect_key, type="primary"):
        progress = st.progress(0, text="Memulai analisis...")
        status = st.empty()

        try:
            status.info("📊 Menganalisis energi audio...")
            progress.progress(20, text="Audio energy analysis...")

            highlights = detect_highlights(
                video_path,
                top_k=top_k,
                min_distance_sec=min_distance,
                clip_padding=padding,
                use_whisper=use_whisper,
                whisper_model=whisper_model,
            )

            progress.progress(70, text="Menyusun hasil...")

            # Keep full transcript if whisper used (for captions later)
            full_segments = []
            if use_whisper:
                status.info("🗣️ Whisper sedang transcribe (bisa lama di CPU)...")
                full_segments = transcribe_with_whisper(video_path, model_size=whisper_model)

            progress.progress(100, text="Selesai!")
            time.sleep(0.3)
            progress.empty()
            status.empty()

            st.session_state[f"highlights_{file_idx}"] = highlights
            st.session_state[f"video_path_{file_idx}"] = video_path
            st.session_state[f"segments_{file_idx}"] = full_segments
            st.session_state[f"duration_{file_idx}"] = duration
            st.success(f"✅ Ditemukan **{len(highlights)}** momen berpotensi viral!")

        except Exception as e:
            progress.empty()
            status.empty()
            st.error(f"Gagal deteksi: {e}")
            continue

    # Show results if available
    h_key = f"highlights_{file_idx}"
    if h_key in st.session_state and st.session_state[h_key]:
        highlights = st.session_state[h_key]
        video_path = st.session_state[f"video_path_{file_idx}"]
        full_segments = st.session_state.get(f"segments_{file_idx}", [])

        st.subheader(f"🔥 {len(highlights)} Momen Terdeteksi")

        sort_by = st.radio(
            "Urutkan:",
            ["Viral Score ↓", "Waktu (awal → akhir)"],
            horizontal=True,
            key=f"sort_{file_idx}",
        )
        if sort_by.startswith("Waktu"):
            highlights = sorted(highlights, key=lambda x: x["peak_time"])
        else:
            highlights = sorted(highlights, key=lambda x: x["viral_score"], reverse=True)

        for idx, h in enumerate(highlights):
            score = h["viral_score"]
            if score >= 80:
                score_class, emoji = "score-high", "🚀"
            elif score >= 60:
                score_class, emoji = "score-mid", "🔥"
            else:
                score_class, emoji = "score-low", "👀"

            source_badge = "🎤 Keyword" if h.get("source") == "keyword" else "🔊 Audio"
            if h.get("keywords_found"):
                source_badge += " + ✨ Keyword boost"

            with st.expander(
                f"{emoji} **#{idx+1}**  {h['label']}  •  Score **{score}**  •  {h['duration']}s  •  {source_badge}",
                expanded=(idx < 2),
            ):
                c1, c2 = st.columns([3, 2])

                with c1:
                    st.markdown(f"**Peak:** `{h['peak_time']}s`  |  **Range:** `{h['start']}s → {h['end']}s`")
                    st.markdown(
                        f'<span class="{score_class}">Viral Score: {score}/100</span>',
                        unsafe_allow_html=True,
                    )
                    if h.get("transcript"):
                        st.markdown(f"**Transcript:** _{h['transcript']}_")

                    if show_titles:
                        titles = generate_viral_titles(h)
                        st.markdown("**💡 Saran judul viral:**")
                        for t in titles:
                            st.markdown(f"- `{t}`")

                with c2:
                    gen_key = f"gen_{file_idx}_{idx}"
                    if st.button(f"✂️ Generate Clip #{idx+1}", key=gen_key):
                        with st.spinner("Rendering clip..."):
                            try:
                                video = VideoFileClip(video_path)
                                sub = video.subclipped(h["start"], h["end"])

                                if make_vertical:
                                    w, hgt = sub.size
                                    target_ratio = 9 / 16
                                    current_ratio = w / hgt
                                    if current_ratio > target_ratio:
                                        new_w = int(hgt * target_ratio)
                                        x1 = (w - new_w) // 2
                                        sub = sub.cropped(x1=x1, y1=0, x2=x1 + new_w, y2=hgt)
                                    else:
                                        new_h = int(w / target_ratio)
                                        y1 = (hgt - new_h) // 2
                                        sub = sub.cropped(x1=0, y1=y1, x2=w, y2=y1 + new_h)

                                out_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                                sub.write_videofile(
                                    out_path,
                                    codec="libx264",
                                    audio_codec="aac",
                                    logger=None,
                                    preset="ultrafast",
                                    threads=2,
                                )
                                sub.close()
                                video.close()

                                st.session_state[f"clip_{file_idx}_{idx}"] = out_path

                                # Captions
                                if generate_captions and full_segments:
                                    clip_segs = get_clip_segments(full_segments, h["start"], h["end"])
                                    srt_content = generate_srt_from_segments(clip_segs)
                                    srt_path = save_srt(srt_content, prefix=f"clip{idx}_")
                                    st.session_state[f"srt_{file_idx}_{idx}"] = srt_path

                                st.success("Clip siap di-download!")
                            except Exception as e:
                                st.error(f"Gagal render: {e}")

                    # Download buttons
                    clip_key = f"clip_{file_idx}_{idx}"
                    if clip_key in st.session_state and os.path.exists(st.session_state[clip_key]):
                        with open(st.session_state[clip_key], "rb") as f:
                            st.download_button(
                                label=f"⬇️ Download Clip #{idx+1}",
                                data=f,
                                file_name=f"viral_{Path(uploaded_file.name).stem}_{idx+1}_s{int(score)}.mp4",
                                mime="video/mp4",
                                key=f"dlv_{file_idx}_{idx}",
                            )

                        srt_key = f"srt_{file_idx}_{idx}"
                        if srt_key in st.session_state and os.path.exists(st.session_state[srt_key]):
                            with open(st.session_state[srt_key], "rb") as f:
                                st.download_button(
                                    label=f"📝 Download Subtitle .srt",
                                    data=f,
                                    file_name=f"viral_{Path(uploaded_file.name).stem}_{idx+1}.srt",
                                    mime="text/plain",
                                    key=f"dls_{file_idx}_{idx}",
                                )

    elif h_key in st.session_state and not st.session_state[h_key]:
        st.warning("Tidak ada peak signifikan. Coba turunkan jarak minimal atau aktifkan Whisper.")

# Footer
st.markdown("---")
st.caption(
    "💡 **Tips:** Aktifkan Whisper untuk hasil jauh lebih bagus (deteksi kata-kata emosional). "
    "Video gaming & reaction biasanya skor tinggi. Gunakan crop 9:16 untuk langsung upload ke TikTok/Reels."
)
st.caption("Versi lengkap: Audio Peak + Whisper Keyword + Auto Title + SRT Caption + Batch Upload + Vertical Crop")
