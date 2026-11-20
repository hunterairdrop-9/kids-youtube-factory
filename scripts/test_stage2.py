#!/usr/bin/env python3
"""Pengujian Tahap 2 — AI Kids YouTube Factory.

Menjalankan semua pemeriksaan penerimaan Tahap 2:
  1. Semua folder produksi ada
  2. FFmpeg berfungsi (versi + encode uji 1 detik, ringan — bukan render berat)
  3. Python berfungsi (versi + Pillow bisa diimpor)
  4. Log produksi bisa ditulis dan dibaca kembali
  5. Checkpoint bisa disimpan, dibaca, dan resume menemukan tahap berikutnya
  6. MoviePy TIDAK dipasang (keputusan Tahap 2: FFmpeg sudah cukup)

Jalankan:  python3 test_stage2.py
Keluar 0 = semua lolos. Bukan 0 = ada yang gagal (lihat baris FAIL).
"""

import json
import os
import subprocess
import sys
import tempfile

FACTORY = os.path.expanduser("~/workspace/youtube-kids")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOLDERS = [
    "projects", "assets", "assets/characters", "assets/backgrounds",
    "audio", "lyrics", "storyboard", "videos/drafts", "videos/final",
    "thumbnails", "logs", "checkpoints",
]

results = []


def check(nama, ok, detail=""):
    results.append((nama, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {nama}" + (f" — {detail}" if detail else ""))


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def main():
    # 1. Folder
    hilang = [f for f in FOLDERS if not os.path.isdir(os.path.join(FACTORY, f))]
    check("folder produksi", not hilang,
          "semua ada" if not hilang else f"hilang: {', '.join(hilang)}")

    # 2. FFmpeg: versi + encode uji 1 detik 1080p (ringan)
    r = run(["ffmpeg", "-version"])
    versi = r.stdout.splitlines()[0] if r.returncode == 0 else ""
    check("ffmpeg terpasang", r.returncode == 0, versi)
    uji_ok = False
    uji_detail = ""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "uji-1detik.mp4")
        r = run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=1920x1080:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
            "-shortest", out,
        ])
        if r.returncode == 0 and os.path.exists(out):
            p = run(["ffprobe", "-v", "error", "-show_entries",
                     "format=duration", "-of", "json", out])
            try:
                dur = float(json.loads(p.stdout)["format"]["duration"])
                uji_ok = 0.9 <= dur <= 1.1
                uji_detail = f"durasi {dur:.2f} dtk, {os.path.getsize(out)} byte"
            except (KeyError, ValueError, json.JSONDecodeError):
                uji_detail = "ffprobe tidak bisa membaca durasi"
        else:
            uji_detail = (r.stderr or "").strip().splitlines()[-1:] and \
                (r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "encode gagal")
    check("ffmpeg encode uji 1 dtk", uji_ok, uji_detail)

    # 3. Python + Pillow
    check("python", sys.version_info >= (3, 10),
          f"Python {sys.version.split()[0]}")
    try:
        import PIL
        check("pillow", True, f"Pillow {PIL.__version__}")
    except ImportError:
        check("pillow", False, "tidak terpasang")

    # 4. Log: tulis + baca kembali
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import production_log
    import checkpoint
    log_test = os.path.join(tempfile.gettempdir(), "uji-log-produksi.json")
    if os.path.exists(log_test):
        os.remove(log_test)
    try:
        production_log.create(log_test, "UJI001", "Episode Uji")
        production_log.update(log_test, "UJI001", status="berjalan",
                              status_rendering="berjalan")
        entry = production_log.get(log_test, "UJI001")
        ok = (entry["judul"] == "Episode Uji" and entry["status"] == "berjalan"
              and entry["status_rendering"] == "berjalan"
              and entry["waktu_mulai"])
        check("log tulis + baca", ok, f"id UJI001, status {entry['status']}")
    except Exception as e:  # noqa: BLE001
        check("log tulis + baca", False, str(e))
    finally:
        if os.path.exists(log_test):
            os.remove(log_test)

    # 5. Checkpoint: simpan + baca + resume
    ck_dir = os.path.join(tempfile.gettempdir(), "uji-checkpoint")
    os.makedirs(ck_dir, exist_ok=True)
    try:
        checkpoint.init(ck_dir, "UJI001")
        checkpoint._set_status(ck_dir, "UJI001", "lirik", "selesai", "uji")
        checkpoint._set_status(ck_dir, "UJI001", "musik", "gagal", "uji gagal")
        berikut = checkpoint.tahap_berikutnya(ck_dir, "UJI001")
        ok = berikut is not None and berikut["nama"] == "musik"
        check("checkpoint + resume", ok,
              f"tahap berikutnya: {berikut['nama'] if berikut else 'tidak ada'}")
    except Exception as e:  # noqa: BLE001
        check("checkpoint + resume", False, str(e))
    finally:
        for f in os.listdir(ck_dir):
            os.remove(os.path.join(ck_dir, f))
        os.rmdir(ck_dir)

    # 6. MoviePy memang tidak dipasang (keputusan Tahap 2)
    try:
        import moviepy  # noqa: F401
        check("moviepy tidak dipasang", False, "ternyata terpasang")
    except ImportError:
        check("moviepy tidak dipasang", True, "sesuai keputusan: FFmpeg sudah cukup")

    gagal = [n for n, ok, _ in results if not ok]
    print()
    print(f"HASIL: {len(results) - len(gagal)}/{len(results)} lolos"
          + (f" — GAGAL: {', '.join(gagal)}" if gagal else " — SEMUA LOLOS"))
    return 0 if not gagal else 1


if __name__ == "__main__":
    raise SystemExit(main())
