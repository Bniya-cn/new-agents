# Healing Domain Mind v1.0.0 最终实现交付报告

> 最终等级：**PASS_WITH_LIMITATIONS**
> 本报告由 `scripts/build_final_report.py` 读取验证结果生成；不使用旧的 PASS 文案覆盖当前状态。

## 1. 实现范围

- 保留原有 `.agents/skills/book-distiller/SKILL.md` 的既有章节、四层证据、输出契约和质量门槛；本轮仅增加自适应复杂度与 segment-first 约束。
- `004` 保持 `blocked_ocr_unavailable`；`020` 保持 `duplicate_of=015`，未伪造模型。
- canonical 可综合书目：19。
- Direct rebuilt books：9。
- Hierarchical rebuilt books：10。
- Segment count：111。

## 2. HEAD 与 Book Model tree

- Starting HEAD：`85ed21e45742960460db9cae6276c726af767eb1`。
- Ending HEAD（本轮最终门禁生成时）：`49d32c55774ccec17966806c80186d2304e88288`。
- Book Model tree SHA before：`11791fd2fc579df7035d1549c53e19a6be5195b221e2f16731f253db3284d9ce`。
- Book Model tree SHA after：`12431175f3215e47a6bbe53642ddad7d88a313717c178f286aae4287d9518b0a`。

## 3. Gate 结果

- Adaptive distillation：`PASSED`。
- True segment-first hierarchical：`PASSED`。
- Corpus synthesis：`PASSED`。
- Semantic provenance items：715；unsupported：0。
- E10 cold-start：`PASSED`；E10-B client matrix：`PASS_WITH_LIMITATIONS`。
- E11 clean-room：`PASSED`。
- E12 bootstrap robustness：`PASSED`。
- Package validator：`PASSED`；runtime package validator：`PASSED`。

## 4. 客户端矩阵

- Codex：`PASS`；fresh_session=True；files_loaded=AGENTS.md,knowledge/index.md,.agents/skills/domain-mind/SKILL.md。
- Claude Code：`NOT_RUN_ENV_UNAVAILABLE`；fresh_session=False；files_loaded=none。
- Gemini CLI：`NOT_RUN_ENV_UNAVAILABLE`；fresh_session=False；files_loaded=none。

Codex 的 E10-B 已实际启动并得到 PASS；Claude Code、Gemini CLI 不存在于当前环境，因此保留 `NOT_RUN_ENV_UNAVAILABLE`，没有从静态适配器推断通过。

## 5. Runtime 与发布

- Runtime validation：`PASSED`。
- Runtime bundle：`dist/healing-domain-mind`；contains_raw=False；contains_work=False。
- Tag：`v1.0.0`。
- Release：`RELEASED`。
- Full repository contains raw：`true`；copyright distribution risk：`true`；本轮未改写 Git 历史。

## 6. Knowledge hashes

- `anti-patterns.md`：`d260c1925214b56c1edbbe6f78886f7ee1f8eb35331e9aad626432899de6ff06`
- `boundaries.md`：`6ef2e0146a9f225019387fda30cefae4912a1ca5a5417204b2d155e2e05dce8b`
- `causal-models.md`：`735583284d89982e2a40d579183ba5bf64523987939090efaadd562999f67513`
- `cognitive-model.md`：`87db11f21470d386acf5c9057f501fb62e1aad58fbce7d093eca93ff032b708a`
- `concepts.md`：`22108c2d264d6e80bfcba9edfcb769b4706fb9eae4fdf82bc404d0af8358c20b`
- `corpus-synthesis.report.md`：`07bc9e1b84f02f4a0d9423de065e490b72728904ad7fb4ee073891b1dade7234`
- `decision-framework.md`：`dcbc5a099ea20c830ad26fd9357cef000282dbd48de8529d1686a24b3d942632`
- `id-migrations.json`：`bfabcea58c009a8a18c569c2edbe180abf915128d786adade621878bcae75233`
- `index.md`：`040c908073fb62ea421ecdadcfdc515c235e26a4afb5a78679e73b68a4d21173`
- `mental-models.md`：`dbd352d8bc314b8435e894cdb848a731c146eabe65d635c3ff1a2de8a4d375d3`
- `ontology.md`：`bfe6d802391372f9aa4a7bb651675ebdb4a68f86ae49975c7528c99d3732ab64`
- `principles.md`：`0e4c8dff8a223f7511b0ecd18a80eabdb3435f2226573b529c74e46b6f6bb3fc`
- `problem-solving.md`：`6d0df732442ee25b24e4f565addc7d85aa7167150a1c82ddcba28f60768d041d`
- `source-map.json`：`4f9cdffab4f30368feb8decd0026dca30eef3cf1353df62282d089ea5174ae10`
- `tensions.md`：`309b072a653ddb64c0636bd7a705204e5743f36523fc2af07153b6c9a113f77c`
- `thinking-habits.md`：`860688f0ba5046cd08ed91d302e41b3b5950401fd74291217e6ff8f2d988b9b7`
- `worldview.md`：`2b9c302c789f77e8225006429602eedcebaf92bfab1a7fe0a1ba8a5ad81f5b5f`

## 7. Limitations

- E10-B client matrix=PASS_WITH_LIMITATIONS; 不能据静态文件推断未启动客户端通过
- full repository contains corpus/raw; copyright distribution risk remains until repository visibility/content boundary changes

## 8. 生成记录

- generated_by：`scripts/build_final_report.py`
- generated_at：2026-08-13T05:30:04.006182+00:00
