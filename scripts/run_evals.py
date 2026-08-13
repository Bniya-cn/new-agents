#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
healing-agents evaluation runner (deterministic + audit-trail gates).

IMPORTANT:
- Does NOT overwrite evals/semantic_eval_cases.md by default.
- To rebuild the human-readable report, use:
    python3 scripts/render_semantic_eval_report.py
- Optional empty template generation requires --init-template --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_deterministic_validators() -> bool:
    print("=== 1. Deterministic Validators ===")
    errors: list[str] = []
    os.chdir(ROOT)

    core_files = [
        "corpus/manifest.json",
        "generated/reports/corpus-status.md",
        "knowledge/index.md",
        "knowledge/principles.md",
        "knowledge/cognitive-model.md",
        "knowledge/corpus-synthesis.report.md",
        "evals/rubric.md",
    ]
    for f in core_files:
        if Path(f).exists():
            print(f"[PASS] core file: {f}")
        else:
            errors.append(f"missing core file: {f}")

    prov_pattern = re.compile(r"\[\d{3}:L\d+\]")
    for doc in [
        "knowledge/index.md",
        "knowledge/principles.md",
        "knowledge/cognitive-model.md",
        "knowledge/corpus-synthesis.report.md",
    ]:
        if not Path(doc).exists():
            continue
        content = Path(doc).read_text(encoding="utf-8")
        matches = prov_pattern.findall(content)
        if matches:
            print(f"[PASS] {doc} provenance refs={len(matches)} sample={matches[0]}")
        else:
            errors.append(f"{doc} missing provenance refs")

    validation_files = [
        "evals/results/book-model-validation.json",
        "evals/results/provenance-validation.json",
        "evals/results/source-consistency.json",
        "evals/results/semantic-eval-results.json",
    ]
    for vf in validation_files:
        if Path(vf).exists():
            print(f"[PASS] result file: {vf}")
        else:
            errors.append(f"missing result file: {vf}")

    # Source consistency exactness
    sc_path = Path("evals/results/source-consistency.json")
    if sc_path.exists():
        sc = json.loads(sc_path.read_text(encoding="utf-8"))
        if isinstance(sc, list):
            errors.append(
                "source-consistency.json is legacy list format; re-run "
                "scripts/validate_source_consistency.py for full audit object"
            )
        else:
            if sc.get("match_policy") != "exact_hash_chars_lines":
                errors.append("source-consistency match_policy must be exact_hash_chars_lines")
            if sc.get("tolerance", 1) != 0:
                errors.append("source-consistency tolerance must be 0")
            items = sc.get("items") or []
            if not sc.get("all_ok", False) or any(not x.get("ok") for x in items):
                errors.append("source-consistency has failing items")
            else:
                # require model_meta present
                if items and "model_meta" not in items[0]:
                    errors.append("source-consistency items missing model_meta")
                else:
                    print(f"[PASS] source-consistency exact OK ({len(items)} books)")

    # Semantic audit trail
    sem_file = Path("evals/results/semantic-eval-results.json")
    if sem_file.exists():
        sem = json.loads(sem_file.read_text(encoding="utf-8"))
        items = sem.get("items", [])
        total = sem.get("total_questions_evaluated", 0)
        if len(items) != 45 or total != 45:
            errors.append(f"semantic items mismatch: len={len(items)} total={total}")
        else:
            adv = sum(1 for x in items if x.get("is_adversarial"))
            missing_fields = 0
            for it in items:
                for k in ("domain_mind_response", "baseline_response", "attribution_response"):
                    if not it.get(k) or "[待评测" in str(it.get(k)):
                        missing_fields += 1
                judge = it.get("judge") or {}
                for k in ("model", "prompt_version", "rationale", "provenance_check_result"):
                    if k not in judge:
                        missing_fields += 1
            if missing_fields:
                errors.append(f"semantic audit trail incomplete missing_fields={missing_fields}")
            else:
                print(f"[PASS] semantic audit trail complete (45 items, adv={adv})")

    # Fail-closed gates in manifest
    if Path("corpus/manifest.json").exists():
        manifest = json.loads(Path("corpus/manifest.json").read_text(encoding="utf-8"))
        complete_count = manifest.get("complete_count", 0)
        actual_models = len([x for x in os.listdir("generated/book-models") if x.endswith(".md")])
        print(f"[PASS] manifest.complete_count={complete_count} models={actual_models}")
        if complete_count != actual_models:
            errors.append(
                f"manifest.complete_count={complete_count} != models={actual_models}"
            )
        for b in manifest.get("books", []):
            if b.get("status") == "complete":
                if b.get("provenance_status") not in (None, "passed"):
                    # allow missing field on older manifests, but if present must be passed
                    if b.get("provenance_status") != "passed":
                        errors.append(
                            f"book {b.get('id')} provenance_status={b.get('provenance_status')}"
                        )
                if b.get("accepted_partial") and b.get("synthesis_eligible"):
                    errors.append(
                        f"fail-open leak: book {b.get('id')} accepted_partial && synthesis_eligible"
                    )

    # Hierarchical synthesis manifests for known large books
    for bid in ("013", "015"):
        syn = Path(f"generated/book-models/.work/{bid}/synthesis_manifest.json")
        if syn.exists():
            print(f"[PASS] hierarchical synthesis manifest: {syn}")
        else:
            errors.append(f"missing hierarchical synthesis manifest: {syn}")

    if errors:
        print("\nDeterministic validation FAILED:")
        for err in errors:
            print(f"- [ERROR] {err}")
        return False

    print("\nDeterministic validation ALL PASS\n")
    return True


def init_template(force: bool = False) -> None:
    """Dangerous helper: writes empty placeholders. Requires --force."""
    output_template = Path("evals/semantic_eval_cases.TEMPLATE.md")
    if not force:
        print("[REFUSE] refusing to write empty template without --force")
        print("Hint: use scripts/render_semantic_eval_report.py to refresh the real report.")
        return

    cases = []
    for path in ("evals/questions.jsonl", "evals/adversarial.jsonl"):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    item = json.loads(line)
                    if "adversarial" in path:
                        item["is_adversarial"] = True
                    cases.append(item)

    with output_template.open("w", encoding="utf-8") as fh:
        fh.write("# EMPTY TEMPLATE — do not treat as completed eval\n\n")
        for idx, case in enumerate(cases):
            fh.write(f"### {case.get('id')}\n")
            fh.write(f"- scenario: {case.get('scenario') or case.get('question')}\n")
            fh.write("- Domain Mind: [待评测回答内容]\n\n")
    print(f"[PASS] wrote empty template to {output_template} (not semantic_eval_cases.md)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--init-template",
        action="store_true",
        help="write EMPTY template to semantic_eval_cases.TEMPLATE.md (requires --force)",
    )
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--render-report",
        action="store_true",
        help="also render semantic_eval_cases.md from results JSON",
    )
    args = ap.parse_args()

    ok = run_deterministic_validators()

    if args.init_template:
        init_template(force=args.force)

    if args.render_report:
        from subprocess import run

        rc = run([sys.executable, str(ROOT / "scripts" / "render_semantic_eval_report.py")]).returncode
        if rc != 0:
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
