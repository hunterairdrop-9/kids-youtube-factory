#!/usr/bin/env python3
"""Rasterizer v2 — prototipe (Uji 6, AI Kids YouTube Factory).

Rasterizer segitiga murni numpy + Pillow, SEPARAT dari raytracer lama
(scripts/render_3d_preview.py tidak diubah sama sekali).

Cara kerja:
  1. Setiap ellipsoid diubah menjadi mesh segitiga (tessellasi bola
     lat-long, stacks x slices — default 16x24).
  2. Proyeksi perspektif dengan kamera yang SAMA dengan raytracer
     (posisi mata, target, FOV 42 derajat).
  3. Z-buffer (disimpan sebagai w = 1/z_kamera; nilai besar = dekat),
     rasterisasi segitiga dengan fungsi tepi (edge function),
     shading Gouraud: Lambert + ambient + specular Blinn-Phong dengan
     parameter material yang SAMA dengan Elips. Interpolasi warna
     perspective-correct (warna * w diinterpolasi, lalu dibagi w).
  4. Tanah (bidang y=0) + langit dihitung dengan matematika yang SAMA
     dengan raytracer (vektor penuh, bukan per-segitiga), termasuk
     bayangan gajah di atas tanah (shadow ray ke matahari, sama seperti
     raytracer).

Yang DIHILANGKAN (jujur, dicatat di dokumen perbandingan):
  - Bayangan diri (self-shadow) pada permukaan gajah sendiri: sinar
    bayangan hanya diuji untuk titik tanah, bukan untuk titik gajah.
    Dampak visual: bayangan belalai/telinga di atas badan tidak ada;
    pada sudut kamera preview-1 dampaknya kecil karena matahari datang
    dari kanan-atas-depan dan permukaan yang menghadap kamera sebagian
    besar langsung terkena matahari.
  - Kabut diterapkan per-vertex (bukan per-piksel seperti raytracer);
    untuk segitiga kecil selisihnya tidak terlihat.

Tidak memakai Blender, tidak memakai API, tidak ada instalasi baru.
Hanya numpy + Pillow. Hemat RAM.

Pemakaian:
  python3 render_rasterizer_v2.py --out previews/rasterizer-v2-frame1.png
  python3 render_rasterizer_v2.py --stacks 12 --slices 18 --out /tmp/x.png
"""

import argparse
import importlib.util
import json
import math
import os
import resource
import sys
import time

import numpy as np
from PIL import Image

FACTORY = os.path.expanduser("~/workspace/youtube-kids")
RT_PATH = os.path.expanduser(
    "~/workspace/kids-youtube-factory/scripts/render_3d_preview.py")

# Muat modul raytracer LAMA hanya untuk dibaca (model + konstanta warna).
# File itu tidak diubah; importlib di sini hanya membaca.
_spec = importlib.util.spec_from_file_location("rt_preview", RT_PATH)
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

MATAHARI = rt.MATAHARI


