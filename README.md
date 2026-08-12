# healing-agents

可炼化知识工程基础设施 — 将原始书籍 Markdown 炼化为结构化认知模型。

## 目录结构

```text
healing-agents/
├── README.md
├── AGENTS.md
├── corpus-audit.md          # 书库审计报告
├── corpus/raw/              # 原始 Markdown 书库（只读输入）
├── generated/book-models/   # book-distiller 输出
├── knowledge/               # corpus-synthesizer 输出
├── evals/                   # 炼化质量评估
├── scripts/                 # 工具脚本
└── .agents/skills/          # Agent Skills
```

## 当前阶段

**Phase 1 — 全量炼化与 Domain Mind 交付 (已完成)**

- [x] 建立 `corpus/raw/` 原始书库并运行 `scripts/audit_corpus.py`
- [x] 升级 `book-distiller` Skill 至 v0.2，定义 Hierarchical Mode 分段融合机制
- [x] 完成 19 本 Canonical 书籍的单书炼化 → `generated/book-models/` 和 `generated/reports/`
- [x] 实现并安装 `corpus-synthesizer` Skill，生成跨书本体、通用原则与三大张力
- [x] 部署 `domain-mind` 运行时推理框架，定义下钻停止红线
- [x] 建立自动化确定性与语义评分评测集 `evals/`
- [x] 一次性交付完毕所有工程成果

## 流水线

```text
corpus/raw/  →  book-distiller  →  generated/book-models/ & generated/reports/
                                      ↓
                              corpus-synthesizer  →  knowledge/ (跨书整合)
                                      ↓
                                domain-mind  →  运行决策推理与 E9 测试
```

## 快速命令

```bash
# 1. 审计书库并校验各单书处理状态
python3 scripts/audit_corpus.py

# 2. 执行确定性验证与生成语义评估报告模板
python3 scripts/run_evals.py
```

## 原则

1. **原始资料不可变** — `corpus/raw/` 中的文件为只读输入，AI 绝不删改。
2. **Provenance 精准追溯** — 每一个概念、原则和因果模式必须附带物理行号标记（如 `[ID:Line]`）。
3. **防止 RAG 低效退化** — 运行时推理基于领域层高级原则进行智能拦截，仅在面临例外、冲突或高精质证时向下钻取单书。
4. **捍卫来源独立性** — 过滤由重复翻译或抄袭构成的“证据膨胀”，客观计算原则的 Confidence 信度。
