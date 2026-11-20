# AI Kids YouTube Factory

Sistem produksi YouTube lagu anak secara otomatis, berjalan di Muse Secure VM
(Linux, tanpa komputer fisik). Satu video = satu episode lagu anak 3 menit,
dengan karakter konsisten, lirik tersinkron, dan thumbnail.

## Peran

| Peran | Alat | Status |
|---|---|---|
| Pengendali utama | Muse (VM ini) | Berjalan |
| Riset, konsep, storyboard | Gemini | API key BELUM disetujui — menunggu pemeriksaan ketentuan untuk konten anak (keputusan user 20 Nov 2026) |
| Lirik, naskah, QC | GPT (rencana awal) | Tidak tersedia gratis — perlu keputusan user (alternatif: Gemini) |
| Kode & workflow | GitHub — repo ini | Berjalan |
| Penyimpanan hasil | Google Drive | Terhubung 20 Nov 2026 |
| Publikasi | YouTube | Channel ada (@stonecrafttt, rebrand menunggu keputusan) |

## Struktur folder produksi (di VM)

```
~/workspace/youtube-kids/
├── projects/            # satu folder per episode (EP001, EP002, ...)
├── assets/
│   ├── characters/      # gambar referensi karakter (mis. Tomo)
│   └── backgrounds/     # latar yang dipakai ulang
├── audio/               # lagu jadi (.mp3)
├── lyrics/              # lirik per episode
├── storyboard/          # storyboard per episode
├── videos/
│   ├── drafts/          # hasil antara / uji
│   └── final/           # video final yang lolos QC
├── thumbnails/          # thumbnail 1280x720
├── logs/                # production_log.json
└── checkpoints/         # <production_id>.json (resume)
```

Kode, konfigurasi, dokumentasi, dan template tinggal di repo ini:

```
kids-youtube-factory/
├── README.md
├── SYSTEM_STATUS.md
├── PRODUCTION_WORKFLOW.md
├── RESOURCE_LIMITS.md
├── config/production_config.json
├── scripts/
│   ├── production_log.py   # pencatatan produksi
│   ├── checkpoint.py       # checkpoint & resume
│   ├── test_stage2.py      # pengujian penerimaan Tahap 2
│   ├── render_test30.py    # mesin uji video 30 detik (Tahap 3)
│   ├── render_3d_preview.py # raytracer 3D v0.1 (pembanding)
│   ├── render_character_bible.py # render Character Bible v1 (Uji 2)
│   ├── render_rasterizer_v2.py   # rasterizer 3D v2, prototipe (Uji 6)
│   ├── storyboard.py       # validator storyboard (Uji 7)
│   └── test_storyboard.py  # uji validator (7 kasus)
└── templates/
    ├── lyrics_template.md
    ├── storyboard_template.md
    └── episode_brief.md
```

Video MP4 besar, audio, dan model AI **tidak** disimpan di repo ini
(lihat `.gitignore`).

## Alur produksi (ringkas)

1. **Lirik** — tulis dari `templates/lyrics_template.md`, disetujui user.
2. **Musik** — Lyria ($0,08/lagu, API) atau ACE-Step gratis (uji dulu).
3. **Gambar** — Nano Banana / stills Blender, selalu dengan gambar referensi karakter.
4. **Video** — Ken Burns (ffmpeg, $0) atau photo-to-video (Veo/Omni, ~$10/video).
5. **Rakit** — ffmpeg: gabung klip + lagu + teks lirik tersinkron (ASS).
6. **Lirik di layar** — WhisperX (timestamp kata) → subtitle karaoke.
7. **QC** — tonton penuh, cek sinkronisasi, audio, thumbnail.
8. **Upload** — unlisted dulu, publikasi hanya setelah persetujuan.

Detail lengkap: [PRODUCTION_WORKFLOW.md](PRODUCTION_WORKFLOW.md).

## Aturan yang mengikat

- **Gratis dulu** — tanpa langganan, tanpa beli API, tanpa API key tanpa izin user.
- **Jangan publikasi** sebelum persetujuan (uji = unlisted).
- **Jangan hapus file asli.**
- **Jangan anggap berhasil** sebelum file benar-benar bisa diputar.
- **Checkpoint/resume wajib** — VM bisa restart kapan saja; pekerjaan panjang
  tidak boleh mengulang dari nol.
- **ACE-Step jangan dijalankan** untuk sementara (perintah user 20 Nov 2026);
  folder build 4 GB di `tools/acestep.cpp` jangan dihapus.
- **Blender jangan dijalankan tanpa persetujuan** (perintah user 20 Nov 2026).
- **Gemini API key BELUM disetujui** — jangan membuat/menyimpan key, jangan
  aktifkan billing (keputusan user 20 Nov 2026, menunggu pemeriksaan
  ketentuan untuk konten anak).

## Arah pengembangan (ditetapkan user 20 Nov 2026)

Lihat `~/workspace/youtube-kids/docs/arah-pengembangan.md`. Tujuan: mesin
editing otomatis video lagu anak kartun 3D berkualitas tinggi. Strategi:
Python + FFmpeg dipertahankan; rasterizer v2 sebagai kandidat mesin 3D;
raytracer lama sebagai pembanding; layered animation sebagai pelengkap.
Tahap: (1) Character Bible, (2) storyboard otomatis, (3) mesin gambar 3D,
(4) animasi karakter, (5) editing otomatis FFmpeg, (6) Monetization
Quality Control Agent, (7) uji satu episode lengkap.

## Status

- Tahap 1 (audit) — SELESAI 20 Nov 2026 ([SYSTEM_STATUS.md](SYSTEM_STATUS.md)).
- Tahap 2 (persiapan) — SELESAI 20 Nov 2026 (repo ini + pengujian).
- Tahap 3 (uji video 30 detik) — SELESAI 20 Nov 2026 (gajah biru, 720p + 1080p lolos).
- Uji 2 (Character Bible v1) — SELESAI 20 Nov 2026: 12 render (3 master +
  4 ekspresi + 5 pose), 11,3 dtk, RAM ~105 MB. Model lama tidak diubah.
- Uji 7 (Storyboard Validator) — SELESAI 20 Nov 2026: 7/7 kasus lolos
  (1 valid + 6 tidak valid ditolak dengan pesan tepat).
- Uji 6 (Rasterizer v2) — SELESAI 20 Nov 2026: satu frame 640×360,
  1,33 dtk (verifikasi mandiri) vs raytracer 1,0 dtk, RAM 94 vs 103 MB,
  selisih piksel rata-rata 0,58/255. LAYAK LANJUT sebagai kandidat,
  BUKAN standar final (butuh optimasi ke <0,5 dtk/frame).
- Tahap 4 / produksi episode penuh — BELUM dimulai, menunggu persetujuan user.
