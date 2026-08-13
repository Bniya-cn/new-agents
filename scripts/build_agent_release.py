#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_agent_release.py

Release Builder for Healing Domain Mind (v1.0.0).
Compiles the clean Runtime Distribution Package under dist/healing-domain-mind/
and creates a zipped bundle dist/healing-domain-mind-v1.0.0.zip.

Safety Rules:
- Excludes copyrighted corpus/raw/
- Excludes internal .work/ directory
- Excludes internal scripts and evals results
- Rewrites agent-manifest.yaml for evidence_mode=model_only
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = ROOT / "dist"
DIST_DIR = DIST_ROOT / "healing-domain-mind"
ZIP_PATH = DIST_ROOT / "healing-domain-mind-v1.0.0.zip"


def create_runtime_manifest(target_file: Path) -> None:
    manifest_content = """name: healing-domain-mind
version: 1.0.0
type: cognitive-agent

entrypoint:
  instructions: AGENTS.md
  claude_instructions: CLAUDE.md
  gemini_instructions: GEMINI.md
  runtime_skill: .agents/skills/domain-mind/SKILL.md
  knowledge_router: knowledge/index.md

runtime:
  default_mode: domain-mind
  progressive_disclosure: true
  provenance_on_demand: true
  evidence_mode: model_only
  raw_available: false
  raw_access_default: false

knowledge:
  primary:
    - knowledge/index.md
    - knowledge/cognitive-model.md
    - knowledge/principles.md
    - knowledge/causal-models.md
    - knowledge/tensions.md
    - knowledge/boundaries.md
    - knowledge/worldview.md
    - knowledge/ontology.md
    - knowledge/concepts.md
    - knowledge/mental-models.md
    - knowledge/decision-framework.md
    - knowledge/problem-solving.md
    - knowledge/thinking-habits.md
    - knowledge/anti-patterns.md

  fallback:
    - generated/book-models/

loading_policy:
  level_1: knowledge
  level_2: book_models

drill_down_when:
  - explicit_source_request
  - unresolved_tension
  - low_confidence
  - boundary_case
  - exact_attribution_required
"""
    target_file.write_text(manifest_content, encoding="utf-8")


def create_runtime_readme(target_file: Path) -> None:
    """写入面向外部用户的 Runtime README，不暴露 Refinery 目录与命令。"""
    readme = """# Healing Domain Mind

Portable Cognitive Agent Repository

Healing Domain Mind 是一个由多源知识炼化而成的可移植认知 Agent 仓库。它不是书籍 RAG 搜索器，也不是摘要拼盘，而是使用机制、变量、张力和边界来分析新的现实问题。

## Quick Start

```bash
git clone https://github.com/Bniya-cn/healing-domain-mind.git
cd healing-domain-mind
```

用 Codex、Cursor、Claude Code 或 Gemini CLI 打开仓库，开启新会话后直接提问即可。无需额外输入 `use domain-mind` 或其他启动 Prompt。

例如：

> 一个核心员工能力越来越强，影响力开始超过直属领导，我应该怎么看？

Agent 会自动执行：

`Repository Bootstrap → 问题分类 → Knowledge Router → 机制化判断`

## Runtime 行为

- 默认先读取 `knowledge/index.md`，再按问题加载相关知识节点。
- 默认输出问题本质、核心机制、关键变量、张力与边界、可执行判断和不确定度。
- 不默认扫描原始书库，不默认输出书名、作者或物理行号。
- 只有用户明确追问依据、来源或证据时，才下钻到结构化单书模型与来源元数据。

## 仓库结构

```text
healing-domain-mind/
├── AGENTS.md
├── CLAUDE.md
├── GEMINI.md
├── agent-manifest.yaml
├── .agents/skills/domain-mind/SKILL.md
├── knowledge/
│   ├── index.md
│   ├── principles.md
│   ├── mental-models.md
│   ├── causal-models.md
│   ├── tensions.md
│   ├── boundaries.md
│   └── ...
├── generated/book-models/
└── examples/
```

## 证据边界

这是 `evidence_mode: model_only` 的 Runtime Distribution。原始第三方书籍全文没有随本仓库提供；来源追溯路径为 `knowledge → book model → source metadata`。不得在发行包模式下伪造原文、引文或行号。

## 许可

工程结构和运行时知识架构遵循 [Apache-2.0](LICENSE)。第三方原始资料不随 Runtime Distribution 提供，详见 [NOTICE.md](NOTICE.md)。
"""
    target_file.write_text(readme, encoding="utf-8")


