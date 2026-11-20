#!/usr/bin/env python3
"""Character Bible v1 — render master gajah biru (Uji 2).

Merender dari model LAMA render_3d_preview.py TANPA mengubah file itu:
model di-import, disalin, lalu divariasikan (ekspresi/pose) pada salinan.
File lama tidak disentuh; git history adalah backup-nya.

Hasil: assets/characters/gajah-biru/
  master-front.png, master-side.png, master-back.png
  ekspresi/senang.png, ekspresi/terkejut.png, ekspresi/tidur.png,
  ekspresi/sedih.png
  pose/berdiri.png, pose/berjalan.png, pose/melambai.png,
  pose/duduk.png, pose/melompat.png

Kamera:
  - depan : mata (5.2, 1.6, 0.0), target (0.6, 1.1, 0)
  - samping: mata (0, 1.6, 5.6), target (0, 1.1, 0)
  - belakang: mata (-5.2, 1.6, 0), target (-0.4, 1.1, 0)
  - ekspresi/pose: kamera 3/4 preview-1 (2.6, 1.9, 5.4), target (0, 1.0, 0)

Indeks ellipsoid gajah() (jangan diubah urutannya di file lama):
  0 badan, 1 perut, 2 kepala, 3 telinga luar, 4 telinga dalam,
  5-10 belalai (6 bola), 11-14 kaki, 15 ekor, 16 rumbai ekor,
  17 mata putih, 18 pupil, 19 pantulan, 20 pipi, 21-22 jambul.
"""

import copy
import importlib.util
import json
import os
import resource
import sys
import time

import numpy as np
from PIL import Image

REPO = os.path.expanduser("~/workspace/kids-youtube-factory")
FACTORY = os.path.expanduser("~/workspace/youtube-kids")
KARAKTER = os.path.join(FACTORY, "assets", "characters", "gajah-biru")

# --- import model lama TANPA mengubahnya
_spec = importlib.util.spec_from_file_location(
    "r3d", os.path.join(REPO, "scripts", "render_3d_preview.py"))
r3d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(r3d)


def salin(objek):
    """Salinan dalam dari daftar ellipsoid (pusat/jari/warna bisa diubah)."""
    hasil = []
    for e in objek:
        baru = r3d.Elips(tuple(e.c), tuple(e.r), e.warna, e.ambient,
                         e.diffuse, e.specular, e.kilau, e.kulit)
        hasil.append(baru)
    return hasil


def geser(objek, indeks, dx=0.0, dy=0.0, dz=0.0):
    for i in indeks:
        objek[i].c = objek[i].c + np.array([dx, dy, dz], dtype=np.float32)


def skala(objek, indeks, sx=1.0, sy=1.0, sz=1.0):
    for i in indeks:
        objek[i].r = objek[i].r * np.array([sx, sy, sz], dtype=np.float32)


def atur_pusat(objek, indeks, pusat):
    objek[indeks].c = np.array(pusat, dtype=np.float32)


def atur_jari(objek, indeks, jari):
    objek[indeks].r = np.array(jari, dtype=np.float32)


# ------------------------------------------------------------------ ekspresi
def ekspresi_senang(objek):
    return objek  # model dasar = senang


def ekspresi_terkejut(objek):
    skala(objek, [17], 1.3, 1.3, 1.3)   # mata membesar
    skala(objek, [18], 1.25, 1.25, 1.25)
    geser(objek, [5, 6, 7, 8, 9, 10], dy=0.25, dx=-0.05)  # belalai terangkat
    geser(objek, [3, 4], dz=0.06)       # telinga sedikit terbuka
    return objek


def ekspresi_tidur(objek):
    # mata menutup: putih mata jadi garis tipis warna biru tua
    atur_jari(objek, 17, (0.14, 0.03, 0.14))
    objek[17].warna = r3d.BIRU_TUA
    skala(objek, [18, 19], 0.001, 0.001, 0.001)  # pupil + pantulan hilang
    geser(objek, [5, 6, 7, 8, 9, 10], dy=-0.08)  # belalai rileks
    return objek


def ekspresi_sedih(objek):
    geser(objek, [18], dy=-0.03)        # pupil turun
    skala(objek, [18], 0.8, 0.8, 0.8)   # pupil mengecil
    geser(objek, [3, 4], dy=-0.08)      # telinga terkulai
    geser(objek, [5, 6, 7, 8, 9, 10], dy=-0.05)
    return objek


EKSPRESI = {
    "senang": ekspresi_senang,
    "terkejut": ekspresi_terkejut,
    "tidur": ekspresi_tidur,
    "sedih": ekspresi_sedih,
}

# ------------------------------------------------------------------ pose
POSES = {}


def pose_berdiri(objek):
    return objek


def pose_berjalan(objek):
    geser(objek, [11], dx=0.18)   # kaki depan-dekat maju
    geser(objek, [12], dx=-0.12)  # kaki depan-jauh mundur
    geser(objek, [13], dx=-0.18)  # kaki belakang-dekat mundur
    geser(objek, [14], dx=0.12)   # kaki belakang-jauh maju
    geser(objek, [5, 6, 7, 8, 9, 10], dx=0.05)  # belalai berayun
    return objek


