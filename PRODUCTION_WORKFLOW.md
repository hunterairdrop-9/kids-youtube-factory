# PRODUCTION_WORKFLOW — AI Kids YouTube Factory

Satu episode = satu lagu anak 3 menit (180 detik), 12 scene × 15 detik.
Setiap tahap dicatat di log produksi (`scripts/production_log.py`) dan
checkpoint (`scripts/checkpoint.py`). Tahap yang sudah selesai tidak diulang.

## Tahapan

### 0. Brief episode
- Isi `templates/episode_brief.md`: judul, tema, pesan, karakter, jalur video.
- Buat entri log: `production_log.py create --id EP001 --judul "..."`.
- Buat checkpoint: `checkpoint.py init --id EP001`.
- **Gate:** brief disetujui user sebelum lanjut.

### 1. Lirik (`lirik`)
- Tulis dari `templates/lyrics_template.md` — asli, Bahasa Indonesia,
  kata sederhana, 1 scene = 2 baris.
- Simpan di `lyrics/EP001.md`.
- **Gate:** lirik disetujui user.

### 2. Musik (`musik`)
- Mesin utama: **Lyria 3.5 via Gemini API** (~$0,08/lagu, Bahasa Indonesia).
- Alternatif gratis: **ACE-Step 1.5** (uji dulu; saat ini JANGAN dijalankan
  — perintah user 20 Nov 2026).
- Input: lirik + deskripsi gaya. Output: `audio/EP001.mp3` (3:00).
- Catat durasi dan file di log.

### 3. Gambar (`gambar`)
- 12 gambar (1 per scene), dari Nano Banana atau stills Blender.
- **Wajib:** setiap prompt dilampiri gambar referensi karakter yang sama
  (di `assets/characters/`).
- Simpan di `projects/EP001/gambar/scene-01.png` dst.

### 4. Video per scene (`video`)
- Jalur A (utama): **Ken Burns via ffmpeg** — zoom/pan pelan pada gambar diam ($0).
- Jalur B: photo-to-video Veo/Omni API (~$10/video) — hanya bila disetujui.
- Jalur C: Blender 3D penuh ($0, ~10–11 jam render) — sesekali saja.
- Output: `projects/EP001/klip/scene-01.mp4` dst. (15 detik per scene di jalur A/C,
  8 detik per klip di jalur B — 2 klip per scene).

### 5. Rakit (`rakit`)
- ffmpeg: gabung 12 klip → tempel `audio/EP001.mp3` → output
  `videos/drafts/EP001.mp4` (1920×1080, 24 fps, H.264 + AAC).

### 6. Lirik di layar (`lirik_layar`)
- Sederhana: satu baris lirik per scene (15 detik).
- Karaoke: WhisperX pada lagu → timestamp kata → subtitle ASS → burn ke video.
- Output akhir: `videos/final/EP001.mp4`.

### 7. QC (`qc`)
- **Wajib tonton penuh** dari awal sampai akhir sebelum dinyatakan selesai.
- Periksa: gambar konsisten, lirik sinkron, audio jernih, durasi 3:00,
  thumbnail 1280×720 siap.
- Hasil QC dicatat di log (`--qc lolos/gagal`).

### 8. Upload (`upload`)
- **Hanya setelah persetujuan user.**
- Uji = unlisted. Judul/deskripsi/tag dari branding. Made for Kids: YA.
  Pengungkapan AI: YA.
- Publikasi (public) hanya bila user menyetujui.

## Perintah yang dipakai

```bash
# Log
python3 scripts/production_log.py create --id EP001 --judul "Truk Tahu Bulat"
python3 scripts/production_log.py update --id EP001 --status rendering --rendering berjalan
python3 scripts/production_log.py selesai --id EP001 --qc lolos

# Checkpoint
python3 scripts/checkpoint.py init --id EP001
python3 scripts/checkpoint.py selesai --id EP001 --tahap lirik --detail "disetujui user"
python3 scripts/checkpoint.py lanjut --id EP001   # lanjut dari tahap yang tertunda

# Pengujian Tahap 2
python3 scripts/test_stage2.py
```

## Aturan biaya (per video 3 menit)

| Jalur | Biaya | Waktu |
|---|---|---|
| A. Ken Burns + Lyria | ~$0,88 | hitungan menit |
| B. Veo photo-to-video + Lyria | ~$10 | menit–jam |
| C. Blender + Lyria | ~$0,08 | ~10–11 jam render |

Jalur A adalah jalur utama mingguan. Jalur C untuk format premium sesekali.
