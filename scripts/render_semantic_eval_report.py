#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render evals/semantic_eval_cases.md FROM semantic-eval-results.json.

Never invent empty placeholders. If results lack audit fields, fail.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results" / "semantic-eval-results.json"
OUT = ROOT / "evals" / "semantic_eval_cases.md"

REQUIRED = (
    "domain_mind_response",
    "baseline_response",
    "attribution_response",
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not RESULTS.exists():
        print(f"[ERROR] missing {RESULTS}")
        return 1

    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if len(items) != 45:
        print(f"[ERROR] expected 45 items, got {len(items)}")
        return 1

    errors = []
    for it in items:
        for k in REQUIRED:
            if not it.get(k):
                errors.append(f"{it.get('id')}: missing {k}")
        judge = it.get("judge") or {}
        for k in ("model", "prompt_version", "rationale", "provenance_check_result"):
            if k not in judge:
                errors.append(f"{it.get('id')}: missing judge.{k}")
    if errors:
        print("[ERROR] audit trail incomplete:")
        for e in errors[:20]:
            print(" -", e)
        return 1

    summary = data.get("summary", {})
    dm = summary.get("domain_mind_averages", {})
    bl = summary.get("baseline_averages", {})

    lines = [
        "# Domain Mind 语义评估报告（可审计全文）",
        "",
        f"> 生成方式: 由 `scripts/render_semantic_eval_report.py` 从 `{RESULTS.relative_to(ROOT)}` 渲染",
        f"> 评测时间: {data.get('eval_date')}",
        f"> 条目数: {len(items)}（必须含回答正文、Baseline、Judge rationale）",
        f"> 评分政策: Attribution 按需（见 attribution_response）；默认回答禁止强制证据链倾销",
        "",
        "## 1. 评分标准",
        "",
        "- **Bookless (0-5)**: 默认回答不靠书名/作者撑场面，却能体现本语料特有机制。",
        "- **Attribution (0-5)**: 按需来源回答是否可回溯到原则/模型/行号，且无伪造。",
        "- **Logic (0-5)**: 机制、边界、可执行动作是否闭环。",
        "",
        "## 2. 汇总",
        "",
        f"| 维度 | Domain Mind | Baseline |",
        f"|---|---:|---:|",
        f"| Bookless | {dm.get('bookless')} | {bl.get('bookless')} |",
        f"| Attribution | {dm.get('attribution')} | {bl.get('attribution')} |",
        f"| Logic | {dm.get('logic')} | {bl.get('logic')} |",
        "",
        f"Verdict: **{summary.get('verdict')}** / E9: **{summary.get('e9_corpus_distinctiveness_test')}**",
        "",
        "## 3. 逐题全文",
        "",
    ]

    for it in items:
        tag = "对抗" if it.get("is_adversarial") else "普通"
        ds = it["domain_mind_score"]
        bs = it["baseline_score"]
        judge = it["judge"]
        lines.extend(
            [
                f"### {it['id']} [{it.get('domain')}] ({tag})",
                "",
                f"- **场景**: {it.get('scenario')}",
                f"- **Rubric**: {it.get('rubric')}",
                "",
                "#### Domain Mind 实际回答",
                "",
                it["domain_mind_response"].rstrip(),
                "",
                "#### Baseline 实际回答",
                "",
                it["baseline_response"].rstrip(),
                "",
                "#### 按需来源回答（Attribution）",
                "",
                it["attribution_response"].rstrip(),
                "",
                "#### Score Sheet",
                "",
                f"- Domain Mind: Bookless {ds['bookless']} / Attribution {ds['attribution']} / Logic {ds['logic']}",
                f"- Baseline: Bookless {bs['bookless']} / Attribution {bs['attribution']} / Logic {bs['logic']}",
                f"- Judge model: `{judge['model']}` / prompt: `{judge['prompt_version']}`",
                f"- Judge rationale: {judge['rationale']}",
                f"- Provenance check: `{json.dumps(judge['provenance_check_result'], ensure_ascii=False)}`",
                f"- Verdict: **{it.get('verdict')}**",
                "",
                "---",
                "",
            ]
        )

    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out.relative_to(ROOT) if args.out.is_absolute() else args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
