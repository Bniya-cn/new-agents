#!/usr/bin/env python3
"""审计 corpus/raw/ 书库，生成 corpus-audit.md。

只读取，不修改任何原始文件。
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "corpus" / "raw"
OUTPUT = ROOT / "corpus-audit.md"

# 常见乱码 / OCR 噪声字符
GARBLED_PATTERN = re.compile(r"[\u0080-\u009f\u200b-\u200f\ufeff\ufff0-\uffff]")
PRIVATE_USE_PATTERN = re.compile(r"[\uE000-\uF8FF]")
REPLACEMENT_CHAR = "\ufffd"

# 疑似目录页特征：短行多、章节关键词多、正文占比低
TOC_KEYWORDS = re.compile(r"^(目录|contents|第[一二三四五六七八九十百]+[章节篇部]|chapter\s+\d+)", re.I)


@dataclass
class FileReport:
    name: str
    size_bytes: int
    char_count: int
    line_count: int
    heading_count: int
    h1_count: int
    page_sep_count: int
    garbled_ratio: float
    empty: bool
    warnings: list[str] = field(default_factory=list)


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def content_fingerprint(text: str) -> str:
    """用于检测内容高度相似（去空白后哈希）。"""
    normalized = re.sub(r"\s+", "", text[:50000])
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def detect_garbled_ratio(text: str) -> float:
    if not text:
        return 0.0
    bad = 0
    for ch in text:
        if ch == REPLACEMENT_CHAR:
            bad += 1
        elif GARBLED_PATTERN.match(ch) or PRIVATE_USE_PATTERN.match(ch):
            bad += 1
    return bad / len(text)


def analyze_headings(text: str) -> tuple[int, int]:
    h_total = 0
    h1 = 0
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+", line)
        if m:
            h_total += 1
            if len(m.group(1)) == 1:
                h1 += 1
    return h_total, h1


def estimate_toc_only(text: str) -> bool:
    """启发式：前 200 行几乎全是短行 + 目录关键词，且全文很短。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 5:
        return len(text.strip()) < 200
    head = lines[: min(200, len(lines))]
    short = sum(1 for ln in head if len(ln) < 40)
    toc_like = sum(1 for ln in head if TOC_KEYWORDS.match(ln))
    avg_len = sum(len(ln) for ln in head) / max(len(head), 1)
    # 全文极短或前几页像目录且无长段落
    if len(text) < 3000 and toc_like >= 3:
        return True
    if short / len(head) > 0.85 and avg_len < 25 and toc_like >= 2:
        return True
    return False


def longest_section_chars(text: str) -> int:
    sections = re.split(r"\n---\n", text)
    return max((len(s) for s in sections), default=0)


