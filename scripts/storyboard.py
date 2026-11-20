#!/usr/bin/env python3
"""Storyboard Validator — AI Kids YouTube Factory (Uji 7).

Memvalidasi storyboard episode (JSON) terhadap skema di
docs/ai-visual-production-architecture.md §4.2.

Pemakaian:
  python3 scripts/storyboard.py validate <file.json>
      [--bible <character_bible.json>] [--root <factory-dir>]
  python3 scripts/storyboard.py --help

Aturan validasi:
  Episode:
    - field wajib: episode_id, judul, durasi_total_dtk, karakter,
      character_bible, lirik_file, musik, adegan
    - episode_id: huruf besar/angka/strip (mis. EP-TEST01)
    - durasi_total_dtk: angka > 0
    - karakter: list tak kosong
    - character_bible: file harus ada (relatif ke --root)
    - lirik_file: file harus ada (relatif ke --root)
    - musik: dict dengan sumber, tempo_bpm, nada_dasar
    - adegan: list tak kosong
  Adegan (setiap adegan):
    - field wajib: scene_id, durasi_dtk, deskripsi_visual, karakter,
      aksi, ekspresi, gerakan_kamera, lirik, audio, referensi_gambar,
      prompt_gambar, status
    - scene_id: unik, pola <episode_id>-S<2 digit> (mis. EP-TEST01-S01)
    - durasi_dtk: angka > 0
    - jumlah durasi adegan == durasi_total_dtk (toleransi 0,01 dtk)
    - ekspresi: harus ada di Character Bible (bila --bible diberikan;
      bila tidak, daftar bawaan Bible v1 gajah biru)
    - status: draft | disetujui | ditolak | selesai
    - karakter adegan: subset dari karakter episode
    - referensi_gambar: file harus ada (relatif ke --root)

Keluaran: laporan JSON di stdout {valid, errors, warnings}.
Exit code 0 bila valid (warning tidak menggagalkan), 1 bila ada error.
Tidak memakai API, tidak ada instalasi baru.
"""

import argparse
import json
import os
import re
import sys

FACTORY = os.path.expanduser("~/workspace/youtube-kids")

EPISODE_WAJIB = ["episode_id", "judul", "durasi_total_dtk", "karakter",
                 "character_bible", "lirik_file", "musik", "adegan"]
MUSIK_WAJIB = ["sumber", "tempo_bpm", "nada_dasar"]
ADEGAN_WAJIB = ["scene_id", "durasi_dtk", "deskripsi_visual", "karakter",
                "aksi", "ekspresi", "gerakan_kamera", "lirik", "audio",
                "referensi_gambar", "prompt_gambar", "status"]
STATUS_OK = {"draft", "disetujui", "ditolak", "selesai"}
EKSPRESI_BAWAAN = {"senang", "terkejut", "tidur", "sedih"}


def _ada(path_root, rel):
    return os.path.isfile(os.path.join(path_root, rel))


def _ekspresi_bible(path_bible):
    """Daftar ekspresi dari character_bible.json (bila bisa dibaca)."""
    try:
        with open(path_bible) as f:
            data = json.load(f)
        eks = data.get("referensi_visual", {}).get("ekspresi", {})
        if isinstance(eks, dict) and eks:
            return set(eks.keys())
    except (OSError, ValueError):
        pass
    return None


