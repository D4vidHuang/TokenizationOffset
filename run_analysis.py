#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tree-sitter Rule-level Alignment Score 分析运行脚本
提供简单的命令行界面来运行各种分析功能
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"正在执行: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✓ {description} 完成")
            return True
        else:
            print(f"❌ {description} 失败")
            return False
    except Exception as e:
        print(f"❌ 执行错误: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Tree-sitter Rule-level Alignment Score 分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_analysis.py --test                    # 运行环境测试
  python run_analysis.py --analyze                 # 运行所有语言分析
  python run_analysis.py --language python         # 只分析指定语言
  python run_analysis.py --visualize               # 生成可视化图表
  python run_analysis.py --all                     # 运行所有功能
  python run_analysis.py --language python --visualize  # 分析指定语言并生成图表
        """
    )
    
    parser.add_argument('--test', action='store_true', 
                       help='运行简单测试脚本')
    parser.add_argument('--analyze', action='store_true', 
                       help='运行完整的多语言分析')
    parser.add_argument('--visualize', action='store_true', 
                       help='生成可视化图表')
    parser.add_argument('--all', action='store_true', 
                       help='运行所有功能（测试 + 分析 + 可视化）')
    parser.add_argument('--language', type=str, 
                       help='指定要分析的语言（如：python, javascript）')
    
    args = parser.parse_args()
    
    # 检查必要文件是否存在
    required_files = ['quick_analyzer.py', 'simple_test.py', 'visualize_multilang_results.py']
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for file in missing_files:
            print(f"  - {file}")
        return 1
    
    print("Tree-sitter Rule-level Alignment Score 分析工具")
    print("=" * 60)
    
    success_count = 0
    total_count = 0
    
    # 如果指定了语言但没有指定操作，默认执行分析
    if args.language and not any([args.test, args.analyze, args.visualize, args.all]):
        args.analyze = True
    
    # 如果没有指定任何参数，显示帮助
    if not any([args.test, args.analyze, args.visualize, args.all]):
        parser.print_help()
        return 0
    
    # 运行测试
    if args.test or args.all:
        total_count += 1
        if run_command("python simple_test.py", "环境测试"):
            success_count += 1
    
    # 运行分析
    if args.analyze or args.all:
        total_count += 1
        if args.language:
            command = f"python quick_analyzer.py --language {args.language}"
            description = f"{args.language} 语言分析"
        elif args.all:
            command = "python quick_analyzer.py --all_languages"
            description = "所有语言分析"
        else:
            command = "python quick_analyzer.py"
            description = "多语言分析"
        
        if run_command(command, description):
            success_count += 1
    
    # 生成可视化
    if args.visualize or args.all:
        total_count += 1
        if run_command("python visualize_multilang_results.py", "生成可视化图表"):
            success_count += 1
    
    # 显示总结
    print(f"\n{'='*60}")
    print("执行总结")
    print(f"{'='*60}")
    print(f"成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 所有任务执行成功！")
        
        if args.all or args.analyze:
            print("\n📊 分析结果位置:")
            print("  - 详细报告: results/multilang/")
            print("  - 可视化图表: results/multilang/ (如果生成)")
        
        print("\n📖 更多信息请查看:")
        print("  - README_multilang.md - 详细使用说明")
        print("  - project_status.md - 项目状态报告")
        
        return 0
    else:
        print("⚠️  部分任务执行失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())