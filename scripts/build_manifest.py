#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 raw、模型和独立验证结果生成 corpus/manifest.json。

处理模式是可解释的多因素判断：源文件规模、结构质量、OCR 噪声、章节/页
结构、语义分段可行性和上下文预算共同决定 direct/hierarchical。不存在以
单一 ``DIRECT_MAX`` 为依据的硬切线。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
MODELS = ROOT / "generated" / "book-models"
REPORTS = ROOT / "generated" / "reports"
RESULTS = ROOT / "evals" / "results"
OUT = ROOT / "corpus" / "manifest.json"

KNOWN_DUPLICATES = {"020": "015"}
CONTEXT_BUDGET = 120_000
HIERARCHICAL_SCORE = 2.4


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def book_id(name: str) -> str:
    match = re.match(r"^(\d{3})-", name)
    return match.group(1) if match else name


def title_from_name(name: str) -> str:
    return re.sub(r"^\d{3}-", "", Path(name).stem)


def garbled_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = sum(1 for char in text if char == "\ufffd" or "\ue000" <= char <= "\uf8ff")
    return bad / len(text)


def structural_features(text: str) -> dict:
    lines = text.splitlines()
    headings = [line.strip() for line in lines if re.match(r"^#{1,3}\s+", line.strip())]
    chapter_markers = sum(
        bool(re.match(r"^第[一二三四五六七八九十百千零〇\d]+[章节卷篇部回]", line.strip()))
        for line in lines
    )
    page_markers = sum(bool(re.match(r"^(第一部分|第二部分|第\d+部分).*\(\d+\)$", line.strip())) for line in lines)
    nonempty = [line for line in lines if line.strip()]
    avg_line = sum(len(line) for line in nonempty) / max(1, len(nonempty))
    return {
        "heading_count": len(headings),
        "chapter_marker_count": chapter_markers,
        "page_marker_count": page_markers,
        "nonempty_line_count": len(nonempty),
        "average_nonempty_line_characters": round(avg_line, 2),
        "semantic_break_count": len(headings) + chapter_markers + page_markers,
    }


def infer_processing_mode(text: str, garbled: float) -> tuple[str, dict, str]:
    chars = len(text)
    lines = len(text.splitlines())
    features = structural_features(text)
    size_factor = min(4.0, chars / 140_000)
    context_factor = 0.9 if chars > CONTEXT_BUDGET else 0.0
    coverage_factor = 0.8 if lines > 7_000 else 0.0
    structure_factor = 0.8 if features["semantic_break_count"] >= 8 and chars > 150_000 else 0.0
    segmentation_factor = 0.8 if (features["semantic_break_count"] >= 3 or lines > 7_000) else 0.0
    ocr_factor = min(2.0, garbled * 100) if garbled > 0.002 else 0.0
    score = size_factor + context_factor + coverage_factor + structure_factor + segmentation_factor + ocr_factor
    mode = "hierarchical" if score >= HIERARCHICAL_SCORE else "direct"
    if chars == 0:
        mode = "blocked"
    factors = {
        "source_characters": chars,
        "source_lines": lines,
        "context_budget_characters": CONTEXT_BUDGET,
        "size_factor": round(size_factor, 4),
        "context_budget_factor": round(context_factor, 4),
        "coverage_factor": round(coverage_factor, 4),
        "structure_factor": round(structure_factor, 4),
        "semantic_segmentation_factor": round(segmentation_factor, 4),
        "ocr_factor": round(ocr_factor, 4),
        "decision_score": round(score, 4),
        "hierarchical_score_threshold": HIERARCHICAL_SCORE,
        "structural_features": features,
    }
    reasons = [
        f"score={score:.2f} from size/context/structure/coverage/segmentation/OCR factors",
        f"source={chars} chars/{lines} lines",
        f"semantic_breaks={features['semantic_break_count']}",
    ]
    if chars > CONTEXT_BUDGET:
        reasons.append("context budget requires multi-pass reading")
    if features["semantic_break_count"] >= 3 or lines > 7_000:
        reasons.append("raw structure supports independent semantic segments")
    if garbled > 0.002:
        reasons.append("OCR noise increases review and coverage risk")
    return mode, factors, "; ".join(reasons)


