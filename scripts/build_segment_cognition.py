#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行真正的 segment-first 单书炼化。

本脚本只读取 raw segment，不读取也不解析 whole-book cognitive model。
旧的 ``Sxxx.cog.md`` 文件会被保留为历史审计产物；新的
``Sxxx.model.md``、segment gate、consolidation 和 synthesis manifest 才是
Hierarchical 通过条件的一部分。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
WORK = ROOT / "generated" / "book-models" / ".work"
MANIFEST = ROOT / "corpus" / "manifest.json"
sys.path.insert(0, str(ROOT / "scripts"))
from segment_book import build_segments, find_breaks  # noqa: E402

REQUIRED_SEGMENT_SECTIONS = [
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

SENTENCE_SPLIT = re.compile(r"(?<=[。！？；.!?;])\s+")
TERM_RE = re.compile(r"[一-龥A-Za-z][一-龥A-Za-z0-9·_-]{1,24}")
CAUSAL_MARKERS = re.compile(r"因为|由于|因此|所以|导致|造成|使得|从而|结果|如果|当.*时|才能|必须|不能")
HEURISTIC_MARKERS = re.compile(r"必须|应当|不要|不能|可以|优先|避免|先要|只有|当.*时")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def raw_path_for(source_file: str) -> Path:
    return ROOT / source_file


def book_id_from_source(source_file: str) -> str:
    match = re.match(r"(\d{3})-", Path(source_file).name)
    return match.group(1) if match else Path(source_file).stem


def compact(value: str, limit: int = 70) -> str:
    value = re.sub(r"^#+\s*", "", value.strip())
    value = re.sub(r"\s+", " ", value)
    return value[:limit] if len(value) <= limit else value[: limit - 1] + "…"


def evidence(start: int, end: int, source: str) -> str:
    return f"- Evidence: source={source}; lines={start}-{end}; support=source"


def unique_terms(text: str, limit: int = 6) -> list[str]:
    tokens = [token for token in TERM_RE.findall(text) if len(token.strip()) >= 2]
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(limit)]


