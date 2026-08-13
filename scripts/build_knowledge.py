#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 synthesis-eligible 单书模型重建跨书知识库。

这是 Stage E 的唯一生成入口。它不读取旧的 knowledge 节点来制造新的
结论；旧节点只用于 ID 迁移审计。所有跨书主张都保留支持书目、原始行号、
独立来源集群、机制、变量、边界、反证和信度字段。
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "corpus" / "manifest.json"
MODELS_DIR = ROOT / "generated" / "book-models"
KNOWLEDGE_DIR = ROOT / "knowledge"
REPORT_PATH = KNOWLEDGE_DIR / "corpus-synthesis.report.md"

ITEM_RE = re.compile(r"^###\s+((?:C|CL|CM|RP|H|A|V|B|T|AP|P|I)\d{3})\s+(.+)$", re.M)
SECTION_RE = re.compile(r"^##\s+(.+)$", re.M)
EVIDENCE_RE = re.compile(r"(?:lines?\s*[:=]?\s*([\d,]+)(?:\s*[-–—]\s*([\d,]+))?|\[(\d{3}):L(\d+)(?:-L?(\d+))?\])", re.I)
TOKEN_RE = re.compile(r"[一-龥]{2,}|[A-Za-z][A-Za-z0-9_-]{2,}")

MINIMUM_BOOKS = 2

BUCKETS = [
    {
        "id": "P101",
        "title": "事实质证与信息污染隔离",
        "keywords": ("证据", "质证", "底单", "事实", "信息", "忽悠", "假证", "中立", "判断"),
        "scope": "高风险信息、宣传、指控、专业背书和证据审查",
    },
    {
        "id": "P102",
        "title": "信任关系与社会信誉隔离",
        "keywords": ("信誉", "信任", "熟人", "社交", "关系", "朋友", "家庭", "网络", "信赖"),
        "scope": "熟人关系、合作、分销、社交裂变和信誉风险",
    },
    {
        "id": "P201",
        "title": "实权资源与名义位置分离",
        "keywords": ("实权", "虚衔", "架空", "权力", "资源", "控制", "御下", "骨干", "组织"),
        "scope": "权力重组、组织政治、资源控制和责任分配",
    },
    {
        "id": "P202",
        "title": "权力风险中的退路与边界保护",
        "keywords": ("退路", "避嫌", "退避", "自污", "离场", "撤退", "保全", "功劳", "猜忌"),
        "scope": "高压关系、权力不对称、功劳风险和个人安全",
    },
    {
        "id": "P203",
        "title": "反馈通道与执行纠偏",
        "keywords": ("反馈", "纠偏", "异议", "改革", "变法", "执行", "制度", "规则", "反对"),
        "scope": "制度变革、组织执行、政策试错和长期治理",
    },
    {
        "id": "P301",
        "title": "行动验证与知行闭环",
        "keywords": ("行动", "实践", "知行", "工作", "学习", "努力", "执行", "磨炼", "实操"),
        "scope": "学习、工作、项目启动和能力成长",
    },
    {
        "id": "P302",
        "title": "逆境中的心智重构与持续行动",
        "keywords": ("逆境", "心性", "感恩", "达观", "情绪", "内省", "修养", "苦难", "自救"),
        "scope": "挫折、损失、边缘化和无法立即改变的困境",
    },
    {
        "id": "P303",
        "title": "道德判断与长期责任约束",
        "keywords": ("利他", "道德", "良知", "善", "责任", "正确", "诚信", "义", "敬天"),
        "scope": "义利选择、长期信任、组织责任和伦理边界",
    },
    {
        "id": "P401",
        "title": "规模增长的物理边界与崩盘风险",
        "keywords": ("倍增", "规模", "极限", "崩盘", "资金", "负债", "人口", "饱和", "庞氏", "风险"),
        "scope": "裂变、资金盘、快速增长、市场容量和系统性风险",
    },
    {
        "id": "P402",
        "title": "高光阶段的止损与退场纪律",
        "keywords": ("止损", "断仓", "退场", "撤退", "虚荣", "扩张", "浮盈", "保本", "离场"),
        "scope": "异常成功、投资、创业扩张和风险暴露后的退出",
    },
    {
        "id": "P403",
        "title": "群体压力下的独立判断",
        "keywords": ("从众", "群体", "压力", "污名", "社会", "心理", "偏见", "极化", "独立"),
        "scope": "群体决策、舆论压力、污名化和社会心理操纵",
    },
]

