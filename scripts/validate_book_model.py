#!/usr/bin/env python3
"""Structural validation for Book Cognitive Model markdown files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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
]

ID_PATTERNS = {
    "C": re.compile(r"\bC\d{3}\b"),
    "CL": re.compile(r"\bCL\d{3}\b"),
    "CM": re.compile(r"\bCM\d{3}\b"),
    "H": re.compile(r"\bH\d{3}\b"),
    "P": re.compile(r"\bP\d{3}\b"),
}

EVIDENCE_HINT = re.compile(r"(Evidence|evidence|lines?\s*\d+|corpus/raw/)", re.I)


def validate(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    counts = {k: len(set(p.findall(text))) for k, p in ID_PATTERNS.items()}
    evidence_hits = len(EVIDENCE_HINT.findall(text))
    summaryish = len(re.findall(r"作者首先|作者随后|本章主要|这一章讲述", text))
    ok = (
        not missing
        and counts["C"] >= 3
        and counts["CL"] >= 3
        and counts["CM"] >= 2
        and counts["H"] >= 2
        and counts["P"] >= 3
        and evidence_hits >= 5
        and summaryish < 8
    )
    return {
        "path": str(path.relative_to(ROOT)),
        "ok": ok,
        "missing_sections": missing,
        "id_counts": counts,
        "evidence_hits": evidence_hits,
        "summaryish_hits": summaryish,
        "characters": len(text),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="model md paths; default all in generated/book-models")
    args = ap.parse_args()
    paths = [Path(p) for p in args.paths] if args.paths else sorted((ROOT / "generated" / "book-models").glob("*.md"))
    results = []
    fail = 0
    for p in paths:
        if not p.exists() or p.name.startswith("."):
            continue
        r = validate(p if p.is_absolute() else ROOT / p)
        results.append(r)
        status = "PASS" if r["ok"] else "FAIL"
        if not r["ok"]:
            fail += 1
        print(f"{status}\t{r['path']}\tC={r['id_counts']['C']} CL={r['id_counts']['CL']} CM={r['id_counts']['CM']} P={r['id_counts']['P']} miss={len(r['missing_sections'])}")
    out = ROOT / "evals" / "results" / "book-model-validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}; fail={fail}/{len(results)}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
