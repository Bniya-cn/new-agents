# Corpus Processing Status

> 生成时间: 2026-08-12T15:54:02.400259+00:00
> Manifest: `corpus/manifest.json`

## 汇总

| 指标 | 数量 |
|---|---:|
| 总书数 | 21 |
| Canonical（非 blocked） | 19 |
| Duplicate | 1 |
| Blocked | 1 |
| Complete (model+report) | 19 |
| Pending | 0 |
| Modeled only | 0 |
| Direct mode | 11 |
| Hierarchical mode | 8 |

## 逐书状态

| ID | Title | Status | Mode | Chars | Model | Report | Notes |
|---|---|---|---|---:|---|---|---|
| 001 | 20世纪五大传记书系 | complete | hierarchical | 1070256 | Y | Y |  |
| 002 | 商君书 | complete | direct | 100458 | Y | Y |  |
| 003 | 传习录 | complete | hierarchical | 252756 | Y | Y |  |
| 004 | 传销原理 | blocked_ocr_unavailable | blocked | 0 | - | - | raw empty; PDF exists but lacks a text layer; do_not_forge_model |
| 005 | 传销学 | complete | hierarchical | 816976 | Y | Y |  |
| 006 | 传销洗脑实录 | complete | direct | 119123 | Y | Y |  |
| 007 | 做局 | complete | direct | 34435 | Y | Y |  |
| 008 | 天下无谋之密卷 | complete | direct | 82889 | Y | Y |  |
| 009 | 影响力 | complete | direct | 166218 | Y | Y |  |
| 010 | 心-稻盛和夫的一生嘱托 | complete | direct | 68181 | Y | Y |  |
| 011 | 忽悠的原理与技巧 | complete | hierarchical | 207334 | Y | Y |  |
| 012 | 我是怎么割韭菜的 | complete | direct | 161320 | Y | Y |  |
| 013 | 新厚黑学全书 | complete | hierarchical | 2070699 | Y | Y |  |
| 014 | 格局的力量 | complete | direct | 55348 | Y | Y |  |
| 015 | 汇评精注资治通鉴 | complete | hierarchical | 3432347 | Y | Y | canonical for duplicate 020 |
| 016 | 活法 | complete | hierarchical | 279528 | Y | Y |  |
| 017 | 社会性动物 | complete | hierarchical | 519578 | Y | Y |  |
| 018 | 素书 | complete | direct | 83570 | Y | Y |  |
| 019 | 罗织经 | complete | direct | 183294 | Y | Y |  |
| 020 | 资治通鉴 | duplicate | skip_duplicate | 3432347 | - | - | explicit duplicate of 015; identical content weight once |
| 021 | 骗局之王 | complete | direct | 123065 | Y | Y |  |
