#!/usr/bin/env python3
"""Deterministic semantic/structural segmentation for hierarchical distillation.

Writes generated/book-models/.work/<id>/structure.json and segments.json.
Does not modify corpus/raw/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
WORK = ROOT / "generated" / "book-models" / ".work"

CHAPTER_PATTERNS = [
    re.compile(r"^#{1,3}\s+(.+)$"),
    re.compile(r"^第[一二三四五六七八九十百千零〇\d]+[章节卷篇部回]\s*.*$"),
    re.compile(r"^卷[第]?[一二三四五六七八九十百千零〇\d]+\s*.*$"),
    re.compile(r"^Chapter\s+\d+.*$", re.I),
    re.compile(r"^第\d+章\s*.*$"),
    re.compile(r"^.+[卷部篇]第[一二三四五六七八九十]+$"),
]

PAGE_MARK = re.compile(r"^(第一部分|第二部分|第\d+部分).*\(\d+\)$")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def find_breaks(lines: list[str]) -> list[tuple[int, str]]:
    breaks: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        s = line.strip()
        if not s:
            continue
        for pat in CHAPTER_PATTERNS:
            if pat.match(s):
                breaks.append((i, s[:120]))
                break
        else:
            if PAGE_MARK.match(s):
                breaks.append((i, s[:120]))
    return breaks


def chunk_by_size(lines: list[str], max_chars: int) -> list[tuple[int, int, str]]:
    """Fallback length-based segments. Returns (start_line, end_line, label)."""
    segs = []
    start = 1
    buf = 0
    for i, line in enumerate(lines, start=1):
        buf += len(line) + 1
        if buf >= max_chars:
            segs.append((start, i, f"length-chunk@{start}-{i}"))
            start = i + 1
            buf = 0
    if start <= len(lines):
        segs.append((start, len(lines), f"length-chunk@{start}-{len(lines)}"))
    return segs


def build_segments(lines: list[str], max_chars: int = 80_000) -> list[dict]:
    breaks = find_breaks(lines)
    segments: list[dict] = []

    if len(breaks) >= 3:
        # Merge tiny neighboring breaks into segments of reasonable size
        points = [b[0] for b in breaks] + [len(lines) + 1]
        labels = {b[0]: b[1] for b in breaks}
        cur_start = points[0]
        cur_label = labels.get(cur_start, f"seg@{cur_start}")
        for nxt in points[1:]:
            end = nxt - 1
            text_len = sum(len(lines[i - 1]) + 1 for i in range(cur_start, end + 1) if 1 <= i <= len(lines))
            # If still small, keep accumulating unless end of book
            if text_len < max_chars and nxt != points[-1]:
                continue
            sid = f"S{len(segments) + 1:03d}"
            body = "\n".join(lines[cur_start - 1 : end])
            segments.append(
                {
                    "id": sid,
                    "label": cur_label,
                    "start_line": cur_start,
                    "end_line": end,
                    "characters": len(body),
                    "content_hash": sha256_text(body)[:16],
                }
            )
            if nxt <= len(lines):
                cur_start = nxt
                cur_label = labels.get(nxt, f"seg@{nxt}")
    else:
        for start, end, label in chunk_by_size(lines, max_chars):
            sid = f"S{len(segments) + 1:03d}"
            body = "\n".join(lines[start - 1 : end])
            segments.append(
                {
                    "id": sid,
                    "label": label,
                    "start_line": start,
                    "end_line": end,
                    "characters": len(body),
                    "content_hash": sha256_text(body)[:16],
                }
            )

    # Deduplicate identical content hashes (OCR repeats)
    seen: dict[str, str] = {}
    for seg in segments:
        h = seg["content_hash"]
        if h in seen:
            seg["duplicate_of"] = seen[h]
            seg["weight"] = 0.0
        else:
            seen[h] = seg["id"]
            seg["duplicate_of"] = None
            seg["weight"] = 1.0
    return segments


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("book", help="filename or id, e.g. 007-做局.md or 007")
    ap.add_argument("--max-chars", type=int, default=80_000)
    args = ap.parse_args()

    target = args.book
    if re.fullmatch(r"\d{3}", target):
        matches = list(RAW.glob(f"{target}-*.md"))
        if not matches:
            raise SystemExit(f"No raw file for id {target}")
        path = matches[0]
    else:
        path = RAW / target if not Path(target).is_absolute() else Path(target)
        if not path.exists():
            path = RAW / Path(target).name

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    bid = path.stem[:3]
    work = WORK / bid
    work.mkdir(parents=True, exist_ok=True)

    breaks = find_breaks(lines)
    segments = build_segments(lines, max_chars=args.max_chars)

    structure = {
        "book_id": bid,
        "source": str(path.relative_to(ROOT)),
        "characters": len(text),
        "lines": len(lines),
        "break_count": len(breaks),
        "sample_breaks": breaks[:40],
        "segment_count": len(segments),
        "mode_hint": "hierarchical" if len(text) >= 200_000 or len(breaks) < 3 else "direct",
    }
    (work / "structure.json").write_text(json.dumps(structure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (work / "segments.json").write_text(json.dumps({"book_id": bid, "segments": segments}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Optional: write compact segment stubs (metadata only, not full text dump for huge books)
    for seg in segments:
        stub = {
            "id": seg["id"],
            "label": seg["label"],
            "start_line": seg["start_line"],
            "end_line": seg["end_line"],
            "characters": seg["characters"],
            "duplicate_of": seg["duplicate_of"],
            "weight": seg["weight"],
            "source": structure["source"],
        }
        (work / f"{seg['id']}.meta.json").write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{bid}: segments={len(segments)} breaks={len(breaks)} -> {work.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
