# Domain Mind Knowledge Router & Runtime Routing Map

> 本 Router 由新单书模型综合生成。默认先读取 knowledge；只有遇到未决张力、边界风险或用户明确索要出处时才下钻。

## Power / Organization

- Triggers：领导、下属、功劳、架空、权力、组织政治
- Load：`P201` (实权资源与名义位置分离), `P202` (权力风险中的退路与边界保护), `P203` (反馈通道与执行纠偏)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Manipulation / Persuasion

- Triggers：洗脑、暗示、说服、信息污染、假证据
- Load：`P101` (事实质证与信息污染隔离), `P403` (群体压力下的独立判断)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Fraud / Pyramid Systems

- Triggers：骗局、庞氏、传销、直销、裂变、资金盘
- Load：`P102` (信任关系与社会信誉隔离), `P401` (规模增长的物理边界与崩盘风险)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Relationships

- Triggers：信任、背叛、自卫、退隐、留后路
- Load：`P102` (信任关系与社会信誉隔离), `P202` (权力风险中的退路与边界保护)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Self-cognition

- Triggers：心性、知行、逆境、内省、情绪
- Load：`P301` (行动验证与知行闭环), `P303` (道德判断与长期责任约束)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Ethics / Values

- Triggers：道德、善恶、利他、底线、责任
- Load：`P303` (道德判断与长期责任约束), `P101` (事实质证与信息污染隔离)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Decision Making

- Triggers：决策、不确定、止损、风险控制
- Load：`P101` (事实质证与信息污染隔离), `P401` (规模增长的物理边界与崩盘风险)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Institution / Incentives

- Triggers：制度、激励、规则、绩效、防作弊
- Load：`P201` (实权资源与名义位置分离), `P203` (反馈通道与执行纠偏), `P303` (道德判断与长期责任约束)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Social Psychology

- Triggers：从众、群体压力、污名化、极化
- Load：`P102` (信任关系与社会信誉隔离), `P403` (群体压力下的独立判断)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## Change / Reform

- Triggers：变革、阻力、改革、转型、反馈
- Load：`P203` (反馈通道与执行纠偏), `P301` (行动验证与知行闭环), `P202` (权力风险中的退路与边界保护)
- Do not：默认不扫描 corpus/raw；不按书名堆砌；不把文本展示的策略直接当作建议。

## 渐进式披露

1. Level 1：knowledge/index.md、principles.md、causal-models.md、tensions.md、boundaries.md。
2. Level 2：发生关键张力、低信度或需要单书细节时读取 generated/book-models/*.md。
3. Level 3：全量库且用户明确要求原文证据时读取 corpus/raw；运行时发行包不含 raw。
