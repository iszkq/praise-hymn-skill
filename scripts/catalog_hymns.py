#!/usr/bin/env python3
"""Create a stable, auditable manifest for hymn-sheet image files.

Uses only the Python standard library so it can run in a clean workspace.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

SUPPORTED = {".png", ".jpg", ".jpeg"}
PREFIX = re.compile(r"^\s*(\d+)\s*(.*)$")


def digest(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def title_parts(path: Path) -> tuple[str | None, str]:
    match = PREFIX.match(path.stem)
    if not match:
        return None, path.stem.strip()
    return match.group(1), match.group(2).strip() or path.stem.strip()


def collect(root: Path) -> list[dict]:
    records = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        number, title = title_parts(path)
        records.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "extension": path.suffix.lower().lstrip("."),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
                "catalog_number": number,
                "title_from_filename": title,
                "issues": [] if number else ["missing_numeric_prefix"],
            }
        )
    records.sort(key=lambda r: (int(r["catalog_number"]) if r["catalog_number"] else 10**12, r["relative_path"]))
    by_number: dict[str, list[str]] = {}
    for row in records:
        if row["catalog_number"]:
            by_number.setdefault(row["catalog_number"], []).append(row["relative_path"])
    for row in records:
        if row["catalog_number"] and len(by_number[row["catalog_number"]]) > 1:
            row["issues"].append("duplicate_catalog_number")
    by_hash: dict[str, list[str]] = {}
    for row in records:
        by_hash.setdefault(row["sha256"], []).append(row["relative_path"])
    for row in records:
        if len(by_hash[row["sha256"]]) > 1:
            row["issues"].append("duplicate_content_hash")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Corpus directory")
    parser.add_argument("-o", "--output", type=Path, help="Output .json or .csv; stdout if omitted")
    parser.add_argument("--csv", action="store_true", help="Write CSV instead of JSON")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    records = collect(root)
    if args.csv:
        fields = ["relative_path", "extension", "bytes", "sha256", "catalog_number", "title_from_filename", "issues"]
        stream = args.output.open("w", encoding="utf-8", newline="") if args.output else sys.stdout
        try:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for row in records:
                row = dict(row)
                row["issues"] = ";".join(row["issues"])
                writer.writerow(row)
        finally:
            if args.output:
                stream.close()
    else:
        payload = {
            "manifest_version": "1.0",
            "root": str(root),
            "file_count": len(records),
            "records": records,
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
