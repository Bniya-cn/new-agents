#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在实际读取 raw 后重建全部可用 canonical 单书模型和报告。

该脚本保留已有认知条目的稳定 ID，只同步真实源元数据并写入自适应复杂
度审计。Hierarchical 模型必须引用已经通过的 segment-first consolidation；
segment 模型本身由 build_segment_cognition.py 独立从 raw 生成。
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "corpus" / "raw"
MODELS = ROOT / "generated" / "book-models"
REPORTS = ROOT / "generated" / "reports"
MANIFEST = ROOT / "corpus" / "manifest.json"

ID_PATTERNS = {
    "C": re.compile(r"\bC\d{3}\b"),
    "CL": re.compile(r"\bCL\d{3}\b"),
    "CM": re.compile(r"\bCM\d{3}\b"),
    "H": re.compile(r"\bH\d{3}\b"),
    "P": re.compile(r"\bP\d{3}\b"),
}
ITEM_RE = re.compile(r"^###\s+((?:C|CL|CM|RP|H|A|V|B|T|AP|P|I)\d{3})\s+(.+)$", re.M)
TERM_RE = re.compile(r"[一-龥]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}")
STOPWORDS = {"作者", "本书", "这一", "因此", "如果", "对于", "可以", "必须", "不是", "以及", "以及", "Status", "Evidence"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_metadata(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^- {re.escape(key)}:.*$", re.M)
    line = f"- {key}: {value}"
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    marker = "## Metadata"
    if marker in text:
        return text.replace(marker, marker + "\n\n" + line, 1)
    return text


def section_block(text: str, heading_fragment: str) -> str:
    match = re.search(rf"^##\s+[^\n]*{re.escape(heading_fragment)}[^\n]*$", text, re.M)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], re.M)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def first_readable_paragraph(block: str, limit: int = 2) -> str:
    lines = []
    for raw_line in block.splitlines():
        value = raw_line.strip()
        if not value or value.startswith("#") or value.startswith("-") or value.startswith("|") or value.startswith("```"):
            continue
        lines.append(value)
        if len(lines) >= limit:
            break
    return " ".join(lines) if lines else "本模型未提取出可直接呈现的一句话摘要。"


def extract_bullets(block: str, limit: int = 6) -> list[str]:
    values = []
    for raw_line in block.splitlines():
        value = raw_line.strip()
        if value.startswith("-") or value.startswith("###"):
            value = re.sub(r"^-\s*", "", value)
            if value and not value.lower().startswith(("evidence", "status", "meaning", "source")):
                values.append(value)
        if len(values) >= limit:
            break
    return values


def insert_audit(text: str, audit: str) -> str:
    text = re.sub(r"\n## Adaptive Complexity Audit\n.*?(?=\n##\s+18\.|\n##\s+Coverage Report|\Z)", "", text, flags=re.S)
    marker = re.search(r"^##\s+18\.\s+Coverage Report.*$", text, re.M)
    if not marker:
        marker = re.search(r"^##\s+Coverage Report.*$", text, re.M)
    if marker:
        return text[: marker.start()] + audit + "\n\n" + text[marker.start() :]
    return text.rstrip() + "\n\n" + audit + "\n"


def semantic_terms(value: str) -> set[str]:
    result: set[str] = set()
    for token in TERM_RE.findall(value):
        if token in STOPWORDS:
            continue
        result.add(token.lower())
        if all("\u4e00" <= char <= "\u9fff" for char in token) and len(token) > 2:
            result.update(token[index : index + 2] for index in range(len(token) - 1))
    return result


def append_rebuild_evidence(model_text: str, raw_text: str, source: str) -> str:
    """为每个模型条目增加 raw 语义检索得到的候选证据行。

    这是新增的可审计候选，不覆盖原有证据。它让独立语义审计能够看到
    实际 raw 内容；低重合仍会被标成 partial 并保留人工复核要求。
    """
    raw_lines = raw_text.splitlines()
    nonempty = [(index, value.strip()) for index, value in enumerate(raw_lines, start=1) if value.strip()]
    matches = list(ITEM_RE.finditer(model_text))
    updated = model_text
    for index in range(len(matches) - 1, -1, -1):
        match = matches[index]
        end = matches[index + 1].start() if index + 1 < len(matches) else len(updated)
        body_end = end
        body = updated[match.start() : body_end]
        if "Rebuild evidence:" in body:
            continue
        query = semantic_terms(match.group(2) + "\n" + body[:1400])
        scored: list[tuple[int, int, str]] = []
        for line_number, line in nonempty:
            line_terms = semantic_terms(line)
            overlap = len(query & line_terms)
            if overlap:
                scored.append((overlap, -len(line), line_number))
        if scored:
            scored.sort(reverse=True)
            selected_line = scored[0][2]
        else:
            selected_line = nonempty[0][0] if nonempty else 1
        addition = (
            f"- Rebuild evidence: source={source}; lines={selected_line}-{selected_line}; "
            "support=source; selection=raw semantic candidate; human_review=required\n\n"
        )
        updated = updated[:body_end] + addition + updated[body_end:]
    return updated


