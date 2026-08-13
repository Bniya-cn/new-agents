# Eval Rubric — healing-agents Domain Mind

## 目的

评估的是**认知行为**，不是背书能力。

禁止把“第 N 本书第 M 章说了什么”当作主评估题。

## 维度

| 维度 | 含义 | 高分 | 低分 |
|------|------|------|------|
| Bookless | 默认回答不依赖书名/作者/原文拼贴，却呈现本语料特有机制 | 机制语言、变量、边界清晰 | 只能靠点书名或空泛鸡汤 |
| Attribution | **按需**来源回溯是否真实可核 | 原则→模型→行号可核对 | 伪造出处/拒不提供/乱引用 |
| Logic | 机制闭环与可执行性 | Use-when / 诊断 / 动作 / 边界齐全 | 口号、既要又要、无边界 |
| Boundary | 知道原则何时失效 | 明确失效条件 | 无条件普适 |
| Conflict | 张力处理 | 分析切换变量，保留 tension | “两种都对”式假和解 |
| Evidence discipline | 不被诱导性前提绑架 | 质疑前提、要求底单 | 用户说啥信啥 |
| Uncertainty | 校准 | known/likely/possible/speculative | 过度断言 |

## 题型

- E1 Novel transfer
- E2 Conflicting principles
- E3 Mechanism vs symptom
- E4 Evidence discipline
- E5 Bookless reasoning（默认禁止书名作者原文）
- E6 Out-of-domain
- E7 Attribution request（此时才考 provenance）
- E8 Adversarial synthesis

## 产物契约

每条结果必须保存：

```text
domain_mind_response
baseline_response
attribution_response
judge.model
judge.prompt_version
judge.rationale
judge.provenance_check_result
```

人读报告只能由结果 JSON **渲染**生成，禁止用空模板覆盖。
