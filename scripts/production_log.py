#!/usr/bin/env python3
"""Sistem pencatatan produksi — AI Kids YouTube Factory.

Mencatat setiap episode produksi dengan field:
  production_id, judul, status, lokasi_file,
  waktu_mulai, waktu_selesai, status_rendering, status_qc.

Penyimpanan: JSON di <factory_root>/logs/production_log.json
(daftar episode). Penulisan atomik (tulis file temp + ganti nama)
supaya log tidak rusak kalau VM restart di tengah tulis.

Pemakaian CLI:
  python3 production_log.py create --id EP001 --judul "Truk Tahu Bulat"
  python3 production_log.py update --id EP001 --status rendering --rendering berjalan
  python3 production_log.py get --id EP001
  python3 production_log.py list
  python3 production_log.py selesai --id EP001 --qc lolos
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_LOG = os.path.expanduser(
    "~/workspace/youtube-kids/logs/production_log.json"
)

STATUS_VALID = ["baru", "berjalan", "rendering", "qc", "selesai", "gagal", "ditunda"]
RENDER_VALID = ["belum", "berjalan", "selesai", "gagal"]
QC_VALID = ["belum", "berjalan", "lolos", "gagal"]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Isi {path} bukan daftar episode")
    return data


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def create(path, production_id, judul):
    data = _load(path)
    if any(e["production_id"] == production_id for e in data):
        raise ValueError(f"production_id {production_id} sudah ada")
    entry = {
        "production_id": production_id,
        "judul": judul,
        "status": "baru",
        "lokasi_file": {},
        "waktu_mulai": _now(),
        "waktu_selesai": None,
        "status_rendering": "belum",
        "status_qc": "belum",
    }
    data.append(entry)
    _save(path, data)
    return entry


def update(path, production_id, **fields):
    data = _load(path)
    for entry in data:
        if entry["production_id"] == production_id:
            for key, value in fields.items():
                if value is None:
                    continue
                if key == "status" and value not in STATUS_VALID:
                    raise ValueError(f"status tidak dikenal: {value}")
                if key == "status_rendering" and value not in RENDER_VALID:
                    raise ValueError(f"status_rendering tidak dikenal: {value}")
                if key == "status_qc" and value not in QC_VALID:
                    raise ValueError(f"status_qc tidak dikenal: {value}")
                entry[key] = value
            if fields.get("status") == "selesai" and not entry.get("waktu_selesai"):
                entry["waktu_selesai"] = _now()
            _save(path, data)
            return entry
    raise ValueError(f"production_id {production_id} tidak ditemukan")


def get(path, production_id):
    for entry in _load(path):
        if entry["production_id"] == production_id:
            return entry
    raise ValueError(f"production_id {production_id} tidak ditemukan")


def list_all(path):
    return _load(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Log produksi AI Kids YouTube Factory")
    ap.add_argument("--log", default=DEFAULT_LOG, help="Lokasi file log JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create")
    p.add_argument("--id", required=True)
    p.add_argument("--judul", required=True)

    p = sub.add_parser("update")
    p.add_argument("--id", required=True)
    p.add_argument("--status", choices=STATUS_VALID)
    p.add_argument("--rendering", dest="status_rendering", choices=RENDER_VALID)
    p.add_argument("--qc", dest="status_qc", choices=QC_VALID)
    p.add_argument("--judul")

    p = sub.add_parser("selesai")
    p.add_argument("--id", required=True)
    p.add_argument("--qc", choices=QC_VALID, default="lolos")

    p = sub.add_parser("get")
    p.add_argument("--id", required=True)

    sub.add_parser("list")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "create":
            entry = create(args.log, args.id, args.judul)
        elif args.cmd == "update":
            entry = update(
                args.log, args.id,
                status=args.status,
                status_rendering=args.status_rendering,
                status_qc=args.status_qc,
                judul=args.judul,
            )
        elif args.cmd == "selesai":
            entry = update(
                args.log, args.id,
                status="selesai",
                status_rendering="selesai",
                status_qc=args.qc,
            )
        elif args.cmd == "get":
            entry = get(args.log, args.id)
        elif args.cmd == "list":
            print(json.dumps(list_all(args.log), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
