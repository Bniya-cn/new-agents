---
name: book-distiller
description: >
  Distill one Markdown book from healing-agents/corpus/raw into a structured,
  provenance-preserving cognitive model and a Chinese human-readable
  distillation report. Use when deeply analyzing or cognitively modeling one
  individual book. Do not use for corpus-wide synthesis, quotation retrieval,
  or final domain advice.
---

# Book Distiller

## 1. 目的与边界

Book Distiller 一次只处理一本逻辑上的书。结果不是章节摘要、原文搜索索引、RAG 拼接、书摘集合或最终领域建议，而是可追溯、可审计、可增量更新的单书认知模型。

输入只能来自：

~~~text
corpus/raw/<book>.md
~~~

默认输出：

~~~text
generated/book-models/<book>.md
generated/reports/<book>.report.md
~~~

处理单书时禁止：

- 读取其他书并把其他书的观点混入当前模型；
- 修改 corpus/raw/；
- 修改 knowledge/ 或创建 domain-mind；
- 把分析者常识、现代建议或道德评价伪装成原书观点；
- 大段复制或连续改写受版权保护的原文。

## 2. 四层证据

所有重要结论必须标记以下四类之一：

### SOURCE

原书明确说出、明确展示，或由叙事中的直接行动结果支持的内容。必须附原始行号或其他稳定源位置。

### RECONSTRUCTION

原书没有用完全相同的句子说出，但多个文本区域共同支持的稳定结构，例如反复出现的因果链、问题拆解方式或行动逻辑。必须列出多个证据位置，并明确这是重建。

### INFERENCE

基于原书进一步推导的可能结论，证据不足以称为作者明确观点。必须单独登记，不能进入 SOURCE 原则，也不能在跨书综合时被当作同等强度证据。

### EVALUATION

分析者提出的批评、局限、反例、替代解释、风险判断或现代适用性判断。必须与原书内容分开。

机器字段使用稳定值：source、reconstructed、inference、evaluation。分析正文使用中文解释。

## 3. 处理模式

### Mode A：Direct Processing

适用于能够在一次完整分析中可靠检查的书：

~~~text
book → structural inspection → whole-book reading
     → cognitive extraction → whole-book synthesis → coverage audit
~~~

必须先读完整输入，再形成全书模型；不能只看目录、开头或若干热门段落。

### Mode B：Hierarchical Processing

适用于大书、严重 OCR、上下文无法完整容纳或论证跨越大量文本的书：

~~~text
book → structural mapping → semantic segmentation
     → segment cognitive models → cross-segment consolidation
     → whole-book cognitive reconstruction → coverage audit
~~~

分块模型只能作为中间证据，不能把 chunk1 summary + chunk2 summary 直接拼成最终答案。最后必须重新做全书级合并，并记录未可靠处理的区域。

## 4. 结构检查与分段

开始时记录文件路径、字符数、行数、编码、标题/章节/页码、目录和非正文区域、重复页、乱码、表格残留、异常长段和无法解释区域，并说明处理模式选择原因。

Hierarchical Processing 的分段优先级：

1. 明确章节；
2. OCR 页分隔；
3. 编号结构；
4. 明显语义转折；
5. 最后才使用长度边界。

每个 segment 使用稳定 ID：S001、S002……，并保留 source、start_line、end_line。重复 OCR 区域不得重复放大概念权重，应标记为 duplicate/repeated evidence。

## 5. 必须提取的结构

最终模型至少包含以下稳定 ID：

~~~text
C001...  Core Concepts
CL001... Major Claims
CM001... Causal Models
RP001... Reasoning Patterns
H001...  Decision Heuristics
A001...  Assumptions
V001...  Important Variables
B001...  Boundary Conditions
T001...  Internal Tensions
AP001... Anti-patterns
P001...  Transferable Principles
I001...  Analyst Inferences
~~~

必须回答：

