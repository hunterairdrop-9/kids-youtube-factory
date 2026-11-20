# RESOURCE_LIMITS — AI Kids YouTube Factory

Batas sumber daya VM dan aturan yang mengikutinya. Dokumen ini adalah
kontrak kerja: kalau sebuah rencana melanggar batas di sini, rencana itu
harus diubah, bukan batasnya yang dilanggar.

## Mesin (dicek 20 Nov 2026)

| Sumber daya | Nilai | Dampak |
|---|---|---|
| CPU | 4 core (AMD EPYC 9D25) | 1 pekerjaan berat dalam satu waktu |
| RAM | 7,7 GB total; **~500 MB tersedia saat audit** | Kerja berat pakai paralelisme rendah; jangan jalankan 2 build/render bersamaan |
| Disk | 150 GB total; **142 GB kosong** | Cukup untuk ratusan video; bersihkan `videos/drafts/` berkala (jangan hapus `videos/final/` dan file asli) |
| GPU | **Tidak ada** | Model video/musik open-source lokal (Wan, ACE-Step Python, YuE2) tidak bisa jalan di VM ini |
| OS | Linux x86_64 | Semua alat CLI tersedia |

## Batas waktu (terukur)

| Pekerjaan | Waktu di VM ini |
|---|---|
| Render Blender 30 detik (720 frame, EEVEE) | ~1 jam 45 menit |
| Render Blender 3 menit (4.320 frame) | ~10–11 jam |
| Render 1 still Blender | ~17 detik |
| Encode ffmpeg 1 detik 1080p (ultrafast) | <2 detik |
| Build acestep.cpp (C++) | puluhan menit (ditunda — jangan dijalankan) |

## Aturan operasional

1. **Satu pekerjaan berat dalam satu waktu.** Periksa `free -h` dan `ps` sebelum
   memulai build/render.
2. **Checkpoint/resume wajib** untuk pekerjaan >10 menit. VM bisa restart
   kapan saja; pekerjaan harus bisa dilanjutkan tanpa mengulang.
3. **Render per scene/frame, bukan sekali jalan.** Kalau mati di tengah,
   lanjutkan dari frame terakhir.
4. **Jangan jalankan ACE-Step** untuk sementara (perintah user 20 Nov 2026).
   Folder `tools/acestep.cpp` (4 GB) **jangan dihapus**.
5. **Jangan pakai Blender selama Tahap 2** (perintah user 20 Nov 2026).
6. **FFmpeg adalah alat utama perakitan.** MoviePy tidak dipasang karena
   FFmpeg sudah cukup.
7. **Jangan simpan video MP4 besar di repo GitHub.** Repo hanya untuk
   kode, konfigurasi, dokumentasi, template.

## Aturan biaya (mengikat)

- **Gratis dulu.** Tanpa langganan, tanpa beli API, tanpa API key tanpa izin user.
- Biaya per video jalur utama (Ken Burns + Lyria): ~$0,88.
- Biaya per video jalur Veo: ~$10 — hanya bila disetujui user per video.
- Tidak ada biaya bulanan wajib: semua alat inti (Python, FFmpeg, Git,
  Pillow, Blender) gratis.

## Layanan & izin

| Layanan | Kebutuhan | Status |
|---|---|---|
| Gemini API (Nano Banana, Lyria, Veo) | API key + billing | ⏳ Menunggu user |
| GPT (OpenAI API) | API key + bayar per pakai | ❌ Tidak tersedia gratis — perlu keputusan user |
| Google Drive | Koneksi (sudah) | ✅ Terhubung |
| GitHub | Koneksi (sudah) | ✅ Terhubung |
| YouTube | Upload via API (nanti) | ⏳ Menunggu Tahap 3 |

## Yang tidak boleh dilakukan

- Menghapus file asli (termasuk folder build ACE-Step 4 GB).
- Mengunggah video ke YouTube sebelum persetujuan (uji = unlisted).
- Menggunakan API berbayar tanpa izin eksplisit per tindakan.
- Menyatakan berhasil sebelum file benar-benar bisa diputar penuh.
