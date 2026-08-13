#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_agent_package.py

Runtime Package & Contract Validator (v1.0.0).
Verifies:
- AGENTS.md, CLAUDE.md, GEMINI.md exist and are properly wired.
- agent-manifest.yaml is valid and correctly specifies evidence_mode.
- domain-mind SKILL and knowledge router (knowledge/index.md) are complete.
- All referenced knowledge nodes exist.
- No personal remote rules in .cursor/rules/.
- Distribution bundle contains no raw corpus, no .work, no broken references.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_bootstrap_files() -> list[str]:
    errors = []
    agents_md = ROOT / "AGENTS.md"
    claude_md = ROOT / "CLAUDE.md"
    gemini_md = ROOT / "GEMINI.md"

    if not agents_md.exists():
        errors.append("AGENTS.md missing in root")
    else:
        text = agents_md.read_text(encoding="utf-8")
        if "Runtime Bootstrap Protocol" not in text and "domain-mind" not in text:
            errors.append("AGENTS.md missing cold-start bootstrap instructions")

    if not claude_md.exists():
        errors.append("CLAUDE.md missing in root")
    else:
        text = claude_md.read_text(encoding="utf-8")
        if "AGENTS.md" not in text:
            errors.append("CLAUDE.md does not reference/import AGENTS.md")

    if not gemini_md.exists():
        errors.append("GEMINI.md missing in root")
    else:
        text = gemini_md.read_text(encoding="utf-8")
        if "AGENTS.md" not in text:
            errors.append("GEMINI.md does not reference/import AGENTS.md")

    return errors


def check_manifest(target_dir: Path, is_dist: bool = False) -> list[str]:
    errors = []
    manifest_path = target_dir / "agent-manifest.yaml"
    if not manifest_path.exists():
        errors.append(f"agent-manifest.yaml missing in {target_dir}")
        return errors

    content = manifest_path.read_text(encoding="utf-8")
    for key in ("name:", "version:", "entrypoint:", "runtime:", "knowledge:"):
        if key not in content:
            errors.append(f"agent-manifest.yaml missing required field: {key}")

    if is_dist:
        if "evidence_mode: model_only" not in content and "evidence_mode: \"model_only\"" not in content:
            errors.append("Runtime distribution agent-manifest.yaml must specify evidence_mode: model_only")
        if "corpus/raw/" in content:
            errors.append("Runtime distribution agent-manifest.yaml must not reference corpus/raw/")

    return errors


def check_router_and_skill() -> list[str]:
    errors = []
    skill = ROOT / ".agents" / "skills" / "domain-mind" / "SKILL.md"
    router = ROOT / "knowledge" / "index.md"

    if not skill.exists():
        errors.append(".agents/skills/domain-mind/SKILL.md missing")
    else:
        text = skill.read_text(encoding="utf-8")
        if "Runtime Reasoning Pipeline" not in text:
            errors.append("domain-mind SKILL.md missing runtime reasoning pipeline")

    if not router.exists():
        errors.append("knowledge/index.md missing")
    else:
        text = router.read_text(encoding="utf-8")
        required_topics = [
            "Power / Organization",
            "Manipulation / Persuasion",
            "Fraud / Pyramid",
            "Relationships",
            "Self-cognition",
            "Ethics / Values",
            "Decision Making",
            "Institution / Incentives",
            "Social Psychology",
            "Change / Reform",
        ]
        for topic in required_topics:
            if topic not in text:
                errors.append(f"knowledge/index.md missing router topic: {topic}")

    return errors


def check_knowledge_nodes() -> list[str]:
    errors = []
    required_nodes = [
        "knowledge/index.md",
        "knowledge/cognitive-model.md",
        "knowledge/principles.md",
        "knowledge/causal-models.md",
        "knowledge/worldview.md",
        "knowledge/ontology.md",
        "knowledge/concepts.md",
        "knowledge/mental-models.md",
        "knowledge/tensions.md",
        "knowledge/boundaries.md",
        "knowledge/decision-framework.md",
        "knowledge/problem-solving.md",
        "knowledge/thinking-habits.md",
        "knowledge/anti-patterns.md",
        "knowledge/source-map.json",
        "knowledge/id-migrations.json",
    ]
    for node in required_nodes:
        if not (ROOT / node).exists():
            errors.append(f"Referenced knowledge node missing: {node}")
    return errors