def create_runtime_agents(target_file: Path) -> None:
    """写入只面向 Runtime 的冷启动协议，避免暴露 Refinery 路径。"""
    agents = """# AGENTS.md — Healing Domain Mind Runtime Bootstrap

## Runtime Bootstrap Protocol

当用户提出涉及 decision、organization、relationship、power、incentive、persuasion、conflict、social behavior、risk、self-cognition 或 strategy 的现实问题时，必须默认启动 Runtime Path：

1. 读取 `.agents/skills/domain-mind/SKILL.md`。
2. 读取 `knowledge/index.md` Router。
3. 只加载与当前问题相关的 principles、causal models、tensions 和 boundaries。
4. 形成机制化判断，不退化为逐书摘要或全文搜索。

## 默认行为

- 默认模式为 `domain-mind`，遵循 `agent-manifest.yaml` 的 progressive disclosure 规则。
- 默认不访问发行包未提供的原始全文，不伪造原文、引文或物理行号。
- 默认不输出书名、作者或出处堆砌；只有用户明确追问依据、来源或证据时，才下钻到结构化单书模型与来源元数据。
- 普通回答优先说明问题本质、核心机制、关键变量、张力与边界、可执行判断和不确定度。

## Runtime 内容边界

- `knowledge/` 是 Level 1 领域知识与 Router。
- `generated/book-models/` 是 Level 2 单书结构化认知模型与来源元数据。
- `.agents/skills/domain-mind/SKILL.md` 是 Runtime 推理控制器。
- `examples/` 是使用示例，不是额外的系统指令。

本发行包为 `evidence_mode: model_only`。原始第三方书籍全文没有随包提供；如果用户要求原始全文，必须明确说明这一限制。
"""
    target_file.write_text(agents, encoding="utf-8")


def sanitize_runtime_text(text: str) -> str:
    """移除 Runtime 中不可访问的 Refinery 路径，同时保留来源元数据语义。"""
    text = re.sub(
        r"generated/book-models/\.work/[^\s`，。；;]+",
        "runtime segment metadata (not shipped)",
        text,
    )
    text = re.sub(
        r"corpus/raw/([^\s`，。；;]+)",
        r"source metadata (original full text not included): \1",
        text,
    )
    text = text.replace("corpus/raw", "unavailable original source corpus")
    text = text.replace("corpus/raw/", "original source metadata/")
    text = text.replace("scripts/", "refinery tooling/")
    text = text.replace("evals/", "internal evaluation data/")
    text = text.replace("dist/healing-domain-mind/", "runtime distribution/")
    return text


def sanitize_runtime_tree(root: Path) -> None:
    """对复制进 Runtime 的文本资料做路径边界清理。"""
    text_suffixes = {".md", ".json", ".yaml", ".yml", ".txt"}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        original = path.read_text(encoding="utf-8")
        sanitized = sanitize_runtime_text(original)
        if sanitized != original:
            path.write_text(sanitized, encoding="utf-8")


def refresh_runtime_source_map(source_map_file: Path, runtime_root: Path) -> None:
    """让 Runtime source-map 的模型哈希对应脱敏后的发行模型。"""
    if not source_map_file.exists():
        return
    payload = json.loads(source_map_file.read_text(encoding="utf-8"))
    for record in payload.get("books", {}).values():
        model_ref = record.get("model")
        if not model_ref:
            continue
        model_file = runtime_root / model_ref
        if model_file.exists():
            record["model_sha256"] = hashlib.sha256(model_file.read_bytes()).hexdigest()
    source_map_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_tree(src: Path, dst: Path, ignore_patterns: tuple[str, ...] = ()) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name.startswith(".") or item.name in ignore_patterns:
            continue
        if item.is_dir():
            copy_tree(item, dst / item.name, ignore_patterns)
        else:
            shutil.copy2(item, dst / item.name)


