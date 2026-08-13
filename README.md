# Healing Domain Mind (v1.0.0)

> 一个通过多源知识炼化形成的 **Cognitive Agent Repository**。
> 可通过 `git clone` 直接启动，无需 Prompt 工程，自动以“内化了整套领域知识体系”的视角回答现实判断与决策问题。

---

## 🌟 核心理念与定位

Healing Domain Mind 不是书籍搜索器，也不是 RAG 摘要拼盘。

它回答的核心问题是：
> **“一个真正吸收并内化了这些深刻知识的人，会如何判断当前这个全新的现实问题？”**

### 核心特性
- 🚀 **Zero-Prompt Quick Start**: 使用 `git clone` 下载仓库后，用 Codex / Cursor / Claude Code / Gemini CLI 直接打开项目，无需提示“使用 domain-mind”，直接提问现实问题即可自动激活。
- 🛡️ **机制化推理 (Mechanism-First Reasoning)**: 默认以“问题本质、核心机制、关键变量、张力与边界、可执行判断、不确定度”输出判断，绝不默认书名堆砌或强吐行号。
- 🔍 **按需出示证据 (Provenance on Demand)**: 仅当用户明确追问“依据是什么”时，才向下下钻至单书模型与原著证据链。
- 📦 **双阶发行架构 (Evidence Capability Split)**: 区分 Internal 全量研发库 (`evidence_mode=full`) 与 Clean Runtime 发行包 (`dist/healing-domain-mind/`, `evidence_mode=model_only`)，严格隔离第三方版权文本。

---

## 🚀 Quick Start (快速启动)

### 1. 克隆与打开仓库

```bash
git clone https://github.com/Bniya-cn/healing-domain-mind.git
cd healing-domain-mind
```

用你习惯的 Repo-Aware Agent 打开目录：
- **Codex / Cursor**: 原生读取 `AGENTS.md`
- **Claude Code**: 原生通过 `CLAUDE.md` 自动导入 `AGENTS.md`
- **Gemini CLI**: 原生通过 `GEMINI.md` 自动导入 `AGENTS.md`

### 2. 直接提问现实问题

在新会话中直接输入普通现实问题，例如：

> **“一个核心员工能力越来越强，影响力开始超过直属领导，这件事应该怎么看？”**

Agent 将自动完成：
`Repository Bootstrap` → `问题分类` → `Domain Mind Router` → `按需加载节点` → `机制化判断输出`。

---

## 📂 仓库结构

```text
healing-domain-mind/
├── AGENTS.md                   # Canonical Bootstrap Protocol
├── CLAUDE.md                   # Claude Code Bootstrap Adapter
├── GEMINI.md                   # Gemini CLI Bootstrap Adapter
├── agent-manifest.yaml         # 跨 Agent 机器协议契约
├── README.md                   # 产品化说明文档
├── LICENSE                     # 软件与工程结构授权
├── NOTICE.md                   # 第三方原著版权隔离说明
├── knowledge/                  # 跨书合成知识库 (Index / Principles / Models)
│   ├── index.md                # 10 大主题 Active Router
│   ├── principles.md           # 通用原则库
│   ├── causal-models.md        # 因果机制网络
│   ├── tensions.md             # 结构张力库
│   └── boundaries.md           # 决策边界与失效条件
├── generated/
│   └── book-models/            # 19 本 Canonical 单书结构化认知模型
├── examples/                   # 10 个真实场景使用用例
├── dist/                       # Clean Runtime 发行包构建产物
└── scripts/                    # 自动化炼化、校验与 Build 脚本
```

---

## 🛠️ 运维与验证命令

```bash
# 1. 物理源一致性校验
python3 scripts/validate_source_consistency.py

# 2. 单书认知模型与行号 Locator 校验
python3 scripts/validate_book_model.py
python3 scripts/validate_provenance.py

# 3. Agent Package 契约与 Router 完整性校验
python3 scripts/validate_agent_package.py

# 4. 执行全套 Quality Gates 校验
python3 scripts/run_evals.py

# 5. 编译 Clean Runtime 发行包
python3 scripts/build_agent_release.py
```

---

## 📜 版权与授权

- 本项目的代码、脚本、技能定义与知识工程结构采用 [Apache-2.0](LICENSE) 授权。
- 详见 [NOTICE.md](NOTICE.md) 了解第三方原著著作权隔离说明。
