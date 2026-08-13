#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证单书认知模型的结构、证据和自适应复杂度。

最低数量只是质量下限，不是每本书的目标模板。复杂度结论必须来自模型
中的 ``Adaptive Complexity Audit`` 以及全库 ID 数量签名审计；缺少审计时
只能是 untested，不能向下游发放 synthesis eligibility。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "generated" / "book-models"
RESULT = ROOT / "evals" / "results" / "book-model-validation.json"

REQUIRED_SECTIONS = [
    "Metadata",
    "核心问题",
    "核心论证结构",
    "世界模型",
    "核心概念",
    "主要判断",
    "因果模型",
    "思考方式",
    "判断规则",
    "隐含前提",
    "重要变量",
    "边界条件",
    "内部张力",
    "失败模式",
    "可迁移原则",
    "思考习惯",
    "跨书连接",
    "Analyst Cautions",
    "Coverage Report",
    "Adaptive Complexity Audit",
]

SECTION_ALIASES = {
    "边界条件": ("边界条件", "Boundary Conditions"),
    "跨书连接": ("跨书连接", "Future Connections"),
}

ID_PATTERNS = {
    "C": re.compile(r"\bC\d{3}\b"),
    "CL": re.compile(r"\bCL\d{3}\b"),
    "CM": re.compile(r"\bCM\d{3}\b"),
    "RP": re.compile(r"\bRP\d{3}\b"),
    "H": re.compile(r"\bH\d{3}\b"),
    "A": re.compile(r"\bA\d{3}\b"),
    "V": re.compile(r"\bV\d{3}\b"),
    "B": re.compile(r"\bB\d{3}\b"),
    "T": re.compile(r"\bT\d{3}\b"),
    "AP": re.compile(r"\bAP\d{3}\b"),
    "P": re.compile(r"\bP\d{3}\b"),
    "I": re.compile(r"\bI\d{3}\b"),
}

MINIMUMS = {"C": 3, "CL": 3, "CM": 2, "H": 2, "P": 3}
ITEM_RE = re.compile(
    r"^###\s+((?:C|CL|CM|RP|H|A|V|B|T|AP|P|I)\d{3})\s+(.+)$", re.M
)
EVIDENCE_RE = re.compile(
    r"(?:Evidence|证据|source:|corpus/raw/|\[\d{3}:L\d+|lines?\s*\d+)", re.I
)
STATUS_RE = re.compile(
    r"(?:Audit status|审计结论|complexity_status)\s*[:：]\s*`?\s*(passed|warning|failed|untested)",
    re.I,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_book_id(path: Path) -> str:
    match = re.match(r"(\d{3})-", path.name)
    return match.group(1) if match else path.stem


def parse_items(text: str) -> list[dict]:
    matches = list(ITEM_RE.finditer(text))
    items: list[dict] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start() : end]
        items.append(
            {
                "id": match.group(1),
                "title": match.group(2).strip(),
                "evidence_hits": len(EVIDENCE_RE.findall(body)),
                "has_evidence": bool(EVIDENCE_RE.search(body)),
            }
        )
    return items


def source_metadata(path: Path, text: str) -> dict:
    source_match = re.search(r"^- Source:\s*(.+)$", text, re.M)
    source = source_match.group(1).strip() if source_match else None
    if not source:
        return {"source": None, "source_exists": False}
    source_path = ROOT / source
    if not source_path.is_file():
        return {"source": source, "source_exists": False}
    source_text = source_path.read_text(encoding="utf-8", errors="replace")
    declared_chars = re.search(r"^- Source characters:\s*([\d,]+)", text, re.M)
    declared_lines = re.search(r"^- Source lines:\s*([\d,]+)", text, re.M)
    declared_sha = re.search(r"^- Source SHA-256:\s*([0-9a-f]{64})", text, re.M | re.I)
    actual = {
        "characters": len(source_text),
        "lines": len(source_text.splitlines()),
        "sha256": sha256_file(source_path),
    }
    actual["declared_match"] = bool(
        declared_chars
        and declared_lines
        and declared_sha
        and int(declared_chars.group(1).replace(",", "")) == actual["characters"]
        and int(declared_lines.group(1).replace(",", "")) == actual["lines"]
        and declared_sha.group(1).lower() == actual["sha256"]
    )
    return {"source": source, "source_exists": True, "actual": actual}


