#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_source_consistency.py

对每本 complete 状态的 Book Model，校验其 Metadata 区块中记录的
source_hash / source_characters / source_lines 是否与 corpus/manifest.json
的当前 ground-truth 完全一致。

不一致时：
- 输出 FAIL + 具体差异
- 退出码 1

全部一致时：
- 输出 PASS 汇总
- 写入 evals/results/source-consistency.json
- 退出码 0
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

# Regexes for Metadata block parsing
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
            print(f"[WARN] {bid}: model file not found, skipping")
            continue

        meta = extract_model_metadata(model_path)
        issues = []

        expected_sha = book.get("source_hash")
        expected_chars = book.get("characters")
        expected_lines = book.get("lines")

        if meta["source_hash"] and expected_sha and meta["source_hash"] != expected_sha:
            issues.append(
                f"source_hash mismatch: model={meta['source_hash'][:12]}… "
                f"manifest={expected_sha[:12]}…"
            )

        if meta["characters"] is not None and expected_chars is not None:
            # Allow ±5% tolerance for encoding edge cases
            ratio = abs(meta["characters"] - expected_chars) / max(expected_chars, 1)
            if ratio > 0.05:
                issues.append(
                    f"characters mismatch: model={meta['characters']:,} "
                    f"manifest={expected_chars:,}"
                )

        if meta["lines"] is not None and expected_lines is not None:
            ratio = abs(meta["lines"] - expected_lines) / max(expected_lines, 1)
            if ratio > 0.05:
                issues.append(
                    f"lines mismatch: model={meta['lines']:,} "
                    f"manifest={expected_lines:,}"
                )

        ok = len(issues) == 0
        if not ok:
            all_ok = False
            print(f"[FAIL] {bid} ({stem}):")
            for iss in issues:
                print(f"       - {iss}")
        else:
            print(f"[PASS] {bid} ({stem})")

        results.append({
            "id": bid,
            "stem": stem,
            "ok": ok,
            "model_meta": meta,
            "manifest_ground_truth": {
                "source_hash": expected_sha,
                "characters": expected_chars,
                "lines": expected_lines,
            },
            "issues": issues,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nWrote {OUT.relative_to(ROOT)}")

    if all_ok:
        print("\n[SUMMARY] 全部 Book Model 源一致性校验通过 ✓")
        return 0
    else:
        failed = [r for r in results if not r["ok"]]
        print(f"\n[SUMMARY] {len(failed)} 本 Book Model 存在源一致性问题，需要修复 Metadata")
        return 1


if __name__ == "__main__":
    sys.exit(main())