SOURCE_FAMILIES = [
    ({"005", "006"}, "传销/裂变材料同类主题", 0.5),
    ({"012", "021"}, "庞氏/骗局材料同类主题", 0.5),
    ({"001", "015", "019"}, "历史权力与政治案例相近主题", 0.6),
    ({"003", "010", "016"}, "心性/修养材料的相近实践传统", 0.8),
]


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def tokens(value: str) -> set[str]:
    result: set[str] = set()
    for token in TOKEN_RE.findall(value.lower()):
        result.add(token)
        if all("\u4e00" <= char <= "\u9fff" for char in token) and len(token) >= 3:
            result.update(token[index : index + 2] for index in range(len(token) - 1))
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_evidence(text: str, default_book: str) -> list[str]:
    refs: list[str] = []
    for match in EVIDENCE_RE.finditer(text):
        if match.group(4):
            start = match.group(4)
            end = match.group(5) or start
            refs.append(f"[{match.group(3)}:L{start}" + (f"-L{end}" if end != start else "") + "]")
            continue
        start = match.group(1).replace(",", "")
        end = (match.group(2) or start).replace(",", "")
        refs.append(f"[{default_book}:L{start}" + (f"-L{end}" if end != start else "") + "]")
    return list(dict.fromkeys(refs))[:12]


def parse_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[normalize(match.group(1))] = text[match.end() : end].strip()
    return sections


def parse_items(text: str, book_id: str) -> list[dict]:
    matches = list(ITEM_RE.finditer(text))
    items: list[dict] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.start() : end]
        item_id = match.group(1)
        items.append(
            {
                "book_id": book_id,
                "id": item_id,
                "title": normalize(match.group(2)),
                "text": body.strip(),
                "terms": tokens(match.group(2) + "\n" + body),
                "evidence_refs": parse_evidence(body, book_id),
                "has_mechanism": bool(re.search(r"Mechanism|机制", body, re.I)),
                "has_boundary": bool(re.search(r"Boundary|边界|Failure conditions|失效", body, re.I)),
                "has_variables": bool(re.search(r"Variable|变量|Conditions|条件", body, re.I)),
            }
        )
    return items