- Core Problem Space：这本书真正试图解释什么问题，而不是目录讲了什么。
- Central Thesis Architecture：主要观点如何通过概念、关系和因果连接。
- World Model：人、信息、权力、资源、制度、环境、激励、能动性和历史连续性如何运作。
- Core Concepts：每个概念的含义、作用、关系、状态和证据。
- Major Claims：判断、类型、状态、机制、前提、边界和证据。
- Causal Models：反馈回路、延迟效果、二阶后果、中介、权衡、路径依赖、激励、信息不对称和选择效应。
- Reasoning Patterns：文本稳定采用的推理方式，而不只是结论。
- Decision Heuristics：Use when、Diagnostic question、Reasoning、Action tendency、Boundary conditions、Evidence。
- Assumptions、Variables、Boundaries、Tensions：明确区分作者前提、重建前提、例外和未解决矛盾。
- Transferable Principles：只能在前述分析后形成，写明机制、范围、条件、失效条件、状态和证据。
- Thinking Habits：一个真正读懂本书的人遇到新问题时会多问什么。

Decision Heuristic 不得写成“沟通很重要”这类空泛句子，必须能用于书中没有出现过的新问题。

## 6. Provenance

重要概念、判断、因果模型和可迁移原则都必须可反查原始 Markdown。证据优先级为：原有标题/章节、OCR 页码或分页标识、原始行号、segment ID + 行号。

推荐格式：

~~~yaml
evidence:
  - source: corpus/raw/<book>.md
    lines: 315-329
    support: direct
~~~

不允许只写“作者在书中多次提到”“主要来自第三章”“根据全书来看”。

## 7. Coverage Audit

结束前检查：

- 所有主要文本区域是否都被检查；
- 是否错误地只分析开头；
- 目录、注释、参考文献和案例是否被误当成中心论点；
- 重复 OCR 是否造成概念权重失真；
- 每个 CL、CM、P 是否有 Evidence；
- INFERENCE 和 EVALUATION 是否显式；
- 是否存在大型未处理区或来源无法定位的主要判断。

Coverage 不完整时必须写 Coverage status: partial，说明缺口，禁止宣称完整。

## 8. 输出契约

机器模型使用以下顶层结构：

~~~markdown
# Book Cognitive Model
## Metadata
## 1. 核心问题 Core Problem Space
## 2. 核心论证结构 Central Thesis Architecture
## 3. 世界模型 World Model
## 4. 核心概念 Core Concepts
## 5. 主要判断 Major Claims
## 6. 因果模型 Causal Models
## 7. 思考方式 Reasoning Patterns
## 8. 判断规则 Decision Heuristics
## 9. 隐含前提 Assumptions
## 10. 重要变量 Important Variables
## 11. 边界条件与例外 Boundary Conditions
## 12. 内部张力与未解决矛盾
## 13. 失败模式与错误思维 Anti-patterns
## 14. 可迁移原则 Transferable Principles
## 15. 读完本书后可能形成的思考习惯 Thinking Habits
## 16. 未来跨书连接候选
## 17. Analyst Cautions
## 18. Coverage Report
~~~

人读报告必须中文优先、自然易读，至少包含：一句话结果、炼化概览、认知结构、思考习惯、重要因果关系、可迁移原则、谨慎使用、内部张力、Coverage 和版本变更记录。报告不得只是机器模型的字段逐条复制。

## 9. 版本与失败行为

首次报告使用 v0.1。重新炼化时保持稳定 ID，只在新增、合并、降级、删除或修正时更新，并在版本变更记录中用中文解释原因。

遇到空文件、严重损坏、无法建立证据或输入不存在时禁止猜测。部分可读时可以处理可靠部分，但必须标记 partial。

对小说、传记、案例集等材料，必须明确“文本展示的策略”不等于“作者建议采用的策略”，并对违法、操纵、欺诈或伤害性行为做风险标注。

## 10. 质量门槛

每次输出前逐项检查：

~~~text
Q1 Source Preservation
Q2 Whole-book Coverage
Q3 Not a Summary
Q4 Provenance
Q5 Epistemic Separation
Q6 No Fabricated Consensus
Q7 No Quote Mosaic
Q8 Transferability
Q9 Compression Without Collapse
Q10 Auditability
Q11 Human Readability
Q12 Version Visibility
~~~

任何 FAIL 都必须写明原因。