# ------------------------------------------------------------------ mesh
def tessellasi(e, stacks, slices):
    """Satu ellipsoid -> titik, normal, segitiga (grid lat-long bola).

    Mengembalikan pos (V,3) dunia, normal (V,3) permukaan ellipsoid,
    dan tris (T,3) indeks. Baris kutub menghasilkan segitiga
    degenerat (luas 0) yang nanti dilewati saat rasterisasi.
    """
    theta = np.linspace(0.0, np.pi, stacks + 1)          # 0 = kutub atas
    phi = np.linspace(0.0, 2 * np.pi, slices, endpoint=False)
    st, ct = np.sin(theta), np.cos(theta)
    sp, cp = np.sin(phi), np.cos(phi)
    # arah bola satuan: (sin t cos p, cos t, sin t sin p)
    arah = np.stack([
        np.outer(st, cp),
        np.outer(ct, np.ones_like(cp)),
        np.outer(st, sp),
    ], axis=-1)                                          # (stacks+1, slices, 3)
    pos = e.c[None, None, :] + arah * e.r[None, None, :]
    # normal ellipsoid: (p - c) / r^2, dinormalisasi
    nor = arah / (e.r[None, None, :] ** 2)
    nor /= np.linalg.norm(nor, axis=-1, keepdims=True)
    v = pos.reshape(-1, 3)
    n = nor.reshape(-1, 3)
    # segitiga antar baris grid
    ii, jj = np.meshgrid(np.arange(stacks), np.arange(slices), indexing="ij")
    a = ii * slices + jj
    b = ii * slices + (jj + 1) % slices
    c = (ii + 1) * slices + (jj + 1) % slices
    d = (ii + 1) * slices + jj
    tris = np.stack([
        np.stack([a, b, c], axis=-1),
        np.stack([a, c, d], axis=-1),
    ], axis=1).reshape(-1, 3)
    return v.astype(np.float32), n.astype(np.float32), tris.astype(np.int32)


def bangun_mesh(objek, stacks, slices):
    """Gabungkan semua ellipsoid jadi satu mesh + albedo per vertex."""
    semua_pos, semua_nor, semua_alb, semua_mat = [], [], [], []
    semua_tris = []
    offset = 0
    for e in objek:
        pos, nor, tris = tessellasi(e, stacks, slices)
        alb = np.broadcast_to(e.warna, pos.shape).copy()
        if e.kulit:
            mott = 0.97 + 0.03 * np.sin(pos[:, 0] * 9) \
                * np.sin(pos[:, 1] * 7 + 1) * np.sin(pos[:, 2] * 8)
            alb *= mott[:, None]
        semua_pos.append(pos)
        semua_nor.append(nor)
        semua_alb.append(alb.astype(np.float32))
        semua_mat.append(np.tile(
            np.array([e.ambient, e.diffuse, e.specular, e.kilau],
                     dtype=np.float32), (len(pos), 1)))
        semua_tris.append(tris + offset)
        offset += len(pos)
    return (np.concatenate(semua_pos), np.concatenate(semua_nor),
            np.concatenate(semua_alb), np.concatenate(semua_mat),
            np.concatenate(semua_tris))


# ------------------------------------------------------------------ kamera
def basis_kamera(mata, target):
    fwd = np.array(target, dtype=np.float32) - np.array(mata, dtype=np.float32)
    fwd /= np.linalg.norm(fwd)
    atas = np.array([0, 1, 0], dtype=np.float32)
    kanan = np.cross(fwd, atas)
    kanan /= np.linalg.norm(kanan)
    atas2 = np.cross(kanan, fwd)
    return fwd, kanan, atas2


def cahaya_vertex(pos, nor, alb, mat, mata):
    """Shading Gouraud per vertex: ambient + Lambert + Blinn-Phong + kabut.

    Sama rumusnya dengan raytracer, tanpa faktor bayangan (self-shadow
    dihilangkan — lihat catatan di docstring modul).
    """
    lambert = np.clip(np.sum(nor * MATAHARI[None, :], axis=-1), 0, 1)
    pandang = mata[None, :] - pos
    pandang /= np.linalg.norm(pandang, axis=-1, keepdims=True)
    tengah = MATAHARI[None, :] + pandang
    tengah /= np.linalg.norm(tengah, axis=-1, keepdims=True)
    blinn = np.clip(np.sum(nor * tengah, axis=-1), 0, 1) ** mat[:, 3]
    cahaya = mat[:, 0] + mat[:, 1] * lambert
    warna = alb * cahaya[:, None] + mat[:, 2][:, None] * blinn[:, None]
    # kabut jarak (sama seperti raytracer, tapi memakai jarak vertex)
    jarak = np.linalg.norm(mata[None, :] - pos, axis=-1)
    kabut = (1 - np.exp(-0.02 * jarak))
    kabut = np.where(jarak > 5, kabut * 0.6, 0.0)
    langit_horizon = np.array([0.85, 0.92, 1.0], dtype=np.float32)
    warna = warna * (1 - kabut[:, None]) + langit_horizon[None, :] * kabut[:, None]
    return np.clip(warna, 0, 1).astype(np.float32)


