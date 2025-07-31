#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule-level Alignment Score 演示脚本
"""

from rule_level_analysis import RuleLevelAlignmentAnalyzer

def demo_simple_analysis():
    """演示简单的分析功能"""
    
    print("=" * 60)
    print("Rule-level Tokenization Alignment Score 演示")
    print("=" * 60)
    
    # 创建分析器
    analyzer = RuleLevelAlignmentAnalyzer("gpt2")
    
    # 示例代码
    sample_code = '''
def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        self.result = x + y
        return self.result

# 使用示例
calc = Calculator()
print(f"fibonacci(5) = {fibonacci(5)}")
print(f"3 + 4 = {calc.add(3, 4)}")
'''
    
    print("分析的代码:")
    print("-" * 40)
    print(sample_code)
    print("-" * 40)
    
    # 计算对齐分数
    score, details = analyzer.calculate_rule_level_alignment(sample_code)
    
    print(f"\nRule-level Alignment Score: {score:.2f}%")
    print(f"总规则数: {len(details)}")
    
    # 显示一些具体的规则对齐情况
    print("\n部分规则对齐详情:")
    print("-" * 50)
    
    count = 0
    for node_id, detail in details.items():
        if count >= 10:  # 只显示前10个
            break
        
        status = "✓ 对齐" if detail['fully_aligned'] else "✗ 不对齐"
        code_snippet = detail['code_snippet'][:30] + ('...' if len(detail['code_snippet']) > 30 else '')
        
        print(f"{detail['type']:<20} {status:<8} '{code_snippet}'")
        count += 1
    
    # 按规则类型分析
    rule_type_stats = analyzer.analyze_by_rule_type(details)
    
    print(f"\n规则类型统计 (前5个):")
    print("-" * 40)
    sorted_types = sorted(rule_type_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:5]
    
    for rule_type, stats in sorted_types:
        print(f"{rule_type:<20} {stats['aligned']:>2}/{stats['total']:>2} ({stats['alignment_rate']:>5.1f}%)")

if __name__ == "__main__":
    demo_simple_analysis()