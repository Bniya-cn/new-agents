#!/usr/bin/env python3
"""Validate that Evidence line ranges exist in the referenced raw source."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINE_RANGE = re.compile(
    r"(?:source:\s*)?(corpus/raw/[^\s,]+\.md)?[^\n]{0,80}?lines?\s*[:=]?\s*(\d+)(?:\s*[-–—]\s*(\d+))?",
    re.I,
)


def check_model(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    # Prefer explicit source in metadata
    src_m = re.search(r"Source:\s*(corpus/raw/[^\s]+)", text)
    default_src = src_m.group(1) if src_m else None
    issues = []
    checked = 0
    cache: dict[str, list[str]] = {}

    for m in LINE_RANGE.finditer(text):
        src = m.group(1) or default_src
        if not src:
            continue
        a = int(m.group(2))
        b = int(m.group(3) or m.group(2))
        checked += 1
        p = ROOT / src
        if not p.exists():
            issues.append({"lines": f"{a}-{b}", "error": f"missing source {src}"})
            continue
        if src not in cache:
            cache[src] = p.read_text(encoding="utf-8", errors="replace").splitlines()
        lines = cache[src]
        if a < 1 or b > len(lines) or a > b:
            issues.append({"lines": f"{a}-{b}", "error": f"out of range (file has {len(lines)} lines)", "source": src})
    return {
        "path": str(path.relative_to(ROOT)),
        "checked": checked,
        "issues": issues,
        "ok": checked > 0 and len(issues) == 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()
    paths = [Path(p) for p in args.paths] if args.paths else sorted((ROOT / "generated" / "book-models").glob("*.md"))
    results = []
    fail = 0
    for p in paths:
        r = check_model(p if p.is_absolute() else ROOT / p)
        results.append(r)
        if not r["ok"]:
            fail += 1
        print(f"{'PASS' if r['ok'] else 'FAIL'}\t{r['path']}\tchecked={r['checked']}\tissues={len(r['issues'])}")
    out = ROOT / "evals" / "results" / "provenance-validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