def pose_melambai(objek):
    # belalai terangkat tinggi (melambai)
    pusat_baru = [(1.45, 1.55, 0.06), (1.42, 1.72, 0.06),
                  (1.35, 1.85, 0.06), (1.25, 1.92, 0.06),
                  (1.12, 1.95, 0.06), (1.00, 1.92, 0.06)]
    for i, p in zip(range(5, 11), pusat_baru):
        atur_pusat(objek, i, p)
    geser(objek, [3], dz=0.08)
    return objek


def pose_duduk(objek):
    # badan + kepala turun; kaki depan lurus ke depan (horizontal)
    geser(objek, [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 16, 17, 18, 19, 20,
                  21, 22], dy=-0.30)
    geser(objek, [1], dy=-0.27)
    atur_pusat(objek, 11, (1.05, 0.18, 0.30))
    atur_pusat(objek, 12, (1.05, 0.18, -0.30))
    atur_jari(objek, 11, (0.44, 0.17, 0.17))
    atur_jari(objek, 12, (0.44, 0.17, 0.17))
    return objek


def pose_melompat(objek):
    geser(objek, list(range(23)), dy=0.45)   # seluruh tubuh naik
    geser(objek, [11, 12, 13, 14], dy=0.15)  # kaki terlipat ke atas
    geser(objek, [5, 6, 7, 8, 9, 10], dy=0.10)
    return objek


POSES = {
    "berdiri": pose_berdiri,
    "berjalan": pose_berjalan,
    "melambai": pose_melambai,
    "duduk": pose_duduk,
    "melompat": pose_melompat,
}

KAMERA_34 = ((2.6, 1.9, 5.4), (0, 1.0, 0))
KAMERA = {
    "master-front": ((5.2, 1.6, 0.0), (0.6, 1.1, 0)),
    "master-side": ((0.0, 1.6, 5.6), (0, 1.1, 0)),
    "master-back": ((-5.2, 1.6, 0.0), (-0.4, 1.1, 0)),
}


def render_satu(objek, mata, target, keluar, w=640, h=360):
    mulai = time.time()
    linear = r3d.render(objek, w, h, mata, target)
    gambar = (np.clip(linear, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    os.makedirs(os.path.dirname(keluar), exist_ok=True)
    Image.fromarray(gambar, "RGB").save(keluar)
    total = time.time() - mulai
    puncak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {
        "file": keluar,
        "ukuran_byte": os.path.getsize(keluar),
        "waktu_render_dtk": round(total, 2),
        "puncak_ram_proses_mb": round(puncak_mb, 1),
    }


def main():
    ringkasan = []
    # --- 3 tampak master (model dasar, tanpa variasi)
    for nama, (mata, target) in KAMERA.items():
        r = render_satu(salin(r3d.gajah()), mata, target,
                        os.path.join(KARAKTER, f"{nama}.png"))
        r["jenis"] = "master"
        r["nama"] = nama
        ringkasan.append(r)
        print(f"{nama}: {r['waktu_render_dtk']} dtk, "
              f"{r['puncak_ram_proses_mb']} MB", flush=True)
    # --- 4 ekspresi (kamera 3/4)
    mata, target = KAMERA_34
    for nama, fn in EKSPRESI.items():
        objek = fn(salin(r3d.gajah()))
        r = render_satu(objek, mata, target,
                        os.path.join(KARAKTER, "ekspresi", f"{nama}.png"))
        r["jenis"] = "ekspresi"
        r["nama"] = nama
        ringkasan.append(r)
        print(f"ekspresi/{nama}: {r['waktu_render_dtk']} dtk, "
              f"{r['puncak_ram_proses_mb']} MB", flush=True)
    # --- 5 pose (kamera 3/4)
    for nama, fn in POSES.items():
        objek = fn(salin(r3d.gajah()))
        r = render_satu(objek, mata, target,
                        os.path.join(KARAKTER, "pose", f"{nama}.png"))
        r["jenis"] = "pose"
        r["nama"] = nama
        ringkasan.append(r)
        print(f"pose/{nama}: {r['waktu_render_dtk']} dtk, "
              f"{r['puncak_ram_proses_mb']} MB", flush=True)

    total_waktu = round(sum(x["waktu_render_dtk"] for x in ringkasan), 1)
    with open(os.path.join(KARAKTER, "render-summary.json"), "w") as f:
        json.dump({"total_gambar": len(ringkasan),
                   "total_waktu_render_dtk": total_waktu,
                   "resolusi": "640x360",
                   "mesin": "render_3d_preview.py (raytracer, tidak diubah)",
                   "gambar": ringkasan}, f, indent=2)
    print(json.dumps({"total_gambar": len(ringkasan),
                      "total_waktu_render_dtk": total_waktu}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
