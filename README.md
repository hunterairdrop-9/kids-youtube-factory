# AI Kids YouTube Factory

Sistem produksi YouTube lagu anak secara otomatis, berjalan di Muse Secure VM
(Linux, tanpa komputer fisik). Satu video = satu episode lagu anak 3 menit,
dengan karakter konsisten, lirik tersinkron, dan thumbnail.

## Peran

| Peran | Alat | Status |
|---|---|---|
| Pengendali utama | Muse (VM ini) | Berjalan |
| Riset, konsep, storyboard | Gemini | Menunggu API key user |
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
│   └── test_stage2.py      # pengujian penerimaan Tahap 2
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
- **Blender jangan dipakai selama Tahap 2** (perintah user 20 Nov 2026).

## Status

- Tahap 1 (audit) — SELESAI 20 Nov 2026 ([SYSTEM_STATUS.md](SYSTEM_STATUS.md)).
- Tahap 2 (persiapan) — SELESAI 20 Nov 2026 (repo ini + pengujian).
- Tahap 3 (uji video 30 detik) — MENUNGGU persetujuan user.
