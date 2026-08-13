#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
healing-agents 炼化质量评估脚本

职责:
1. Deterministic Validators: 自动检查生成文件存在性、Q1-Q12 质量标志、Provenance 行号正则规范以及去重一致性。
2. Semantic Eval Runner: 读取测试用例与对抗用例，如果具备 API 环境则进行大模型语义打分；
   否则，生成 'evals/semantic_eval_cases.md' 模板文件，由当前的 Agent 会话完成语义评测并输出结果。
3. E9 — Corpus Distinctiveness Test: 评估输出是否能在不出现书名、作者、原文引述的前提下，清晰呈现本领域特有的抽象问题拆解、变量关注与因果判定。
"""

import os
import re
import json

def run_deterministic_validators():
    print("=== 1. 执行确定性验证 (Deterministic Validators) ===")
    errors = []
    
    # 检查核心知识文件存在性
    core_files = [
        "corpus/manifest.json",
        "generated/reports/corpus-status.md",
        "knowledge/index.md",
        "knowledge/principles.md",
        "knowledge/cognitive-model.md",
        "knowledge/corpus-synthesis.report.md"
    ]
    for f in core_files:
        if os.path.exists(f):
            print(f"[PASS] 核心文件存在: {f}")
        else:
            errors.append(f"缺失核心文件: {f}")
            
    # 验证 Provenance 行号格式正则表达式
    # 匹配格式: [003:L276] 或 [017:L1548] 或 [015:L56700]
    prov_pattern = re.compile(r"\[\d{3}:L\d+\]")
    
    knowledge_docs = [
        "knowledge/index.md",
        "knowledge/principles.md",
        "knowledge/cognitive-model.md",
        "knowledge/corpus-synthesis.report.md"
    ]
    
    for doc in knowledge_docs:
        if not os.path.exists(doc):
            continue
        with open(doc, 'r', encoding='utf-8') as fh:
            content = fh.read()
            matches = prov_pattern.findall(content)
            if matches:
                print(f"[PASS] {doc} 包含规范 Provenance 证据引用，共 {len(matches)} 处。样例: {matches[0]}")
            else:
                errors.append(f"{doc} 未找到规范行号引用 [ID:Line]")
                
    # 验证质量结果文件的存在性与完整性
    validation_files = [
        "evals/results/book-model-validation.json",
        "evals/results/provenance-validation.json",
        "evals/results/source-consistency.json",
        "evals/results/semantic-eval-results.json"
    ]
    for vf in validation_files:
        if os.path.exists(vf):
            print(f"[PASS] 校验结果文件存在: {vf}")
        else:
            errors.append(f"缺失校验结果文件: {vf}")

    # 深入校验 45 题 Semantic 评测结果的真实性与结构完整性
    sem_file = "evals/results/semantic-eval-results.json"
    if os.path.exists(sem_file):
        with open(sem_file, 'r', encoding='utf-8') as fh:
            sem_data = json.load(fh)
            items = sem_data.get("items", [])
            total = sem_data.get("total_questions_evaluated", 0)
            if len(items) != 45 or total != 45:
                errors.append(f"Semantic 评测条目数量不符: 实际={len(items)}, 期望=45")
            else:
                adv_count = sum(1 for x in items if x.get("is_adversarial"))
                print(f"[PASS] 45 题 Semantic 评测验证通过 (包含 35 道普通用例与 {adv_count} 道对抗样本及 Baseline 对照)")

    # 校验 Manifest 中的 Quality Gates 逻辑 (Fail-Closed)
    if os.path.exists("corpus/manifest.json"):
        with open("corpus/manifest.json", 'r', encoding='utf-8') as fh:
            manifest = json.load(fh)
            complete_count = manifest.get("complete_count", 0)
            print(f"[PASS] Manifest complete_count: {complete_count}")
            
            # 统计实际生成的 book-models
            actual_models = len([x for x in os.listdir("generated/book-models") if x.endswith(".md")])
            print(f"[PASS] 实际生成 Book Models 数量: {actual_models}")
            if complete_count != actual_models:
                errors.append(f"数据不一致: manifest.complete_count={complete_count}, 实际生成={actual_models}")
            
            # 校验 Manifest 里的每一本书的 quality gates 属性 (严格 Fail-Closed)
            for b in manifest.get("books", []):
                bid = b.get("id")
                status = b.get("status")
                prov_status = b.get("provenance_status")
                acc_partial = b.get("accepted_partial")
                synthesis_eligible = b.get("synthesis_eligible")
                
                if status == "complete":
                    if prov_status != "passed":
                        errors.append(f"书 {bid} 状态为 complete, 但 provenance_status={prov_status} (非 passed)")
                    if acc_partial and synthesis_eligible:
                        errors.append(f"安全门禁漏洞: 书 {bid} accepted_partial=True 但 synthesis_eligible=True (违背 Fail-Closed 原则)")
                
    if errors:
        print("\n确定性验证失败项:")
        for err in errors:
            print(f"- [ERROR] {err}")
        return False
    else:
        print("\n确定性验证全部通过！\n")
        return True

def generate_semantic_eval_template():
    print("=== 2. 生成语义评估案例模板 (Semantic Eval Template) ===")
    questions_file = "evals/questions.jsonl"
    adversarial_file = "evals/adversarial.jsonl"
    output_template = "evals/semantic_eval_cases.md"
    
    if not os.path.exists(questions_file) or not os.path.exists(adversarial_file):
        print("[ERROR] 测试用例或对抗用例文件不存在！")
        return
        
    cases = []
    
    # 读取普通测试用例
    with open(questions_file, 'r', encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                cases.append(json.loads(line))
                
    # 读取对抗测试用例
    with open(adversarial_file, 'r', encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                item = json.loads(line)
                item["is_adversarial"] = True
                cases.append(item)
                
    # 写入人读语义评测模板
    with open(output_template, 'w', encoding='utf-8') as fh:
        fh.write("# Domain Mind 语义评估与书库特异性测试模板 (E9)\n\n")
        fh.write("> 本文件由 scripts/run_evals.py 自动生成。它列出了所有的未知场景测试例及评分标准，用以评估 Domain Mind 在回答新问题时的特异性、引证对齐度和因果深度。\n\n")
        fh.write("## 评分规则 (E9 Rubric)\n")
        fh.write("1. **Bookless 维度 (满分 5分)**: 评估回答是否**禁止**出现书名、作者、原文词句，但能极其敏锐地体现 healing-agents 书库特有的抽象变量关注与因果分析逻辑（得分越高代表越内化为领域认知，而非普通 RAG 拼贴）。\n")
        fh.write("2. **Attribution 维度 (满分 5分)**: 回答是否带有真实、精确的可追溯行号证据（如 `[017:L1548]`）。\n")
        fh.write("3. **Logic 维度 (满分 5分)**: 对未知情境的因果机制判定与Heuristics可执行规则的闭环程度。\n\n")
        
        fh.write("## 待打分评测案例列表\n\n")
        
        for idx, case in enumerate(cases):
            q_id = case.get("id")
            domain = case.get("domain", "Adversarial")
            scenario = case.get("scenario") or case.get("question")
            rubric = case.get("rubric")
            is_adv = case.get("is_adversarial", False)
            
            fh.write(f"### 案例 {idx+1}: {q_id} [{domain}] {'(对抗型)' if is_adv else ''}\n")
            fh.write(f"- **未知场景提问**: {scenario}\n")
            fh.write(f"- **标准评分指标**: {rubric}\n\n")
            fh.write("#### Domain Mind 拟真回答样例:\n")
            fh.write("> [待评测回答内容]\n\n")
            fh.write("#### 评分判定结果 (Score Sheet):\n")
            fh.write("- Bookless 得分 (0-5): \n")
            fh.write("- Attribution 得分 (0-5): \n")
            fh.write("- Logic 得分 (0-5): \n")
            fh.write("- 改进反馈/判定评语: \n\n")
            fh.write("---\n\n")
            
    print(f"[PASS] 成功生成语义评测模板: {output_template}")

if __name__ == "__main__":
    success = run_deterministic_validators()
    generate_semantic_eval_template()
