#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build hierarchical segment cognitive artifacts from whole-book models.

For each hierarchical book with .work/<id>/segments.json:
1. Parse evidence line ranges from the book model
2. Assign concepts/claims/principles to segments by line overlap
3. Write Sxxx.cog.md (segment cognitive notes) + synthesis_manifest.json

This does NOT invent unread content. It reconstructs an auditable map from
the already-accepted whole-book model back onto segments.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "generated" / "book-models" / ".work"
MODELS = ROOT / "generated" / "book-models"

ITEM_RE = re.compile(
    r"^###\s+((?:C|CL|CM|H|P|RP|T|AP|A|V|B|I)\d{3})\s+(.+)$", re.M
)
# Capture: lines 124-126 | lines 97, 105, 123 | Evidence: lines 1548, 1649
LINE_CLUSTER_RE = re.compile(
    r"lines?\s*[:=]?\s*([\d,\s\-–—]+)",
    re.I,
)
BLOCK_REF_RE = re.compile(r"\[(\d{3}):L(\d+)(?:-(\d+))?\]")
NUM_RANGE_RE = re.compile(r"(\d+)(?:\s*[-–—]\s*(\d+))?")


def parse_line_ranges(body: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for cluster in LINE_CLUSTER_RE.findall(body):
        for m in NUM_RANGE_RE.finditer(cluster):
            a = int(m.group(1))
            b = int(m.group(2) or m.group(1))
            ranges.append((a, b))
    for bm in BLOCK_REF_RE.finditer(body):
        a = int(bm.group(2))
        b = int(bm.group(3) or bm.group(2))
        ranges.append((a, b))
    # dedupe
    return list(dict.fromkeys(ranges))[:40]


def parse_model_items(text: str) -> list[dict]:
    items = []
    matches = list(ITEM_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end]
        items.append(
            {
                "id": m.group(1),
                "title": m.group(2).strip()[:120],
                "line_ranges": parse_line_ranges(body),
            }
        )
    return items


def overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] < b[0] or b[1] < a[0])


def build_for_book(book_id: str) -> dict:
    work = WORK / book_id
    seg_path = work / "segments.json"
    if not seg_path.exists():
        raise FileNotFoundError(f"missing {seg_path}")

    model_candidates = list(MODELS.glob(f"{book_id}-*.md"))
    if not model_candidates:
        raise FileNotFoundError(f"no book model for {book_id}")
    model_path = model_candidates[0]
    model_text = model_path.read_text(encoding="utf-8", errors="replace")
    items = parse_model_items(model_text)
    segments = list(json.loads(seg_path.read_text(encoding="utf-8"))["segments"])

    # Ensure preamble/uncovered line spans exist as explicit segments for auditability.
    if segments:
        first_start = min(s["start_line"] for s in segments)
        last_end = max(s["end_line"] for s in segments)
        if first_start > 1:
            segments.insert(
                0,
                {
                    "id": "S000",
                    "label": "preamble-before-first-break",
                    "start_line": 1,
                    "end_line": first_start - 1,
                    "characters": None,
                    "weight": 1.0,
                    "duplicate_of": None,
                    "synthetic": True,
                },
            )
        # trailing gap unlikely but keep schema ready
        _ = last_end

    assignment: dict[str, list[dict]] = defaultdict(list)
    unassigned = []

    for item in items:
        placed = False
        for seg in segments:
            if seg.get("weight", 1) == 0:
                continue
            span = (seg["start_line"], seg["end_line"])
            hit_ranges = [r for r in item["line_ranges"] if overlaps(r, span)]
            if hit_ranges:
                assignment[seg["id"]].append(
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "overlapping_ranges": hit_ranges,
                    }
                )
                placed = True
        if not placed and item["line_ranges"]:
            unassigned.append(item)
        elif not item["line_ranges"]:
            # structural items without line evidence stay at whole-book level
            unassigned.append({**item, "reason": "no_line_evidence_in_model_block"})

    # write per-segment cognition notes
    for seg in segments:
        sid = seg["id"]
        mapped = assignment.get(sid, [])
        lines = [
            f"# Segment Cognitive Note — {book_id}/{sid}",
            "",
            f"- Label: {seg.get('label')}",
            f"- Lines: {seg['start_line']}-{seg['end_line']}",
            f"- Characters: {seg.get('characters')}",
            f"- Weight: {seg.get('weight', 1)}",
            f"- Duplicate of: {seg.get('duplicate_of')}",
            f"- Source model: {model_path.relative_to(ROOT)}",
            "",
            "## Mapped whole-book items (by evidence overlap)",
            "",
        ]
        if not mapped:
            lines.append("- (none with overlapping evidence ranges)")
        else:
            for it in mapped:
                ranges = ", ".join(f"{a}-{b}" for a, b in it["overlapping_ranges"])
                lines.append(f"- `{it['id']}` {it['title']} — overlap lines: {ranges}")
        lines.extend(
            [
                "",
                "## Note",
                "",
                "This artifact is a **cross-segment consolidation map** derived from the",
                "accepted whole-book cognitive model. It is not a fresh independent",
                "reading of unread pages. Unmapped regions remain covered only at",
                "whole-book synthesis level.",
                "",
            ]
        )
        (work / f"{sid}.cog.md").write_text("\n".join(lines), encoding="utf-8")

    manifest = {
        "book_id": book_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/build_segment_cognition.py",
        "source_model": str(model_path.relative_to(ROOT)),
        "segment_count": len(segments),
        "mapped_item_count": sum(len(v) for v in assignment.values()),
        "unique_items_parsed": len(items),
        "unassigned_or_wholebook_only": unassigned,
        "pipeline": [
            "structure.json / segments.json (deterministic segmentation)",
            "whole-book cognitive model (accepted)",
            "evidence-line → segment overlap mapping",
            "Sxxx.cog.md segment cognitive notes",
            "synthesis_manifest.json (this file)",
        ],
        "limitations": [
            "Does not claim each segment was independently re-read end-to-end in this rebuild.",
            "Provides auditable consolidation evidence linking whole-book IDs to segments.",
        ],
        "segments": [
            {
                "id": s["id"],
                "label": s.get("label"),
                "start_line": s["start_line"],
                "end_line": s["end_line"],
                "mapped_ids": [x["id"] for x in assignment.get(s["id"], [])],
                "cog_artifact": f"generated/book-models/.work/{book_id}/{s['id']}.cog.md",
            }
            for s in segments
        ],
    }
    out = work / "synthesis_manifest.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "book_ids",
        nargs="*",
        default=["001", "003", "005", "011", "013", "015", "016", "017"],
        help="hierarchical book ids to process",
    )
    args = ap.parse_args()
    for bid in args.book_ids:
        work = WORK / bid
        if not (work / "segments.json").exists():
            print(f"[SKIP] {bid}: no segments.json")
            continue
        m = build_for_book(bid)
        print(
            f"[OK] {bid}: segments={m['segment_count']} "
            f"mapped_links={m['mapped_item_count']} -> .work/{bid}/synthesis_manifest.json"
        )


if __name__ == "__main__":
    main()
