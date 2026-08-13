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

import os
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

    # 1. Copy core root docs & bootstrap adapters
    for fname in ("README.md", "LICENSE", "NOTICE.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        src = ROOT / fname
        if src.exists():
            shutil.copy2(src, DIST_DIR / fname)
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
        print("[COPY] knowledge/")

    # 5. Copy generated/book-models/*.md (EXCLUDE .work/)
    bm_src = ROOT / "generated" / "book-models"
    bm_dst = DIST_DIR / "generated" / "book-models"
    bm_dst.mkdir(parents=True, exist_ok=True)
    if bm_src.exists():
        for f in bm_src.glob("*.md"):
            shutil.copy2(f, bm_dst / f.name)
        print("[COPY] generated/book-models/*.md (canonical models, .work excluded)")

    # 6. Copy examples/
    ex_src = ROOT / "examples"
    ex_dst = DIST_DIR / "examples"
    if ex_src.exists():
        copy_tree(ex_src, ex_dst)
        print("[COPY] examples/")

    # 7. Zip release bundle
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(DIST_DIR):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(DIST_ROOT)
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
