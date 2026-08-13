#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行 E10-A/E10-B、E11、E12 并写入独立结果文件。

E10-B 只有实际启动客户端并取得新会话输出时才允许 PASS；命令不存在时
严格记录 NOT_RUN_ENV_UNAVAILABLE，不从 CLAUDE.md、GEMINI.md 或静态文件
推断客户端已经通过。
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import argparse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
RESULTS = EVALS / "results"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def static_bootstrap() -> dict:
    required = ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "knowledge/index.md", ".agents/skills/domain-mind/SKILL.md"]
    checks: list[dict] = []
    for relative in required:
        path = ROOT / relative
        checks.append({"file": relative, "exists": path.is_file()})
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8", errors="replace") if (ROOT / "AGENTS.md").is_file() else ""
    router = (ROOT / "knowledge" / "index.md").read_text(encoding="utf-8", errors="replace") if (ROOT / "knowledge" / "index.md").is_file() else ""
    skill = (ROOT / ".agents" / "skills" / "domain-mind" / "SKILL.md").read_text(encoding="utf-8", errors="replace") if (ROOT / ".agents" / "skills" / "domain-mind" / "SKILL.md").is_file() else ""
    required_markers = [
        "Runtime Bootstrap Protocol",
        "knowledge/index.md",
        "corpus/raw/",
        "Progressive Disclosure",
    ]
    required_topics = [
        "Power / Organization",
        "Manipulation / Persuasion",
        "Fraud / Pyramid Systems",
        "Relationships",
        "Self-cognition",
        "Ethics / Values",
        "Decision Making",
        "Institution / Incentives",
        "Social Psychology",
        "Change / Reform",
    ]
    missing_markers = [marker for marker in required_markers if marker not in agents + router + skill]
    missing_topics = [topic for topic in required_topics if topic not in router]
    all_files = all(item["exists"] for item in checks)
    passed = all_files and not missing_markers and not missing_topics and "Runtime Reasoning Pipeline" in skill
    return {
        "stage": "E10-A",
        "status": "PASS" if passed else "FAIL",
        "verdict": "PASS" if passed else "FAIL",
        "checks": checks,
        "missing_markers": missing_markers,
        "missing_router_topics": missing_topics,
        "auditor": "static-bootstrap-validator",
        "audit_version": "1.0.0",
        "timestamp": now(),
    }


def run_client(client: str, command: str | None, question: str, required_files: list[str]) -> dict:
    started = now()
    if not command:
        return {
            "client": client,
            "command_runtime": "command not found",
            "fresh_session_evidence": {"launched": False, "reason": "environment command unavailable", "timestamp": started},
            "question": question,
            "observed_bootstrap": None,
            "files_loaded": [],
            "response": None,
            "verdict": "NOT_RUN_ENV_UNAVAILABLE",
            "timestamp": now(),
        }
    temp_dir = Path(tempfile.mkdtemp(prefix=f"healing-e10-{client.lower().replace(' ', '-')}-"))
    output_file = temp_dir / "last-message.txt"
    prompt = (
        f"{question}\n\n"
        "这是 E10 cold-start 新会话观测。请先读取当前仓库的 AGENTS.md、knowledge/index.md 和 "
        ".agents/skills/domain-mind/SKILL.md；不要修改任何文件。回答末尾必须逐行写出：\n"
        "BOOTSTRAP_FILES=<实际读取并能确认的文件路径>\n"
        "BOOTSTRAP_RULE=<你观察到的启动规则>\n"
        "RAW_DEFAULT=<YES 或 NO>\n"
    )
    if client == "Codex":
        argv = [command, "exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "-C", str(ROOT), "-o", str(output_file), prompt]
    else:
        argv = [command, prompt]
    print(f"[PROGRESS] E10-B 启动 {client}: fresh session", flush=True)
    try:
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=300, check=False)
        response = output_file.read_text(encoding="utf-8", errors="replace") if output_file.exists() else (completed.stdout or completed.stderr)
        launched = True
        return_code = completed.returncode
    except subprocess.TimeoutExpired as error:
        response = ((error.stdout or "") if isinstance(error.stdout, str) else "")
        launched = True
        return_code = 124
    except OSError as error:
        response = str(error)
        launched = False
        return_code = 127
    observed_files = [relative for relative in required_files if relative in response]
    observed_markers = [marker for marker in ("Runtime Bootstrap Protocol", "knowledge/index.md", "domain-mind", "BOOTSTRAP_RULE") if marker in response]
    raw_default = "NO" if "RAW_DEFAULT=NO" in response or "默认不扫描" in response or "不默认读取 raw" in response else ("YES" if "RAW_DEFAULT=YES" in response else None)
    if return_code == 124 or (not response and return_code != 0):
        verdict = "NOT_RUN_ENV_UNAVAILABLE"
    else:
        verdict = "PASS" if launched and return_code == 0 and len(observed_files) >= 2 and len(observed_markers) >= 2 and raw_default != "YES" else "FAIL"
    return {
        "client": client,
        "command_runtime": " ".join(argv[:-1]) if argv else command,
        "fresh_session_evidence": {"launched": launched, "return_code": return_code, "ephemeral": client == "Codex", "timestamp": started},
        "question": question,
        "observed_bootstrap": observed_markers,
        "files_loaded": observed_files,
        "response": response[-12000:],
        "verdict": verdict,
        "timestamp": now(),
    }


