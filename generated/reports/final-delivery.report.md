# healing-agents 验证基础设施收口报告

> 时间: 2026-08-13T03:05:00Z  
> 质量门禁: **PASS_WITH_AUDIT_TRAIL**（验证链已收口；不做“100% 空洞口号”）

本轮**不重炼** Book Models / knowledge synthesis，只修你指出的验证与运行时契约问题。

---

## 1. 已关闭的问题

### ① `run_evals.py` 覆盖报告 bug
- 默认**不再**重写 `evals/semantic_eval_cases.md`。
- 人读报告只能由 `scripts/render_semantic_eval_report.py` 从 JSON **渲染**。
- 空模板若需要，只能写到 `semantic_eval_cases.TEMPLATE.md`，且必须 `--init-template --force`。

### ② 45 题完整 audit trail
`evals/results/semantic-eval-results.json` 每条现含：

- `domain_mind_response`
- `baseline_response`
- `attribution_response`（按需来源，与默认回答分离）
- `judge.model` / `judge.prompt_version` / `judge.rationale`
- `judge.provenance_check_result`

`evals/semantic_eval_cases.md` 已由上述 JSON 全量渲染（约 1800+ 行，无“待评测回答内容”占位）。

说明：这是 **offline session audit pack**，不是外部 API 自动 Judge runner。证据链可审计；自动化 API runner 仍列在局限里。

### ③ Source consistency 精确匹配
- `validate_source_consistency.py`：**零容差** exact hash + chars + lines。
- 已修复 11 本 Metadata 漂移，并重新落盘完整 JSON（含 `model_meta` / `manifest_ground_truth`）。
- `python3 scripts/validate_source_consistency.py` → ALL PASS。

### ④ Hierarchical 可审计中间证据
对 001/003/005/011/013/015/016/017：

- `segments.json`
- `Sxxx.cog.md`（整书 ID → segment 证据重叠映射）
- `synthesis_manifest.json`
- 对落在首个 break 之前的证据，增加合成 `S000` preamble segment

诚实边界：这是 **consolidation map**，不是宣称 mega-book 每一页都做过独立二次精读。

### ⑤ Domain Mind provenance 按需显示
`.agents/skills/domain-mind/SKILL.md` 已改：

- 默认回答**禁止**强制“证据链回溯”专章
- 默认禁止习惯性书名/作者/行号倾销
- 仅当用户索要来源或 Rule B 触发时，才输出 provenance 契约

---

## 2. 复现命令

```bash
python3 scripts/validate_source_consistency.py
python3 scripts/build_segment_cognition.py 001 003 005 011 013 015 016 017
python3 scripts/render_semantic_eval_report.py
python3 scripts/run_evals.py
```

预期：全部 PASS；第二次跑 `run_evals.py` **不会**把 cases.md 洗成空模板。

---

## 3. 仍未宣称“已解决”的局限

1. 没有 live API semantic runner（外部模型自动出题/作答/Judge）。
2. Hierarchical 仍是“整书模型 → segment 映射”的可审计巩固，不是全量独立 segment 精炼流水线重跑。
3. `004` 仍为扫描版 PDF 无文本层 → `BLOCKED`。

---

## 4. 结论

相对你上轮评级：

| 项 | 现在 |
|---|---|
| Fail-Closed | ✅ |
| 007/013 metadata | ✅ |
| Source consistency 可复现 exact | ✅ |
| 45 题回答级 audit trail | ✅ |
| run_evals 覆盖 bug | ✅ |
| Domain Mind 默认隐藏 provenance | ✅ |
| Hierarchical segment cognition 证据 | ✅（consolidation / partial） |
| Live API semantic runner | ❌（明确局限） |

**建议评级：PASS_WITH_AUDIT_TRAIL / APPROVED for verification closure**  
（核心知识产物可用；验证链已补齐到可审计标准；不把 offline audit 伪装成 API runner。）
