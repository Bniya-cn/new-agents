# AGENTS.md — Healing Domain Mind Repository Bootstrap

## 1. Runtime Bootstrap Protocol

当在本项目中接收到任何涉及以下主题的现实判断与决策问题时：

> `decision`, `organization`, `relationship`, `power`, `incentive`, `persuasion`, `conflict`, `social behavior`, `risk`, `self-cognition`, `strategy`

**必须默认自动按照以下 8 步执行 Runtime Path**：

```text
1. Activate domain-mind (.agents/skills/domain-mind/SKILL.md)
2. Read knowledge/index.md Router
3. Load ONLY relevant knowledge nodes (principles, causal models, tensions, boundaries)
4. Check principles (knowledge/principles.md)
5. Check causal models (knowledge/causal-models.md)
6. Check tensions (knowledge/tensions.md / cognitive-model.md)
7. Check boundaries (knowledge/boundaries.md)
8. Formulate mechanism-based decision for current problem
```

### 默认禁令 (Default Forbid)
- 🚫 禁止从 `corpus/raw/` 原始书库开始阅读。
- 🚫 禁止从 `generated/reports/` 总结报告开始阅读。
- 🚫 禁止逐书全文扫描或按书名总结（如“《书A》说……《书B》说……”）。
- 🚫 默认禁止输出书名、作者或 `[015:Lxxxxx]` 行号；仅当用户明确提问“依据是什么 / 来自哪些书 / 给我证据”时才下钻出示。

### 证据能力分级 (Evidence Capability Split)
- **全量炼化库 (evidence_mode=full)**: 追溯路径为 `knowledge → book-model → raw`。
- **Runtime 发行包 (evidence_mode=model_only)**: 追溯路径为 `knowledge → book-model → source metadata`。若用户要求查阅原始全文，明确说明：“本 Runtime 发行包未随附第三方原始全本书籍，出处已精准定位至单书认知模型”，**绝对禁止伪造原文或假行号**。

---

## 2. 项目定位与目录职责

`healing-agents` 是一个**可炼化知识工程与认知推理**仓库。

| 目录 | 职责 | 访问权限 |
|------|------|----------|
| `agent-manifest.yaml` | 跨 Agent 机器协议契约 | 读取 |
| `knowledge/` | 跨书合成知识库与 Router 索引 | **优先读取 (Level 1)** |
| `generated/book-models/` | 单书结构化认知模型 | **下钻读取 (Level 2)** |
| `corpus/raw/` | 原始 Markdown 书籍 | **按需盲查 (Level 3, 只读)** |
| `.agents/skills/` | Agent Reasoning Skills | 运行时推理引擎 |
| `evals/` | 质量评估与 Benchmark | 评估脚本维护 |
| `scripts/` | 自动化炼化与验证脚本 | 工具维护 |

---

## 3. 核心强制规则 (P0)

1. **原始资料保护**: `corpus/raw/` 只读，禁止删改。
2. **渐进式披露 (Progressive Disclosure)**: 机制层解答问题，拦截低效 RAG 退化。
3. **来源独立性**: 剔除重复翻译或抄袭构成的证据膨胀。
4. **验证门禁 Fail-Closed**: 任何未通过 Gate 验证的模型禁止加入合成知识库。

---

## 4. 验证与运维命令

```bash
python3 scripts/validate_source_consistency.py   # 物理源一致性校验
python3 scripts/validate_book_model.py           # 单书模型与 Provenance 校验
python3 scripts/validate_provenance.py           # 行号定位精确校验
python3 scripts/validate_agent_package.py        # Agent Package 契约与 Router 校验
python3 scripts/run_evals.py                     # 执行 Gate 校验与 E10-E12 评估
```

---

## 5. 语言规范

- 架构说明、技术推理、评估报告、回答自然语言：**中文**
- 代码、命令、路径、字段、变量名：**英文**
