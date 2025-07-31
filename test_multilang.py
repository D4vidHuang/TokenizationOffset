#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语言支持测试脚本
"""

from multilang_rule_analysis import MultiLanguageRuleLevelAnalyzer
from pathlib import Path

def test_multilang_support():
    """测试多语言支持"""
    
    print("=" * 60)
    print("多语言 Rule-level Alignment Score 测试")
    print("=" * 60)
    
    # 创建分析器
    analyzer = MultiLanguageRuleLevelAnalyzer("gpt2")
    
    # 测试代码样本
    test_codes = {
        'python': '''
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        return x + y
''',
        
        'javascript': '''
function fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n-1) + fibonacci(n-2);
}

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(x, y) {
        return x + y;
    }
}
''',
        
        'java': '''
public class Calculator {
    private int result;
    
    public Calculator() {
        this.result = 0;
    }
    
    public int add(int x, int y) {
        return x + y;
    }
    
    public static int fibonacci(int n) {
        if (n <= 1) {
            return n;
        }
        return fibonacci(n-1) + fibonacci(n-2);
    }
}
''',
        
        'c': '''
#include <stdio.h>

int fibonacci(int n) {
    if (n <= 1) {
        return n;
    }
    return fibonacci(n-1) + fibonacci(n-2);
}

int main() {
    int result = fibonacci(10);
    printf("Fibonacci(10) = %d\\n", result);
    return 0;
}
''',
        
        'go': '''
package main

import "fmt"

func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}

type Calculator struct {
    result int
}

func (c *Calculator) Add(x, y int) int {
    return x + y
}

func main() {
    calc := Calculator{}
    fmt.Printf("Fibonacci(5) = %d\\n", fibonacci(5))
    fmt.Printf("3 + 4 = %d\\n", calc.Add(3, 4))
}
'''
    }
    
    # 测试每种语言
    results = {}
    
    for language, code in test_codes.items():
        print(f"\n正在测试 {language.upper()}:")
        print("-" * 40)
        
        try:
            score, details = analyzer.calculate_rule_level_alignment(code, language)
            
            results[language] = {
                'score': score,
                'total_rules': len(details),
                'aligned_rules': sum(1 for d in details.values() if d['fully_aligned'])
            }
            
            print(f"Rule-level Alignment Score: {score:.2f}%")
            print(f"总规则数: {len(details)}")
            print(f"对齐规则数: {sum(1 for d in details.values() if d['fully_aligned'])}")
            
            # 显示前3个最常见的规则类型
            rule_type_stats = analyzer.analyze_by_rule_type(details)
            sorted_types = sorted(rule_type_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:3]
            
            print("前3个最常见的规则类型:")
            for rule_type, stats in sorted_types:
                print(f"  {rule_type}: {stats['aligned']}/{stats['total']} ({stats['alignment_rate']:.1f}% 对齐)")
            
        except Exception as e:
            print(f"测试 {language} 时出错: {e}")
            results[language] = {'error': str(e)}
    
    # 显示汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    
    successful_tests = {k: v for k, v in results.items() if 'error' not in v}
    failed_tests = {k: v for k, v in results.items() if 'error' in v}
    
    if successful_tests:
        print(f"\n成功测试的语言 ({len(successful_tests)}/{len(test_codes)}):")
        for language, result in successful_tests.items():
            print(f"  {language}: {result['score']:.2f}% (规则数: {result['total_rules']})")
    
    if failed_tests:
        print(f"\n失败的语言 ({len(failed_tests)}/{len(test_codes)}):")
        for language, result in failed_tests.items():
            print(f"  {language}: {result['error']}")
    
    # 计算平均分数
    if successful_tests:
        avg_score = sum(r['score'] for r in successful_tests.values()) / len(successful_tests)
        print(f"\n平均 Rule-level Alignment Score: {avg_score:.2f}%")


def test_directory_analysis():
    """测试目录分析功能"""
    
    print(f"\n{'='*60}")
    print("目录分析测试")
    print(f"{'='*60}")
    
    analyzer = MultiLanguageRuleLevelAnalyzer("gpt2")
    
    # 测试分析 code_samples 目录
    code_samples_dir = Path("code_samples")
    
    if code_samples_dir.exists():
        print(f"正在分析目录: {code_samples_dir}")
        
        try:
            summary = analyzer.analyze_directory(str(code_samples_dir), output_dir="results/multilang_test")
            
            if summary:
                print(f"\n目录分析完成:")
                print(f"分析文件数: {summary['analyzed_files']}")
                print(f"平均分数: {summary['average_score']:.2f}%")
                
                # 按语言统计
                lang_stats = {}
                for file_path, result in summary['file_results'].items():
                    lang = result['language']
                    if lang not in lang_stats:
                        lang_stats[lang] = {'files': 0, 'total_score': 0}
                    lang_stats[lang]['files'] += 1
                    lang_stats[lang]['total_score'] += result['rule_level_score']
                
                print(f"\n按语言统计:")
                for lang, stats in sorted(lang_stats.items()):
                    avg_score = stats['total_score'] / stats['files']
                    print(f"  {lang}: {stats['files']} 个文件, 平均: {avg_score:.2f}%")
            
        except Exception as e:
            print(f"目录分析失败: {e}")
    else:
        print(f"目录 {code_samples_dir} 不存在，跳过目录分析测试")


if __name__ == "__main__":
    test_multilang_support()
    test_directory_analysis()
