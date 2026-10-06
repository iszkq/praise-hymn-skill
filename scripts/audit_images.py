#!/usr/bin/env python3
"""Audit hymn-sheet image headers, dimensions, and likely truncation.

The audit is intentionally conservative: it reports warnings for human review
and never claims that a file is visually legible just because its header works.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

EXTENSIONS = {".png", ".jpg", ".jpeg"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def png_end_status(path: Path) -> str:
    """Return a conservative chunk-stream status for a PNG file."""
    data = path.read_bytes()
    if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return "invalid_png_signature"
    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        end = offset + 12 + length
        if end > len(data):
            return "truncated_png_chunk"
        kind = data[offset + 4 : offset + 8]
        if kind == b"IEND":
            return "png_trailing_data" if end < len(data) else "ok"
        offset = end
    return "missing_png_iend"


def jpeg_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as fh:
        if fh.read(2) != b"\xff\xd8":
            return None
        while True:
            byte = fh.read(1)
            if not byte:
                return None
            if byte != b"\xff":
                continue
            marker = fh.read(1)
            while marker == b"\xff":
                marker = fh.read(1)
            if not marker:
                return None
            code = marker[0]
            if code in {0xD8, 0xD9}:
                continue
            length_bytes = fh.read(2)
            if len(length_bytes) != 2:
                return None
            length = struct.unpack(">H", length_bytes)[0]
            if length < 2:
                return None
            if code in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
                body = fh.read(5)
                if len(body) != 5:
                    return None
                height, width = struct.unpack(">HH", body[1:5])
                return width, height
            fh.seek(length - 2, 1)


def inspect(path: Path, root: Path, min_width: int, min_height: int) -> dict:
    ext = path.suffix.lower()
    size = path.stat().st_size
    issues: list[str] = []
    warnings: list[str] = []
    dims: tuple[int, int] | None = None
    with path.open("rb") as fh:
        head = fh.read(64)
        fh.seek(max(0, size - 16))
        tail = fh.read(16)
    if ext == ".png":
        dims = png_dimensions(head)
        if dims:
            end_status = png_end_status(path)
            if end_status == "png_trailing_data":
                warnings.append(end_status)
            elif end_status != "ok":
                issues.append(end_status)
    else:
        dims = jpeg_dimensions(path)
        if not tail.endswith(b"\xff\xd9"):
            issues.append("missing_jpeg_eoi_at_eof")
    if not dims:
        issues.append("unreadable_image_header")
    else:
        width, height = dims
        if width < min_width or height < min_height:
            issues.append("below_dimension_threshold")
    if size < 20 * 1024:
        warnings.append("very_small_file")
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "format": ext.lstrip("."),
        "bytes": size,
        "sha256": sha256(path),
        "width": dims[0] if dims else None,
        "height": dims[1] if dims else None,
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--min-width", type=int, default=1000)
    parser.add_argument("--min-height", type=int, default=1000)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    records = [inspect(p, root, args.min_width, args.min_height) for p in sorted(root.rglob("*")) if p.is_file() and p.suffix.lower() in EXTENSIONS]
    payload = {"audit_version": "1.0", "root": str(root), "file_count": len(records), "records": records}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