def validasi(data, path_root, path_bible=None):
    errors = []
    warnings = []

    if not isinstance(data, dict):
        return False, ["storyboard harus berupa objek JSON"], []

    # --- episode: field wajib
    for field in EPISODE_WAJIB:
        if field not in data:
            errors.append(f"episode: field wajib '{field}' hilang")

    episode_id = data.get("episode_id", "")
    if episode_id and not re.fullmatch(r"[A-Z0-9][A-Z0-9-]*", str(episode_id)):
        errors.append("episode_id harus huruf besar/angka/strip "
                      "(mis. EP-TEST01)")

    total = data.get("durasi_total_dtk")
    if total is not None and (not isinstance(total, (int, float))
                             or total <= 0):
        errors.append("durasi_total_dtk harus angka > 0")

    karakter_ep = data.get("karakter")
    if karakter_ep is not None and (not isinstance(karakter_ep, list)
                                    or not karakter_ep):
        errors.append("karakter episode harus list tak kosong")

    bible = data.get("character_bible")
    if bible and not _ada(path_root, bible):
        errors.append(f"character_bible tidak ditemukan: {bible}")

    lirik = data.get("lirik_file")
    if lirik and not _ada(path_root, lirik):
        errors.append(f"lirik_file tidak ditemukan: {lirik}")

    musik = data.get("musik")
    if isinstance(musik, dict):
        for field in MUSIK_WAJIB:
            if field not in musik:
                errors.append(f"musik: field wajib '{field}' hilang")
        tempo = musik.get("tempo_bpm")
        if tempo is not None and (not isinstance(tempo, (int, float))
                                  or tempo <= 0):
            errors.append("musik.tempo_bpm harus angka > 0")
    elif musik is not None:
        errors.append("musik harus berupa objek")

    # --- ekspresi yang diizinkan
    ekspresi_ok = EKSPRESI_BAWAAN
    if path_bible and os.path.isfile(path_bible):
        dari_bible = _ekspresi_bible(path_bible)
        if dari_bible:
            ekspresi_ok = dari_bible

    # --- adegan
    adegan = data.get("adegan")
    if adegan is None:
        return False, errors, warnings
    if not isinstance(adegan, list) or not adegan:
        errors.append("adegan harus list tak kosong")
        return False, errors, warnings

    pola_scene = re.compile(rf"^{re.escape(str(episode_id))}-S\d{{2}}$") \
        if episode_id else None
    lihat_id = set()
    jumlah_durasi = 0.0
    for i, adeg in enumerate(adegan):
        label = adeg.get("scene_id", f"adegan[{i}]") \
            if isinstance(adeg, dict) else f"adegan[{i}]"
        if not isinstance(adeg, dict):
            errors.append(f"{label}: adegan harus berupa objek")
            continue
        for field in ADEGAN_WAJIB:
            if field not in adeg:
                errors.append(f"{label}: field wajib '{field}' hilang")
        sid = adeg.get("scene_id")
        if sid:
            if sid in lihat_id:
                errors.append(f"{label}: scene_id duplikat '{sid}'")
            lihat_id.add(sid)
            if pola_scene and not pola_scene.match(str(sid)):
                errors.append(f"{label}: scene_id harus pola "
                              f"'{episode_id}-SNN' (mis. {episode_id}-S01)")
        dur = adeg.get("durasi_dtk")
        if dur is not None:
            if isinstance(dur, (int, float)) and dur > 0:
                jumlah_durasi += dur
            else:
                errors.append(f"{label}: durasi_dtk harus angka > 0")
        eks = adeg.get("ekspresi")
        if eks and eks not in ekspresi_ok:
            errors.append(f"{label}: ekspresi '{eks}' tidak ada di "
                          f"Character Bible (diizinkan: "
                          f"{', '.join(sorted(ekspresi_ok))})")
        status = adeg.get("status")
        if status and status not in STATUS_OK:
            errors.append(f"{label}: status '{status}' tidak dikenal "
                          f"(diizinkan: {', '.join(sorted(STATUS_OK))})")
        kar = adeg.get("karakter")
        if isinstance(kar, list) and isinstance(karakter_ep, list):
            for k in kar:
                if k not in karakter_ep:
                    errors.append(f"{label}: karakter '{k}' tidak ada di "
                                  "karakter episode")
        elif kar is not None and not isinstance(kar, list):
            errors.append(f"{label}: karakter harus berupa list")
        ref = adeg.get("referensi_gambar")
        if ref and not _ada(path_root, ref):
            errors.append(f"{label}: referensi_gambar tidak ditemukan: {ref}")
        for teks in ("deskripsi_visual", "aksi", "gerakan_kamera", "lirik",
                     "audio", "prompt_gambar"):
            nilai = adeg.get(teks)
            if nilai is not None and (not isinstance(nilai, str)
                                      or not nilai.strip()):
                errors.append(f"{label}: '{teks}' harus teks tak kosong")

    # --- jumlah durasi adegan vs total episode
    if isinstance(total, (int, float)) and jumlah_durasi > 0:
        if abs(jumlah_durasi - total) > 0.01:
            errors.append(f"jumlah durasi adegan ({jumlah_durasi} dtk) "
                          f"!= durasi_total_dtk ({total} dtk)")

    # --- warning: adegan tanpa lirik yang cocok dengan file lirik
    # (ringan: hanya bila file lirik bisa dibaca)
    if lirik and _ada(path_root, lirik):
        try:
            with open(os.path.join(path_root, lirik)) as f:
                isi_lirik = f.read()
            for adeg in adegan:
                if isinstance(adeg, dict) and adeg.get("lirik"):
                    if adeg["lirik"].strip() not in isi_lirik:
                        warnings.append(
                            f"{adeg.get('scene_id', '?')}: lirik adegan "
                            "tidak ditemukan di file lirik")
        except OSError:
            pass

    return (not errors), errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Storyboard Validator")
    ap.add_argument("perintah", choices=["validate"])
    ap.add_argument("file", help="file storyboard JSON")
    ap.add_argument("--bible", default=None,
                    help="character_bible.json untuk daftar ekspresi")
    ap.add_argument("--root", default=FACTORY,
                    help="direktori factory (untuk memeriksa file referensi)")
    args = ap.parse_args(argv)

    try:
        with open(args.file) as f:
            data = json.load(f)
    except OSError as e:
        print(json.dumps({"valid": False, "errors": [f"tidak bisa dibaca: {e}"],
                          "warnings": []}, indent=2))
        return 1
    except ValueError as e:
        print(json.dumps({"valid": False, "errors": [f"JSON tidak valid: {e}"],
                          "warnings": []}, indent=2))
        return 1

    bible = args.bible
    if not bible and isinstance(data, dict) and data.get("character_bible"):
        bible = os.path.join(args.root, data["character_bible"])

    valid, errors, warnings = validasi(data, args.root, bible)
    print(json.dumps({"file": args.file, "valid": valid,
                      "errors": errors, "warnings": warnings}, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