def load_json(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def index_by_id(payload: dict | list, key: str = "book_id") -> dict:
    if isinstance(payload, list):
        result = {}
        for item in payload:
            value = item.get(key) or item.get("id")
            if not value and key == "book_id":
                path_value = item.get("path") or item.get("model") or ""
                match = re.search(r"(?:^|/)(\d{3})-", str(path_value))
                value = match.group(1) if match else None
            if value:
                result[value] = item
        return result
    if isinstance(payload, dict):
        values = payload.get("items") or payload.get("books") or []
        return index_by_id(values, key)
    return {}


def model_path_for(stem: str) -> Path | None:
    path = MODELS / f"{stem}.md"
    return path if path.is_file() and path.stat().st_size > 0 else None


def report_path_for(stem: str) -> Path | None:
    path = REPORTS / f"{stem}.report.md"
    return path if path.is_file() and path.stat().st_size > 0 else None


def main() -> None:
    model_validation = load_json(RESULTS / "book-model-validation.json", {})
    model_by_id = index_by_id(model_validation)
    provenance = index_by_id(load_json(RESULTS / "provenance-validation.json", []), key="book_id")
    semantic_payload = load_json(RESULTS / "book-semantic-provenance.json", {})
    semantic_by_id = index_by_id(semantic_payload.get("books", []) if isinstance(semantic_payload, dict) else semantic_payload)
    segment_payload = load_json(RESULTS / "segment-coverage.json", {})
    segment_by_id = index_by_id(segment_payload)

    books: list[dict] = []
    hash_index: dict[str, list[str]] = {}
    for raw_path in sorted(RAW.glob("*.md")):
        data = raw_path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        bid = book_id(raw_path.name)
        stem = raw_path.stem
        digest = sha256_bytes(data)
        chars = len(text)
        lines = len(text.splitlines())
        garbled = garbled_ratio(text)
        mode, processing_features, processing_reason = infer_processing_mode(text, garbled)
        hash_index.setdefault(digest, []).append(bid)
        entry = {
            "id": bid,
            "title": title_from_name(raw_path.name),
            "source_file": f"corpus/raw/{raw_path.name}",
            "source_hash": digest,
            "size": len(data),
            "characters": chars,
            "lines": lines,
            "garbled_ratio": round(garbled, 6),
            "garbled_ratio_sample": round(garbled, 6),
            "status": "pending",
            "canonical": True,
            "duplicate_of": None,
            "source_quality": "empty" if chars == 0 else ("ocr_noisy" if garbled > 0.01 else "readable"),
            "processing_mode": mode,
            "processing_mode_reason": processing_reason,
            "processing_features": processing_features,
            "book_model": None,
            "report": None,
            "notes": [],
            "schema_version": "2.0.0",
            "distiller_version": "1.0.0",
            "model_status": "untested",
            "provenance_location_status": "untested",
            "provenance_semantic_status": "untested",
            "coverage_status": "incomplete",
            "complexity_status": "untested",
            "segment_coverage_status": "n_a" if mode != "hierarchical" else "untested",
            "synthesis_eligible": False,
        }
        if chars == 0:
            entry.update(
                {
                    "status": "blocked_ocr_unavailable",
                    "canonical": False,
                    "processing_mode": "blocked",
                    "source_pdf_exists": True,
                    "text_layer": False,
                }
            )
            entry["notes"].extend(["raw empty; PDF may exist but text extraction failed or not usable", "do_not_forge_model"])
        books.append(entry)

    by_id = {book["id"]: book for book in books}
    for duplicate_id, canonical_id in KNOWN_DUPLICATES.items():
        if duplicate_id in by_id and canonical_id in by_id:
            entry = by_id[duplicate_id]
            entry.update({"status": "duplicate", "canonical": False, "duplicate_of": canonical_id, "processing_mode": "skip_duplicate", "segment_coverage_status": "n_a"})
            entry["notes"].append(f"explicit duplicate of {canonical_id}")
    for digest, ids in hash_index.items():
        if len(ids) < 2:
            continue
        canonical = sorted(ids)[0]
        for duplicate_id in sorted(ids)[1:]:
            if by_id[duplicate_id]["status"] == "blocked_ocr_unavailable" or by_id[duplicate_id]["duplicate_of"]:
                continue
            by_id[duplicate_id].update({"status": "duplicate", "canonical": False, "duplicate_of": canonical, "processing_mode": "skip_duplicate", "segment_coverage_status": "n_a"})
            by_id[duplicate_id]["notes"].append(f"hash-identical to {canonical}")

    for entry in books:
        if entry["status"] in {"blocked_ocr_unavailable", "duplicate"}:
            continue
        stem = Path(entry["source_file"]).stem
        model_path = model_path_for(stem)
        report_path = report_path_for(stem)
        model_result = model_by_id.get(entry["id"], {})
        location_result = provenance.get(entry["id"], {})
        semantic_result = semantic_by_id.get(entry["id"], {})
        segment_result = segment_by_id.get(entry["id"], {})
        if model_path:
            entry["book_model"] = str(model_path.relative_to(ROOT))
        if report_path:
            entry["report"] = str(report_path.relative_to(ROOT))
        entry["model_status"] = "pass" if model_result.get("ok") else ("failed" if model_result else "untested")
        entry["provenance_location_status"] = "passed" if location_result.get("ok") else ("failed" if location_result else "untested")
        entry["provenance_semantic_status"] = semantic_result.get("provenance_semantic_status", "untested")
        entry["complexity_status"] = (model_result.get("adaptive_complexity") or {}).get("status", "untested")
        if entry["processing_mode"] == "hierarchical":
            entry["segment_coverage_status"] = segment_result.get("status", "incomplete" if segment_result else "untested")
            entry["coverage_status"] = "complete" if segment_result.get("status") == "complete" and model_result.get("ok") else "incomplete"
        else:
            entry["coverage_status"] = "complete" if model_result.get("ok") and report_path else "incomplete"
        required_files = bool(model_path and report_path)
        entry["status"] = "complete" if required_files else ("modeled" if model_path else "pending")
        entry["synthesis_eligible"] = bool(
            entry["canonical"]
            and entry["duplicate_of"] is None
            and entry["status"] == "complete"
            and entry["model_status"] == "pass"
            and entry["provenance_location_status"] == "passed"
            and entry["provenance_semantic_status"] == "passed"
            and entry["complexity_status"] == "passed"
            and entry["coverage_status"] == "complete"
            and (entry["processing_mode"] != "hierarchical" or entry["segment_coverage_status"] == "complete")
        )

    manifest = {
        "pipeline_version": "2.0.0",
        "generated_by": "scripts/build_manifest.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "raw_dir": "corpus/raw",
        "book_count": len(books),
        "canonical_count": sum(1 for book in books if book["canonical"] and book["status"] != "blocked_ocr_unavailable"),
        "duplicate_count": sum(1 for book in books if book["status"] == "duplicate"),
        "blocked_count": sum(1 for book in books if book["status"] == "blocked_ocr_unavailable"),
        "complete_count": sum(1 for book in books if book["status"] == "complete"),
        "synthesis_eligible_count": sum(1 for book in books if book["synthesis_eligible"]),
        "gate_policy": {
            "adaptive_distillation": "complexity_status must be passed from validator result",
            "segment_first_hierarchical": "requires segment coverage result complete",
            "provenance_location": "only deterministic location validator may set passed",
            "provenance_semantic": "only independent semantic audit may set passed; unsupported fails",
            "missing_artifact": "untested/incomplete never becomes synthesis eligible",
        },
        "books": books,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(
        f"books={manifest['book_count']} canonical={manifest['canonical_count']} "
        f"dup={manifest['duplicate_count']} blocked={manifest['blocked_count']} "
        f"complete={manifest['complete_count']} synthesis_eligible={manifest['synthesis_eligible_count']}"
    )
    for entry in books:
        print(
            f"{entry['id']}\tmode={entry['processing_mode']}\tstatus={entry['status']}\t"
            f"complexity={entry['complexity_status']}\tsemantic={entry['provenance_semantic_status']}\t"
            f"segment={entry['segment_coverage_status']}\teligible={entry['synthesis_eligible']}"
        )


if __name__ == "__main__":
    main()
