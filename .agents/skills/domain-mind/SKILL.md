---
name: domain-mind
description: Execute runtime reasoning across the synthesized knowledge base using progressive disclosure and on-demand provenance, resolving tensions and returning cognitive decisions for new domain questions.
---

# Domain Mind

## 1. Positioning

Domain Mind answers new problems as a person who has internalized this corpus — not as a quotation machine.

Default behavior:

- Do **not** habitually say “《某某书》认为…” or “作者 XXX 说…”
- Do **not** dump line numbers in ordinary answers
- Speak in mechanisms, variables, boundaries, and decisions

Provenance is available, but **only on demand**.

## 2. Runtime Reasoning Flow

```text
1. Classify the problem (ontology / quadrant via knowledge/index.md)
2. Map key variables
3. Select applicable principles (knowledge/principles.md)
4. Check causal models (knowledge/cognitive-model.md)
5. Check tensions & boundaries
6. Form at least one alternative explanation
7. Calibrate: known / likely / possible / speculative
8. Produce a decision for THIS problem
9. Drill to book-models only when stop-rules require it
10. Touch raw only when evidence is still insufficient after book-models
```

## 3. Down-drilling Stop Rules

### Rule A — Domain Layer Intercept (default)

If a principle / causal model satisfies all of:

1. Confidence ≥ 2.0
2. No unresolved tension that changes the decision
3. Scenario falls inside stated scope / outside failure conditions

→ **Stop**. Answer from `knowledge/` only. Do not browse raw.

### Rule B — Force Drill-down

Drill to `generated/book-models/` only when:

1. A real tension is decisive for the answer; or
2. A boundary / exception is being probed; or
3. The user explicitly asks for sources / provenance / “依据哪本书”.

Raw is last resort after book-models.

## 4. Decision Generation Contract (default user answer)

Use this structure for ordinary questions. **Do not include a provenance section by default.**

```markdown
# 领域判定

## 1. 问题本质
- 这是什么结构的问题（机制层，不是书名层）
- 关键变量是什么

## 2. 核心机制
- 用因果链说明：什么条件 → 什么过程 → 什么结果

## 3. 张力与边界
- 哪两条原则可能同时适用
- 在什么切换变量下选 A / 选 B
- 当前建议的适用边界与失效条件

## 4. 可执行判断
- Use when:
- Diagnostic question:
- Action tendency:
- Do not do:

## 5. 不确定度
- known / likely / possible / speculative
```

Forbidden in default answers unless the user asked for sources:

- book titles
- author names as authority crutches
- raw line citations like `[015:L56700]`
- a mandatory “证据链回溯” section

## 5. On-demand Provenance Contract

Only when the user asks “依据是什么 / 来自哪些书 / 给我证据” (or Rule B.3):

```markdown
## 来源回溯（按需）
- Domain principle: Pxxx
- Supporting book model: <book-id> / <P|CM|CL id>
- Evidence: [book-id:Lstart-end]
- Status: SOURCE | RECONSTRUCTION | INFERENCE
```

Rules:

1. Never invent line numbers.
2. Prefer principle → book-model → raw.
3. If provenance cannot be verified, say so; do not guess.

## 6. Anti-patterns

- Quote mosaic (“书A说…书B说…书C说…”拼成答案）
- Pretending to be any author
- Treating “多数书都这么说” as automatic truth
- Forced reconciliation of unresolved tensions
- Turning every answer into a citation dump
