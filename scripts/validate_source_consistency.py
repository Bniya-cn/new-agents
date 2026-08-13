#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_source_consistency.py

Exact-match consistency check between Book Model Metadata and corpus/manifest.json.

Checks (NO tolerance):
- source_hash (SHA-256)
- characters
- lines

Writes full audit JSON to evals/results/source-consistency.json
including model_meta and manifest_ground_truth for every complete book.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.json"
MODELS_DIR = ROOT / "generated" / "book-models"
OUT = ROOT / "evals" / "results" / "source-consistency.json"

RE_SHA = re.compile(r"Source SHA-256:\s*([0-9a-f]{64})", re.I)
RE_CHARS = re.compile(r"Source characters:\s*([\d,]+)", re.I)
RE_LINES = re.compile(r"Source lines:\s*([\d,]+)", re.I)


def parse_int(s: str) -> int:
    return int(s.replace(",", "").strip())


def extract_model_metadata(model_path: Path) -> dict:
    text = model_path.read_text(encoding="utf-8", errors="replace")
    sha_m = RE_SHA.search(text)
    chars_m = RE_CHARS.search(text)
    lines_m = RE_LINES.search(text)
    return {
        "source_hash": sha_m.group(1) if sha_m else None,
        "characters": parse_int(chars_m.group(1)) if chars_m else None,
        "lines": parse_int(lines_m.group(1)) if lines_m else None,
    }


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = []
    all_ok = True

    for book in manifest["books"]:
        if book["status"] != "complete":
            continue

        bid = book["id"]
        stem = Path(book["source_file"]).stem
        model_path = MODELS_DIR / f"{stem}.md"

        if not model_path.exists():
            print(f"[FAIL] {bid}: model file missing")
            all_ok = False
            results.append(
                {
                    "id": bid,
                    "stem": stem,
                    "ok": False,
                    "model_meta": None,
                    "manifest_ground_truth": {
                        "source_hash": book.get("source_hash"),
                        "characters": book.get("characters"),
                        "lines": book.get("lines"),
                    },
                    "issues": ["model file not found"],
                }
            )
            continue

        meta = extract_model_metadata(model_path)
        expected_sha = book.get("source_hash")
        expected_chars = book.get("characters")
        expected_lines = book.get("lines")
        issues: list[str] = []

        if not meta["source_hash"]:
            issues.append("model Metadata missing Source SHA-256")
        elif meta["source_hash"] != expected_sha:
            issues.append(
                f"source_hash mismatch: model={meta['source_hash']} "
                f"manifest={expected_sha}"
            )

        if meta["characters"] is None:
            issues.append("model Metadata missing Source characters")
        elif meta["characters"] != expected_chars:
            issues.append(
                f"characters mismatch (exact): model={meta['characters']} "
                f"manifest={expected_chars}"
            )

        if meta["lines"] is None:
            issues.append("model Metadata missing Source lines")
        elif meta["lines"] != expected_lines:
            issues.append(
                f"lines mismatch (exact): model={meta['lines']} "
                f"manifest={expected_lines}"
            )

        ok = len(issues) == 0
        if not ok:
            all_ok = False
            print(f"[FAIL] {bid} ({stem}):")
            for iss in issues:
                print(f"       - {iss}")
        else:
            print(f"[PASS] {bid} ({stem})")

        results.append(
            {
                "id": bid,
                "stem": stem,
                "ok": ok,
                "model_meta": meta,
                "manifest_ground_truth": {
                    "source_hash": expected_sha,
                    "characters": expected_chars,
                    "lines": expected_lines,
                },
                "match_policy": "exact",
                "issues": issues,
            }
        )

    payload = {
        "generated_by": "scripts/validate_source_consistency.py",
        "match_policy": "exact_hash_chars_lines",
        "tolerance": 0,
        "complete_books_checked": len(results),
        "all_ok": all_ok,
        "items": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(ROOT)}")

    if all_ok:
        print("\n[SUMMARY] exact source consistency PASS for all complete book models")
        return 0

    failed = [r for r in results if not r["ok"]]
    print(f"\n[SUMMARY] {len(failed)} book model(s) failed exact consistency")
    return 1


if __name__ == "__main__":
    sys.exit(main())
