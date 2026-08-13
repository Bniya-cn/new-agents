# Domain Mind Knowledge Router & Runtime Routing Map

> 本文件是 Domain Mind 运行时的**核心知识分流与路由引擎**。它将用户提出的现实判断问题映射至最精准的原则 (Principles)、因果模型 (Causal Models)、张力 (Tensions) 与边界 (Boundaries)。

---

## 1. 领域路由表 (Runtime Routing Map)

### 1. Power / Organization (权力与组织博弈)

- **Triggers**: 领导、下属、功劳、架空、权力、威望、晋升、组织政治、实权、高管斗争、功高震主、越级
- **Load**:
  - `principles`: `P201` (实权架空), `P202` (自污避嫌), `P203` (办事二术)
  - `causal-models`: `CM-power-autocracy`, `CM-power-takeover`
  - `tensions`: `T001` (纯善利他 vs 冷酷隔离), `T002` (低位架空 vs 忠诚服从)
  - `boundaries`: `B-power-autocracy`, `B-power-takeover`
- **Do not**:
  - 默认加载 `corpus/raw/` 原始书库。
  - 逐书罗列历史案例或强行给领导/下属贴《资治通鉴》标签。

---

### 2. Manipulation / Persuasion (说服与认知操纵)

- **Triggers**: 洗脑、暗示、说服、话语权、认知失调、假证据、信息污染、罗生门、舆论构陷、控脑
- **Load**:
  - `principles`: `P101` (物理底单质证), `P102` (社交信誉隔离)
  - `causal-models`: `CM-manipulation-dissonance`, `CM-manipulation-fake-evidence`
  - `tensions`: `T003` (防范忽悠 vs 团队一致性)
  - `boundaries`: `B-manipulation-dissonance`
- **Do not**:
  - 默认加载原始文本。

---

### 3. Fraud / Pyramid Systems (骗局与庞氏裂变)

- **Triggers**: 骗局、庞氏、传销、直销、裂变、高额返利、套现、资金盘、割韭菜、暴雷
- **Load**:
  - `principles`: `P102` (社交信誉隔离), `P402` (庞氏崩盘临界线)
  - `causal-models`: `CM-fraud-ponzi`, `CM-fraud-pyramid`
  - `tensions`: `T004` (短利引诱 vs 长期信誉破产)
  - `boundaries`: `B-fraud-ponzi`
- **Do not**:
  - 默认加载原始文本。

---

### 4. Relationships (人际防御与生存)

- **Triggers**: 人际关系、背叛、信任、自卫、退隐、御下、留后路、防身、避险
- **Load**:
  - `principles`: `P202` (自污求生), `P102` (信誉隔离)
  - `causal-models`: `CM-relationship-detachment`
  - `tensions`: `T001` (利他 vs 隔离)
  - `boundaries`: `B-relationship-survival`
- **Do not**:
  - 默认加载原始文本。

---

### 5. Self-cognition (心性存续与知行合一)

- **Triggers**: 心性、修养、知行合一、致良知、逆境、情绪、迷茫、内省、精神超越
- **Load**:
  - `principles`: `P301` (知行合一), `P302` (逆境消化), `P303` (达观隔离)
  - `causal-models`: `CM-self-moral-realism`
  - `tensions`: `T005` (心即理内求 vs 外在环境归因)
  - `boundaries`: `B-self-cultivation`
- **Do not**:
  - 默认加载原始文本。

---

### 6. Ethics / Values (道德与义利抉择)

- **Triggers**: 道德、善恶、敬天爱人、纯善、利他、义利之辨、底线、选择
- **Load**:
  - `principles`: `P301` (知行合一), `P403` (利他格局共振)
  - `causal-models`: `CM-ethics-altruism`
  - `tensions`: `T001` (纯善利他 vs 政治生存)
  - `boundaries`: `B-ethics-altruism`
- **Do not**:
  - 默认加载原始文本。

---

### 7. Decision Making (决策与不确定性)

- **Triggers**: 决策、不确定、止损、风险控制、关键变量、抉择、战略
- **Load**:
  - `principles`: `P101` (底单质证), `P401` (几何倍增极限)
  - `causal-models`: `CM-decision-framework`
  - `tensions`: `T006` (激进扩张 vs 物理极限)
  - `boundaries`: `B-decision-limits`
- **Do not**:
  - 默认加载原始文本。

---

### 8. Institution / Incentives (制度与激励博弈)

- **Triggers**: 制度、激励、弱民、赏罚、法治、绩效、规则、防作弊、机制设计
- **Load**:
  - `principles`: `P201` (实权垄断), `P203` (办事二术)
  - `causal-models`: `CM-institution-incentives`
  - `tensions`: `T007` (刚性制度 vs 灵活变通)
  - `boundaries`: `B-institution-limits`
- **Do not**:
  - 默认加载原始文本。

---

### 9. Social Psychology (社会心理与群体动向)

- **Triggers**: 从众、群体压力、去人性化、污名化、羊群效应、社会偏见、极化
- **Load**:
  - `principles`: `P101` (底单质证), `P102` (信誉隔离)
  - `causal-models`: `CM-social-conformity`, `CM-social-dehumanization`
  - `tensions`: `T008` (个人独立思考 vs 群体从众)
  - `boundaries`: `B-social-psychology`
- **Do not**:
  - 默认加载原始文本。

---

### 10. Change / Reform (变革、阻力与破局)

- **Triggers**: 变革、阻力、破局、借势、改革、动荡、转型、新旧交替
- **Load**:
  - `principles`: `P201` (实权垄断), `P302` (逆境消化)
  - `causal-models`: `CM-change-reform`
  - `tensions`: `T009` (渐进改良 vs 激进重构)
  - `boundaries`: `B-change-reform`
- **Do not**:
  - 默认加载原始文本。

---

## 2. 路由下钻规则 (Drill-Down Policy)

1. **Level 1 (Default)**: 匹配上述主题，仅加载 `knowledge/*.md` 节点。直接输出决策。
2. **Level 2 (Fallback)**: 当遭遇未决张力、高风险边界或用户提问出处时，下钻加载 `generated/book-models/*.md`。
3. **Level 3 (Evidence)**: 在全量库 (`evidence_mode=full`) 环境下，用户明确追问原始证据时，下钻 `corpus/raw/*.md`；在发行包 (`evidence_mode=model_only`) 环境下，告知原文未打包，出处定位至单书模型。
