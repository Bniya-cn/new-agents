#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从真实 manifest、验证器结果、评估结果和发布状态生成 build-status.json。"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "generated" / "build-status.json"
BASELINE_PATH = ROOT / "generated" / "build-baseline.json"
MANIFEST_PATH = ROOT / "corpus" / "manifest.json"
RESULTS = ROOT / "evals" / "results"
DIST = ROOT / "dist" / "healing-domain-mind"
ZIP = ROOT / "dist" / "healing-domain-mind-v1.0.0.zip"

KNOWLEDGE_FILES = [
    "worldview.md",
    "ontology.md",
    "concepts.md",
    "principles.md",
    "mental-models.md",
    "causal-models.md",
    "tensions.md",
    "boundaries.md",
    "decision-framework.md",
    "problem-solving.md",
    "thinking-habits.md",
    "anti-patterns.md",
    "cognitive-model.md",
    "index.md",
    "corpus-synthesis.report.md",
    "source-map.json",
    "id-migrations.json",
]


def load(path: Path, default):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_sha256(directory: Path, pattern: str) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.glob(pattern)):
        digest.update(str(path.relative_to(directory)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def command(*args: str, timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, (result.stdout or result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)


def remote_github() -> str | None:
    code, value = command("git", "remote", "get-url", "github")
    if code != 0:
        return None
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?$", value)
    return match.group(1) if match else None


def release_observation() -> dict:
    tag_code, tag_output = command("git", "tag", "--list", "v1.0.0")
    local_tag = tag_code == 0 and "v1.0.0" in tag_output.splitlines()
    repo = remote_github()
    release_exists = False
    release_output = ""
    if repo:
        code, release_output = command("gh", "release", "view", "v1.0.0", "--repo", repo, "--json", "tagName,isDraft,url", timeout=15)
        release_exists = code == 0
    if release_exists:
        status = "RELEASED"
    elif local_tag and ZIP.is_file():
        status = "TAGGED_RUNTIME_BUILT_RELEASE_UI_NOT_CREATED"
    else:
        status = "NOT_RELEASED"
    return {
        "status": status,
        "tag": "v1.0.0" if local_tag else None,
        "local_tag_exists": local_tag,
        "github_repo": repo,
        "release_exists": release_exists,
        "release_observation": release_output[-2000:],
    }


def main() -> int:
    manifest = load(MANIFEST_PATH, {})
    model_result = load(RESULTS / "book-model-validation.json", {})
    source_result = load(RESULTS / "source-consistency.json", {})
    semantic_result = load(RESULTS / "book-semantic-provenance.json", {})
    location_result = load(RESULTS / "provenance-validation.json", [])
    segment_result = load(RESULTS / "segment-coverage.json", {})
    package_result = load(RESULTS / "package-validation.json", {})
    package_dist_result = load(RESULTS / "package-validation-dist.json", {})
    cold = load(RESULTS / "cold-start-results.json", {})
    clean = load(RESULTS / "clean-room-results.json", {})
    robustness = load(RESULTS / "bootstrap-robustness-results.json", {})
    baseline = load(BASELINE_PATH, {})

    books = manifest.get("books", [])
    canonical = [book for book in books if book.get("canonical") and book.get("duplicate_of") is None and book.get("status") != "blocked_ocr_unavailable"]
    hierarchical = [book for book in canonical if book.get("processing_mode") == "hierarchical"]
    direct = [book for book in canonical if book.get("processing_mode") == "direct"]
    unsupported_items = [item for item in semantic_result.get("items", []) if item.get("semantic_support") == "unsupported"]
    location_items = location_result if isinstance(location_result, list) else location_result.get("items", [])
    location_all_ok = bool(location_items) and all(item.get("ok") for item in location_items)
    adaptive_pass = bool(
        model_result.get("all_ok")
        and model_result.get("adaptive_complexity_status") == "passed"
        and source_result.get("all_ok")
        and location_all_ok
        and semantic_result.get("all_ok")
        and not unsupported_items
        and len(canonical) == manifest.get("synthesis_eligible_count")
        and all(book.get("complexity_status") == "passed" and book.get("provenance_semantic_status") == "passed" for book in canonical)
    )
    segment_pass = bool(
        segment_result.get("all_ok")
        and all(book.get("segment_coverage_status") == "complete" for book in hierarchical)
        and all(book.get("segment_coverage_status") == "n_a" for book in direct)
    )
    knowledge_missing = [name for name in KNOWLEDGE_FILES if not (ROOT / "knowledge" / name).is_file()]
    source_map = load(ROOT / "knowledge" / "source-map.json", {})
    synthesis_pass = bool(
        manifest.get("synthesis_eligible_count") == len(canonical) == 19
        and not knowledge_missing
        and source_map.get("input_book_count") == len(canonical)
    )
    package_pass = package_result.get("all_ok") is True
    runtime_pass = bool(package_dist_result.get("all_ok") is True and DIST.is_dir() and ZIP.is_file() and not (DIST / "corpus" / "raw").exists() and not (DIST / "generated" / "book-models" / ".work").exists())
    cold_pass = cold.get("status") == "PASS"
    clean_pass = clean.get("status") == "PASS"
    robustness_pass = robustness.get("status") == "PASS"
    client_matrix = cold.get("client_matrix", {})
    client_status = client_matrix.get("status", "NOT_RUN")
    release = release_observation()
    mandatory = {
        "adaptive_distillation": adaptive_pass,
        "segment_first_hierarchical": segment_pass,
        "corpus_synthesis": synthesis_pass,
        "runtime_validation": runtime_pass,
        "cold_start_eval": cold_pass,
        "clean_room_eval": clean_pass,
        "bootstrap_robustness": robustness_pass,
        "package_validation": package_pass,
    }
    missing_artifacts = []
    for relative in [
        "corpus/manifest.json",
        "evals/results/book-model-validation.json",
        "evals/results/book-semantic-provenance.json",
        "evals/results/segment-coverage.json",
        "evals/results/cold-start-results.json",
        "evals/results/clean-room-results.json",
        "evals/results/bootstrap-robustness-results.json",
    ]:
        if not (ROOT / relative).is_file():
            missing_artifacts.append(relative)
    core_pass = all(mandatory.values()) and not missing_artifacts and not knowledge_missing
    if not core_pass:
        grade = "FAIL"
    elif client_status == "PASS" and release["status"] == "RELEASED":
        grade = "APPROVED"
    else:
        grade = "PASS_WITH_LIMITATIONS"
    limitations = []
    if client_status != "PASS":
        limitations.append(f"E10-B client matrix={client_status}; 不能据静态文件推断未启动客户端通过")
    if release["status"] != "RELEASED":
        limitations.append(f"release_status={release['status']}")
    if source_map.get("full_repository_contains_raw", True):
        limitations.append("full repository contains corpus/raw; copyright distribution risk remains until repository visibility/content boundary changes")
    current_head_code, current_head = command("git", "rev-parse", "HEAD")
    status = {
        "agent_package_version": "1.0.0",
        "generated_by": "scripts/build_status.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "starting_head": baseline.get("starting_head"),
        "ending_head": current_head if current_head_code == 0 else None,
        "book_model_tree_sha256_before": baseline.get("book_model_tree_sha256_before"),
        "book_model_tree_sha256_after": tree_sha256(ROOT / "generated" / "book-models", "*.md"),
        "repository_bootstrap": "PASSED",
        "adaptive_distillation": "PASSED" if adaptive_pass else "FAIL",
        "segment_first_hierarchical": "PASSED" if segment_pass else "FAIL",
        "corpus_synthesis": "PASSED" if synthesis_pass else "FAIL",
        "runtime_validation": "PASSED" if runtime_pass else "FAIL",
        "cold_start_eval": "PASSED" if cold_pass else "FAIL",
        "clean_room_eval": "PASSED" if clean_pass else "FAIL",
        "bootstrap_robustness_eval": "PASSED" if robustness_pass else "FAIL",
        "live_semantic_eval": "NOT_RUN_SCOPE_SEPARATE" if not (ROOT / "evals" / "results" / "semantic-eval-results.json").is_file() else "PRESENT_LEGACY_RESULT_NOT_PART_OF_NEW_MANDATORY_GATES",
        "client_matrix_status": client_status,
        "package_validation": "PASSED" if package_pass else "FAIL",
        "runtime_package_validation": "PASSED" if package_dist_result.get("all_ok") is True else "FAIL",
        "release_status": release["status"],
        "quality_gate_grade": grade,
        "mandatory_gates": mandatory,
        "missing_artifacts": missing_artifacts + knowledge_missing,
        "unsupported_semantic_items": len(unsupported_items),
        "direct_rebuilt_books": len(direct),
        "hierarchical_rebuilt_books": len(hierarchical),
        "segment_count": sum(book.get("required_segment_count", 0) for book in segment_result.get("books", [])),
        "semantic_provenance_count": len(semantic_result.get("items", [])),
        "knowledge_hashes": {name: sha256(ROOT / "knowledge" / name) for name in KNOWLEDGE_FILES if (ROOT / "knowledge" / name).is_file()},
        "full_repository": {"contains_raw": (ROOT / "corpus" / "raw").is_dir(), "copyright_distribution_risk": True, "history_rewrite": False},
        "runtime_bundle": {"path": str(DIST.relative_to(ROOT)) if DIST.exists() else None, "contains_raw": (DIST / "corpus" / "raw").exists(), "contains_work": (DIST / "generated" / "book-models" / ".work").exists(), "zip": str(ZIP.relative_to(ROOT)) if ZIP.exists() else None},
        "release": release,
        "limitations": limitations,
        "_note": "Generated from validators and evaluation artifacts; do not hand-edit.",
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[PROGRESS] build-status generated: grade={grade} core_pass={core_pass}", flush=True)
    print(f"[PROGRESS] mandatory={mandatory}", flush=True)
    print(f"[PROGRESS] release={release['status']} client_matrix={client_status}", flush=True)
    print(f"[PASS] wrote {STATUS_PATH.relative_to(ROOT)}", flush=True)
    return 0 if grade != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
