#!/usr/bin/env python3
"""Mesin editing visual v1 — AI Kids YouTube Factory (Tahap 3).

Membuat video kartun uji 30 detik: gajah kecil biru, 3 adegan, lirik
tersinkron, musik orisinal hasil sintesis sendiri (tanpa hak cipta).

Cara kerja:
  1. Gambar latar tiap adegan di-render sekali (numpy + Pillow).
  2. Tiap frame: salin latar, gambar elemen bergerak + gajah + teks lirik,
     lalu kirim frame mentah ke ffmpeg (streaming, hemat RAM).
  3. Musik: melodi orisinal C mayor disintesis (numpy) -> WAV.
  4. Rakit: gabung 3 klip adegan + audio -> MP4 H.264 + AAC.

Pemakaian:
  python3 render_test30.py --width 1280 --height 720 --out videos/drafts/TEST30-720p.mp4
  python3 render_test30.py --width 1920 --height 1080 --out videos/drafts/TEST30-1080p.mp4

Tidak memakai Blender, ACE-Step, atau API apa pun. Hanya Pillow + numpy + ffmpeg.
Penjaga RAM: berhenti aman kalau MemAvailable < 250 MB.
"""

import argparse
import json
import math
import os
import resource
import subprocess
import sys
import time
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FACTORY = os.path.expanduser("~/workspace/youtube-kids")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FPS = 24
DURASI_ADEGAN = 10  # detik
JUMLAH_ADEGAN = 3

# Lirik asli (ditulis untuk uji ini), 5 detik per baris.
LIRIK = [
    (0, 5, "Gajah biru kecil"),
    (5, 10, "berjalan di pagi hari"),
    (10, 15, "Cip cip, airnya dingin"),
    (15, 20, "gajah mandi senang sekali"),
    (20, 25, "Balon warna-warni"),
    (25, 30, "terbang ke langit biru"),
]

# Warna gajah & dunia (RGB)
BIRU = (79, 163, 224)
BIRU_MUDA = (143, 196, 238)
BIRU_TUA = (58, 130, 190)
PIPI = (255, 150, 170)
PUTIH = (255, 255, 255)
HITAM = (30, 30, 30)


def cek_ram(min_kb=250_000):
    """Berhenti aman kalau RAM tersedia terlalu rendah."""
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                tersedia_kb = int(line.split()[1])
                if tersedia_kb < min_kb:
                    print(f"RAM TIDAK CUKUP: tersedia {tersedia_kb // 1024} MB "
                          f"(butuh >= {min_kb // 1024} MB). Berhenti aman.",
                          file=sys.stderr)
                    return False
                print(f"RAM tersedia: {tersedia_kb // 1024} MB — lanjut.")
                return True
    return True


def lirik_pada(detik):
    for awal, akhir, teks in LIRIK:
        if awal <= detik < akhir:
            return teks
    return LIRIK[-1][2]


# ------------------------------------------------------------------ latar
def gradasi_langit(w, h, atas, bawah):
    atas = np.array(atas, dtype=float)
    bawah = np.array(bawah, dtype=float)
    t = np.linspace(0, 1, h)[:, None, None]
    grad = atas[None, None, :] * (1 - t) + bawah[None, None, :] * t
    grad = np.repeat(grad, w, axis=1)
    return Image.fromarray(grad.astype(np.uint8), "RGB")


def gambar_matahari(d, x, y, r):
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 64))
    for i in range(12):
        a = 2 * math.pi * i / 12
        x1 = x + math.cos(a) * (r + 6)
        y1 = y + math.sin(a) * (r + 6)
        x2 = x + math.cos(a) * (r + 22)
        y2 = y + math.sin(a) * (r + 22)
        d.line([x1, y1, x2, y2], fill=(255, 214, 64), width=5)