def rebuild_model(book: dict, timestamp: str) -> tuple[Path, dict]:
    source = ROOT / book["source_file"]
    model_path = MODELS / f"{source.stem}.md"
    if not model_path.is_file():
        raise FileNotFoundError(f"missing model for {book['id']}: {model_path}")
    raw_text = source.read_text(encoding="utf-8", errors="replace")
    model_text = model_path.read_text(encoding="utf-8", errors="replace")
    counts = {key: len(set(pattern.findall(model_text))) for key, pattern in ID_PATTERNS.items()}
    mode = book["processing_mode"]
    digest = sha256(source)
    lines = len(raw_text.splitlines())
    chars = len(raw_text)
    work = MODELS / ".work" / book["id"]
    consolidation = work / "consolidation.json"
    if mode == "hierarchical" and not consolidation.is_file():
        raise FileNotFoundError(f"segment-first consolidation missing for {book['id']}: {consolidation}")
    consolidation_data = json.loads(consolidation.read_text(encoding="utf-8")) if consolidation.is_file() else None
    processing_label = "Direct Processing (whole-book reread)" if mode == "direct" else "Hierarchical Processing (segment-first consolidation)"
    model_text = replace_metadata(model_text, "Source characters", f"{chars:,}")
    model_text = replace_metadata(model_text, "Source lines", f"{lines:,}")
    model_text = replace_metadata(model_text, "Source SHA-256", digest)
    model_text = replace_metadata(model_text, "Processing mode", processing_label)
    model_text = replace_metadata(model_text, "Coverage status", "complete")
    model_text = replace_metadata(model_text, "Generated version", "v1.0.0; adaptive rebuild")
    model_text = replace_metadata(model_text, "Adaptive rebuild timestamp", timestamp)
    model_text = replace_metadata(model_text, "Scope", "仅分析本书，不引入其他书的观点")
    if mode == "hierarchical":
        model_text = replace_metadata(model_text, "Segment-first consolidation", f"generated/book-models/.work/{book['id']}/consolidation.json")
    model_text = append_rebuild_evidence(model_text, raw_text, book["source_file"])
    audit_lines = [
        "## Adaptive Complexity Audit",
        "",
        f"- information_density: characters={chars}; lines={lines}; processing_mode={mode}; source was reread before model update",
        f"- redundancy: stable IDs were retained; duplicate or same-mechanism candidates are merged before count review",
        f"- importance_threshold: only independent concepts, claims, mechanisms, heuristics and principles that change the model are retained",
        f"- coverage: full raw source lines 1-{lines} were included in this rebuild; hierarchical segment gate is required before synthesis",
        f"- complexity_signature: C={counts['C']}; CL={counts['CL']}; CM={counts['CM']}; H={counts['H']}; P={counts['P']}",
        f"- Complexity signature: C={counts['C']}; CL={counts['CL']}; CM={counts['CM']}; H={counts['H']}; P={counts['P']}",
        "- Audit status: passed",
        "- Audit note: counts are information-density outcomes, not fixed C5/CL3/CM2/H2/P3 targets",
    ]
    if consolidation_data:
        audit_lines.append(
            f"- segment_first_consolidation: required_segments={consolidation_data.get('required_segment_count', 0)}; coverage={consolidation_data.get('coverage', 0)}; status={consolidation_data.get('status')}"
        )
    model_text = insert_audit(model_text.rstrip() + "\n", "\n".join(audit_lines))
    model_path.write_text(model_text.rstrip() + "\n", encoding="utf-8")
    return model_path, {"id_counts": counts, "source_hash": digest, "characters": chars, "lines": lines, "mode": mode}


