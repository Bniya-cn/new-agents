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

**Phase 0 — 基础设施**

- [x] 建立 `corpus/raw/` 原始书库
- [x] 运行书库审计 → `corpus-audit.md`
- [ ] 实现 `book-distiller` Skill
- [ ] 炼化首本试点书 → `generated/book-models/`

## 流水线

```text
corpus/raw/  →  book-distiller  →  generated/book-models/
                                      ↓
                              corpus-synthesizer  →  knowledge/
                                      ↓
                                domain-mind  →  Cursor / Codex / Claude
```

## 快速命令

```bash
# 审计书库（只读，不修改原始文件）
python3 scripts/audit_corpus.py
```

## 原则

1. **原始资料不可变** — `corpus/raw/` 中的文件不做删改、不合并、不总结
2. **先审计再炼化** — 每次扩充书库后重新运行审计
3. **渐进式验证** — 从中等篇幅的书开始试点，再处理大部头