def latar_adegan(adegan, w, h):
    """Latar statis tiap adegan (di-render sekali, dipakai ulang tiap frame)."""
    if adegan == 1:  # padang rumput
        img = gradasi_langit(w, h, (135, 206, 250), (220, 245, 255))
        d = ImageDraw.Draw(img)
        gambar_matahari(d, int(w * 0.85), int(h * 0.16), int(h * 0.07))
        # bukit hijau
        d.ellipse([-w * 0.2, h * 0.72, w * 0.65, h * 1.25], fill=(96, 200, 90))
        d.ellipse([w * 0.45, h * 0.78, w * 1.2, h * 1.3], fill=(74, 180, 80))
        # bunga (posisi tetap, seed acak deterministik)
        rng = np.random.default_rng(7)
        for _ in range(26):
            x = int(rng.uniform(0, w))
            y = int(rng.uniform(h * 0.8, h * 0.97))
            warna = [(255, 120, 160), (255, 200, 60), (200, 120, 255),
                     (255, 255, 255)][int(rng.integers(0, 4))]
            r = max(4, h // 90)
            d.ellipse([x - r, y - r, x + r, y + r], fill=warna)
            d.ellipse([x - r // 2, y - r // 2, x + r // 2, y + r // 2],
                      fill=(255, 220, 40))
    elif adegan == 2:  # kolam
        img = gradasi_langit(w, h, (120, 200, 250), (210, 240, 255))
        d = ImageDraw.Draw(img)
        gambar_matahari(d, int(w * 0.15), int(h * 0.16), int(h * 0.07))
        # daratan kiri-kanan
        d.ellipse([-w * 0.15, h * 0.55, w * 0.3, h * 0.95], fill=(96, 200, 90))
        d.ellipse([w * 0.75, h * 0.55, w * 1.15, h * 0.95], fill=(96, 200, 90))
        # alang-alang
        for x in (int(w * 0.06), int(w * 0.12), int(w * 0.88), int(w * 0.94)):
            d.line([x, h * 0.62, x, h * 0.42], fill=(60, 160, 70), width=5)
            d.ellipse([x - 8, h * 0.40, x + 8, h * 0.46], fill=(150, 110, 60))
    else:  # balon
        img = gradasi_langit(w, h, (140, 210, 255), (255, 230, 180))
        d = ImageDraw.Draw(img)
        gambar_matahari(d, int(w * 0.5), int(h * 0.14), int(h * 0.06))
        d.ellipse([-w * 0.2, h * 0.8, w * 1.2, h * 1.3], fill=(120, 205, 100))
        # bunga di bukit
        rng = np.random.default_rng(11)
        for _ in range(18):
            x = int(rng.uniform(0, w))
            y = int(rng.uniform(h * 0.86, h * 0.97))
            r = max(4, h // 90)
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=(255, 120, 160))
    return img


def gambar_awan(d, x, y, s):
    d.ellipse([x, y, x + s, y + s * 0.55], fill=PUTIH)
    d.ellipse([x + s * 0.25, y - s * 0.2, x + s * 0.8, y + s * 0.4], fill=PUTIH)
    d.ellipse([x + s * 0.55, y, x + s * 1.1, y + s * 0.55], fill=PUTIH)


# ------------------------------------------------------------------ gajah
def gambar_gajah(d, cx, cy, s, t, berjalan=False):
    """Gajah kecil biru. cx,cy = titik tengah badan; s = panjang badan (px).
    t = waktu (detik) untuk animasi: kaki, telinga, belalai."""
    biru = BIRU
    # ekor
    d.line([cx - s * 0.48, cy - s * 0.05, cx - s * 0.58, cy + s * 0.12],
           fill=BIRU_TUA, width=max(3, int(s * 0.03)))
    d.ellipse([cx - s * 0.62, cy + s * 0.08, cx - s * 0.54, cy + s * 0.16],
              fill=BIRU_TUA)
    # kaki (4) — melangkah kalau berjalan
    for i, fx in enumerate([-0.32, -0.12, 0.12, 0.32]):
        angkat = 0
        if berjalan:
            angkat = abs(math.sin(t * 6 + i * math.pi)) * s * 0.06
        x0 = cx + fx * s - s * 0.045
        x1 = cx + fx * s + s * 0.045
        y1 = cy + s * 0.30 - angkat
        d.rounded_rectangle([x0, cy + s * 0.10, x1, y1],
                            radius=int(s * 0.04), fill=BIRU_TUA)
        d.ellipse([x0, y1 - s * 0.05, x1, y1 + s * 0.01], fill=(230, 240, 250))
    # badan
    d.ellipse([cx - s * 0.5, cy - s * 0.28, cx + s * 0.5, cy + s * 0.28],
              fill=biru)
    d.ellipse([cx - s * 0.28, cy - s * 0.10, cx + s * 0.30, cy + s * 0.28],
              fill=BIRU_MUDA)
    # telinga (mengepak pelan)
    flap = math.sin(t * 3) * s * 0.03
    ex, ey = cx + s * 0.28, cy - s * 0.30
    d.ellipse([ex - s * 0.02, ey - s * 0.20 - flap, ex + s * 0.24,
               ey + s * 0.10], fill=BIRU_MUDA)
    d.ellipse([ex + s * 0.05, ey - s * 0.14 - flap, ex + s * 0.18,
               ey + s * 0.04], fill=(255, 180, 200))
    # kepala
    d.ellipse([cx + s * 0.18, cy - s * 0.48, cx + s * 0.62, cy - s * 0.04],
              fill=biru)
    # mata
    mx, my = cx + s * 0.47, cy - s * 0.30
    d.ellipse([mx - s * 0.055, my - s * 0.055, mx + s * 0.055, my + s * 0.055],
              fill=PUTIH)
    d.ellipse([mx - s * 0.028, my - s * 0.028, mx + s * 0.028, my + s * 0.028],
              fill=HITAM)
    d.ellipse([mx + s * 0.005, my - s * 0.04, mx + s * 0.025, my - s * 0.02],
              fill=PUTIH)
    # pipi + senyum
    d.ellipse([mx + s * 0.02, my + s * 0.07, mx + s * 0.10, my + s * 0.13],
              fill=PIPI)
    d.arc([mx - s * 0.06, my + s * 0.05, mx + s * 0.10, my + s * 0.17],
          start=15, end=165, fill=HITAM, width=max(2, int(s * 0.015)))
    # jambul
    d.line([cx + s * 0.38, cy - s * 0.48, cx + s * 0.36, cy - s * 0.56],
           fill=BIRU_TUA, width=max(2, int(s * 0.015)))
    d.line([cx + s * 0.42, cy - s * 0.48, cx + s * 0.43, cy - s * 0.57],
           fill=BIRU_TUA, width=max(2, int(s * 0.015)))
    # belalai: kurva Bezier kuadratik, ujung bergoyang
    goyang = math.sin(t * 2.5) * s * 0.04
    p0 = (cx + s * 0.58, cy - s * 0.16)
    p1 = (cx + s * 0.72, cy + s * 0.05)
    p2 = (cx + s * 0.66 + goyang, cy + s * 0.30)
    for i in range(11):
        u = i / 10
        bx = (1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u ** 2 * p2[0]
        by = (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u ** 2 * p2[1]
        r = s * (0.085 - 0.045 * u)
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=biru)
    return p2  # ujung belalai (untuk cipratan air di adegan 2)


# ------------------------------------------------------------------ frame
def buat_frame(adegan, bg, t_lokal, t_global, w, h, font):
    frame = bg.copy()
    d = ImageDraw.Draw(frame, "RGBA")
    s = h * 0.30  # skala gajah
    # awan bergerak pelan
    for i, (bx, by, bs) in enumerate([(0.1, 0.10, 0.14), (0.55, 0.06, 0.18),
                                      (0.8, 0.20, 0.11)]):
        x = (bx * w + t_global * (12 + i * 5)) % (w + 300) - 150
        gambar_awan(d, x, by * h, bs * w)
    if adegan == 1:
        # berjalan kiri -> kanan
        x = -s + (t_lokal / DURASI_ADEGAN) * (w + 2 * s)
        y = h * 0.72
        gambar_gajah(d, x, y, s, t_global, berjalan=True)
    elif adegan == 2:
        # berdiri di kolam (air menutupi kaki)
        cx, cy = w * 0.5, h * 0.62
        ujung = gambar_gajah(d, cx, cy, s, t_global, berjalan=False)
        # permukaan air menutupi bagian bawah gajah
        d.ellipse([-w * 0.05, h * 0.68, w * 1.05, h * 0.86],
                  fill=(70, 160, 230, 210))
        d.ellipse([-w * 0.05, h * 0.70, w * 1.05, h * 0.80],
                  fill=(120, 200, 250, 180))
        # riak membesar
        for i in range(3):
            fase = ((t_lokal * 0.7 + i / 3) % 1.0)
            rx = w * 0.18 + fase * w * 0.12
            d.ellipse([cx - rx, h * 0.74 - 6 - fase * 8,
                       cx + rx, h * 0.74 + 6 + fase * 8],
                      outline=(255, 255, 255, int(180 * (1 - fase))), width=3)
        # cipratan dari belalai
        for i in range(7):
            u = ((t_lokal * 1.4 + i / 7) % 1.0)
            dx = ujung[0] + u * w * 0.06
            dy = ujung[1] - u * h * 0.10 + u * u * h * 0.16
            r = max(2, int(h * 0.008 * (1 - u * 0.5)))
            d.ellipse([dx - r, dy - r, dx + r, dy + r], fill=(180, 225, 255))
    else:
        # melompat riang + balon naik
        lompat = abs(math.sin(t_lokal * 2.2)) * h * 0.045
        gambar_gajah(d, w * 0.5, h * 0.74 - lompat, s, t_global, berjalan=False)
        rng_warna = [(255, 90, 90), (255, 200, 60), (120, 200, 90),
                     (150, 120, 255), (255, 140, 200)]
        for i, warna in enumerate(rng_warna):
            bx = w * (0.12 + i * 0.19) + math.sin(t_global * 0.8 + i) * w * 0.015
            by = h * 0.62 - ((t_lokal * 0.03 + i * 0.13) % 0.55) * h
            br = h * 0.055
            d.ellipse([bx - br, by - br * 1.2, bx + br, by + br * 1.2], fill=warna)
            d.polygon([(bx - br * 0.25, by + br * 1.2), (bx + br * 0.25, by + br * 1.2),
                       (bx, by + br * 1.45)], fill=warna)
            d.line([bx, by + br * 1.45, bx, by + br * 2.1], fill=HITAM, width=2)
        # confetti
        rng = np.random.default_rng(23)
        for _ in range(24):
            cx = float(rng.uniform(0, w))
            cy = (float(rng.uniform(0, h)) + t_lokal * 40) % h
            c = [(255, 90, 90), (255, 200, 60), (120, 200, 90),
                 (150, 120, 255)][int(rng.integers(0, 4))]
            d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=c)
    # teks lirik di bawah
    teks = lirik_pada(t_global)
    ukuran = max(28, h // 18)
    f = ImageFont.truetype(FONT_BOLD, ukuran)
    bbox = d.textbbox((0, 0), teks, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 28, 14
    x0 = (w - tw) // 2 - pad_x
    y0 = h - th - pad_y * 2 - int(h * 0.03)
    d.rounded_rectangle([x0, y0, x0 + tw + pad_x * 2, y0 + th + pad_y * 2],
                        radius=18, fill=(0, 0, 0, 120))
    d.text(((w - tw) // 2 - bbox[0], y0 + pad_y - bbox[1]), teks,
           font=f, fill=PUTIH)
    return frame


def render_adegan(adegan, bg, w, h, font, keluar):
    """Render 1 adegan (10 detik) -> file MP4 tanpa audio (streaming frame)."""
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", keluar]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    n = FPS * DURASI_ADEGAN
    for i in range(n):
        t_lokal = i / FPS
        t_global = (adegan - 1) * DURASI_ADEGAN + t_lokal
        frame = buat_frame(adegan, bg, t_lokal, t_global, w, h, font)
        try:
            proc.stdin.write(frame.tobytes())
        except BrokenPipeError:
            proc.wait()
            raise RuntimeError(f"ffmpeg mati saat adegan {adegan} frame {i}")
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal (adegan {adegan}, kode {proc.returncode})")


# ------------------------------------------------------------------ musik
def nada(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def sintesis_melodi(wav_path, durasi=30, sr=44100):
    """Melodi orisinal C mayor, 120 BPM, 15 bar. Tanpa hak cipta (dibuat sendiri)."""
    # (midi, ketuk) — C5=72, D5=74, E5=76, F5=77, G5=79, A5=81, C6=84
    melodi = [
        (72, 1), (76, 1), (79, 1), (76, 1), (81, 1), (79, 1), (76, 1), (72, 1),
        (74, 1), (76, 1), (77, 1), (76, 1), (74, 2), (72, 2),
        (76, 1), (79, 1), (81, 1), (79, 1), (77, 1), (76, 1), (74, 1), (76, 1),
        (72, 1), (74, 1), (76, 1), (77, 1), (79, 2), (76, 2),
        (72, 1), (76, 1), (79, 1), (84, 1), (81, 1), (79, 1), (77, 1), (76, 1),
        (74, 1), (77, 1), (81, 1), (77, 1), (76, 2), (74, 2),
        (72, 1), (76, 1), (79, 1), (76, 1), (77, 1), (81, 1), (79, 1), (77, 1),
        (76, 2), (72, 2),
    ]
    bass_bar = [48, 53, 55, 48, 48, 53, 55, 48, 48, 53, 55, 48, 48, 53, 48]
    ketuk_dtk = 0.5  # 120 BPM
    total = int(durasi * sr)
    audio = np.zeros(total, dtype=np.float64)

    def tambah_nada(midi, mulai_dtk, lama_dtk, volume):
        f = nada(midi)
        n = int(lama_dtk * sr)
        t = np.arange(n) / sr
        # attack 10 ms, decay eksponensial
        env = np.minimum(1.0, t / 0.01) * np.exp(-2.2 * t / max(lama_dtk, 0.1))
        gel = (np.sin(2 * np.pi * f * t)
               + 0.3 * np.sin(2 * np.pi * 2 * f * t)
               + 0.12 * np.sin(2 * np.pi * 3 * f * t))
        awal = int(mulai_dtk * sr)
        akhir = min(total, awal + n)
        audio[awal:akhir] += volume * gel[:akhir - awal]

    t = 0.0
    for midi, ketuk in melodi:
        tambah_nada(midi, t, ketuk * ketuk_dtk * 0.95, 0.30)
        t += ketuk * ketuk_dtk
    for i, midi in enumerate(bass_bar):
        tambah_nada(midi, i * 4 * ketuk_dtk, 4 * ketuk_dtk * 0.95, 0.22)
    audio /= max(1e-9, np.max(np.abs(audio)))
    audio *= 0.85
    stereo = np.column_stack([audio, audio])
    data = (stereo * 32767).astype(np.int16)
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


# ------------------------------------------------------------------ utama
def main():
    ap = argparse.ArgumentParser(description="Render video uji 30 detik — gajah biru")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    mulai = time.time()
    if not cek_ram():
        return 3
    w, h = args.width, args.height
    draf = os.path.join(FACTORY, "videos", "drafts")
    os.makedirs(draf, exist_ok=True)
    tag = f"{w}x{h}"
    audio_path = os.path.join(FACTORY, "audio", "TEST30-melodi.wav")
    font = ImageFont.truetype(FONT_BOLD, max(28, h // 18))

    # musik (sekali saja; pakai ulang kalau sudah ada)
    if not os.path.exists(audio_path):
        print("Sintesis melodi orisinal...")
        sintesis_melodi(audio_path)
    print(f"Audio: {audio_path} ({os.path.getsize(audio_path)} byte)")

    scene_files = []
    for adegan in range(1, JUMLAH_ADEGAN + 1):
        t0 = time.time()
        bg = latar_adegan(adegan, w, h)
        keluar = os.path.join(draf, f"TEST30-adegan{adegan}-{tag}.mp4")
        print(f"Adegan {adegan}/{JUMLAH_ADEGAN} -> {keluar} ...", flush=True)
        render_adegan(adegan, bg, w, h, font, keluar)
        scene_files.append(keluar)
        print(f"  selesai {time.time() - t0:.1f} dtk, "
              f"{os.path.getsize(keluar)} byte", flush=True)

    # rakit: gabung adegan + audio
    daftar = os.path.join(draf, f"TEST30-daftar-{tag}.txt")
    with open(daftar, "w") as f:
        for p in scene_files:
            f.write(f"file '{p}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", daftar,
           "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
           "-shortest", args.out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR rakit:", r.stderr[-2000:], file=sys.stderr)
        return 1
    total = time.time() - mulai
    puncak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    ringkasan = {
        "resolusi": f"{w}x{h}", "fps": FPS,
        "durasi_target_dtk": JUMLAH_ADEGAN * DURASI_ADEGAN,
        "adegan": JUMLAH_ADEGAN,
        "file": args.out,
        "ukuran_byte": os.path.getsize(args.out),
        "waktu_render_dtk": round(total, 1),
        "puncak_ram_proses_mb": round(puncak_mb, 1),
    }
    print(json.dumps(ringkasan, indent=2))
    with open(os.path.join(draf, f"TEST30-ringkasan-{tag}.json"), "w") as f:
        json.dump(ringkasan, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