# ------------------------------------------------------------------ tanah + langit
def latar_dan_zbuf(w, h, mata, target, fov_derajat, objek):
    """Tanah + langit persis seperti raytracer (vektor penuh).

    Mengembalikan gambar latar (linear, h,w,3) dan w-buffer tanah
    (w = 1/z_kamera; 0 = tidak ada tanah / langit).
    Termasuk bayangan gajah di tanah (shadow ray, sama seperti raytracer).
    """
    fwd, kanan, atas2 = basis_kamera(mata, target)
    aspek = w / h
    tan = math.tan(math.radians(fov_derajat) / 2)
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
    ys = 1 - (np.arange(h, dtype=np.float32) + 0.5) / h * 2
    xx, yy = np.meshgrid(xs, ys)
    arah = (fwd[None, None, :]
            + (xx * aspek * tan)[..., None] * kanan[None, None, :]
            + (yy * tan)[..., None] * atas2[None, None, :])
    arah /= np.linalg.norm(arah, axis=-1, keepdims=True)
    asal = np.array(mata, dtype=np.float32)

    dy = arah[..., 1]
    t_tanah = np.where(dy < -1e-6, -asal[1] / np.where(dy == 0, -1, dy), np.inf)
    ada_tanah = np.isfinite(t_tanah)
    titik = asal[None, None, :] + arah * t_tanah[..., None]

    # shading tanah (normal (0,1,0); material sama seperti raytracer)
    albedo = np.zeros((h, w, 3), dtype=np.float32)
    albedo[ada_tanah] = rt.warna_tanah(titik[ada_tanah])
    lambert = np.clip(dy * 0 + MATAHARI[1], 0, 1)  # N=(0,1,0) . matahari
    pandang = -arah
    tengah = MATAHARI[None, None, :] + pandang
    tengah /= np.linalg.norm(tengah, axis=-1, keepdims=True)
    blinn = np.clip(tengah[..., 1], 0, 1) ** 8.0
    # bayangan: sinar dari titik tanah ke matahari, kena ellipsoid?
    bayang = np.zeros((h, w), dtype=bool)
    if np.any(ada_tanah):
        idx = np.where(ada_tanah)
        asal_b = titik[ada_tanah] + np.array([0, 1e-3, 0], dtype=np.float32)
        arah_b = np.broadcast_to(MATAHARI, asal_b.shape)
        for e in objek:
            oc = asal_b - e.c[None, :]
            inv_r = 1.0 / e.r
            a = np.sum((arah_b * inv_r[None, :]) ** 2, axis=-1)
            bq = 2 * np.sum((oc * inv_r[None, :])
                            * (arah_b * inv_r[None, :]), axis=-1)
            c0 = np.sum((oc * inv_r[None, :]) ** 2, axis=-1) - 1.0
            disc = bq * bq - 4 * a * c0
            valid = disc > 0
            akar = np.sqrt(np.maximum(disc, 0))
            t1 = (-bq - akar) / (2 * a)
            t2 = (-bq + akar) / (2 * a)
            kena_b = valid & ((t1 > 0.001) | (t2 > 0.001))
            bayang[idx[0][kena_b], idx[1][kena_b]] = True
    cahaya = 0.35 + 0.65 * lambert * np.where(bayang, 0.0, 1.0)
    warna_t = albedo * cahaya[..., None] \
        + 0.05 * blinn[..., None] * np.where(bayang, 0.0, 1.0)[..., None]
    # kabut tanah (sama seperti raytracer)
    langit_horizon = np.array([0.85, 0.92, 1.0], dtype=np.float32)
    kabut = (1 - np.exp(-0.02 * t_tanah))[..., None]
    kabut = np.where((t_tanah > 5)[..., None], kabut * 0.6, 0.0)
    warna_t = warna_t * (1 - kabut) + langit_horizon[None, None, :] * kabut

    langit = rt.warna_langit(arah)
    gambar = np.where(ada_tanah[..., None], warna_t, langit)
    # w-buffer tanah: w = 1/z_kamera ; z_kamera = t * (arah . fwd)
    cos_t = np.sum(arah * fwd[None, None, :], axis=-1)
    z_tanah = t_tanah * cos_t
    w_tanah = np.where(ada_tanah & (z_tanah > 1e-6), 1.0 / z_tanah, 0.0)
    return np.clip(gambar, 0, 1), w_tanah.astype(np.float32)


