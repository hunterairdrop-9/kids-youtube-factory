# SYSTEM_STATUS — AI Kids YouTube Factory

**Terakhir diperiksa:** 20 Nov 2026, 13:26 WIB (Uji 2, 6, 7)
**Mesin:** Muse Secure VM — Linux 7.0.0-44-generic x86_64

## Hasil audit Tahap 1 (A–J)

| # | Pertanyaan | Jawaban | Bukti |
|---|---|---|---|
| A | Terminal Linux? | ✅ YA | Shell Linux penuh, dipakai untuk semua pekerjaan |
| B | Python tersedia? | ✅ YA | Python 3.12.3, pip 24.0, Pillow 10.2.0 |
| C | FFmpeg tersedia? | ✅ YA | ffmpeg 8.1.2, sudah dipakai membuat video uji |
| D | Penyimpanan? | ✅ 142 GB kosong | Total 150 GB, terpakai 7,2 GB |
| E | RAM & CPU? | ⚠️ 4 CPU, RAM 7,7 GB — ketat | Saat audit hanya ~500 MB tersedia; kerja berat pakai paralelisme rendah |
| F | Render background? | ✅ YA | Render Blender 30 detik jalan ~1 jam 45 menit di background |
| G | VM aktif saat app ditutup? | ⚠️ SEBAGIAN | File + cron aman; proses panjang bisa mati saat VM diganti (pernah terjadi: render mati di frame 328/720, dilanjutkan) |
| H | Unduh/buat/pindah video? | ✅ YA | Video uji Tomo dibuat, dipindah, dikirim ke user |
| I | GitHub? | ✅ YA | Konektor terhubung (hunterairdrop-9); repo dibuat via browser |
| J | Google Drive? | ✅ YA (sejak 12:36 WIB) | Sempat belum terhubung; user mengetuk tautan koneksi 20 Nov 2026 |

## Perangkat lunak (status Tahap 2)

| Perangkat | Versi | Status |
|---|---|---|
| Python | 3.12.3 | ✅ Terpasang |
| FFmpeg | 8.1.2 | ✅ Terpasang (alat utama perakitan) |
| Git | 2.43.0 | ✅ Terpasang |
| Pillow | 10.2.0 | ✅ Terpasang |
| MoviePy | — | ❌ TIDAK dipasang — keputusan Tahap 2: FFmpeg sudah cukup |
| Blender | 4.0.2 | ✅ Ada di `~/workspace/tools/` (jangan dijalankan tanpa persetujuan user) |
| ACE-Step (acestep.cpp) | — | ⏸️ JANGAN dijalankan untuk sementara; folder build 4 GB jangan dihapus |

## Layanan

| Layanan | Status |
|---|---|
| GitHub (hunterairdrop-9) | ✅ Terhubung |
| Google Drive | ✅ Terhubung 20 Nov 2026 |
| Gemini API | ⏳ BELUM disetujui — jangan buat key, jangan aktifkan billing (keputusan user 20 Nov 2026) |
| GPT (OpenAI API) | ❌ Tidak tersedia gratis — berbayar, butuh key + izin user |
| YouTube | ⏳ Channel @stonecrafttt ada; rebrand menunggu keputusan user |

## Hasil Tahap 3 (uji video 30 detik, 20 Nov 2026)

- Video: gajah kecil biru, 3 adegan, lirik tersinkron, melodi orisinal
  hasil sintesis sendiri. Mesin: `scripts/render_test30.py` (Pillow + numpy + ffmpeg).
- 720p: 30,00 dtk, H.264 + AAC, 1.424.706 byte, render 11,1 dtk, puncak RAM 96,7 MB.
- 1080p: 30,00 dtk, H.264 + AAC, 1.805.465 byte, render 21,9 dtk, puncak RAM 114,4 MB.
- Pengujian A–H: 8/8 lolos (durasi, 3 adegan, gerakan, teks tepat waktu,
  audio sinkron, bisa diputar/decode OK, resolusi + ukuran, waktu + RAM).
  8 frame dicek visual langsung.

## Hasil Uji 2, 6, 7 (20 Nov 2026 — fondasi karakter, storyboard, mesin visual)

- **Uji 2 — Character Bible v1 gajah biru** (`scripts/render_character_bible.py`):
  12 gambar 640×360 (master depan/samping/belakang + 4 ekspresi + 5 pose),
  total 11,3 dtk (~0,95 dtk/gambar), puncak RAM ~105 MB. Model lama
  (`render_3d_preview.py`) tidak diubah — varian dibuat pada salinan.
  Keterbatasan v1: belum ada mulut; pose melambai terbaca seperti belalai
  tergulung; ekspresi sedih bedanya halus. Aset di
  `assets/characters/gajah-biru/` (bukan di repo ini).
- **Uji 7 — Storyboard Validator** (`scripts/storyboard.py` +
  `scripts/test_storyboard.py`): 7/7 kasus lolos — storyboard contoh
  EP-TEST01 (6 adegan × 5 dtk) valid; 6 storyboard rusak ditolak dengan
  pesan tepat (field hilang, durasi tidak cocok, scene_id duplikat,
  ekspresi tidak ada di Bible, gambar referensi hilang, status tidak
  dikenal).
- **Uji 6 — Rasterizer v2** (`scripts/render_rasterizer_v2.py`): satu
  frame gajah 640×360, mesh 16×24 (17.664 segitiga). Verifikasi mandiri:
  1,33 dtk, CPU 1,52 dtk, RAM 94,4 MB vs raytracer 1,0 dtk / 102,9 MB
  (render ulang hari yang sama). Selisih piksel rata-rata 0,58/255.
  **Tidak lebih cepat dari raytracer di 640×360** (~30% lebih lambat —
  loop Python per segitiga); lebih cepat ~29% di 1080p (6,13 vs 8,6 dtk)
  tapi RAM 542 MB melebihi RAM tersedia tipikal. LAYAK LANJUT sebagai
  kandidat, BUKAN standar final. Self-shadow belum ada; lingkungan
  belum dirasterisasi.

## Batasan yang diketahui

- **RAM ketat:** tersedia ~500 MB saat audit. Jangan menjalankan dua pekerjaan berat
  bersamaan; render/build pakai paralelisme rendah.
- **VM bisa restart:** proses panjang bisa mati. Semua pekerjaan panjang wajib
  checkpoint/resume (lihat `scripts/checkpoint.py`).
- **Tanpa GPU:** model video/musik open-source lokal tidak bisa jalan di VM ini
  (butuh GPU). Jalur gratis: acestep.cpp CPU (ditunda), Colab T4 gratis.
- **Render Blender 3 menit ≈ 10–11 jam** di VM ini (EEVEE ~8,7 dtk/frame).
