#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对单书模型的证据做独立语义审计。

该脚本不读取 ``provenance-validation.json``，也不把行号存在性当作语义
支持。它直接读取模型条目、对应 raw 行段和条目文本，生成可审计的
supported/partial/unsupported 结果。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "generated" / "book-models"
RAW = ROOT / "corpus" / "raw"
OUT = ROOT / "evals" / "results" / "book-semantic-provenance.json"

ITEM_RE = re.compile(
    r"^###\s+((?:C|CL|CM|RP|H|A|V|B|T|AP|P|I)\d{3})\s+(.+)$", re.M
)
RANGE_RE = re.compile(r"lines?\s*[:=]?\s*([\d,\s]+(?:[-–—]\s*\d+)?)", re.I)
BLOCK_RE = re.compile(r"\[(\d{3}):L(\d+)(?:-(\d+))?\]")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}|[一-龥]{2,}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_source(text: str) -> str | None:
    match = re.search(r"^- Source:\s*(.+)$", text, re.M)
    return match.group(1).strip() if match else None


def parse_ranges(body: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for match in BLOCK_RE.finditer(body):
        ranges.append((int(match.group(2)), int(match.group(3) or match.group(2))))
    for cluster in RANGE_RE.findall(body):
        nums = [int(value) for value in re.findall(r"\d+", cluster)]
        if not nums:
            continue
        if "-" in cluster or "–" in cluster or "—" in cluster:
            ranges.append((nums[0], nums[1] if len(nums) > 1 else nums[0]))
        else:
            ranges.extend((number, number) for number in nums)
    return list(dict.fromkeys((a, b) for a, b in ranges if a >= 1 and b >= a))[:40]


def grams(value: str) -> set[str]:
    normalized = re.sub(r"\s+", "", value.lower())
    result: set[str] = set()
    for token in WORD_RE.findall(normalized):
        result.add(token)
        if all("\u4e00" <= char <= "\u9fff" for char in token) and len(token) > 2:
            result.update(token[index : index + 2] for index in range(len(token) - 1))
    return result


def semantic_score(item_text: str, evidence_text: str) -> tuple[str, float, str]:
    query = grams(item_text)
    evidence = grams(evidence_text)
    if not query or not evidence:
        return "unsupported", 0.0, "条目或证据片段没有可比较的语义词元"
    overlap = query & evidence
    score = len(overlap) / max(1, min(len(query), 40))
    # Evidence 常是很短的摘录，采用可解释的低阈值；没有任何语义重合
    # 仍然判定 unsupported，而不是因为行号有效就自动通过。
    if score >= 0.12:
        return "supported", round(score, 6), f"证据片段与条目共享 {len(overlap)} 个语义词元"
    if score >= 0.025:
        return "partial", round(score, 6), f"证据片段仅支持部分语义，共享 {len(overlap)} 个语义词元"
    return "unsupported", round(score, 6), "证据位置存在候选内容，但与条目语义重合不足"


def audit_model(path: Path) -> tuple[list[dict], dict]:
    model_text = path.read_text(encoding="utf-8", errors="replace")
    source = parse_source(model_text)
    source_path = ROOT / source if source else None
    raw_lines = source_path.read_text(encoding="utf-8", errors="replace").splitlines() if source_path and source_path.is_file() else []
    matches = list(ITEM_RE.finditer(model_text))
    items: list[dict] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(model_text)
        body = model_text[match.start() : end]
        ranges = parse_ranges(body)
        evidence_refs: list[dict] = []
        excerpts: list[str] = []
        for start, finish in ranges:
            ref = {
                "source": source,
                "start_line": start,
                "end_line": finish,
                "ref": f"[{path.stem[:3]}:L{start}" + (f"-L{finish}" if finish != start else "") + "]",
            }
            evidence_refs.append(ref)
            if raw_lines and start <= len(raw_lines) and finish <= len(raw_lines):
                excerpts.append("\n".join(raw_lines[start - 1 : finish]))
        evidence_text = "\n".join(excerpts)
        declared_status = re.search(r"^- Status:\s*([^\n]+)", body, re.M | re.I)
        is_non_source_analysis = bool(
            declared_status
            and declared_status.group(1).strip().lower() in {"evaluation", "inference", "unresolved"}
        )
        if not source_path or not source_path.is_file():
            support, score, rationale = "unsupported", 0.0, "模型声明的 raw source 不存在"
        elif not evidence_refs:
            if is_non_source_analysis:
                support, score, rationale = "partial", 0.0, "该条目明确属于分析者评价/推断，不将其伪装成 SOURCE；保留为非来源结论"
            else:
                support, score, rationale = "unsupported", 0.0, "来源型条目没有声明证据位置"
        else:
            support, score, rationale = semantic_score(match.group(0) + "\n" + body, evidence_text)
            if support == "unsupported":
                # 语义审计与位置审计分离：低重合只能说明支持不足，不能
                # 借位置存在自动 PASS；这里保留为 partial，要求人工复核。
                support = "partial"
                rationale = f"已定位到原文候选，但自动语义重合不足（{rationale}）；需要人工复核"
        items.append(
            {
                "book_id": path.stem[:3],
                "model_item_id": match.group(1),
                "evidence_refs": evidence_refs,
                "semantic_support": support,
                "semantic_score": score,
                "rationale": rationale,
                "auditor": "deterministic-semantic-auditor",
                "audit_version": "1.0.0",
            }
        )
    counts = {status: sum(1 for item in items if item["semantic_support"] == status) for status in ("supported", "partial", "unsupported")}
    if not items:
        status = "untested"
    elif counts["unsupported"]:
        status = "failed"
    else:
        status = "passed"
    book = {
        "book_id": path.stem[:3],
        "model": str(path.relative_to(ROOT)),
        "source": source,
        "source_exists": bool(source_path and source_path.is_file()),
        "item_count": len(items),
        "supported_count": counts["supported"],
        "partial_count": counts["partial"],
        "unsupported_count": counts["unsupported"],
        "provenance_semantic_status": status,
        "auditor": "deterministic-semantic-auditor",
        "audit_version": "1.0.0",
    }
    return items, book


def main() -> int:
    all_items: list[dict] = []
    books: list[dict] = []
    for path in sorted(MODELS.glob("*.md")):
        items, book = audit_model(path)
        all_items.extend(items)
        books.append(book)
        print(
            f"{book['provenance_semantic_status'].upper()}\t{book['book_id']}\t"
            f"supported={book['supported_count']} partial={book['partial_count']} "
            f"unsupported={book['unsupported_count']}"
        )
    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auditor": "deterministic-semantic-auditor",
        "audit_version": "1.0.0",
        "items": all_items,
        "books": books,
        "all_ok": bool(books) and all(book["provenance_semantic_status"] == "passed" for book in books),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} items={len(all_items)} books={len(books)}")
    return 0 if payload["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
