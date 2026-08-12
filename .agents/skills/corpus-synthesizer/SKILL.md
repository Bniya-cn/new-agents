# Skill: Corpus Synthesizer

## Metadata

- name: corpus-synthesizer
- description: Synthesize structured cognitive models from multiple individual books into a unified, cross-book cognitive model, ontology, and Chinese human-readable synthesis report, enforcing source independence.

## 1. Purpose and Role

`corpus-synthesizer` 负责在 `healing-agents` 仓库中执行 **Stage E (跨书综合)**。
它的核心职责是：读取 `generated/book-models/*.md` 中的所有单书认知模型，消除多余的抄袭/重复源噪音，归纳出普适的跨书概念本体（Ontology），聚合高信度通用原则（Principles），识别不同认知流派之间的深层张力（Tensions），并输出供人类和 Agent 运行时读取的终极领域认知体系底座。

## 2. Input and Output Schema

### 输入
- `generated/book-models/*.md` (19 本有效 Canonical 单书模型)
- `corpus/manifest.json`

### 输出
1. `knowledge/index.md` (Knowledge Router & Ontology Index)
2. `knowledge/principles.md` (Universal Principles with `independent_source_clusters`)
3. `knowledge/cognitive-model.md` (Synthesized Core Ontology, Causal Models, and Tensions)
4. `knowledge/corpus-synthesis.report.md` (中文跨书综合报告)

## 3. Strict Rules and Constraints

### P0 — 来源独立性校验与信度（Confidence）计算 (Source Independence)
为了防止抄袭者与概念包装导致的“虚假证据链膨胀”（例如庞兹自传与我是怎么割韭菜的属于同一主题，或各类传销书共享同一倍增公式），在 principles 中必须增加 `independent_source_clusters` 记录。
信度（Confidence）的物理计算公式必须刚性遵循以下维度：
$$Confidence = 支持数量 \times 来源独立性 \times 证据质量 \times 机制完整度 \times (1 - 反证权重)$$
1. **支持数量 (Support Count)**：明确声明支持该原则的独立单书数量。
2. **来源独立性 (Source Independence)**：
   - 互为重复翻译/同一历史事件（如 012 与 021 庞氏骗局）：独立性计权为 0.5。
   - 不同文化背景、独立演进但得出相同因果判定（如 传习录心即理 vs 活法作为人何谓正确）：独立性计权为 1.0。
3. **证据质量 (Evidence Quality)**：单书中 Provenance 行号证据的硬核与可信度。
4. **机制完整度 (Mechanism Completeness)**：该原则是否具备完整的“输入变量 -> 因果机制 -> 边界条件 -> 输出结果”闭环。
5. **反证情况 (Refutation / Tensions)**：是否存在直接驳斥或反向因果的流派证据。

### P1 — 中文产出与行号保留
- 所有生成的跨书报告、原则、本体定义、冲突分析必须以**中文**书写，保留核心名词的英文对照。
- 每一个被引用的概念或原则，必须在其 Provenance 节点中，清晰保留源单书 ID 及其对应的原始行号映射（格式：`[003:L276]`），决不允许丢失证据链。

### P2 — 冲突与张力（Tensions）刚性捕捉
不允许在综合过程中为了追求和谐而强行合并对立观点。必须清晰记录以下三类冲突张力：
- **本体级张力**（如 传习录向内求理 vs 社会性动物向外归因）
- **策略级张力**（如 活法无条件利他 vs 罗织经御下情感隔离）
- **边界级张力**（如 商君书法治铁血动员 vs 忽悠原理中防范集权话术控制）

## 4. Operation Pipeline

```
读取 19 本单书模型
→ 归纳本体提取概念（Ontology）
→ 分类聚合跨书原则（Principles）
→ 划分独立来源集群并计算 Confidence
→ 映射对立张力（Tensions）
→ 生成 Knowledge Router 索引
→ 输出人读中文跨书报告
```