def main() -> int:
    print("=== Building Healing Domain Mind Release Bundle ===")

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Write productized Runtime README and Runtime bootstrap adapter.
    create_runtime_readme(DIST_DIR / "README.md")
    print("[CREATE] README.md (Runtime product documentation)")
    create_runtime_agents(DIST_DIR / "AGENTS.md")
    print("[CREATE] AGENTS.md (Runtime bootstrap protocol)")
    for fname in ("LICENSE", "NOTICE.md", "CLAUDE.md", "GEMINI.md"):
        src = ROOT / fname
        if src.exists():
            content = src.read_text(encoding="utf-8")
            if fname == "LICENSE":
                content = sanitize_runtime_text(content)
            (DIST_DIR / fname).write_text(content, encoding="utf-8")
            print(f"[COPY] {fname}")
        else:
            print(f"[WARN] Optional root file {fname} not found")

    # 2. Write runtime agent-manifest.yaml
    create_runtime_manifest(DIST_DIR / "agent-manifest.yaml")
    print("[CREATE] Runtime agent-manifest.yaml (evidence_mode=model_only)")

    # 3. Copy .agents/skills/domain-mind/
    skill_src = ROOT / ".agents" / "skills" / "domain-mind"
    skill_dst = DIST_DIR / ".agents" / "skills" / "domain-mind"
    if skill_src.exists():
        copy_tree(skill_src, skill_dst)
        print("[COPY] .agents/skills/domain-mind/")

    # 4. Copy knowledge/
    k_src = ROOT / "knowledge"
    k_dst = DIST_DIR / "knowledge"
    if k_src.exists():
        copy_tree(k_src, k_dst)
        sanitize_runtime_tree(k_dst)
        print("[COPY] knowledge/")

    # 5. Copy generated/book-models/*.md (EXCLUDE .work/)
    bm_src = ROOT / "generated" / "book-models"
    bm_dst = DIST_DIR / "generated" / "book-models"
    bm_dst.mkdir(parents=True, exist_ok=True)
    if bm_src.exists():
        for f in bm_src.glob("*.md"):
            content = sanitize_runtime_text(f.read_text(encoding="utf-8"))
            (bm_dst / f.name).write_text(content, encoding="utf-8")
        print("[COPY] generated/book-models/*.md (canonical models, .work excluded)")

    refresh_runtime_source_map(k_dst / "source-map.json", DIST_DIR)
    print("[UPDATE] knowledge/source-map.json (Runtime model hashes)")

    # 6. Copy examples/
    ex_src = ROOT / "examples"
    ex_dst = DIST_DIR / "examples"
    if ex_src.exists():
        copy_tree(ex_src, ex_dst)
        sanitize_runtime_tree(ex_dst)
        print("[COPY] examples/")

    # 7. Zip release bundle
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(DIST_DIR):
            for file in files:
                abs_path = Path(root) / file
                # Release ZIP 与 Public Runtime 仓库根目录一一对应，不再增加外层目录。
                rel_path = abs_path.relative_to(DIST_DIR)
                zf.write(abs_path, rel_path)

    print(f"\n[RELEASE ZIP] Created {ZIP_PATH.relative_to(ROOT)} ({ZIP_PATH.stat().st_size / 1024 / 1024:.2f} MB)")

    # 8. Validate release package
    from subprocess import run

    rc = run([sys.executable, str(ROOT / "scripts" / "validate_agent_package.py"), "--check-dist"]).returncode
    if rc != 0:
        print("[ERROR] Release package validation FAILED!")
        return 1

    print("\nRelease Build & Validation Successful!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
