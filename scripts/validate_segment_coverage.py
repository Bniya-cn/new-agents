#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed 校验 Hierarchical 的 segment-first 产物。"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.json"
WORK = ROOT / "generated" / "book-models" / ".work"
OUT = ROOT / "evals" / "results" / "segment-coverage.json"

REQUIRED_SECTIONS = [
    "Metadata",
    "核心概念",
    "主要判断",
    "因果模型",
    "判断规则",
    "隐含前提",
    "重要变量",
    "边界条件",
    "内部张力",
    "可迁移原则候选",
    "证据",
    "Coverage",
]


def validate_book(book: dict) -> dict:
    bid = book["id"]
    work = WORK / bid
    issues: list[str] = []
    segments_path = work / "segments.json"
    gates_path = work / "segment-gates.json"
    consolidation_path = work / "consolidation.json"
    synthesis_path = work / "synthesis_manifest.json"
    if not segments_path.is_file():
        issues.append("segments.json missing")
    if not gates_path.is_file():
        issues.append("segment-gates.json missing")
    if not consolidation_path.is_file():
        issues.append("consolidation.json missing")
    if not synthesis_path.is_file():
        issues.append("synthesis_manifest.json missing")
    if issues:
        return {"book_id": bid, "status": "incomplete", "coverage": 0.0, "issues": issues}

    segments = json.loads(segments_path.read_text(encoding="utf-8")).get("segments", [])
    gate_payload = json.loads(gates_path.read_text(encoding="utf-8"))
    consolidation = json.loads(consolidation_path.read_text(encoding="utf-8"))
    synthesis = json.loads(synthesis_path.read_text(encoding="utf-8"))
    required = [segment for segment in segments if not segment.get("duplicate_of")]
    gates = {gate.get("segment_id"): gate for gate in gate_payload.get("gates", [])}
    total_lines = sum(int(segment["end_line"]) - int(segment["start_line"]) + 1 for segment in required)
    covered_lines = 0
    segment_results: list[dict] = []
    for segment in required:
        sid = segment["id"]
        model_path = work / f"{sid}.model.md"
        gate_path = work / f"{sid}.gate.json"
        local_issues: list[str] = []
        if not model_path.is_file():
            local_issues.append("Sxxx.model.md missing")
        else:
            model_text = model_path.read_text(encoding="utf-8", errors="replace")
            local_issues.extend(f"missing section: {section}" for section in REQUIRED_SECTIONS if section not in model_text)
            if "whole-book model" in model_text.lower() and "dependency: none" not in model_text.lower():
                local_issues.append("segment model refers to whole-book model")
            source_match = re.search(r"^- Source:\s*(.+)$", model_text, re.M)
            range_match = re.search(r"^- Exact source lines:\s*(\d+)-(\d+)$", model_text, re.M)
            if not source_match or source_match.group(1).strip() != book.get("source_file"):
                local_issues.append("segment source does not match manifest")
            if not range_match or int(range_match.group(1)) != int(segment["start_line"]) or int(range_match.group(2)) != int(segment["end_line"]):
                local_issues.append("segment exact line range does not match segments.json")
        if not gate_path.is_file():
            local_issues.append("segment gate missing")
        else:
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            if gate.get("status") != "passed":
                local_issues.append(f"segment gate status={gate.get('status')}")
            if gate.get("whole_book_reverse_mapping") is not False:
                local_issues.append("segment gate does not explicitly reject reverse mapping")
            if gates.get(sid, {}).get("status") != "passed":
                local_issues.append("segment-gates aggregate does not pass this segment")
        if not local_issues:
            covered_lines += int(segment["end_line"]) - int(segment["start_line"]) + 1
        segment_results.append({"segment_id": sid, "status": "passed" if not local_issues else "failed", "issues": local_issues})

    coverage = covered_lines / total_lines if total_lines else 0.0
    if consolidation.get("status") != "passed":
        issues.append(f"consolidation status={consolidation.get('status')}")
    if synthesis.get("segment_first") is not True:
        issues.append("synthesis manifest is not segment-first")
    if synthesis.get("status") != "complete":
        issues.append(f"synthesis manifest status={synthesis.get('status')}")
    if synthesis.get("synthesis_eligible") is not True:
        issues.append("synthesis manifest is not eligible")
    if coverage < 0.98:
        issues.append(f"coverage={coverage:.6f} below 0.98")
    if any(item["status"] != "passed" for item in segment_results):
        issues.append("one or more required segment gates failed")
    status = "complete" if not issues else "incomplete"
    return {
        "book_id": bid,
        "status": status,
        "coverage": round(coverage, 6),
        "required_segment_count": len(required),
        "passed_segment_count": sum(item["status"] == "passed" for item in segment_results),
        "segments": segment_results,
        "issues": issues,
        "artifacts": {
            "segments": str(segments_path.relative_to(ROOT)),
            "gates": str(gates_path.relative_to(ROOT)),
            "consolidation": str(consolidation_path.relative_to(ROOT)),
            "synthesis_manifest": str(synthesis_path.relative_to(ROOT)),
        },
    }


def main() -> int:
    if not MANIFEST.is_file():
        payload = {"schema_version": "1.0.0", "generated_at": datetime.now(timezone.utc).isoformat(), "all_ok": False, "books": [], "issues": ["manifest missing"]}
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("FAIL manifest missing")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets = [
        book
        for book in manifest.get("books", [])
        if book.get("processing_mode") == "hierarchical" and book.get("canonical") is True and book.get("duplicate_of") is None
    ]
    books = [validate_book(book) for book in targets]
    all_ok = bool(books) and all(book["status"] == "complete" for book in books)
    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segment_first": True,
        "all_ok": all_ok,
        "books": books,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for book in books:
        print(f"{book['status'].upper()}\t{book['book_id']}\tcoverage={book['coverage']}\tissues={len(book['issues'])}")
    print(f"wrote {OUT.relative_to(ROOT)} all_ok={all_ok}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