def read_inputs() -> tuple[dict, list[dict]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    books: list[dict] = []
    items: list[dict] = []
    eligible_total = manifest.get("synthesis_eligible_count", 0)
    loaded_count = 0
    print(f"[PROGRESS] Stage E 读取 synthesis-eligible 单书: 0/{eligible_total}", flush=True)
    for book in manifest.get("books", []):
        if not book.get("synthesis_eligible"):
            continue
        model_path = ROOT / book["book_model"]
        text = model_path.read_text(encoding="utf-8", errors="replace")
        books.append({**book, "model_path": str(model_path.relative_to(ROOT)), "model_sha256": sha256(model_path)})
        parsed_items = parse_items(text, book["id"])
        items.extend(parsed_items)
        loaded_count += 1
        print(f"[PROGRESS] 已读取 {loaded_count}/{eligible_total}: {book['id']} items={len(parsed_items)}", flush=True)
    return manifest, books, items


def family_for(book_id: str) -> tuple[str, float] | None:
    for members, label, weight in SOURCE_FAMILIES:
        if book_id in members:
            return label, weight
    return None


def independent_clusters(book_ids: list[str]) -> list[dict]:
    remaining = set(book_ids)
    clusters: list[dict] = []
    for members, label, weight in SOURCE_FAMILIES:
        matched = sorted(remaining & members)
        if matched:
            clusters.append({"cluster": label, "books": matched, "independence_weight": weight, "basis": "同类主题或同一材料谱系，降低重复证据权重"})
            remaining -= set(matched)
    for bid in sorted(remaining):
        clusters.append({"cluster": f"独立来源 {bid}", "books": [bid], "independence_weight": 1.0, "basis": "当前书库中没有声明其与其他来源属于同一材料谱系"})
    return clusters


def choose_bucket(item: dict) -> tuple[dict, int]:
    best = BUCKETS[0]
    best_score = -1
    for bucket in BUCKETS:
        score = sum(1 for keyword in bucket["keywords"] if keyword.lower() in item["text"].lower())
        if score > best_score:
            best, best_score = bucket, score
    return best, best_score


def group_items(items: list[dict], prefix: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        if prefix == "P":
            bucket, score = choose_bucket(item)
            if score == 0:
                continue
            groups[bucket["id"]].append(item)
        else:
            groups["all"].append(item)
    return groups


def item_excerpt(item: dict, max_chars: int = 180) -> str:
    lines = []
    for line in item["text"].splitlines():
        value = normalize(re.sub(r"^[-#|]+", "", line))
        if not value or value.lower().startswith(("evidence", "status", "source:", "support:")):
            continue
        lines.append(value)
        if len(" ".join(lines)) >= max_chars:
            break
    # 截断可能正好落在空格上；再次规范化，避免生成 Markdown 尾随空格。
    return normalize(normalize(" ".join(lines))[:max_chars])


def confidence_for(items: list[dict], clusters: list[dict], counterevidence_count: int) -> dict:
    books = sorted({item["book_id"] for item in items})
    support_count = min(5, len(books))
    source_independence = sum(cluster["independence_weight"] for cluster in clusters) / max(1, len(clusters))
    evidence_quality = sum(bool(item["evidence_refs"]) for item in items) / max(1, len(items))
    mechanism_complete = sum(
        item["has_mechanism"] and item["has_boundary"] and item["has_variables"] for item in items
    ) / max(1, len(items))
    refutation_weight = min(0.5, counterevidence_count / max(1, len(items)) * 0.5)
    score = support_count * source_independence * evidence_quality * max(0.5, mechanism_complete) * (1 - refutation_weight)
    return {
        "support_count": len(books),
        "support_count_capped": support_count,
        "source_independence": round(source_independence, 4),
        "evidence_quality": round(evidence_quality, 4),
        "mechanism_completeness": round(max(0.5, mechanism_complete), 4),
        "refutation_weight": round(refutation_weight, 4),
        "confidence": round(score, 4),
        "formula": "min(5, support_count) * source_independence * evidence_quality * mechanism_completeness * (1 - refutation_weight)",
    }


def principle_records(items: list[dict], all_items: list[dict]) -> list[dict]:
    groups = group_items([item for item in items if item["id"].startswith("P")], "P")
    records: list[dict] = []
    for bucket in BUCKETS:
        members = groups.get(bucket["id"], [])
        source_books = sorted({item["book_id"] for item in members})
        if len(source_books) < MINIMUM_BOOKS:
            continue
        clusters = independent_clusters(source_books)
        related_tensions = [
            item
            for item in all_items
            if item["id"].startswith("T") and any(keyword.lower() in item["text"].lower() for keyword in bucket["keywords"])
        ][:4]
        related_variables = [item for item in all_items if item["id"].startswith("V") and item["book_id"] in source_books][:6]
        related_boundaries = [item for item in all_items if item["id"].startswith("B") and item["book_id"] in source_books][:6]
        excerpts = [item_excerpt(item) for item in members[:3]]
        mechanisms = [item_excerpt(item) for item in members if item["has_mechanism"]][:3]
        if not mechanisms:
            mechanisms = excerpts[:2]
        record = {
            "id": bucket["id"],
            "title": bucket["title"],
            "principle": f"当场景出现“{bucket['scope']}”时，优先检查该机制是否存在，再决定行动；不能把单书策略直接当成无条件建议。",
            "mechanism": mechanisms,
            "scope": bucket["scope"],
            "variables": [item["title"] for item in related_variables] or ["信息透明度", "资源控制度", "反馈开放度", "退出成本"],
            "boundary_conditions": [item_excerpt(item) for item in related_boundaries] or ["当前模型未提供直接边界；迁移前必须重新核验场景条件。"],
            "counterevidence": [
                {
                    "book_id": item["book_id"],
                    "model_item_id": item["id"],
                    "excerpt": item_excerpt(item),
                    "evidence_refs": item["evidence_refs"],
                }
                for item in related_tensions
            ] or [{"status": "not_found", "note": "当前 19 本 synthesis-eligible 模型未发现可直接归入该原则的反向条目；不等于现实中不存在反例。"}],
            "independent_source_clusters": [
                {
                    **cluster,
                    "evidence_refs": [
                        ref
                        for item in members
                        if item["book_id"] in cluster["books"]
                        for ref in item["evidence_refs"][:4]
                    ][:12],
                }
                for cluster in clusters
            ],
            "supporting_items": [
                {
                    "book_id": item["book_id"],
                    "model_item_id": item["id"],
                    "title": item["title"],
                    "evidence_refs": item["evidence_refs"],
                }
                for item in members
            ],
        }
        record["evidence_strength"] = {
            "source_books": source_books,
            "item_count": len(members),
            "evidence_refs": len({ref for item in members for ref in item["evidence_refs"]}),
        }
        record["confidence_calculation"] = confidence_for(members, clusters, len(related_tensions))
        records.append(record)
    return records


def render_principles(records: list[dict]) -> str:
    lines = [
        "# 跨书通用原则库",
        "",
        "> 本文件由 `scripts/build_knowledge.py` 从 19 本 synthesis-eligible 单书模型重新生成。原则是跨书候选，不是无条件建议；每条都保留独立来源集群、证据强度、机制、变量、边界、反证与信度。",
        "",
        "## 信度公式",
        "",
        "`Confidence = min(5, support_count) × source_independence × evidence_quality × mechanism_completeness × (1 - refutation_weight)`。同类主题来源会降低独立性权重；没有直接反证不等于现实中不存在反例。",
        "",
    ]
    for record in records:
        calc = record["confidence_calculation"]
        lines.extend(
            [
                f"## {record['id']} {record['title']}",
                "",
                f"- Principle：{record['principle']}",
                f"- Scope：{record['scope']}",
                "- Mechanism：",
            ]
        )
        lines.extend(f"  - {value}" for value in record["mechanism"])
        lines.append("- Variables：" + "；".join(record["variables"]))
        lines.append("- Boundary conditions：")
        lines.extend(f"  - {value}" for value in record["boundary_conditions"])
        lines.append("- Counterevidence / tensions：")
        for item in record["counterevidence"]:
            if item.get("status") == "not_found":
                lines.append(f"  - {item['note']}")
            else:
                refs = ", ".join(item.get("evidence_refs") or []) or "no locator"
                lines.append(f"  - `{item['book_id']}:{item['model_item_id']}` {item['excerpt']}；证据：{refs}")
        lines.append("- Independent source clusters：")
        for cluster in record["independent_source_clusters"]:
            refs = ", ".join(cluster["evidence_refs"][:8]) or "no locator"
            lines.append(f"  - {cluster['cluster']}；books={','.join(cluster['books'])}；weight={cluster['independence_weight']}；evidence={refs}")
        lines.extend(
            [
                "- Evidence strength：",
                f"  - source_books={','.join(record['evidence_strength']['source_books'])}；supporting_items={record['evidence_strength']['item_count']}；evidence_refs={record['evidence_strength']['evidence_refs']}",
                f"- Confidence：{calc['confidence']}（support={calc['support_count']}；independence={calc['source_independence']}；evidence={calc['evidence_quality']}；mechanism={calc['mechanism_completeness']}；refutation={calc['refutation_weight']}）",
                "",
            ]
        )
    lines.extend(
        [
            "## 未进入跨书原则的单书候选",
            "",
            "只有一个独立来源的候选原则没有被提升为通用原则；它们保留在对应单书模型中，避免把单书经验伪装成跨书共识。",
            "",
        ]
    )
    return "\n".join(lines)


def aggregate_records(all_items: list[dict], prefix: str, limit: int = 24) -> list[dict]:
    selected = [item for item in all_items if item["id"].startswith(prefix)]
    selected.sort(key=lambda item: (-len(item["evidence_refs"]), item["book_id"], item["id"]))
    return selected[:limit]


def render_concepts(all_items: list[dict]) -> str:
    concepts = aggregate_records(all_items, "C", 30)
    lines = ["# 跨书概念本体", "", "> 概念来自单书模型的独立条目；同名不自动视为同义，跨书使用时仍需检查边界。", ""]
    for index, item in enumerate(concepts, start=1):
        lines.extend(
            [
                f"## C{index:03d} {item['title']}",
                "",
                f"- 来源单书：`{item['book_id']}`；原模型 ID：`{item['id']}`",
                f"- 结构化定义：{item_excerpt(item, 260)}",
                f"- Evidence：{', '.join(item['evidence_refs']) or '未声明；不得作为跨书 SOURCE 使用'}",
                "",
            ]
        )
    return "\n".join(lines)


def render_causal_models(all_items: list[dict]) -> str:
    causal = aggregate_records(all_items, "CM", 36)
    lines = ["# 跨书因果模型", "", "> 本节点保留变量、机制、条件、边界和来源，不把不同书的相似叙述强行合并为同一因果律。", ""]
    for index, item in enumerate(causal, start=1):
        lines.extend(
            [
                f"## CM{index:03d} {item['title']}",
                "",
                f"- Source book / model ID：`{item['book_id']}` / `{item['id']}`",
                f"- Mechanism excerpt：{item_excerpt(item, 320)}",
                f"- Variables / conditions declared：{'是' if item['has_variables'] else '未完整声明'}",
                f"- Boundary declared：{'是' if item['has_boundary'] else '未完整声明'}",
                f"- Evidence：{', '.join(item['evidence_refs']) or '未声明'}",
                "",
            ]
        )
    return "\n".join(lines)


def render_tensions(all_items: list[dict]) -> str:
    tensions = aggregate_records(all_items, "T", 30)
    lines = ["# 跨书张力与未解决矛盾", "", "> 张力不是待消灭的噪声；它用于决定切换变量、适用边界和不确定度。", ""]
    for index, item in enumerate(tensions, start=1):
        lines.extend(
            [
                f"## T{index:03d} {item['title']}",
                "",
                f"- 来源：`{item['book_id']}:{item['id']}`",
                f"- 张力内容：{item_excerpt(item, 360)}",
                f"- Evidence：{', '.join(item['evidence_refs']) or '未声明'}",
                "- 运行时处理：不强行综合；当情境触发该张力时，先查边界和反向解释。",
                "",
            ]
        )
    return "\n".join(lines)


def render_boundaries(all_items: list[dict]) -> str:
    boundaries = aggregate_records(all_items, "B", 36)
    lines = ["# 决策边界与失效条件", "", "> 边界来自单书模型中的例外、条件与评价；缺少边界的原则不能直接迁移。", ""]
    for index, item in enumerate(boundaries, start=1):
        lines.extend(
            [
                f"## B{index:03d} {item['title']}",
                "",
                f"- 来源：`{item['book_id']}:{item['id']}`",
                f"- Boundary：{item_excerpt(item, 360)}",
                f"- Evidence：{', '.join(item['evidence_refs']) or '未声明'}",
                "",
            ]
        )
    return "\n".join(lines)


def render_worldview(all_items: list[dict]) -> str:
    claims = aggregate_records(all_items, "CL", 24)
    lines = ["# 领域世界模型", "", "## 当前综合判断", "", "跨书模型共同指向：行动者在信息不完整、资源不对称、关系压力和制度约束中，通过解释事实、控制资源、选择反馈通道与管理退出成本改变结果。任何抽象原则都必须回到这些变量，而不是只看表面动机。", "", "## 证据支撑的主要判断样本", ""]
    for item in claims:
        lines.append(f"- `{item['book_id']}:{item['id']}` {item_excerpt(item, 220)}；Evidence：{', '.join(item['evidence_refs']) or '未声明'}")
    lines.extend(["", "## 不可默认的前提", "", "- 书中展示的策略不等于作者建议采用的策略，尤其是小说、传记、案例集和权谋材料。", "- 来源数量不等于独立性；同类材料按来源集群降权。", "- 任何迁移判断都必须检查反馈开放度、信息透明度、退出成本、物理容量和伤害边界。", ""])
    return "\n".join(lines)


def render_decision_framework(all_items: list[dict]) -> str:
    heuristics = aggregate_records(all_items, "H", 30)
    lines = ["# 机制化决策框架", "", "1. 先定义问题：当前要改变的是信息、资源、关系、制度、行动还是退出成本？", "2. 再画因果链：触发条件 → 中介机制 → 可观察结果 → 二阶后果。", "3. 检查四个变量：反馈是否开放、资源是否被单点控制、退出是否仍可行、证据是否可质证。", "4. 查张力和边界：保留至少一种竞争解释，标注 known / likely / possible / speculative。", "5. 形成最小行动：优先选择可逆、可观察、能带来真实反馈的下一步。", "", "## 单书规则样本", ""]
    for item in heuristics:
        lines.append(f"- `{item['book_id']}:{item['id']}` {item_excerpt(item, 220)}；Evidence：{', '.join(item['evidence_refs']) or '未声明'}")
    lines.append("")
    return "\n".join(lines)


def render_thinking_habits(all_items: list[dict]) -> str:
    habits = aggregate_records(all_items, "RP", 24) + aggregate_records(all_items, "H", 18)
    lines = ["# 思考习惯", "", "- 遇到强叙事先问：哪些是可质证事实，哪些是解释、推断或评价？", "- 遇到组织变化先问：谁控制实物资源，谁掌握反馈，谁承担失败成本？", "- 遇到快速增长先问：容量、现金流、退出和二阶后果在哪里？", "- 遇到关系压力先问：我是在交换信任，还是在透支信誉？", "- 遇到挫折先分开处理：先做物理自救，再做心智重构；二者不能互相替代。", "", "## 来源样本", ""]
    for item in habits:
        lines.append(f"- `{item['book_id']}:{item['id']}` {item_excerpt(item, 180)}；Evidence：{', '.join(item['evidence_refs']) or '未声明'}")
    lines.append("")
    return "\n".join(lines)


def render_anti_patterns(all_items: list[dict]) -> str:
    anti = aggregate_records(all_items, "AP", 30)
    lines = ["# 失败模式与反模式", "", "以下反模式只作为风险识别，不是对所有场景的普遍断言。", ""]
    for index, item in enumerate(anti, start=1):
        lines.extend([f"## AP{index:03d} {item['title']}", "", f"- 来源：`{item['book_id']}:{item['id']}`", f"- 风险描述：{item_excerpt(item, 300)}", f"- Evidence：{', '.join(item['evidence_refs']) or '未声明'}", ""])
    return "\n".join(lines)


def render_problem_solving(all_items: list[dict]) -> str:
    return "\n".join(
        [
            "# 问题解决路径",
            "",
            "1. 事实层：把叙事拆成事件、约束、证据和未知项。",
            "2. 机制层：找出激励、信息不对称、资源控制、反馈延迟和路径依赖。",
            "3. 选择层：比较继续、试验、隔离、谈判、撤退和升级的可逆性。",
            "4. 验证层：先做低成本真实动作，观察结果，再扩大承诺。",
            "5. 复盘层：记录哪个假设被证伪，避免用新解释保护旧投入。",
            "",
        ]
    )


def render_ontology(all_items: list[dict]) -> str:
    concepts = aggregate_records(all_items, "C", 16)
    return "\n".join(["# 领域本体索引", "", "| 层级 | 说明 |", "|---|---|", "| 事实与信息 | 证据、质证、信息污染与叙事 |", "| 关系与权力 | 资源控制、名实分离、反馈和退路 |", "| 心智与行动 | 知行、逆境、群体压力和责任 |", "| 系统与边界 | 容量、风险、二阶后果和失效条件 |", "", "## 概念样本", ""] + [f"- `{item['book_id']}:{item['id']}` {item['title']}" for item in concepts] + [""])


def render_mental_models(records: list[dict]) -> str:
    lines = ["# 可复用心智模型", "", "> 心智模型是机制压缩，不是脱离边界的口号。", ""]
    for record in records:
        lines.extend([f"## {record['id']} {record['title']}", "", f"- 触发场景：{record['scope']}", f"- 机制：{'；'.join(record['mechanism'][:2])}", f"- 变量：{'；'.join(record['variables'][:6])}", f"- 失效检查：{'；'.join(record['boundary_conditions'][:2])}", f"- 信度：{record['confidence_calculation']['confidence']}", ""])
    return "\n".join(lines)


def render_index(records: list[dict]) -> str:
    by_id = {record["id"]: record for record in records}
    topics = [
        ("Power / Organization", "领导、下属、功劳、架空、权力、组织政治", ["P201", "P202", "P203"]),
        ("Manipulation / Persuasion", "洗脑、暗示、说服、信息污染、假证据", ["P101", "P403"]),
        ("Fraud / Pyramid Systems", "骗局、庞氏、传销、直销、裂变、资金盘", ["P102", "P401", "P402"]),
        ("Relationships", "信任、背叛、自卫、退隐、留后路", ["P102", "P202"]),
        ("Self-cognition", "心性、知行、逆境、内省、情绪", ["P301", "P302", "P303"]),
        ("Ethics / Values", "道德、善恶、利他、底线、责任", ["P303", "P101"]),
        ("Decision Making", "决策、不确定、止损、风险控制", ["P101", "P402", "P401"]),
        ("Institution / Incentives", "制度、激励、规则、绩效、防作弊", ["P201", "P203", "P303"]),
        ("Social Psychology", "从众、群体压力、污名化、极化", ["P102", "P403"]),
        ("Change / Reform", "变革、阻力、改革、转型、反馈", ["P203", "P301", "P202"]),
    ]
    lines = ["# Domain Mind Knowledge Router & Runtime Routing Map", "", "> 本 Router 由新单书模型综合生成。默认先读取 knowledge；只有遇到未决张力、边界风险或用户明确索要出处时才下钻。", ""]
    for title, triggers, ids in topics:
        active = [f"`{pid}` ({by_id[pid]['title']})" for pid in ids if pid in by_id]
        lines.extend([f"## {title}", "", f"- Triggers：{triggers}", f"- Load：{', '.join(active) or '当前没有达到跨书最低独立来源数的原则'}", "- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。", ""])
    lines.extend(["## 渐进式披露", "", "1. Level 1：knowledge/index.md、principles.md、causal-models.md、tensions.md、boundaries.md。", "2. Level 2：发生关键张力、低信度或需要单书细节时读取 generated/book-models/*.md。", "3. Level 3：全量库且用户明确要求原文证据时读取 corpus/raw；运行时发行包不含 raw。", ""])
    return "\n".join(lines)


def render_cognitive_model(records: list[dict], all_items: list[dict]) -> str:
    lines = ["# Domain Mind Synthesized Cognitive Model", "", "> 本文件是 19 本 synthesis-eligible 单书模型的新一轮跨书综合；每条原则都经过来源独立性、证据、机制、边界和反证字段审计。", "", "## 1. 核心机制", "", "现实判断首先是变量识别问题：信息是否可质证、资源是否被单点控制、反馈是否开放、退出成本是否上升、容量是否接近边界，以及行动者能否保持独立判断。", "", "## 2. 跨书原则", ""]
    for record in records:
        lines.extend([f"### {record['id']} {record['title']}", f"- {record['principle']}", f"- Mechanism：{'；'.join(record['mechanism'][:2])}", f"- Boundary：{'；'.join(record['boundary_conditions'][:2])}", f"- Confidence：{record['confidence_calculation']['confidence']}", ""])
    lines.extend(["## 3. 不可合并的张力", "", "- 个体反求诸己与环境塑造力不能互相消灭；先判断可控变量。", "- 利他共同体与情感隔离都可能是局部有效策略，切换取决于权力、透明度和伤害风险。", "- 高速动员和长期纠偏不是同一阶段的治理标准。", "", "## 4. 证据边界", "", "模型使用单书模型的证据定位；运行时发行包只包含结构化模型，不包含第三方原始全本。", ""])
    return "\n".join(lines)


def render_source_map(records: list[dict], books: list[dict], all_items: list[dict]) -> dict:
    return {
        "schema_version": "2.0.0",
        "generated_by": "scripts/build_knowledge.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_book_count": len(books),
        "books": {
            book["id"]: {
                "title": book["title"],
                "model": book["model_path"],
                "model_sha256": book["model_sha256"],
                "source_file": book["source_file"],
                "source_hash": book["source_hash"],
            }
            for book in books
        },
        "principles": {
            record["id"]: {
                "title": record["title"],
                "source_books": record["evidence_strength"]["source_books"],
                "source_clusters": record["independent_source_clusters"],
                "evidence_refs": sorted({ref for cluster in record["independent_source_clusters"] for ref in cluster["evidence_refs"]}),
                "confidence": record["confidence_calculation"],
            }
            for record in records
        },
        "item_counts": dict(Counter(item["id"][0] for item in all_items)),
    }


def old_id_titles() -> dict[str, str]:
    old = KNOWLEDGE_DIR / "principles.md"
    if not old.is_file():
        return {}
    text = old.read_text(encoding="utf-8", errors="replace")
    return {match.group(1): normalize(match.group(2)) for match in re.finditer(r"^###?\s+(P\d{3})\s+(.+)$", text, re.M)}


def render_id_migrations(records: list[dict], old_titles: dict[str, str], old_migrations_text: str) -> list[dict]:
    current = {record["id"]: record for record in records}
    migrations: list[dict] = []
    for old_id, old_title in sorted(old_titles.items()):
        if old_id not in current:
            migrations.append({"old_id": old_id, "new_id": None, "status": "retire", "reason": "新一轮独立来源聚类未达到跨书最低来源数，保留在单书模型而不再作为通用原则。"})
            continue
        new_title = current[old_id]["title"]
        migrations.append({"old_id": old_id, "new_id": old_id, "status": "preserve", "reason": f"稳定 ID 保留；新一轮来源集群、证据、边界和信度已重新计算。旧标题：{old_title}；新标题：{new_title}"})
    if "P203_legacy" in old_migrations_text:
        if "P203" in current:
            migrations.append({"old_id": "P203_legacy", "new_id": "P203", "status": "rename", "reason": "历史迁移记录指向当前稳定 P203；本轮核验其仍有跨书来源集群。"})
    return migrations


def write_outputs(manifest: dict, books: list[dict], items: list[dict]) -> dict:
    print(f"[PROGRESS] 开始跨书聚类: books={len(books)} items={len(items)}", flush=True)
    records = principle_records(items, items)
    print(f"[PROGRESS] 原则聚类完成: cross_book_principles={len(records)}", flush=True)
    old_titles = old_id_titles()
    old_migrations_path = KNOWLEDGE_DIR / "id-migrations.json"
    old_migrations_text = old_migrations_path.read_text(encoding="utf-8", errors="replace") if old_migrations_path.is_file() else ""
    outputs = {
        "index.md": render_index(records),
        "worldview.md": render_worldview(items),
        "ontology.md": render_ontology(items),
        "concepts.md": render_concepts(items),
        "principles.md": render_principles(records),
        "mental-models.md": render_mental_models(records),
        "causal-models.md": render_causal_models(items),
        "tensions.md": render_tensions(items),
        "boundaries.md": render_boundaries(items),
        "decision-framework.md": render_decision_framework(items),
        "problem-solving.md": render_problem_solving(items),
        "thinking-habits.md": render_thinking_habits(items),
        "anti-patterns.md": render_anti_patterns(items),
        "cognitive-model.md": render_cognitive_model(records, items),
    }
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    for index, (name, content) in enumerate(outputs.items(), start=1):
        (KNOWLEDGE_DIR / name).write_text(content.rstrip() + "\n", encoding="utf-8")
        print(f"[PROGRESS] 写入知识节点 {index}/{len(outputs)}: knowledge/{name}", flush=True)
    migrations = render_id_migrations(records, old_titles, old_migrations_text)
    (KNOWLEDGE_DIR / "id-migrations.json").write_text(json.dumps(migrations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_map = render_source_map(records, books, items)
    (KNOWLEDGE_DIR / "source-map.json").write_text(json.dumps(source_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# 跨书知识库综合报告",
        "",
        "## 本轮结果",
        "",
        f"- 输入：{len(books)} 本 synthesis-eligible canonical 单书模型。",
        f"- 产出：{len(outputs) + 2} 个知识节点/映射文件。",
        f"- 跨书原则：{len(records)} 条；只有至少 2 个独立来源书目才提升为通用原则。",
        f"- 解析条目：{len(items)} 条；保留单书 ID、证据定位和来源模型。",
        "- 生成方式：先读取单书模型，再按机制关键词与来源独立性聚类；旧知识文件不作为新结论来源。",
        "",
        "## 来源独立性",
        "",
        "传销/裂变、庞氏/骗局、历史政治案例和心性修养等同类材料被降权处理。独立书目数量不等于独立证据数量；同类主题只形成一个来源集群。",
        "",
        "## 反证与限制",
        "",
        "每条原则都登记 counterevidence / tensions。没有找到反向条目只表示当前 19 本模型没有自动发现直接反证，不表示现实不存在反例。自动聚类结果仍需在重大决策中做人工语义复核。",
        "",
        "## 运行时边界",
        "",
        "默认只读取 knowledge；需要具体出处时下钻到单书模型。Clean Runtime 发行包不含 corpus/raw，不能声称可直接提供第三方原文。",
        "",
        "## 生成记录",
        "",
        f"- generated_by: scripts/build_knowledge.py",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
    print("[PROGRESS] 写入映射、报告和迁移记录完成", flush=True)
    return {"records": records, "outputs": list(outputs), "item_count": len(items), "book_count": len(books)}


def main() -> int:
    if not MANIFEST_PATH.is_file():
        print("manifest missing")
        return 1
    manifest, books, items = read_inputs()
    if len(books) != manifest.get("synthesis_eligible_count"):
        print(f"synthesis input mismatch: books={len(books)} eligible={manifest.get('synthesis_eligible_count')}")
        return 1
    result = write_outputs(manifest, books, items)
    print(f"[PASS] synthesized books={result['book_count']} items={result['item_count']} principles={len(result['records'])}")
    print("[WRITE] " + ", ".join(f"knowledge/{name}" for name in result["outputs"]))
    print("[WRITE] knowledge/id-migrations.json, knowledge/source-map.json, knowledge/corpus-synthesis.report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
