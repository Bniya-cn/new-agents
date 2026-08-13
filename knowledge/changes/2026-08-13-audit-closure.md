# 知识变更记录 — 2026-08-13 audit closure

## 本轮未改

- 未重写 Book Model 认知内容
- 未重跑 corpus synthesis 主体

## 本轮变更

- Domain Mind：provenance 改为按需；默认回答去掉强制证据链专章
- Eval：45 题补齐回答/Baseline/Judge 全文；cases.md 改为由 JSON 渲染
- Source consistency：±5% → exact；完整 JSON 重跑
- Hierarchical：新增 synthesis_manifest + Sxxx.cog.md 映射证据
- 多本 Metadata 与 raw/manifest 精确对齐（仅元数据字段）