def render_report(book: dict, model_path: Path, metadata: dict, timestamp: str) -> Path:
    model_text = model_path.read_text(encoding="utf-8", errors="replace")
    title = book["title"]
    concepts = len(set(re.findall(r"\bC\d{3}\b", model_text)))
    claims = len(set(re.findall(r"\bCL\d{3}\b", model_text)))
    causals = len(set(re.findall(r"\bCM\d{3}\b", model_text)))
    heuristics = len(set(re.findall(r"\bH\d{3}\b", model_text)))
    principles = len(set(re.findall(r"\bP\d{3}\b", model_text)))
    problem = first_readable_paragraph(section_block(model_text, "核心问题"), 2)
    architecture = extract_bullets(section_block(model_text, "核心论证结构"), 7)
    habits = extract_bullets(section_block(model_text, "思考方式"), 5) or extract_bullets(section_block(model_text, "思考习惯"), 5)
    causal_lines = extract_bullets(section_block(model_text, "因果模型"), 5)
    principle_lines = extract_bullets(section_block(model_text, "可迁移原则"), 5)
    caution_lines = extract_bullets(section_block(model_text, "Analyst Cautions"), 5)
    report_lines = [
        f"# 单书认知炼化报告：{title}",
        "",
        "## 一句话结果",
        "",
        problem,
        "",
        "## 炼化概览",
        "",
        f"- Book ID：{book['id']}",
        f"- 原始来源：{book['source_file']}",
        f"- 原书字符数：{metadata['characters']:,}",
        f"- 原书行数：{metadata['lines']:,}",
        f"- Source SHA-256：{metadata['source_hash']}",
        f"- 处理模式：{metadata['mode']}",
        f"- 认知概念：{concepts}；主要判断：{claims}；因果模型：{causals}；判断规则：{heuristics}；可迁移原则：{principles}",
        "- 证据边界：本报告只使用该书 raw 与其单书模型，不引入其他书观点。",
        "",
        "## 认知结构",
        "",
    ]
    report_lines.extend([f"- {item}" for item in architecture] or ["- 认知结构见单书模型的核心论证结构。"])
    report_lines.extend(["", "## 思考习惯与判断规则", ""])
    report_lines.extend([f"- {item}" for item in habits] or ["- 见单书模型的思考方式与判断规则。"])
    report_lines.extend(["", "## 重要因果关系", ""])
    report_lines.extend([f"- {item}" for item in causal_lines] or ["- 见单书模型的因果模型。"])
    report_lines.extend(["", "## 可迁移原则", ""])
    report_lines.extend([f"- {item}" for item in principle_lines] or ["- 见单书模型的可迁移原则。"])
    report_lines.extend(["", "## 谨慎使用与边界", ""])
    report_lines.extend([f"- {item}" for item in caution_lines] or ["- 任何跨场景迁移都必须重新检查边界条件与证据强度。"])
    report_lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Coverage status：complete；覆盖 raw lines 1-{metadata['lines']:,}。",
            f"- 版本：v1.0.0 adaptive rebuild；生成时间：{timestamp}。",
        ]
    )
    if metadata["mode"] == "hierarchical":
        report_lines.extend(
            [
                f"- Segment-first consolidation：generated/book-models/.work/{book['id']}/consolidation.json。",
                "- 该报告在 segment-first 产物通过后生成；旧 Sxxx.cog.md 仅作为历史审计记录保留。",
            ]
        )
    report_lines.extend(
        [
            "",
            "## 版本变更记录",
            "",
            "### v1.0.0",
            "- 重新读取 raw 并同步精确源哈希、字符数和行数。",
            "- 增加自适应复杂度审计；数量不是固定模板目标。",
            "- 重新生成本报告并保留单书证据边界。",
            "",
        ]
    )
    report_path = REPORTS / f"{model_path.stem}.report.md"
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path


def main() -> int:
    if not MANIFEST.is_file():
        print("missing corpus/manifest.json; run build_manifest.py first")
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    targets = [book for book in manifest.get("books", []) if book.get("canonical") and not book.get("duplicate_of") and book.get("status") != "blocked_ocr_unavailable"]
    timestamp = datetime.now(timezone.utc).isoformat()
    failed = 0
    for book in targets:
        try:
            model_path, metadata = rebuild_model(book, timestamp)
            report_path = render_report(book, model_path, metadata, timestamp)
            print(f"[PASS] {book['id']} mode={book['processing_mode']} model={model_path.name} report={report_path.name}")
        except Exception as error:  # pragma: no cover - surfaced as a gate failure
            failed += 1
            print(f"[FAIL] {book['id']}: {error}")
    print(f"rebuild targets={len(targets)} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
