#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版测试脚本 - 配合 quick_analyzer.py 使用
测试基本的 Tree-sitter 解析和对齐分数计算功能
"""

import os
import sys
from pathlib import Path
from tree_sitter import Language, Parser
from transformers import AutoTokenizer

def test_quick_analyzer_functionality():
    """测试 quick_analyzer.py 的核心功能"""
    print("=" * 60)
    print("Quick Analyzer 功能测试")
    print("=" * 60)
    
    try:
        # 检查编译好的语言库
        build_dir = Path('./build')
        python_library_path = build_dir / 'languages_python.so'
        
        if not python_library_path.exists():
            print("❌ 未找到 Python 语言库")
            print("请先运行 quick_analyzer.py 来编译语言库")
            return False
        
        print("✓ 找到 Python 语言库")
        
        # 测试 Python 解析器
        print("\n正在测试 Python 解析器...")
        parser = Parser()
        
        try:
            python_language = Language(str(python_library_path), 'python')
            parser.set_language(python_language)
            print("✓ Python 解析器加载成功")
        except Exception as e:
            print(f"❌ Python 解析器加载失败: {e}")
            return False
        
        # 初始化 tokenizer
        print("\n正在初始化 tokenizer...")
        try:
            tokenizer = AutoTokenizer.from_pretrained('gpt2')
            print("✓ GPT-2 tokenizer 加载成功")
        except Exception as e:
            print(f"❌ Tokenizer 加载失败: {e}")
            return False
        
        # 测试代码样本
        test_code = '''
def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 测试函数
for i in range(10):
    result = fibonacci(i)
    print(f"fibonacci({i}) = {result}")
'''
        
        print("\n正在分析测试代码...")
        
        # 解析代码
        code_bytes = test_code.encode('utf-8')
        tree = parser.parse(code_bytes)
        
        if tree.root_node.has_error:
            print("❌ 代码解析出现错误")
            return False
        
        print("✓ 代码解析成功")
        
        # 提取语法规则
        def extract_rules(node, rules=None):
            if rules is None:
                rules = []
            
            if node.type and not node.type.startswith('ERROR'):
                rules.append({
                    'type': node.type,
                    'start_byte': node.start_byte,
                    'end_byte': node.end_byte,
                    'start_point': node.start_point,
                    'end_point': node.end_point,
                    'text': code_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')[:30]
                })
            
            for child in node.children:
                extract_rules(child, rules)
            
            return rules
        
        rules = extract_rules(tree.root_node)
        print(f"✓ 提取到 {len(rules)} 个语法规则")
        
        # Tokenization
        tokens = tokenizer.encode(test_code)
        token_texts = [tokenizer.decode([token]) for token in tokens]
        print(f"✓ 生成 {len(tokens)} 个 tokens")
        
        # 计算 token 边界
        token_boundaries = []
        current_pos = 0
        
        for token_text in token_texts:
            # 处理特殊字符
            if token_text.strip():
                token_start = test_code.find(token_text, current_pos)
                if token_start != -1:
                    token_end = token_start + len(token_text)
                    token_boundaries.append((token_start, token_end))
                    current_pos = token_end
                else:
                    # 如果找不到，使用当前位置
                    token_boundaries.append((current_pos, current_pos + 1))
                    current_pos += 1
            else:
                token_boundaries.append((current_pos, current_pos + 1))
                current_pos += 1
        
        print(f"✓ 计算 token 边界完成")
        
        # 计算对齐分数
        aligned_rules = 0
        tolerance = 1  # 允许1字符的误差
        
        for rule in rules:
            rule_start = rule['start_byte']
            rule_end = rule['end_byte']
            
            # 检查起始位置对齐
            start_aligned = any(abs(rule_start - tb[0]) <= tolerance for tb in token_boundaries)
            # 检查结束位置对齐
            end_aligned = any(abs(rule_end - tb[1]) <= tolerance for tb in token_boundaries)
            
            if start_aligned and end_aligned:
                aligned_rules += 1
        
        # 计算最终分数
        alignment_score = (aligned_rules / len(rules) * 100) if rules else 0
        
        print("\n" + "=" * 40)
        print("测试结果")
        print("=" * 40)
        print(f"Rule-level Alignment Score: {alignment_score:.2f}%")
        print(f"总语法规则数: {len(rules)}")
        print(f"对齐规则数: {aligned_rules}")
        print(f"Token 总数: {len(tokens)}")
        print(f"Token 边界数: {len(token_boundaries)}")
        
        # 显示规则类型统计
        rule_types = {}
        for rule in rules:
            rule_type = rule['type']
            rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
        
        print(f"\n语法规则类型统计 (前10种):")
        sorted_rules = sorted(rule_types.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (rule_type, count) in enumerate(sorted_rules, 1):
            print(f"  {i:2d}. {rule_type}: {count}")
        
        # 显示一些示例规则
        print(f"\n示例语法规则 (前5个):")
        for i, rule in enumerate(rules[:5], 1):
            text_preview = rule['text'].replace('\n', '\\n')
            print(f"  {i}. {rule['type']}: '{text_preview}'")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_code_samples():
    """测试 code_samples 目录中的文件"""
    print("\n" + "=" * 60)
    print("测试代码样本目录")
    print("=" * 60)
    
    code_samples_dir = Path('./code_samples')
    if not code_samples_dir.exists():
        print("❌ code_samples 目录不存在")
        return False
    
    print("✓ code_samples 目录存在")
    
    # 检查各语言的样本文件目录
    expected_dirs = {
        'python': 'python',
        'javascript': 'javascript', 
        'typescript': 'typescript',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'csharp': 'csharp',
        'go': 'go',
        'ruby': 'ruby',
        'rust': 'rust',
        'scala': 'scala'
    }
    
    found_files = 0
    total_files = 0
    
    for lang, dirname in expected_dirs.items():
        dir_path = code_samples_dir / dirname
        if dir_path.exists() and dir_path.is_dir():
            # 统计目录中的文件
            files = list(dir_path.glob('*'))
            file_count = len([f for f in files if f.is_file()])
            if file_count > 0:
                print(f"✓ {dirname}/ ({file_count} 个文件)")
                found_files += 1
                total_files += file_count
            else:
                print(f"⚠️  {dirname}/ (目录为空)")
        else:
            print(f"❌ {dirname}/ 目录不存在")
    
    print(f"\n找到 {found_files}/{len(expected_dirs)} 个语言目录，共 {total_files} 个样本文件")
    return found_files > 0

def main():
    """主测试函数"""
    print("Quick Analyzer 简化测试")
    print("测试 Tree-sitter rule-level alignment score 计算功能")
    
    # 测试核心功能
    core_test_passed = test_quick_analyzer_functionality()
    
    # 测试代码样本
    samples_test_passed = test_code_samples()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if core_test_passed:
        print("✓ 核心功能测试通过")
    else:
        print("❌ 核心功能测试失败")
    
    if samples_test_passed:
        print("✓ 代码样本测试通过")
    else:
        print("❌ 代码样本测试失败")
    
    if core_test_passed and samples_test_passed:
        print("\n🎉 所有测试通过！可以使用 quick_analyzer.py 进行完整分析")
        print("\n建议运行命令:")
        print("  python quick_analyzer.py")
    else:
        print("\n⚠️  部分测试失败，请检查环境配置")
        if not core_test_passed:
            print("  - 请确保已安装所有依赖: pip install -r requirements.txt")
            print("  - 请先运行 quick_analyzer.py 来编译语言库")
    
    return core_test_passed and samples_test_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)