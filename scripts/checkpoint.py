#!/usr/bin/env python3
"""Sistem checkpoint & resume — AI Kids YouTube Factory.

Setiap episode punya satu file checkpoint:
  <factory_root>/checkpoints/<production_id>.json

Isinya: daftar tahapan produksi, masing-masing dengan status
(pending / berjalan / selesai / gagal) + waktu + detail.
Kalau VM restart atau proses terhenti, jalankan `lanjut` untuk
melihat tahap mana yang harus dikerjakan berikutnya — tahap yang
sudah `selesai` TIDAK diulang.

Tahapan standar (lihat PRODUCTION_WORKFLOW.md):
  1 lirik, 2 musik, 3 gambar, 4 video, 5 rakit, 6 lirik_layar, 7 qc, 8 upload

Pemakaian CLI:
  python3 checkpoint.py init --id EP001
  python3 checkpoint.py selesai --id EP001 --tahap lirik --detail "lirik disetujui"
  python3 checkpoint.py gagal --id EP001 --tahap musik --detail "API timeout"
  python3 checkpoint.py lanjut --id EP001
  python3 checkpoint.py status --id EP001
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_DIR = os.path.expanduser("~/workspace/youtube-kids/checkpoints")

TAHAPAN = ["lirik", "musik", "gambar", "video", "rakit", "lirik_layar", "qc", "upload"]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(checkpoint_dir, production_id):
    return os.path.join(checkpoint_dir, f"{production_id}.json")


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def init(checkpoint_dir, production_id, tahapan=None):
    path = _path(checkpoint_dir, production_id)
    if os.path.exists(path):
        raise ValueError(f"checkpoint {production_id} sudah ada (pakai status/lanjut)")
    data = {
        "production_id": production_id,
        "dibuat": _now(),
        "diperbarui": _now(),
        "tahapan": [
            {
                "nama": nama,
                "status": "pending",
                "waktu_mulai": None,
                "waktu_selesai": None,
                "detail": "",
            }
            for nama in (tahapan or TAHAPAN)
        ],
    }
    os.makedirs(checkpoint_dir, exist_ok=True)
    _save(path, data)
    return data


def _set_status(checkpoint_dir, production_id, tahap, status, detail=""):
    path = _path(checkpoint_dir, production_id)
    data = _load(path)
    for t in data["tahapan"]:
        if t["nama"] == tahap:
            if status == "berjalan" and not t.get("waktu_mulai"):
                t["waktu_mulai"] = _now()
            if status in ("selesai", "gagal"):
                t["waktu_selesai"] = _now()
            t["status"] = status
            if detail:
                t["detail"] = detail
            data["diperbarui"] = _now()
            _save(path, data)
            return data
    raise ValueError(f"tahap tidak dikenal: {tahap} (tahapan: {TAHAPAN})")


def tahap_berikutnya(checkpoint_dir, production_id):
    """Tahap pertama yang belum selesai — inilah yang dikerjakan saat resume."""
    data = _load(_path(checkpoint_dir, production_id))
    for t in data["tahapan"]:
        if t["status"] in ("pending", "gagal"):
            return t
        if t["status"] == "berjalan":
            return t  # terhenti di tengah tahap ini -> ulangi tahap ini saja
    return None  # semua selesai


def main(argv=None):
    ap = argparse.ArgumentParser(description="Checkpoint & resume AI Kids YouTube Factory")
    ap.add_argument("--dir", default=DEFAULT_DIR, help="Folder checkpoint")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--id", required=True)

    for cmd in ("selesai", "gagal", "berjalan"):
        p = sub.add_parser(cmd)
        p.add_argument("--id", required=True)
        p.add_argument("--tahap", required=True, choices=TAHAPAN)
        p.add_argument("--detail", default="")

    p = sub.add_parser("lanjut")
    p.add_argument("--id", required=True)

    p = sub.add_parser("status")
    p.add_argument("--id", required=True)

    args = ap.parse_args(argv)
    try:
        if args.cmd == "init":
            data = init(args.dir, args.id)
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif args.cmd in ("selesai", "gagal", "berjalan"):
            data = _set_status(args.dir, args.id, args.tahap, args.cmd, args.detail)
            print(json.dumps(data, ensure_ascii=False, indent=2))
        elif args.cmd == "lanjut":
            t = tahap_berikutnya(args.dir, args.id)
            if t is None:
                print(f"{args.id}: SEMUA TAHAP SELESAI")
            else:
                print(
                    f"{args.id}: lanjutkan dari tahap '{t['nama']}' "
                    f"(status: {t['status']})"
                )
        elif args.cmd == "status":
            print(json.dumps(_load(_path(args.dir, args.id)), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
