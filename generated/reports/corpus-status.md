# Corpus Processing Status

> 生成时间: 2026-08-13T00:10:00Z
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

## 逐书状态 (带 Quality Gate 审计)

| ID | Title | Status | Mode | Provenance Status | Accepted Partial | Synthesis Eligible | Chars | Notes |
|---|---|---|---|---|---|---|---:|---|
| 001 | 20世纪五大传记书系 | complete | hierarchical | passed | false | true | 1070256 |  |
| 002 | 商君书 | complete | direct | passed | false | true | 100458 |  |
| 003 | 传习录 | complete | hierarchical | passed | false | true | 252756 |  |
| 004 | 传销原理 | blocked_ocr_unavailable | blocked | untested | false | false | 0 | PDF exists but lacks a text layer |
| 005 | 传销学 | complete | hierarchical | passed | false | true | 816976 |  |
| 006 | 传销洗脑实录 | complete | direct | passed | false | true | 119123 |  |
| 007 | 做局 | complete | direct | passed | false | true | 34435 |  |
| 008 | 天下无谋之密卷 | complete | direct | passed | false | true | 82889 |  |
| 009 | 影响力 | complete | direct | passed | false | true | 166218 |  |
| 010 | 心-稻盛和夫的一生嘱托 | complete | direct | passed | false | true | 68181 |  |
| 011 | 忽悠的原理与技巧 | complete | hierarchical | passed | false | true | 207334 |  |
| 012 | 我是怎么割韭菜的 | complete | direct | passed | false | true | 161320 |  |
| 013 | 新厚黑学全书 | complete | hierarchical | passed | false | true | 2070699 |  |
| 014 | 格局的力量 | complete | direct | passed | false | true | 55348 |  |
| 015 | 汇评精注资治通鉴 | complete | hierarchical | passed | false | true | 3432347 | canonical for duplicate 020 |
| 016 | 活法 | complete | hierarchical | passed | false | true | 279528 |  |
| 017 | 社会性动物 | complete | hierarchical | passed | false | true | 519578 |  |
| 018 | 素书 | complete | direct | passed | false | true | 83570 |  |
| 019 | 罗织经 | complete | direct | passed | false | true | 183294 |  |
| 020 | 资治通鉴 | duplicate | skip_duplicate | untested | false | false | 3432347 | explicit duplicate of 015 |
| 021 | 骗局之王 | complete | direct | passed | false | true | 123065 |  |
