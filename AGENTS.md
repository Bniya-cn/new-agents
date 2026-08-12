# AGENTS.md — healing-agents

## 项目定位

`healing-agents` 是一个**可炼化知识工程**仓库，不是通用 Agent 项目。

当前阶段目标：建立可靠的书库输入 → 炼化流水线基础设施。

## 目录职责

| 目录 | 职责 | 写入权限 |
|------|------|----------|
| `corpus/raw/` | 原始 Markdown 书籍 | **只读**，禁止 AI 修改 |
| `generated/book-models/` | 单书结构化认知模型 | book-distiller 写入 |
| `knowledge/` | 跨书合成知识 | corpus-synthesizer 写入 |
| `evals/` | 炼化质量评估 | 评估脚本写入 |
| `scripts/` | 工具脚本 | 人工维护 |
| `.agents/skills/` | Agent Skills 定义 | 人工维护 |

## 强制规则

### P0 — 原始资料保护

1. **禁止**修改 `corpus/raw/` 中的任何文件内容
2. **禁止**在审计阶段进行总结、合并、删章节
3. **禁止**跳过审计直接炼化

### P1 — 炼化流程

1. 每次扩充书库后，运行 `python3 scripts/audit_corpus.py`
2. 先读 `corpus-audit.md`，确认无阻塞项
3. 从中等篇幅的书开始 book-distiller 试点
4. 输出写入 `generated/book-models/`，不写入 `corpus/raw/`

### P2 — Skill 加载顺序

1. `.agents/skills/book-distiller/SKILL.md` (已就绪)
2. `.agents/skills/corpus-synthesizer/SKILL.md` (已就绪)
3. `.agents/skills/domain-mind/SKILL.md` (已就绪)
4. 项目 `AGENTS.md`
5. 本文件

## 当前可用 Skill

| Skill | 状态 | 职责 |
|-------|------|------|
| `book-distiller` | 已就绪 | 一本书 → 一个结构化认知模型与人读报告 |
| `corpus-synthesizer` | 已就绪 | 19本书结构化模型 → 跨书本体与通用原则整合 |
| `domain-mind` | 已就绪 | 跨书原则因果网络 → 运行时未知场景推理与决策 |

## 验证命令

```bash
python3 scripts/audit_corpus.py   # 书库审计与状态校验
python3 scripts/run_evals.py      # 执行确定性验证与生成语义打分模板
```

## 语言

- 文档、报告、审计结论：中文
- 代码、路径、命令：英文
