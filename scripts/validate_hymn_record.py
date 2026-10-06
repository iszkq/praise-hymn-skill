#!/usr/bin/env python3
"""Validate the stable fields and approval gates of a hymn JSON record."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REQUIRED = {
    "schema_version", "record_id", "status", "processing", "source", "metadata", "transcription",
    "sections", "analysis", "quality", "uncertain_items", "rights", "review", "change_log",
}
STATUSES = {"draft", "review", "approved", "rejected", "needs-input"}
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(payload: object, strict: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["record must be a JSON object"]
    missing = sorted(REQUIRED - payload.keys())
    errors.extend(f"missing required field: {key}" for key in missing)
    if payload.get("schema_version") != "1.2":
        errors.append("schema_version must be '1.2'")
    if payload.get("status") not in STATUSES:
        errors.append(f"status must be one of: {', '.join(sorted(STATUSES))}")
    processing = payload.get("processing")
    if not isinstance(processing, dict):
        errors.append("processing must be an object")
    else:
        for key in ("skill_version", "mode", "processed_at"):
            if not processing.get(key):
                errors.append(f"processing.{key} must be non-empty")
        if processing.get("mode") not in {"transcribe", "analyze", "arrange", "create", "curate", "batch"}:
            errors.append("processing.mode is invalid")
    source = payload.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        if not source.get("path"):
            errors.append("source.path must be non-empty")
        if not isinstance(source.get("sha256"), str) or not SHA256.fullmatch(source["sha256"]):
            errors.append("source.sha256 must be a 64-character hexadecimal SHA-256")
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("language"), str) or not metadata["language"]:
        errors.append("metadata.language must be non-empty")
    transcription = payload.get("transcription")
    if not isinstance(transcription, dict):
        errors.append("transcription must be an object")
    else:
        for key in ("raw", "normalized"):
            if not isinstance(transcription.get(key), str):
                errors.append(f"transcription.{key} must be a string")
    sections = payload.get("sections")
    if not isinstance(sections, list):
        errors.append("sections must be an array")
    else:
        for idx, section in enumerate(sections):
            if not isinstance(section, dict):
                errors.append(f"sections[{idx}] must be an object")
                continue
            for key in ("label", "melody", "lyrics"):
                if key not in section:
                    errors.append(f"sections[{idx}] missing {key}")
            if not isinstance(section.get("melody"), list) or not isinstance(section.get("lyrics"), list):
                errors.append(f"sections[{idx}].melody and lyrics must be arrays")
    for key in ("uncertain_items", "change_log"):
        if not isinstance(payload.get(key), list):
            errors.append(f"{key} must be an array")
    quality = payload.get("quality")
    if not isinstance(quality, dict):
        errors.append("quality must be an object")
    else:
        if quality.get("confidence") not in {"high", "medium", "low"}:
            errors.append("quality.confidence must be high, medium, or low")
        if not isinstance(quality.get("issues"), list):
            errors.append("quality.issues must be an array")
        if "field_confidence" in quality:
            fields = quality["field_confidence"]
            if not isinstance(fields, dict) or any(value not in {"high", "medium", "low"} for value in fields.values()):
                errors.append("quality.field_confidence values must be high, medium, or low")
    if not isinstance(payload.get("analysis"), dict):
        errors.append("analysis must be an object")
    rights = payload.get("rights")
    if not isinstance(rights, dict):
        errors.append("rights must be an object")
    else:
        for key in ("source_provided_by_user", "reuse_permission", "publication_allowed"):
            if key not in rights:
                errors.append(f"rights missing {key}")
    review = payload.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        if not isinstance(review.get("reviewers"), list):
            errors.append("review.reviewers must be an array")
        if review.get("decision") not in {"pending", "approved", "rejected", "needs-input"}:
            errors.append("review.decision is invalid")
    if payload.get("status") == "approved":
        if not sections:
            errors.append("approved record must contain at least one section")
        if payload.get("uncertain_items"):
            errors.append("approved record cannot contain unresolved uncertain_items")
        if not isinstance(quality, dict) or quality.get("confidence") == "low":
            errors.append("approved record cannot have low quality confidence")
        if not isinstance(review, dict) or review.get("decision") != "approved":
            errors.append("approved record needs review.decision=approved")
        if not isinstance(review, dict) or not review.get("reviewers"):
            errors.append("approved record needs at least one reviewer")
        if not isinstance(review, dict) or not review.get("last_reviewed_at"):
            errors.append("approved record needs review.last_reviewed_at")
        if isinstance(quality, dict) and any(isinstance(issue, dict) and issue.get("status") == "open" for issue in quality.get("issues", [])):
            errors.append("approved record cannot contain open quality issues")
    if strict and payload.get("status") in {"review", "approved"} and not payload.get("change_log"):
        errors.append("review/approved record needs at least one change_log entry")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--strict", action="store_true", help="Enforce review audit requirements")
    parser.add_argument("--source-root", type=Path, help="Verify source.sha256 against a corpus root")
    args = parser.parse_args()
    try:
        payload = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR {args.record}: {exc}", file=sys.stderr)
        return 2
    errors = validate(payload, strict=args.strict)
    if args.source_root and isinstance(payload, dict) and isinstance(payload.get("source"), dict):
        source_path = payload["source"].get("path")
        if isinstance(source_path, str):
            root = args.source_root.resolve()
            candidate = (root / source_path).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                errors.append("source.path escapes --source-root")
            else:
                if not candidate.is_file():
                    errors.append(f"source file not found under --source-root: {source_path}")
                elif file_sha256(candidate).lower() != str(payload["source"].get("sha256", "")).lower():
                    errors.append("source.sha256 does not match the source file")
    if errors:
        for error in errors:
            print(f"ERROR {args.record}: {error}")
        return 1
    print(f"OK {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
