#!/usr/bin/env python3
"""Update corpus-status.md from manifest + model/report presence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus" / "manifest.json"
OUT = ROOT / "generated" / "reports" / "corpus-status.md"


def main() -> None:
    # refresh manifest first if possible
    import subprocess

    subprocess.run(["python3", str(ROOT / "scripts" / "build_manifest.py")], check=False)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    books = data["books"]

    def count(pred):
        return sum(1 for b in books if pred(b))

    lines = [
        "# Corpus Processing Status",
        "",
        f"> 生成时间: {datetime.now(timezone.utc).isoformat()}",
        f"> Manifest: `corpus/manifest.json`",
        "",
        "## 汇总",
        "",
        f"| 指标 | 数量 |",
        f"|---|---:|",
        f"| 总书数 | {data['book_count']} |",
        f"| Canonical（非 blocked） | {data['canonical_count']} |",
        f"| Duplicate | {data['duplicate_count']} |",
        f"| Blocked | {data['blocked_count']} |",
        f"| Complete (model+report) | {data['complete_count']} |",
        f"| Pending | {count(lambda b: b['status']=='pending')} |",
        f"| Modeled only | {count(lambda b: b['status']=='modeled')} |",
        f"| Direct mode | {count(lambda b: b.get('processing_mode')=='direct')} |",
        f"| Hierarchical mode | {count(lambda b: b.get('processing_mode')=='hierarchical')} |",
        "",
        "## 逐书状态",
        "",
        "| ID | Title | Status | Mode | Chars | Model | Report | Notes |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for b in books:
        notes = "; ".join(b.get("notes") or [])[:80]
        lines.append(
            f"| {b['id']} | {b['title']} | {b['status']} | {b['processing_mode']} | "
            f"{b['characters']} | {'Y' if b.get('book_model') else '-'} | "
            f"{'Y' if b.get('report') else '-'} | {notes} |"
        )
    lines.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
