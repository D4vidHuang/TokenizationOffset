#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule-level Alignment 结果分析脚本
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_and_analyze_results():
    """加载并分析结果"""
    
    # 读取汇总报告
    summary_file = Path("results/summary_gpt2.json")
    if not summary_file.exists():
        print("错误: 找不到汇总报告文件")
        return
    
    with open(summary_file, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # 读取详细报告
    detail_file = Path("results/rule_level_report_gpt2.json")
    if not detail_file.exists():
        print("错误: 找不到详细报告文件")
        return
    
    with open(detail_file, 'r', encoding='utf-8') as f:
        detail_report = json.load(f)
    
    print("=" * 80)
    print("Rule-level Tokenization Alignment Score 分析报告")
    print("=" * 80)
    print(f"模型: {summary['model_name']}")
    print(f"分析文件数: {summary['analyzed_files']}")
    print(f"平均 Rule-level Alignment Score: {summary['average_score']:.2f}%")
    print()
    
    # 按文件显示分数
    print("各文件的 Rule-level Alignment Score:")
    print("-" * 50)
    file_scores = summary['file_scores']
    for file_name, score in sorted(file_scores, key=lambda x: x[1], reverse=True):
        print(f"{file_name:<40} {score:>6.2f}%")
    
    print()
    
    # 分析规则类型统计
    rule_type_stats = detail_report['rule_type_stats']
    print("规则类型对齐情况分析:")
    print("-" * 50)
    
    # 按总数排序显示前10个最常见的规则类型
    sorted_rule_types = sorted(rule_type_stats.items(), 
                              key=lambda x: x[1]['total'], reverse=True)[:10]
    
    print("前10个最常见的规则类型:")
    for rule_type, stats in sorted_rule_types:
        print(f"{rule_type:<25} 总数: {stats['total']:>3}, "
              f"对齐: {stats['aligned']:>3}, "
              f"对齐率: {stats['alignment_rate']:>5.1f}%")
    
    print()
    
    # 按对齐率排序显示最难对齐的规则类型
    sorted_by_rate = sorted(rule_type_stats.items(), 
                           key=lambda x: x[1]['alignment_rate'])[:10]
    
    print("对齐率最低的10个规则类型:")
    for rule_type, stats in sorted_by_rate:
        if stats['total'] >= 5:  # 只显示出现次数较多的
            print(f"{rule_type:<25} 总数: {stats['total']:>3}, "
                  f"对齐: {stats['aligned']:>3}, "
                  f"对齐率: {stats['alignment_rate']:>5.1f}%")
    
    print()
    
    # 深度分析
    depth_stats = detail_report['depth_stats']
    print("按嵌套深度的对齐情况:")
    print("-" * 30)
    for depth in sorted(depth_stats.keys()):
        stats = depth_stats[str(depth)]
        print(f"深度 {depth}: {stats['aligned']:>3}/{stats['total']:>3} "
              f"({stats['alignment_rate']:>5.1f}%)")
    
    # 生成详细的可视化图表
    generate_detailed_charts(summary, detail_report)

def generate_detailed_charts(summary, detail_report):
    """生成详细的可视化图表"""
    
    # 1. 文件分数对比图
    file_scores = summary['file_scores']
    files = [item[0].split('/')[-1] for item in file_scores]  # 只取文件名
    scores = [item[1] for item in file_scores]
    
    plt.figure(figsize=(12, 8))
    bars = plt.bar(range(len(files)), scores, color='skyblue', edgecolor='navy', alpha=0.7)
    plt.xlabel('Python 文件')
    plt.ylabel('Rule-level Alignment Score (%)')
    plt.title(f'各文件的 Rule-level Alignment Score - {summary["model_name"]}')
    plt.xticks(range(len(files)), files, rotation=45, ha='right')
    
    # 添加平均线
    avg_score = summary['average_score']
    plt.axhline(y=avg_score, color='red', linestyle='--', alpha=0.8, 
                label=f'平均分: {avg_score:.2f}%')
    
    # 添加数值标签
    for i, (bar, score) in enumerate(zip(bars, scores)):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{score:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.legend()
    plt.tight_layout()
    plt.savefig('results/file_scores_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. 规则类型对齐率热力图（前20个最常见的规则类型）
    rule_type_stats = detail_report['rule_type_stats']
    sorted_rule_types = sorted(rule_type_stats.items(), 
                              key=lambda x: x[1]['total'], reverse=True)[:20]
    
    rule_names = [item[0] for item in sorted_rule_types]
    alignment_rates = [item[1]['alignment_rate'] for item in sorted_rule_types]
    totals = [item[1]['total'] for item in sorted_rule_types]
    
    # 创建热力图数据
    data = np.array(alignment_rates).reshape(1, -1)
    
    plt.figure(figsize=(16, 4))
    sns.heatmap(data, 
                xticklabels=rule_names,
                yticklabels=['对齐率'],
                annot=True, 
                fmt='.1f',
                cmap='RdYlBu_r',
                cbar_kws={'label': '对齐率 (%)'})
    
    plt.title('前20个最常见规则类型的对齐率热力图')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('results/rule_type_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. 深度vs对齐率散点图
    depth_stats = detail_report['depth_stats']
    depths = [int(d) for d in depth_stats.keys()]
    rates = [depth_stats[str(d)]['alignment_rate'] for d in depths]
    totals = [depth_stats[str(d)]['total'] for d in depths]
    
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(depths, rates, s=[t*2 for t in totals], 
                         alpha=0.6, c=rates, cmap='viridis')
    
    plt.xlabel('嵌套深度')
    plt.ylabel('对齐率 (%)')
    plt.title('嵌套深度 vs 对齐率 (气泡大小表示规则数量)')
    plt.colorbar(scatter, label='对齐率 (%)')
    plt.grid(True, alpha=0.3)
    
    # 添加趋势线
    z = np.polyfit(depths, rates, 1)
    p = np.poly1d(z)
    plt.plot(depths, p(depths), "r--", alpha=0.8, label=f'趋势线 (斜率: {z[0]:.2f})')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig('results/depth_vs_alignment.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. 对齐率分布直方图
    all_rates = [stats['alignment_rate'] for stats in rule_type_stats.values()]
    
    plt.figure(figsize=(10, 6))
    plt.hist(all_rates, bins=20, alpha=0.7, color='lightblue', edgecolor='black')
    plt.axvline(x=np.mean(all_rates), color='red', linestyle='--', 
                label=f'平均对齐率: {np.mean(all_rates):.1f}%')
    plt.axvline(x=np.median(all_rates), color='green', linestyle='--', 
                label=f'中位数对齐率: {np.median(all_rates):.1f}%')
    
    plt.xlabel('对齐率 (%)')
    plt.ylabel('规则类型数量')
    plt.title('规则类型对齐率分布')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('results/alignment_rate_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("\n详细可视化图表已生成:")
    print("- results/file_scores_comparison.png: 各文件分数对比")
    print("- results/rule_type_heatmap.png: 规则类型对齐率热力图")
    print("- results/depth_vs_alignment.png: 深度vs对齐率分析")
    print("- results/alignment_rate_distribution.png: 对齐率分布直方图")

def generate_insights():
    """生成分析洞察"""
    
    print("\n" + "=" * 80)
    print("分析洞察和建议")
    print("=" * 80)
    
    print("""
主要发现:

1. 整体对齐情况:
   - 平均 Rule-level Alignment Score 为 27.05%，表明 GPT-2 的 tokenization 
     与 Python 语法规则边界的对齐程度较低
   - 这意味着约 73% 的语法规则边界与 token 边界不匹配

2. 文件间差异:
   - data_structures.py 表现最好 (34.98%)
   - async_example.py 表现最差 (19.61%)
   - 不同类型的代码结构对对齐效果有显著影响

3. 规则类型分析:
   - identifier (标识符) 是最常见的规则类型，但对齐率只有约 25-35%
   - expression_statement (表达式语句) 的对齐率普遍较低
   - 函数调用 (call) 和参数列表 (argument_list) 的对齐率特别低

4. 嵌套深度影响:
   - 不同嵌套深度的对齐率存在差异
   - 需要进一步分析深度与对齐率的关系

建议:

1. 对于代码生成任务:
   - 考虑在语法规则边界处进行特殊处理
   - 可能需要后处理步骤来修正边界不匹配问题

2. 对于模型训练:
   - 可以考虑使用语法感知的 tokenization 策略
   - 在预训练时加入语法结构信息

3. 对于代码理解任务:
   - 需要考虑 tokenization 边界对语法理解的影响
   - 可能需要结合语法解析器来提高理解准确性

4. 进一步研究方向:
   - 比较不同模型 (CodeLlama, StarCoder 等) 的表现
   - 分析不同编程语言的对齐情况
   - 研究改进 tokenization 策略的方法
""")

if __name__ == "__main__":
    load_and_analyze_results()
    generate_insights()