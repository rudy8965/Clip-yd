---
title: ViralClipper
emoji: 🔥
colorFrom: red
colorTo: yellow
sdk: streamlit
sdk_version: "1.39.0"
app_file: app.py
pinned: false
license: mit
short_description: Auto-detect viral moments from video (Audio Peak + Whisper AI)
---

# ViralClipper 🔥

Aplikasi **auto-clipper** gratis untuk mencari momen yang berpotensi viral dari video.

Cocok untuk gaming highlight, reaction, podcast, stream, dll.

## Fitur

- **Batch Upload** — banyak video sekaligus
- **Audio Peak Detection** — deteksi lonjakan volume (tawa, teriakan, kill sound)
- **Whisper AI** — speech-to-text + deteksi kata kunci viral (gila, anjir, OMG, clutch, dll)
- **Viral Score 0-100** — skor gabungan audio + keyword
- **Auto Caption (.srt)** — generate subtitle per clip
- **Saran Judul Viral** — template clickbait siap pakai
- **Crop 9:16** — langsung siap TikTok / Reels / Shorts
- **Preview + Download** clip & subtitle

## Cara Pakai (di Space ini)

1. Upload video (disarankan < 5–8 menit agar tidak timeout)
2. (Opsional) centang **Gunakan Whisper** di sidebar kiri
3. Klik **Deteksi Momen Viral**
4. Pilih momen dengan score tinggi → **Generate Clip**
5. Download hasilnya

> **Catatan penting di Hugging Face Spaces (CPU gratis):**
> - Proses Whisper bisa 1–3 menit tergantung panjang video
> - Video terlalu panjang berisiko timeout / out of memory
> - Model Whisper default = `tiny` (paling cepat)

## Jalankan Lokal

```bash
pip install -r requirements.txt
# Pastikan ffmpeg sudah terinstall di sistem
streamlit run app.py
```

## Tech Stack

- Streamlit
- MoviePy + FFmpeg
- Pydub + NumPy
- OpenAI Whisper

---

Dibuat untuk learning & eksperimen. Silakan fork & modifikasi.