def check_personal_rules() -> list[str]:
    errors = []
    bad_rule = ROOT / ".cursor" / "rules" / "auto-sync-remotes.mdc"
    if bad_rule.exists():
        errors.append("Developer personal rule .cursor/rules/auto-sync-remotes.mdc still in public path (should be isolated to .dev/cursor/)")
    return errors


def check_dist_package(dist_dir: Path) -> list[str]:
    errors = []
    if not dist_dir.exists():
        return ["dist directory does not exist yet"]

    raw_in_dist = dist_dir / "corpus" / "raw"
    if raw_in_dist.exists():
        errors.append("dist/ package MUST NOT contain copyrighted corpus/raw/")

    work_in_dist = dist_dir / "generated" / "book-models" / ".work"
    if work_in_dist.exists():
        errors.append("dist/ package MUST NOT contain intermediate .work directory")

    for f in dist_dir.rglob("*.md"):
        text = f.read_text(encoding="utf-8", errors="replace")
        if "[待评测" in text or "[TODO: UNRESOLVED]" in text:
            errors.append(f"dist file {f.relative_to(dist_dir)} contains unresolved placeholders")

    allowed_source_notice_files = {"README.md", "NOTICE.md"}
    for f in dist_dir.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in {".md", ".json", ".yaml", ".yml", ".txt"}:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        relative = f.relative_to(dist_dir)
        if "corpus/raw" in text and f.name not in allowed_source_notice_files:
            errors.append(f"dist file {relative} exposes unavailable raw evidence path")
        if "generated/book-models/.work" in text:
            errors.append(f"dist file {relative} exposes unavailable .work path")
        if "/Users/" in text or "/Desktop/" in text:
            errors.append(f"dist file {relative} exposes a personal filesystem path")

    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-dist", action="store_true", help="also validate dist/ release package")
    args = ap.parse_args()

    print("=== Runtime Package & Contract Validation ===")
    all_errors = []

    errs = check_bootstrap_files()
    if errs:
        all_errors.extend(errs)
    else:
        print("[PASS] Cross-client bootstrap files (AGENTS.md, CLAUDE.md, GEMINI.md)")

    errs = check_manifest(ROOT, is_dist=False)
    if errs:
        all_errors.extend(errs)
    else:
        print("[PASS] Internal agent-manifest.yaml contract")

    errs = check_router_and_skill()
    if errs:
        all_errors.extend(errs)
    else:
        print("[PASS] domain-mind SKILL and 10-domain knowledge router")

    errs = check_knowledge_nodes()
    if errs:
        all_errors.extend(errs)
    else:
        print("[PASS] Core knowledge nodes exist")

    errs = check_personal_rules()
    if errs:
        all_errors.extend(errs)
    else:
        print("[PASS] Personal developer rules isolated")

    if args.check_dist:
        dist_dir = ROOT / "dist" / "healing-domain-mind"
        errs = check_dist_package(dist_dir)
        if errs:
            all_errors.extend(errs)
        else:
            print(f"[PASS] Distribution package clean ({dist_dir.relative_to(ROOT)})")

    result_name = "package-validation-dist.json" if args.check_dist else "package-validation.json"
    result_path = ROOT / "evals" / "results" / result_name
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0.0",
        "generated_by": "scripts/validate_agent_package.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "check_dist": args.check_dist,
        "status": "failed" if all_errors else "passed",
        "all_ok": not all_errors,
        "errors": all_errors,
    }
    result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[RESULT] wrote {result_path.relative_to(ROOT)}")

    if all_errors:
        print("\nPackage Validation FAILED:")
        for err in all_errors:
            print(f" - [ERROR] {err}")
        return 1

    print("\nPackage Validation ALL PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