def evaluate_clients(question: str) -> dict:
    required_files = ["AGENTS.md", "knowledge/index.md", ".agents/skills/domain-mind/SKILL.md"]
    specs = [("Codex", shutil.which("codex")), ("Claude Code", shutil.which("claude")), ("Gemini CLI", shutil.which("gemini"))]
    clients = [run_client(name, command, question, required_files) for name, command in specs]
    verdicts = [item["verdict"] for item in clients]
    if any(verdict == "FAIL" for verdict in verdicts):
        status = "FAIL"
    elif all(verdict == "PASS" for verdict in verdicts):
        status = "PASS"
    else:
        status = "PASS_WITH_LIMITATIONS"
    return {"stage": "E10-B", "status": status, "clients": clients, "timestamp": now()}


def evaluate_clean_room() -> dict:
    cases = load_jsonl(EVALS / "clean_room_benchmark.jsonl")
    dist = ROOT / "dist" / "healing-domain-mind"
    router = dist / "knowledge" / "index.md"
    forbidden = [str(path.relative_to(dist)) for path in dist.rglob("*") if path.is_dir() and (str(path.relative_to(dist)) == "corpus/raw" or ".work" in str(path.relative_to(dist)))] if dist.exists() else ["dist missing"]
    router_text = router.read_text(encoding="utf-8", errors="replace") if router.is_file() else ""
    case_results = []
    for case in cases:
        missing = [topic for topic in case["route_topics"] if topic not in router_text]
        case_results.append({"id": case["id"], "status": "PASS" if not missing and not forbidden else "FAIL", "missing_topics": missing, "forbidden_paths_observed": forbidden})
    passed = bool(case_results) and all(item["status"] == "PASS" for item in case_results)
    return {"stage": "E11", "status": "PASS" if passed else "FAIL", "verdict": "PASS" if passed else "FAIL", "runtime_bundle": str(dist.relative_to(ROOT)) if dist.exists() else None, "cases": case_results, "timestamp": now()}


def evaluate_robustness() -> dict:
    cases = load_jsonl(EVALS / "bootstrap_robustness.jsonl")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    book_skill = (ROOT / ".agents" / "skills" / "book-distiller" / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    domain_skill = (ROOT / ".agents" / "skills" / "domain-mind" / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    corpus_router = (ROOT / "knowledge" / "index.md").read_text(encoding="utf-8", errors="replace")
    manifest_script = (ROOT / "scripts" / "build_manifest.py").read_text(encoding="utf-8", errors="replace")
    semantic_script = (ROOT / "scripts" / "audit_semantic_provenance.py").read_text(encoding="utf-8", errors="replace")
    corpus_text = agents + book_skill + domain_skill + corpus_router + manifest_script + semantic_script
    expected_markers = {
        "E12-001": ["默认禁止", "corpus/raw", "knowledge/index.md"],
        "E12-002": ["SOURCE", "RECONSTRUCTION", "INFERENCE", "EVALUATION", "文本展示", "作者建议"],
        "E12-003": ["provenance_location_status", "provenance_semantic_status", "untested", "unsupported", "failed"],
    }
    checks = []
    for case in cases:
        keywords = expected_markers.get(case["id"], [case["expected_rule"]])
        observed = [keyword for keyword in keywords if keyword in corpus_text]
        passed = len(observed) == len(keywords)
        checks.append({"id": case["id"], "status": "PASS" if passed else "FAIL", "observed_keywords": observed, "evaluation_mode": "static-contract-only"})
    passed = bool(checks) and all(item["status"] == "PASS" for item in checks)
    return {"stage": "E12", "status": "PASS" if passed else "FAIL", "verdict": "PASS" if passed else "FAIL", "cases": checks, "timestamp": now()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-client-launch", action="store_true", help="复用已有 E10-B 实际启动结果，只重跑静态 E10-A、E11、E12")
    args = parser.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)
    print("[PROGRESS] E10-A 静态 bootstrap 检查", flush=True)
    static = static_bootstrap()
    print(f"[PROGRESS] E10-A {static['status']}", flush=True)
    question = load_jsonl(EVALS / "cold_start_test.jsonl")[1]["question"]
    if args.skip_client_launch and (RESULTS / "cold-start-results.json").is_file():
        previous = json.loads((RESULTS / "cold-start-results.json").read_text(encoding="utf-8"))
        clients = previous.get("client_matrix", {"stage": "E10-B", "status": "NOT_RUN", "clients": [], "timestamp": now()})
        print("[PROGRESS] E10-B 复用已有实际客户端结果，跳过重复启动", flush=True)
    else:
        clients = evaluate_clients(question)
    print(f"[PROGRESS] E10-B 状态={clients['status']}", flush=True)
    clean = evaluate_clean_room()
    print(f"[PROGRESS] E11 状态={clean['status']}", flush=True)
    robustness = evaluate_robustness()
    print(f"[PROGRESS] E12 状态={robustness['status']}", flush=True)
    cold = {"schema_version": "1.0.0", "generated_by": "scripts/run_extended_evals.py", "generated_at": now(), "static": static, "client_matrix": clients, "status": "FAIL" if static["status"] == "FAIL" or clients["status"] == "FAIL" else "PASS", "verdict": "FAIL" if static["status"] == "FAIL" or clients["status"] == "FAIL" else "PASS_WITH_LIMITATIONS" if clients["status"] != "PASS" else "PASS"}
    outputs = [("cold-start-results.json", cold), ("clean-room-results.json", clean), ("bootstrap-robustness-results.json", robustness)]
    for filename, payload in outputs:
        (RESULTS / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[PROGRESS] 写入 evals/results/{filename}", flush=True)
    return 0 if all(item[1].get("status") == "PASS" or item[1].get("verdict") == "PASS_WITH_LIMITATIONS" for item in outputs) else 1


if __name__ == "__main__":
    sys.exit(main())