# ------------------------------------------------------------------ rasterisasi
def rasterisasi(pos, nor, alb, mat, tris, w, h, mata, target, fov_derajat,
                gambar, wbuf):
    """Rasterisasi segitiga ke gambar + w-buffer (in-place).

    Mengembalikan jumlah segitiga yang benar-benar dirasterisasi
    (setelah culling) dan jumlah piksel gajah yang ditulis.
    """
    fwd, kanan, atas2 = basis_kamera(mata, target)
    aspek = w / h
    tan = math.tan(math.radians(fov_derajat) / 2)
    mata = np.array(mata, dtype=np.float32)

    # --- ke ruang kamera (vektor penuh)
    d = pos - mata[None, :]
    xc = d @ kanan
    yc = d @ atas2
    zc = d @ fwd
    # --- shading per vertex
    warna_v = cahaya_vertex(pos, nor, alb, mat, mata)
    # --- proyeksi layar
    sx = (xc / (zc * aspek * tan) + 1) * 0.5 * w
    sy = (1 - yc / (zc * tan)) * 0.5 * h
    w_inv = np.where(zc > 1e-6, 1.0 / np.where(zc > 1e-6, zc, 1.0), 0.0)
    cw = warna_v * w_inv[:, None]

    # --- culling per segitiga (vektor penuh): belakang kamera, menghadap
    #     menjauh, atau degenerat
    v0 = pos[tris[:, 0]]
    v1 = pos[tris[:, 1]]
    v2 = pos[tris[:, 2]]
    normal_muka = np.cross(v1 - v0, v2 - v0)
    pusat_muka = (v0 + v1 + v2) / 3.0
    ke_mata = mata[None, :] - pusat_muka
    menghadap = np.sum(normal_muka * ke_mata, axis=-1) > 0
    depan = np.all(zc[tris] > 0.05, axis=1)
    luas = (sx[tris[:, 1]] - sx[tris[:, 0]]) * (sy[tris[:, 2]] - sy[tris[:, 0]]) \
        - (sy[tris[:, 1]] - sy[tris[:, 0]]) * (sx[tris[:, 2]] - sx[tris[:, 0]])
    hidup = menghadap & depan & (np.abs(luas) > 1e-9)
    tris_h = tris[hidup]
    luas_h = luas[hidup]

    piksel_ditulis = 0
    for k in range(len(tris_h)):
        i0, i1, i2 = tris_h[k]
        x0, y0 = sx[i0], sy[i0]
        x1, y1 = sx[i1], sy[i1]
        x2, y2 = sx[i2], sy[i2]
        area = luas_h[k]
        xmin = max(0, int(math.floor(min(x0, x1, x2))))
        xmax = min(w - 1, int(math.ceil(max(x0, x1, x2))))
        ymin = max(0, int(math.floor(min(y0, y1, y2))))
        ymax = min(h - 1, int(math.ceil(max(y0, y1, y2))))
        if xmin > xmax or ymin > ymax:
            continue
        px, py = np.meshgrid(
            np.arange(xmin, xmax + 1, dtype=np.float32) + 0.5,
            np.arange(ymin, ymax + 1, dtype=np.float32) + 0.5)
        # fungsi tepi -> bobot barycentric (berlaku untuk kedua winding)
        b0 = ((x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)) / area
        b1 = ((x0 - x2) * (py - y2) - (y0 - y2) * (px - x2)) / area
        b2 = ((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)) / area
        dalam = (b0 >= 0) & (b1 >= 0) & (b2 >= 0)
        if not np.any(dalam):
            continue
        # interpolasi perspective-correct: w dan (warna*w) linear di layar
        wi = b0 * w_inv[i0] + b1 * w_inv[i1] + b2 * w_inv[i2]
        dekat = dalam & (wi > wbuf[ymin:ymax + 1, xmin:xmax + 1])
        if not np.any(dekat):
            continue
        cwr = b0 * cw[i0, 0] + b1 * cw[i1, 0] + b2 * cw[i2, 0]
        cwg = b0 * cw[i0, 1] + b1 * cw[i1, 1] + b2 * cw[i2, 1]
        cwb = b0 * cw[i0, 2] + b1 * cw[i1, 2] + b2 * cw[i2, 2]
        ys, xs = np.where(dekat)
        wbaru = wi[dekat]
        gambar[ymin + ys, xmin + xs, 0] = cwr[dekat] / wbaru
        gambar[ymin + ys, xmin + xs, 1] = cwg[dekat] / wbaru
        gambar[ymin + ys, xmin + xs, 2] = cwb[dekat] / wbaru
        wbuf[ymin + ys, xmin + xs] = wbaru
        piksel_ditulis += int(np.sum(dekat))
    return int(np.sum(hidup)), piksel_ditulis