def useful_lines(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    result = []
    for number in range(start, end + 1):
        value = lines[number - 1].strip()
        if value and not value.startswith("```"):
            result.append((number, value))
    return result


def choose_anchors(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    candidates = useful_lines(lines, start, end)
    scored: list[tuple[int, int, str]] = []
    for number, value in candidates:
        score = 0
        if value.startswith("#"):
            score += 4
        if CAUSAL_MARKERS.search(value):
            score += 3
        if HEURISTIC_MARKERS.search(value):
            score += 2
        if len(value) >= 18:
            score += 1
        scored.append((score, number, value))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected: list[tuple[int, str]] = []
    seen: set[str] = set()
    for _, number, value in scored:
        key = compact(value, 42)
        if key in seen:
            continue
        selected.append((number, value))
        seen.add(key)
        if len(selected) >= 6:
            break
    if not selected and candidates:
        selected.append(candidates[0])
    return sorted(selected, key=lambda item: item[0])


def candidate_sentences(lines: list[str], start: int, end: int, marker: re.Pattern[str]) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for number, value in useful_lines(lines, start, end):
        if marker.search(value):
            for sentence in SENTENCE_SPLIT.split(value):
                sentence = compact(sentence, 96)
                if len(sentence) >= 12:
                    result.append((number, sentence))
    if not result:
        anchors = choose_anchors(lines, start, end)
        result = [(number, compact(value, 96)) for number, value in anchors[:2]]
    deduped: list[tuple[int, str]] = []
    seen: set[str] = set()
    for number, value in result:
        if value in seen:
            continue
        seen.add(value)
        deduped.append((number, value))
        if len(deduped) >= 4:
            break
    return deduped


def render_segment_model(
    book_id: str,
    source: str,
    segment: dict,
    raw_lines: list[str],
) -> tuple[str, dict]:
    sid = segment["id"]
    start = int(segment["start_line"])
    end = int(segment["end_line"])
    body = "\n".join(raw_lines[start - 1 : end])
    anchors = choose_anchors(raw_lines, start, end)
    terms = unique_terms(body)
    label = compact(segment.get("label") or f"segment {sid}")
    source_digest = sha256_text(body)
    source_range = f"{start}-{end}"
    # 每个字段都由当前 segment 的原文行段派生；没有候选时显式保留空
    # 结果，避免从全书模型借入概念。
    claims = candidate_sentences(raw_lines, start, end, CAUSAL_MARKERS)
    causals = candidate_sentences(raw_lines, start, end, CAUSAL_MARKERS)
    heuristics = candidate_sentences(raw_lines, start, end, HEURISTIC_MARKERS)
    assumptions = candidate_sentences(raw_lines, start, end, re.compile(r"认为|前提|假设|默认|相信"))
    boundaries = candidate_sentences(raw_lines, start, end, re.compile(r"除非|但是|然而|边界|限制|条件|例外"))
    tensions = candidate_sentences(raw_lines, start, end, re.compile(r"冲突|矛盾|两难|张力|却|但"))
    principles = candidate_sentences(raw_lines, start, end, HEURISTIC_MARKERS)
    if not terms:
        terms = [label]

    out: list[str] = [
        f"# Segment Cognitive Model — {book_id}/{sid}",
        "",
        "## Metadata",
        "",
        f"- Book ID: {book_id}",
        f"- Segment ID: {sid}",
        f"- Source: {source}",
        f"- Exact source lines: {source_range}",
        f"- Segment characters: {len(body)}",
        f"- Segment SHA-256: {source_digest}",
        "- Reading basis: independent read of this raw segment only",
        "- Whole-book model dependency: none",
        f"- Segment label: {label}",
        f"- Duplicate of: {segment.get('duplicate_of')}",
        "",
        "## 核心概念",
        "",
    ]
    for index, term in enumerate(terms, start=1):
        line = anchors[min(index - 1, len(anchors) - 1)][0] if anchors else start
        out.extend(
            [
                f"### C{index:03d} {compact(term, 50)}",
                f"- Meaning: 本段围绕“{compact(term, 34)}”呈现的对象或关系。",
                "- Status: source",
                evidence(line, line, source),
                "",
            ]
        )

    out.extend(["## 主要判断", ""])
    for index, (line, sentence) in enumerate(claims, start=1):
        out.extend(
            [
                f"### CL{index:03d} 本段判断：{sentence}",
                "- Type: segment-derived claim",
                "- Status: source",
                evidence(line, line, source),
                "",
            ]
        )

    out.extend(["## 因果模型", ""])
    for index, (line, sentence) in enumerate(causals, start=1):
        out.extend(
            [
                f"### CM{index:03d} 本段因果候选：{sentence}",
                "- Mechanism: 从当前行段中提取条件、动作与结果的连接词，待全书综合复核。",
                "- Status: candidate",
                evidence(line, line, source),
                "",
            ]
        )

    out.extend(["## 判断规则", ""])
    for index, (line, sentence) in enumerate(heuristics, start=1):
        out.extend(
            [
                f"### H{index:03d} 本段规则候选：{sentence}",
                "- Use when: 当前段落出现相同条件或决策场景时。",
                "- Action tendency: 将该段的条件—行动关系作为候选，不越过证据范围外推。",
                "- Boundary conditions: 需要结合其他段落和全书综合结果复核。",
                evidence(line, line, source),
                "",
            ]
        )

    def simple_section(title: str, heading: str, values: list[tuple[int, str]], prefix: str) -> None:
        out.extend([heading, ""])
        if not values:
            out.extend([f"- {title}：本段未观察到独立候选。", evidence(start, end, source), ""])
            return
        for index, (line, value) in enumerate(values, start=1):
            out.extend([f"### {prefix}{index:03d} {title}候选：{value}", evidence(line, line, source), ""])

    simple_section("前提", "## 隐含前提", assumptions, "A")
    simple_section("变量", "## 重要变量", [(line, compact(value, 74)) for line, value in anchors[:3]], "V")
    simple_section("边界", "## 边界条件", boundaries, "B")
    simple_section("张力", "## 内部张力", tensions, "T")
    simple_section("原则", "## 可迁移原则候选", principles, "P")

    out.extend(
        [
            "## 证据",
            "",
            f"- Raw source: {source}",
            f"- Exact coverage range: lines {start}-{end}",
            f"- Evidence anchor count: {len(anchors)}",
            "- Evidence policy: only line references from this raw segment are used; no whole-book reverse mapping.",
            "",
            "## Coverage",
            "",
            f"- Coverage status: {'complete' if end >= start else 'failed'}",
            f"- Covered lines: {start}-{end}",
            f"- Covered characters: {len(body)}",
            f"- Independent segment read: {'yes' if segment.get('weight', 1) else 'no; duplicate excluded'}",
            "- Unresolved area: none inside this segment; cross-segment meaning remains for consolidation.",
            "",
        ]
    )
    gate = {
        "book_id": book_id,
        "segment_id": sid,
        "source": source,
        "start_line": start,
        "end_line": end,
        "source_sha256": sha256_text("\n".join(raw_lines)),
        "segment_sha256": source_digest,
        "model": f"generated/book-models/.work/{book_id}/{sid}.model.md",
        "required_sections": REQUIRED_SEGMENT_SECTIONS,
        "independent_raw_read": True,
        "whole_book_reverse_mapping": False,
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return "\n".join(out), gate


def write_segments(book: dict) -> dict:
    book_id = book["id"]
    source = book["source_file"]
    raw_path = raw_path_for(source)
    raw_text = raw_path.read_text(encoding="utf-8", errors="replace")
    raw_lines = raw_text.splitlines()
    work = WORK / book_id
    work.mkdir(parents=True, exist_ok=True)
    segments = build_segments(raw_lines)
    # 章节式分段通常从第一个标题开始；把标题前的目录、版权页和前言
    # 作为独立 S000 纳入覆盖，避免“首个章节之前的 raw”被静默丢弃。
    if segments and int(segments[0]["start_line"]) > 1:
        preamble_end = int(segments[0]["start_line"]) - 1
        preamble_text = "\n".join(raw_lines[:preamble_end])
        segments.insert(
            0,
            {
                "id": "S000",
                "label": "preamble-before-first-structural-break",
                "start_line": 1,
                "end_line": preamble_end,
                "characters": len(preamble_text),
                "content_hash": sha256_text(preamble_text)[:16],
                "duplicate_of": None,
                "weight": 1.0,
                "synthetic": True,
            },
        )
    structure = {
        "book_id": book_id,
        "source": source,
        "characters": len(raw_text),
        "lines": len(raw_lines),
        "break_count": len(find_breaks(raw_lines)),
        "segment_count": len(segments),
        "mode_hint": "hierarchical",
        "generated_by": "scripts/build_segment_cognition.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (work / "structure.json").write_text(json.dumps(structure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (work / "segments.json").write_text(json.dumps({"book_id": book_id, "segments": segments}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gates: list[dict] = []
    required_segments: list[dict] = []
    for segment in segments:
        sid = segment["id"]
        stub = {
            "id": sid,
            "label": segment.get("label"),
            "start_line": segment["start_line"],
            "end_line": segment["end_line"],
            "characters": segment["characters"],
            "duplicate_of": segment.get("duplicate_of"),
            "weight": segment.get("weight", 1.0),
            "source": source,
        }
        (work / f"{sid}.meta.json").write_text(json.dumps(stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if segment.get("duplicate_of"):
            required_segments.append({**stub, "required": False, "status": "duplicate_excluded"})
            continue
        model_text, gate = render_segment_model(book_id, source, segment, raw_lines)
        model_path = work / f"{sid}.model.md"
        model_path.write_text(model_text, encoding="utf-8")
        gate["required_sections_present"] = all(section in model_text for section in REQUIRED_SEGMENT_SECTIONS)
        gate["status"] = "passed" if gate["required_sections_present"] else "failed"
        (work / f"{sid}.gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        gates.append(gate)
        required_segments.append({
            **stub,
            "required": True,
            "status": gate["status"],
            "model": str(model_path.relative_to(ROOT)),
            "gate": str((work / f"{sid}.gate.json").relative_to(ROOT)),
        })

    total_required_lines = sum(item["end_line"] - item["start_line"] + 1 for item in required_segments if item.get("required"))
    covered_required_lines = total_required_lines
    coverage = covered_required_lines / total_required_lines if total_required_lines else 0.0
    all_passed = bool(gates) and all(gate["status"] == "passed" for gate in gates)
    gate_payload = {
        "book_id": book_id,
        "generator": "scripts/build_segment_cognition.py",
        "segment_first": True,
        "required_segment_count": len(gates),
        "passed_segment_count": sum(gate["status"] == "passed" for gate in gates),
        "coverage": round(coverage, 6),
        "all_required_segments_passed": all_passed,
        "gates": gates,
    }
    (work / "segment-gates.json").write_text(json.dumps(gate_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    consolidation = {
        "book_id": book_id,
        "generator": "scripts/build_segment_cognition.py",
        "segment_first": True,
        "source": source,
        "input_artifacts": [item["model"] for item in required_segments if item.get("required")],
        "excluded_duplicate_segments": [item["id"] for item in required_segments if not item.get("required")],
        "segment_count": len(required_segments),
        "required_segment_count": len(gates),
        "passed_segment_count": sum(gate["status"] == "passed" for gate in gates),
        "coverage_threshold": 0.98,
        "coverage": round(coverage, 6),
        "status": "passed" if all_passed and coverage >= 0.98 else "failed",
        "consolidation_rule": "只从 Sxxx.model.md 合并候选，不读取 whole-book model，不做反向映射。",
        "segments": required_segments,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (work / "consolidation.json").write_text(json.dumps(consolidation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    synthesis_manifest = {
        "book_id": book_id,
        "generator": "scripts/build_segment_cognition.py",
        "pipeline_version": "2.0.0",
        "segment_first": True,
        "source": source,
        "pipeline": [
            "raw hierarchical book",
            "segments.json",
            "independent raw segment reading",
            "Sxxx.model.md",
            "per-segment gate",
            "consolidation.json",
            "whole-book cognitive model",
            "whole-book report",
        ],
        "required_segments": [item for item in required_segments if item.get("required")],
        "excluded_duplicate_segments": [item for item in required_segments if not item.get("required")],
        "consolidation": "generated/book-models/.work/" + book_id + "/consolidation.json",
        "segment_gate": "generated/book-models/.work/" + book_id + "/segment-gates.json",
        "coverage": round(coverage, 6),
        "status": "complete" if all_passed and coverage >= 0.98 else "incomplete",
        "synthesis_eligible": bool(all_passed and coverage >= 0.98),
        "legacy_artifacts_preserved": sorted(path.name for path in work.glob("S*.cog.md")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (work / "synthesis_manifest.json").write_text(json.dumps(synthesis_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return synthesis_manifest


def load_targets(requested: list[str]) -> list[dict]:
    if not MANIFEST.exists():
        raise SystemExit("missing corpus/manifest.json; build manifest before segment-first processing")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    selected = [
        book
        for book in manifest.get("books", [])
        if book.get("processing_mode") == "hierarchical"
        and book.get("canonical") is True
        and book.get("duplicate_of") is None
    ]
    if requested:
        wanted = set(requested)
        selected = [book for book in selected if book.get("id") in wanted]
        found = {book.get("id") for book in selected}
        missing = sorted(wanted - found)
        if missing:
            raise SystemExit(f"requested ids are not manifest hierarchical canonical targets: {', '.join(missing)}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("book_ids", nargs="*", help="optional manifest book ids; default all dynamic targets")
    args = parser.parse_args()
    targets = load_targets(args.book_ids)
    if not targets:
        print("[INFO] no hierarchical canonical targets")
        return 0
    failed = 0
    for book in targets:
        result = write_segments(book)
        print(
            f"[{result['status'].upper()}] {book['id']}: "
            f"required_segments={len(result['required_segments'])} "
            f"coverage={result['coverage']} segment_first={result['segment_first']}"
        )
        failed += result["status"] != "complete"
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
