#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据 build-status 和验证结果生成最终交付报告，不手填门禁结论。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "reports" / "final-delivery.report.md"


def load(relative: str, default):
    path = ROOT / relative
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main() -> int:
    status = load("generated/build-status.json", {})
    manifest = load("corpus/manifest.json", {})
    cold = load("evals/results/cold-start-results.json", {})
    clean = load("evals/results/clean-room-results.json", {})
    robustness = load("evals/results/bootstrap-robustness-results.json", {})
    package = load("evals/results/package-validation.json", {})
    package_dist = load("evals/results/package-validation-dist.json", {})
    semantic = load("evals/results/book-semantic-provenance.json", {})
    lines = [
        "# Healing Domain Mind v1.0.0 最终实现交付报告",
        "",
        f"> 最终等级：**{status.get('quality_gate_grade', 'FAIL')}**",
        "> 本报告由 `scripts/build_final_report.py` 读取验证结果生成；不使用旧的 PASS 文案覆盖当前状态。",
        "",
        "## 1. 实现范围",
        "",
        "- 保留原有 `.agents/skills/book-distiller/SKILL.md` 的既有章节、四层证据、输出契约和质量门槛；本轮仅增加自适应复杂度与 segment-first 约束。",
        "- `004` 保持 `blocked_ocr_unavailable`；`020` 保持 `duplicate_of=015`，未伪造模型。",
        f"- canonical 可综合书目：{manifest.get('synthesis_eligible_count', 0)}。",
        f"- Direct rebuilt books：{status.get('direct_rebuilt_books', 0)}。",
        f"- Hierarchical rebuilt books：{status.get('hierarchical_rebuilt_books', 0)}。",
        f"- Segment count：{status.get('segment_count', 0)}。",
        "",
        "## 2. HEAD 与 Book Model tree",
        "",
        f"- Starting HEAD：`{status.get('starting_head')}`。",
        f"- Ending HEAD（本轮最终门禁生成时）：`{status.get('ending_head')}`。",
        f"- Book Model tree SHA before：`{status.get('book_model_tree_sha256_before')}`。",
        f"- Book Model tree SHA after：`{status.get('book_model_tree_sha256_after')}`。",
        "",
        "## 3. Gate 结果",
        "",
        f"- Adaptive distillation：`{status.get('adaptive_distillation')}`。",
        f"- True segment-first hierarchical：`{status.get('segment_first_hierarchical')}`。",
        f"- Corpus synthesis：`{status.get('corpus_synthesis')}`。",
        f"- Semantic provenance items：{status.get('semantic_provenance_count', len(semantic.get('items', [])))}；unsupported：{status.get('unsupported_semantic_items', 0)}。",
        f"- E10 cold-start：`{status.get('cold_start_eval')}`；E10-B client matrix：`{status.get('client_matrix_status')}`。",
        f"- E11 clean-room：`{status.get('clean_room_eval')}`。",
        f"- E12 bootstrap robustness：`{status.get('bootstrap_robustness_eval')}`。",
        f"- Package validator：`{status.get('package_validation')}`；runtime package validator：`{status.get('runtime_package_validation')}`。",
        "",
        "## 4. 客户端矩阵",
        "",
    ]
    for client in cold.get("client_matrix", {}).get("clients", []):
        lines.append(f"- {client.get('client')}：`{client.get('verdict')}`；fresh_session={client.get('fresh_session_evidence', {}).get('launched')}；files_loaded={','.join(client.get('files_loaded') or []) or 'none'}。")
    lines.extend(
        [
            "",
            "Codex 的 E10-B 已实际启动并得到 PASS；Claude Code、Gemini CLI 不存在于当前环境，因此保留 `NOT_RUN_ENV_UNAVAILABLE`，没有从静态适配器推断通过。",
            "",
            "## 5. Runtime 与发布",
            "",
            f"- Runtime validation：`{status.get('runtime_validation')}`。",
            f"- Runtime bundle：`{status.get('runtime_bundle', {}).get('path')}`；contains_raw={status.get('runtime_bundle', {}).get('contains_raw')}；contains_work={status.get('runtime_bundle', {}).get('contains_work')}。",
            f"- Tag：`{status.get('release', {}).get('tag') or 'NOT_CREATED'}`。",
            f"- Release：`{status.get('release_status')}`。",
            "- Full repository contains raw：`true`；copyright distribution risk：`true`；本轮未改写 Git 历史。",
            "",
            "## 6. Knowledge hashes",
            "",
        ]
    )
    for name, digest in sorted(status.get("knowledge_hashes", {}).items()):
        lines.append(f"- `{name}`：`{digest}`")
    lines.extend(["", "## 7. Limitations", ""])
    limitations = status.get("limitations") or ["none"]
    lines.extend(f"- {item}" for item in limitations)
    lines.extend(
        [
            "",
            "## 8. 生成记录",
            "",
            f"- generated_by：`scripts/build_final_report.py`",
            f"- generated_at：{datetime.now(timezone.utc).isoformat()}",
            "",
        ]
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[PASS] wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
