#!/usr/bin/env python3
"""将 _markdown/ 中的原始 Markdown 复制到 corpus/raw/，按 001-书名.md 命名。

不修改文件内容，仅复制并重命名。
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "_markdown"
TARGET = ROOT / "corpus" / "raw"

# 源文件名 -> 目标短书名（保持原始内容不变）
BOOK_MAP: list[tuple[str, str]] = [
    ("20世纪五大传记书系（全5册）（朱元璋苏东坡王安石李鸿章张居正） (吴晗  林语堂  梁启超  朱东润) .md", "20世纪五大传记书系"),
    ("中华经典名著全本全注全译丛书：商君书 (石磊 译).md", "商君书"),
    ("传习录.md", "传习录"),
    ("传销原理 (胡振华，景进安主编).md", "传销原理"),
    ("传销学 (潘嘉浩, 林力源).md", "传销学"),
    ("传销洗脑实录 (王浩).md", "传销洗脑实录"),
    ("做局 (程小程) .md", "做局"),
    ("天下无谋之密卷.md", "天下无谋之密卷"),
    ("影响力 (经典版) = Influence The Psychology of Persuasion ([美] 西奥迪尼 (Robert B. Cialdini) 著  闾佳 译) .md", "影响力"),
    ("心：稻盛和夫的一生嘱托（“稻盛哲学”集大成之作） (稻盛和夫 [稻盛和夫]) (z-library.sk, 1lib.sk, z-lib.sk).md", "心-稻盛和夫的一生嘱托"),
    ("忽悠的原理与技巧 (段炼) .md", "忽悠的原理与技巧"),
    ("我是怎么割韭菜的：一个骗子的悔过与自白(庞氏骗局的始作俑者透视人性的贪婪) (查尔斯·庞兹 [查尔斯·庞兹]) .md", "我是怎么割韭菜的"),
    ("新厚黑学全书 李宗吾.md", "新厚黑学全书"),
    ("格局的力量 (（英）詹姆士·艾伦).md", "格局的力量"),
    ("汇评精注资治通鉴（全六册） .md", "汇评精注资治通鉴"),
    ("活法（1至4合集） (稻盛和夫 [稻盛和夫]) (z-library.sk, 1lib.sk, z-lib.sk).md", "活法"),
    ("社会性动物（第12版） (艾略特·阿伦森,乔舒亚·阿伦森) .md", "社会性动物"),
    ("素书 (黄石公) .md", "素书"),
    ("罗织经 (来俊臣) .md", "罗织经"),
    ("资治通鉴(汇评精注)(套装共6册)（无障碍阅读版，纸质书畅销数百万册！文白对照、原文精校、注音注释、译文精准，全本附年表） (中国经典古典名著) - 司马光.md", "资治通鉴"),
    ("骗局之王：查尔斯·庞兹自传.md", "骗局之王"),
]


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    copied = 0
    for idx, (src_name, short_title) in enumerate(BOOK_MAP, start=1):
        src = SOURCE / src_name
        dst = TARGET / f"{idx:03d}-{short_title}.md"
        if not src.exists():
            print(f"[跳过] 源文件不存在: {src_name}")
            continue
        shutil.copy2(src, dst)
        copied += 1
        print(f"[复制] {src_name} -> {dst.name}")
    print(f"\n完成: {copied} 个文件已复制到 corpus/raw/")


if __name__ == "__main__":
    main()