# ------------------------------------------------------------------ utama
def main():
    ap = argparse.ArgumentParser(description="Rasterizer v2 (prototipe uji 6)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=360)
    ap.add_argument("--stacks", type=int, default=16,
                    help="baris lat-long per ellipsoid")
    ap.add_argument("--slices", type=int, default=24,
                    help="kolom lat-long per ellipsoid")
    args = ap.parse_args()

    mulai = time.time()
    w, h = args.width, args.height
    mata, target = (2.6, 1.9, 5.4), (0, 1.0, 0)
    objek = rt.gajah()
    print(f"Rasterizer v2: {len(objek)} ellipsoid, mesh "
          f"{args.stacks}x{args.slices}, {w}x{h} ...", flush=True)

    pos, nor, alb, mat, tris = bangun_mesh(objek, args.stacks, args.slices)
    gambar, wbuf = latar_dan_zbuf(w, h, mata, target, 42.0, objek)
    n_hidup, n_piksel = rasterisasi(pos, nor, alb, mat, tris, w, h,
                                    mata, target, 42.0, gambar, wbuf)

    gambar8 = (np.clip(gambar, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    Image.fromarray(gambar8, "RGB").save(args.out)

    total = time.time() - mulai
    ru = resource.getrusage(resource.RUSAGE_SELF)
    puncak_mb = ru.ru_maxrss / 1024
    cpu_dtk = ru.ru_utime + ru.ru_stime
    ringkasan = {
        "metode": "rasterizer-v2",
        "resolusi": f"{w}x{h}",
        "objek": len(objek),
        "mesh": {"stacks": args.stacks, "slices": args.slices,
                 "vertex": int(len(pos)),
                 "segitiga_total": int(len(tris)),
                 "segitiga_dirasterisasi": n_hidup,
                 "piksel_gajah": n_piksel},
        "file": args.out,
        "ukuran_byte": os.path.getsize(args.out),
        "waktu_render_dtk": round(total, 2),
        "waktu_cpu_dtk": round(cpu_dtk, 2),
        "puncak_ram_proses_mb": round(puncak_mb, 1),
    }
    print(json.dumps(ringkasan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
