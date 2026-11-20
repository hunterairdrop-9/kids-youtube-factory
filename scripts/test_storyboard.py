#!/usr/bin/env python3
"""Uji Storyboard Validator (Uji 7).

Menjalankan validator pada:
  1. storyboard contoh yang VALID (harus lolos)
  2. enam storyboard TIDAK VALID (masing-masing harus ditolak dengan
     pesan error yang tepat)

Mutasi dibuat di /tmp dari salinan storyboard contoh — file contoh
tidak diubah.

Pemakaian:  python3 scripts/test_storyboard.py
Exit 0 bila semua ekspektasi terpenuhi, 1 bila ada yang meleset.
"""

import copy
import json
import os
import subprocess
import sys

REPO = os.path.expanduser("~/workspace/kids-youtube-factory")
FACTORY = os.path.expanduser("~/workspace/youtube-kids")
CONTOH = os.path.join(FACTORY, "storyboard",
                      "EP-TEST01-gajah-biru-kecil.json")
BIBLE = os.path.join(FACTORY, "assets", "characters", "gajah-biru",
                     "character_bible.json")
TMP = "/tmp/uji-storyboard"


def jalankan(path):
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "storyboard.py"),
         "validate", path, "--bible", BIBLE, "--root", FACTORY],
        capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"valid": None, "errors": [f"output bukan JSON: {r.stdout}"],
                "warnings": []}


def mutasi(nama, ubah):
    with open(CONTOH) as f:
        data = json.load(f)
    ubah(data)
    path = os.path.join(TMP, f"{nama}.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def main():
    os.makedirs(TMP, exist_ok=True)
    hasil = []

    def catat(nama, lolos, detail=""):
        hasil.append((nama, lolos, detail))
        print(f"{'LOLOS' if lolos else 'GAGAL'}  {nama}"
              + (f" — {detail}" if detail else ""))

    # --- 1. contoh valid
    lap = jalankan(CONTOH)
    catat("valid: storyboard contoh EP-TEST01",
          lap.get("valid") is True and not lap.get("errors"),
          f"errors={lap.get('errors')}, warnings={lap.get('warnings')}")

    # --- 2. field wajib hilang
    p = mutasi("tidak-valid-field-hilang",
               lambda d: d["adegan"][0].pop("aksi"))
    lap = jalankan(p)
    catat("tidak valid: field 'aksi' hilang",
          lap.get("valid") is False
          and any("aksi" in e for e in lap.get("errors", [])),
          "; ".join(lap.get("errors", [])))

    # --- 3. jumlah durasi tidak cocok
    p = mutasi("tidak-valid-durasi",
               lambda d: d["adegan"][0].update({"durasi_dtk": 10}))
    lap = jalankan(p)
    catat("tidak valid: jumlah durasi adegan != total",
          lap.get("valid") is False
          and any("durasi" in e for e in lap.get("errors", [])),
          "; ".join(lap.get("errors", [])))

    # --- 4. scene_id duplikat
    p = mutasi("tidak-valid-duplikat",
               lambda d: d["adegan"][1].update(
                   {"scene_id": "EP-TEST01-S01"}))
    lap = jalankan(p)
    catat("tidak valid: scene_id duplikat",
          lap.get("valid") is False
          and any("duplikat" in e for e in lap.get("errors", [])),
          "; ".join(lap.get("errors", [])))

    # --- 5. ekspresi tidak ada di Bible
    p = mutasi("tidak-valid-ekspresi",
               lambda d: d["adegan"][0].update({"ekspresi": "marah"}))
    lap = jalankan(p)
    catat("tidak valid: ekspresi 'marah' tidak ada di Bible",
          lap.get("valid") is False
          and any("marah" in e for e in lap.get("errors", [])),
          "; ".join(lap.get("errors", [])))

    # --- 6. referensi gambar tidak ada
    p = mutasi("tidak-valid-gambar",
               lambda d: d["adegan"][0].update(
                   {"referensi_gambar":
                    "assets/characters/gajah-biru/pose/tidak-ada.png"}))
    lap = jalankan(p)
    catat("tidak valid: referensi_gambar tidak ditemukan",
          lap.get("valid") is False
          and any("referensi_gambar" in e for e in lap.get("errors", [])),
          "; ".join(lap.get("errors", [])))

    # --- 7. status tidak dikenal
    p = mutasi("tidak-valid-status",
               lambda d: d["adegan"][0].update({"status": "jalan"}))
    lap = jalankan(p)
    catat("tidak valid: status 'jalan' tidak dikenal",
          lap.get("valid") is False
          and any("status" in e for e in lap.get("errors", [])),
          "; ".join(lap.get("errors", [])))

    lolos = sum(1 for _, ok, _ in hasil if ok)
    print(f"\n{len(hasil)} kasus, {lolos} lolos, {len(hasil) - lolos} gagal")
    return 0 if lolos == len(hasil) else 1


if __name__ == "__main__":
    raise SystemExit(main())
