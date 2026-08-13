#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Healing Domain Mind v1.0.0 全量 Gate 编排器。

顺序固定为：单书模型/位置/语义/源一致性 → manifest → 跨书重合成 →
运行时包 → E10/E11/E12 → unsupported PASS 检查 → build-status。
任何缺失结果或不支持的 PASS 都会使本次 Gate 失败。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evals" / "results"


def run_step(label: str, command: list[str]) -> int:
    print(f"\n[PROGRESS] START {label}: {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    print(f"[PROGRESS] END {label}: exit={result.returncode}", flush=True)
    return result.returncode


def read_json(relative: str, default):
    path = ROOT / relative
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def validate_artifacts() -> tuple[list[str], dict]:
    errors: list[str] = []
    manifest = read_json("corpus/manifest.json", {})
    model = read_json("evals/results/book-model-validation.json", {})
    source = read_json("evals/results/source-consistency.json", {})
    semantic = read_json("evals/results/book-semantic-provenance.json", {})
    segment = read_json("evals/results/segment-coverage.json", {})
    required_files = [
        "corpus/manifest.json",
        "evals/results/book-model-validation.json",
        "evals/results/provenance-validation.json",
        "evals/results/source-consistency.json",
        "evals/results/book-semantic-provenance.json",
        "evals/results/segment-coverage.json",
        "evals/results/cold-start-results.json",
        "evals/results/clean-room-results.json",
        "evals/results/bootstrap-robustness-results.json",
    ]
    missing = [path for path in required_files if not (ROOT / path).is_file()]
    errors.extend(f"missing result/artifact: {path}" for path in missing)
    books = manifest.get("books", [])
    canonical = [book for book in books if book.get("canonical") and book.get("duplicate_of") is None and book.get("status") != "blocked_ocr_unavailable"]
    if len(canonical) != 19 or manifest.get("synthesis_eligible_count") != 19:
        errors.append(f"manifest synthesis eligibility mismatch: canonical={len(canonical)} eligible={manifest.get('synthesis_eligible_count')}")
    if not model.get("all_ok") or model.get("adaptive_complexity_status") != "passed":
        errors.append("adaptive model validation is not passed")
    if not source.get("all_ok"):
        errors.append("source consistency is not passed")
    if not semantic.get("all_ok"):
        errors.append("semantic provenance is not passed")
    unsupported = [item for item in semantic.get("items", []) if item.get("semantic_support") == "unsupported"]
    if unsupported:
        errors.append(f"semantic unsupported items present: {len(unsupported)}")
    if not segment.get("all_ok"):
        errors.append("segment-first coverage is not complete")
    for book in canonical:
        if not book.get("synthesis_eligible"):
            errors.append(f"book {book.get('id')} is not synthesis eligible")
        if book.get("complexity_status") not in {"passed"}:
            errors.append(f"book {book.get('id')} complexity_status={book.get('complexity_status')}")
        if book.get("provenance_semantic_status") != "passed":
            errors.append(f"book {book.get('id')} provenance_semantic_status={book.get('provenance_semantic_status')}")
    # 不能存在“build-status 写 PASS，但结果/产物不存在”的 fail-open 情况。
    status = read_json("generated/build-status.json", {})
    pass_keys = [key for key, value in status.items() if key.endswith("_eval") or key.endswith("_validation") or key in {"adaptive_distillation", "segment_first_hierarchical", "corpus_synthesis", "runtime_validation"}]
    for key in pass_keys:
        if str(status.get(key, "")).upper() in {"PASS", "PASSED", "APPROVED"} and missing:
            errors.append(f"unsupported PASS: {key} is PASS while artifacts are missing")
    return errors, {"manifest": manifest, "model": model, "source": source, "semantic": semantic, "segment": segment, "missing": missing}


def write_summary(errors: list[str], details: dict, step_results: list[dict]) -> None:
    payload = {
        "schema_version": "2.0.0",
        "generated_by": "scripts/run_evals.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_ok": not errors,
        "errors": errors,
        "steps": step_results,
        "counts": {
            "canonical": sum(1 for book in details.get("manifest", {}).get("books", []) if book.get("canonical") and not book.get("duplicate_of") and book.get("status") != "blocked_ocr_unavailable"),
            "semantic_items": len(details.get("semantic", {}).get("items", [])),
            "segment_books": len(details.get("segment", {}).get("books", [])),
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "eval-summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[PROGRESS] 写入 evals/results/eval-summary.json all_ok={not errors}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-report", action="store_true", help="在 Gate 后刷新 semantic_eval_cases.md")
    parser.add_argument("--rerun-client", action="store_true", help="重新实际启动 E10-B 可用客户端；默认复用已有实际结果")
    args = parser.parse_args()
    steps: list[dict] = []

    commands = [
        ("book-model-validation", [sys.executable, "scripts/validate_book_model.py"]),
        ("provenance-location", [sys.executable, "scripts/validate_provenance.py"]),
        ("semantic-provenance", [sys.executable, "scripts/audit_semantic_provenance.py"]),
        ("source-consistency", [sys.executable, "scripts/validate_source_consistency.py"]),
        ("segment-first-coverage", [sys.executable, "scripts/validate_segment_coverage.py"]),
        ("manifest", [sys.executable, "scripts/build_manifest.py"]),
        ("corpus-synthesis", [sys.executable, "scripts/build_knowledge.py"]),
        ("package-contract", [sys.executable, "scripts/validate_agent_package.py"]),
        ("runtime-package", [sys.executable, "scripts/build_agent_release.py"]),
    ]
    for label, command in commands:
        code = run_step(label, command)
        steps.append({"label": label, "command": command, "exit_code": code, "status": "PASS" if code == 0 else "FAIL"})

    extended_command = [sys.executable, "scripts/run_extended_evals.py"]
    if not args.rerun_client and (RESULTS / "cold-start-results.json").is_file():
        extended_command.append("--skip-client-launch")
    code = run_step("E10-E12", extended_command)
    steps.append({"label": "E10-E12", "command": extended_command, "exit_code": code, "status": "PASS" if code == 0 else "FAIL"})

    artifact_errors, details = validate_artifacts()
    if artifact_errors:
        print("\n[FAIL] artifact/gate audit:", flush=True)
        for error in artifact_errors:
            print(f"  - {error}", flush=True)
    else:
        print("\n[PASS] artifact/gate audit: no missing or unsupported PASS", flush=True)

    status_code = run_step("build-status", [sys.executable, "scripts/build_status.py"])
    steps.append({"label": "build-status", "command": [sys.executable, "scripts/build_status.py"], "exit_code": status_code, "status": "PASS" if status_code == 0 else "FAIL"})
    write_summary(artifact_errors, details, steps)

    if args.render_report:
        render_code = run_step("semantic-report-render", [sys.executable, "scripts/render_semantic_eval_report.py"])
        if render_code != 0:
            artifact_errors.append("semantic report render failed")

    final_status = read_json("generated/build-status.json", {})
    grade = final_status.get("quality_gate_grade", "FAIL")
    print(f"\n[SUMMARY] quality_gate_grade={grade}; artifact_errors={len(artifact_errors)}; build_status_exit={status_code}", flush=True)
    return 0 if grade != "FAIL" and not artifact_errors else 1


if __name__ == "__main__":
    sys.exit(main())