def audit_file(path: Path) -> FileReport:
    raw = path.read_bytes()
    size = len(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")

    char_count = len(text)
    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    h_total, h1 = analyze_headings(text)
    page_sep = text.count("\n---\n") + (1 if text.strip().startswith("---") else 0)
    garbled = detect_garbled_ratio(text)
    empty = char_count == 0 or not text.strip()

    report = FileReport(
        name=path.name,
        size_bytes=size,
        char_count=char_count,
        line_count=line_count,
        heading_count=h_total,
        h1_count=h1,
        page_sep_count=page_sep,
        garbled_ratio=garbled,
        empty=empty,
    )

    if empty:
        report.warnings.append("空文件或几乎无内容")
    if garbled > 0.01:
        report.warnings.append(f"疑似乱码比例较高 ({garbled:.2%})")
    if char_count < 500 and not empty:
        report.warnings.append("文件过短，可能不完整")
    if h_total == 0 and char_count > 5000:
        report.warnings.append("无 Markdown 标题结构（可能为纯 OCR 分页文本）")
    if estimate_toc_only(text):
        report.warnings.append("疑似仅含目录/封面，正文不足")
    longest = longest_section_chars(text)
    if longest > 500_000:
        report.warnings.append(f"存在异常超长章节/分页块 ({longest:,} 字符)")

    return report


def find_duplicates(files: list[Path]) -> dict[str, list[str]]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    by_fp: dict[str, list[str]] = defaultdict(list)
    for f in files:
        by_hash[file_hash(f)].append(f.name)
        text = f.read_text(encoding="utf-8", errors="replace")
        by_fp[content_fingerprint(text)].append(f.name)

    dups: dict[str, list[str]] = {}
    for label, groups in [("完全相同", by_hash), ("内容高度相似", by_fp)]:
        for key, names in groups.items():
            if len(names) > 1:
                dups[f"{label}: {', '.join(names)}"] = names
    return dups


def find_version_groups(files: list[Path]) -> list[tuple[str, list[str]]]:
    """检测同一书名多个版本（文件名主体相似）。"""
    groups: dict[str, list[str]] = defaultdict(list)
    for f in files:
        base = re.sub(r"^\d{3}-", "", f.stem)
        # 去掉常见后缀变体
        key = re.sub(r"[-_（(].*", "", base)
        groups[key].append(f.name)
    return [(k, v) for k, v in groups.items() if len(v) > 1]


def render_markdown(reports: list[FileReport], dups: dict[str, list[str]], version_groups: list[tuple[str, list[str]]]) -> str:
    total_chars = sum(r.char_count for r in reports)
    total_size = sum(r.size_bytes for r in reports)
    anomaly = [r for r in reports if r.warnings]

    lines = [
        "# Corpus Audit Report",
        "",
        f"> 生成时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"> 审计目录: `corpus/raw/`",
        "",
        "## 1. 当前书库规模",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| Books | {len(reports)} |",
        f"| Total size | {total_size / 1024 / 1024:.2f} MB |",
        f"| Total characters | {total_chars:,} |",
        f"| Avg characters/book | {total_chars // max(len(reports), 1):,} |",
        "",
        "## 2. 文件列表",
        "",
        "| # | 文件 | 大小 | 字符数 | 行数 | 标题数 | 分页符 |",
        "|---|------|------|--------|------|--------|--------|",
    ]

    for i, r in enumerate(reports, 1):
        lines.append(
            f"| {i} | `{r.name}` | {r.size_bytes/1024:.1f} KB | {r.char_count:,} | {r.line_count:,} | {r.heading_count} | {r.page_sep_count} |"
        )

    lines.extend(["", "## 3. 异常文件", ""])
    if not anomaly and not dups and not version_groups:
        lines.append("未发现明显异常。")
    else:
        for r in anomaly:
            lines.append(f"### WARNING: `{r.name}`")
            lines.append("")
            for w in r.warnings:
                lines.append(f"- {w}")
            lines.append("")

        if dups:
            lines.append("### 重复文件")
            lines.append("")
            for desc, names in dups.items():
                lines.append(f"- **{desc}**")
            lines.append("")

        if version_groups:
            lines.append("### 同一书籍多个版本")
            lines.append("")
            for key, names in version_groups:
                lines.append(f"- **{key}**: {', '.join(f'`{n}`' for n in names)}")
            lines.append("")

    preprocess: list[str] = []
    for r in reports:
        if r.garbled_ratio > 0.005:
            preprocess.append(f"- `{r.name}`: OCR 乱码需清洗")
        if r.heading_count == 0 and r.char_count > 5000:
            preprocess.append(f"- `{r.name}`: 建议添加或推断章节标题结构")
        if r.page_sep_count > 50 and r.heading_count < 5:
            preprocess.append(f"- `{r.name}`: OCR 分页符 `{r.page_sep_count}` 个，建议预处理分页")

    lines.extend(["## 4. 需要预处理的内容", ""])
    if preprocess:
        lines.extend(preprocess)
    else:
        lines.append("暂无需强制预处理项；可直接进入 book-distiller 试点。")

    # 判断是否可进入下一阶段
    blockers = [r for r in reports if r.empty or r.char_count < 500]
    high_garbled = [r for r in reports if r.garbled_ratio > 0.05]

    lines.extend(["", "## 5. 是否可以进入下一阶段 book-distiller", ""])
    if blockers:
        lines.append("**结论: 有条件可进入** — 以下文件需先处理：")
        for r in blockers:
            lines.append(f"- `{r.name}`")
    elif high_garbled:
        lines.append("**结论: 有条件可进入** — 部分文件乱码率偏高，建议先清洗 OCR 噪声后再批量炼化。")
    elif dups:
        lines.append("**结论: 有条件可进入** — 存在重复/多版本文件，炼化前需去重。")
    else:
        lines.append("**结论: 可以进入 book-distiller 试点阶段。**")
        lines.append("")
        lines.append("建议先从 1–2 本中等篇幅、结构清晰的书开始验证 Skill，再批量处理大书（如《新厚黑学全书》《资治通鉴》）。")

    return "\n".join(lines) + "\n"


def main() -> None:
    files = sorted(CORPUS_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"未找到 Markdown 文件: {CORPUS_DIR}")

    reports = [audit_file(f) for f in files]
    dups = find_duplicates(files)
    version_groups = find_version_groups(files)
    OUTPUT.write_text(render_markdown(reports, dups, version_groups), encoding="utf-8")
    print(f"审计完成: {len(files)} 本书 -> {OUTPUT}")


if __name__ == "__main__":
    main()