def adaptive_audit(text: str, counts: dict[str, int], evidence_items: list[dict]) -> dict:
    audit_present = "Adaptive Complexity Audit" in text
    status_match = STATUS_RE.search(text)
    status = status_match.group(1).lower() if status_match else "untested"
    signature = ";".join(f"{key}={counts[key]}" for key in ("C", "CL", "CM", "H", "P"))
    required_terms = [
        "information_density",
        "redundancy",
        "importance_threshold",
        "coverage",
    ]
    missing_terms = [term for term in required_terms if term not in text]
    # 每个主要判断、因果模型和原则都必须在自己的条目中带证据。
    evidence_gaps = [
        item["id"]
        for item in evidence_items
        if item["id"].startswith(("CL", "CM", "P")) and not item["has_evidence"]
    ]
    floors_ok = all(counts[key] >= value for key, value in MINIMUMS.items())
    if not audit_present or missing_terms or status == "untested":
        derived_status = "untested"
    elif status not in {"passed", "warning", "failed"}:
        derived_status = "untested"
    elif status == "failed" or evidence_gaps:
        derived_status = "failed"
    elif status == "warning":
        derived_status = "warning"
    else:
        derived_status = "passed"
    return {
        "status": derived_status,
        "declared_status": status,
        "present": audit_present,
        "missing_fields": missing_terms,
        "evidence_gaps": evidence_gaps,
        "minimum_floors_ok": floors_ok,
        "complexity_signature": signature,
        "information_density_declared": bool(re.search(r"information_density\s*[:：]", text)),
        "redundancy_merge_declared": bool(re.search(r"redundancy\s*[:：]", text)),
        "importance_threshold_declared": bool(re.search(r"importance_threshold\s*[:：]", text)),
        "coverage_declared": bool(re.search(r"coverage\s*[:：]", text, re.I)),
    }


def validate(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [
        section
        for section in REQUIRED_SECTIONS
        if not any(alias in text for alias in SECTION_ALIASES.get(section, (section,)))
    ]
    counts = {key: len(set(pattern.findall(text))) for key, pattern in ID_PATTERNS.items()}
    items = parse_items(text)
    evidence_hits = len(EVIDENCE_RE.findall(text))
    summaryish = len(re.findall(r"作者首先|作者随后|本章主要|这一章讲述", text))
    metadata = source_metadata(path, text)
    audit = adaptive_audit(text, counts, items)
    floors_ok = all(counts[key] >= value for key, value in MINIMUMS.items())
    structure_ok = not missing and evidence_hits >= 5 and summaryish < 8
    source_ok = metadata.get("source_exists", False) and metadata.get("actual", {}).get("declared_match", False)
    # source_ok 在旧模型中可能暂时为 False，但它会被 source-consistency
    # 单独报告；新的 rebuild 必须修复它，这里把它纳入 fail-closed 质量门。
    ok = floors_ok and structure_ok and source_ok and audit["status"] == "passed"
    return {
        "book_id": parse_book_id(path),
        "path": str(path.relative_to(ROOT)),
        "ok": ok,
        "missing_sections": missing,
        "id_counts": counts,
        "minimums": MINIMUMS,
        "evidence_hits": evidence_hits,
        "summaryish_hits": summaryish,
        "characters": len(text),
        "items": items,
        "source_metadata": metadata,
        "adaptive_complexity": audit,
    }


def run(paths: list[Path]) -> tuple[dict, int]:
    results: list[dict] = []
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        if not path.is_file() or path.name.startswith("."):
            continue
        results.append(validate(path))

    signature_counts: dict[str, int] = {}
    for result in results:
        signature = result["adaptive_complexity"]["complexity_signature"]
        signature_counts[signature] = signature_counts.get(signature, 0) + 1
    total = len(results)
    repeated = {
        signature: count
        for signature, count in sorted(signature_counts.items())
        if count > 1
    }
    max_count = max(signature_counts.values(), default=0)
    max_share = max_count / total if total else 0.0
    # 这是风险阈值，不是“出现一次重复就失败”。它能抓住模板化集中，
    # 同时允许不同信息密度的书在合理范围内共享最低数量签名。
    template_risk = bool(total and (max_share > 0.35 or len(signature_counts) == 1))
    if template_risk:
        global_complexity_status = "warning"
    elif any(r["adaptive_complexity"]["status"] == "failed" for r in results):
        global_complexity_status = "failed"
    elif any(r["adaptive_complexity"]["status"] == "untested" for r in results):
        global_complexity_status = "untested"
    elif any(r["adaptive_complexity"]["status"] == "warning" for r in results):
        global_complexity_status = "warning"
    else:
        global_complexity_status = "passed"
    all_ok = bool(results) and all(r["ok"] for r in results) and not template_risk
    payload = {
        "schema_version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "minimum_floor_policy": MINIMUMS,
        "adaptive_complexity_status": global_complexity_status,
        "template_signature_risk": template_risk,
        "signature_counts": signature_counts,
        "repeated_signatures": repeated,
        "max_signature_share": round(max_share, 6),
        "all_ok": all_ok,
        "items": results,
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = sum(1 for result in results if not result["ok"])
    if template_risk:
        failures += 1
    return payload, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", help="model paths; default all top-level book models")
    args = parser.parse_args()
    paths = [Path(path) for path in args.paths] if args.paths else sorted(MODELS.glob("*.md"))
    payload, failures = run(paths)
    for result in payload["items"]:
        status = "PASS" if result["ok"] else "FAIL"
        counts = result["id_counts"]
        print(
            f"{status}\t{result['path']}\t"
            f"C={counts['C']} CL={counts['CL']} CM={counts['CM']} H={counts['H']} P={counts['P']}\t"
            f"complexity={result['adaptive_complexity']['status']}"
        )
    print(
        f"adaptive_complexity={payload['adaptive_complexity_status']} "
        f"signatures={len(payload['signature_counts'])} "
        f"template_risk={payload['template_signature_risk']} "
        f"failures={failures}/{len(payload['items'])}"
    )
    print(f"wrote {RESULT.relative_to(ROOT)}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
