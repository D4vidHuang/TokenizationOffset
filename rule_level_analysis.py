#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rule-level Tokenization Alignment Score 计算器

该脚本计算 Python 代码在 GPT-2 模型上的规则级别标记化对齐分数。
它分析 tree-sitter 语法规则边界与 tokenizer 标记边界之间的对齐情况。
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Tuple, Any, Set
from pathlib import Path

# 安装必要的依赖
try:
    import tree_sitter
    from tree_sitter import Language, Parser
except ImportError:
    print("正在安装 tree-sitter...")
    os.system("pip install tree-sitter")
    import tree_sitter
    from tree_sitter import Language, Parser

try:
    from transformers import AutoTokenizer
except ImportError:
    print("正在安装 transformers...")
    os.system("pip install transformers")
    from transformers import AutoTokenizer

try:
    import pandas as pd
except ImportError:
    print("正在安装 pandas...")
    os.system("pip install pandas")
    import pandas as pd

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    print("正在安装 matplotlib 和 seaborn...")
    os.system("pip install matplotlib seaborn")
    import matplotlib.pyplot as plt
    import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class TreeSitterSetup:
    """Tree-sitter 设置和管理类"""
    
    # 支持的语言及其仓库信息
    SUPPORTED_LANGUAGES = {
        'python': 'https://github.com/tree-sitter/tree-sitter-python.git',
        'javascript': 'https://github.com/tree-sitter/tree-sitter-javascript.git',
        'typescript': 'https://github.com/tree-sitter/tree-sitter-typescript.git',
        'java': 'https://github.com/tree-sitter/tree-sitter-java.git',
        'c': 'https://github.com/tree-sitter/tree-sitter-c.git',
        'cpp': 'https://github.com/tree-sitter/tree-sitter-cpp.git',
        'csharp': 'https://github.com/tree-sitter/tree-sitter-c-sharp.git',
        'go': 'https://github.com/tree-sitter/tree-sitter-go.git',
        'ruby': 'https://github.com/tree-sitter/tree-sitter-ruby.git',
        'rust': 'https://github.com/tree-sitter/tree-sitter-rust.git',
        'scala': 'https://github.com/tree-sitter/tree-sitter-scala.git'
    }
    
    # 语言名称映射（用于 tree-sitter Language 构造）
    LANGUAGE_NAMES = {
        'python': 'python',
        'javascript': 'javascript',
        'typescript': 'typescript',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'csharp': 'c_sharp',
        'go': 'go',
        'ruby': 'ruby',
        'rust': 'rust',
        'scala': 'scala'
    }
    
    # 文件扩展名映射
    FILE_EXTENSIONS = {
        'python': ['.py'],
        'javascript': ['.js'],
        'typescript': ['.ts'],
        'java': ['.java'],
        'c': ['.c', '.h'],
        'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.hxx'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'ruby': ['.rb'],
        'rust': ['.rs'],
        'scala': ['.scala']
    }
    
    def __init__(self):
        self.vendor_dir = Path("vendor")
        self.build_dir = Path("build")
        self.languages_so = self.build_dir / "languages.so"
        
    def setup_parser(self, language: str) -> Parser:
        """设置指定语言的 tree-sitter 解析器"""
        
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的语言: {language}. 支持的语言: {list(self.SUPPORTED_LANGUAGES.keys())}")
        
        # 创建必要的目录
        self.vendor_dir.mkdir(exist_ok=True)
        self.build_dir.mkdir(exist_ok=True)
        
        # 检查是否已经编译过
        if not self.languages_so.exists():
            self._build_all_languages()
        
        # 创建解析器
        try:
            language_name = self.LANGUAGE_NAMES[language]
            lang = Language(str(self.languages_so), language_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception as e:
            print(f"加载 {language} 语言失败: {e}")
            print("尝试重新编译...")
            self._build_all_languages()
            language_name = self.LANGUAGE_NAMES[language]
            lang = Language(str(self.languages_so), language_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
    
    def _build_all_languages(self):
        """编译所有支持语言的 tree-sitter 库"""
        print("正在准备编译所有支持的语言...")
        
        # 克隆所有语言仓库
        repo_paths = []
        for language, repo_url in self.SUPPORTED_LANGUAGES.items():
            repo_path = self.vendor_dir / f"tree-sitter-{language}"
            
            # 特殊处理一些仓库名称
            if language == 'csharp':
                repo_path = self.vendor_dir / "tree-sitter-c-sharp"
            
            if not repo_path.exists():
                print(f"正在克隆 {language} 仓库...")
                result = os.system(f"git clone {repo_url} {repo_path}")
                if result != 0:
                    print(f"警告: 克隆 {language} 仓库失败")
                    continue
            
            repo_paths.append(str(repo_path))
        
        # 编译语言库
        if repo_paths:
            print("正在编译语言库...")
            try:
                Language.build_library(str(self.languages_so), repo_paths)
                print("编译完成！")
            except Exception as e:
                print(f"编译失败: {e}")
                # 尝试逐个编译
                self._build_languages_individually(repo_paths)
    
    def _build_languages_individually(self, repo_paths):
        """逐个编译语言库（备用方案）"""
        print("尝试逐个编译语言...")
        successful_paths = []
        
        for repo_path in repo_paths:
            try:
                temp_so = self.build_dir / f"temp_{Path(repo_path).name}.so"
                Language.build_library(str(temp_so), [repo_path])
                successful_paths.append(repo_path)
                print(f"✓ {Path(repo_path).name} 编译成功")
            except Exception as e:
                print(f"✗ {Path(repo_path).name} 编译失败: {e}")
        
        if successful_paths:
            try:
                Language.build_library(str(self.languages_so), successful_paths)
                print(f"成功编译 {len(successful_paths)} 种语言")
            except Exception as e:
                print(f"最终编译失败: {e}")


class RuleLevelAlignmentAnalyzer:
    """规则级别对齐分析器"""
    
    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tree_sitter_setup = TreeSitterSetup()
        self.parser = self.tree_sitter_setup.setup_python_parser()
        
        # 如果 tokenizer 没有 pad_token，设置一个
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def calculate_rule_level_alignment(self, code: str) -> Tuple[float, Dict[str, Any]]:
        """
        计算给定代码的 rule-level alignment score
        
        Args:
            code: 源代码字符串
        
        Returns:
            rule_level_score: 规则级别的对齐分数
            rule_alignment_details: 每个规则的对齐详情
        """
        # 1. 使用 tree-sitter 解析代码
        tree = self.parser.parse(bytes(code, 'utf8'))
        
        # 2. 使用 tokenizer 对代码进行标记化
        encoding = self.tokenizer(code, return_offsets_mapping=True, add_special_tokens=False)
        token_boundaries = set()
        
        # 收集所有 token 边界
        for start, end in encoding.offset_mapping:
            if start >= 0:  # 包含起始位置
                token_boundaries.add(start)
            if end > 0:  # 包含结束位置
                token_boundaries.add(end)
        
        # 添加代码的开始和结束位置
        token_boundaries.add(0)
        token_boundaries.add(len(code.encode('utf8')))
        
        # 3. 遍历语法树，检查每个规则节点的对齐情况
        rule_alignment_details = {}
        
        def traverse_tree(node, depth=0):
            # 只考虑命名节点（规则节点），排除一些不重要的节点
            if not node.is_named:
                for child in node.children:
                    traverse_tree(child, depth)
                return
            
            # 跳过一些不重要的节点类型
            skip_types = {'comment', 'string_content', 'escape_sequence'}
            if node.type in skip_types:
                for child in node.children:
                    traverse_tree(child, depth)
                return
            
            # 检查该规则的边界是否与 token 边界对齐
            start_aligned = node.start_byte in token_boundaries
            end_aligned = node.end_byte in token_boundaries
            
            # 获取代码片段
            try:
                code_snippet = code.encode('utf8')[node.start_byte:node.end_byte].decode('utf8')
            except:
                code_snippet = f"<无法解码: {node.start_byte}-{node.end_byte}>"
            
            # 记录对齐详情
            rule_alignment_details[node.id] = {
                'type': node.type,
                'start_byte': node.start_byte,
                'end_byte': node.end_byte,
                'start_aligned': start_aligned,
                'end_aligned': end_aligned,
                'fully_aligned': start_aligned and end_aligned,
                'code_snippet': code_snippet,
                'depth': depth,
                'parent_type': node.parent.type if node.parent else None
            }
            
            # 递归处理子节点
            for child in node.children:
                traverse_tree(child, depth + 1)
        
        # 从根节点开始遍历
        traverse_tree(tree.root_node)
        
        # 4. 计算 rule-level alignment score
        aligned_rules = sum(1 for details in rule_alignment_details.values() if details['fully_aligned'])
        total_rules = len(rule_alignment_details)
        
        rule_level_score = (aligned_rules / total_rules) * 100 if total_rules > 0 else 100
        
        return rule_level_score, rule_alignment_details
    
    def analyze_by_rule_type(self, rule_alignment_details: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """按规则类型分析对齐情况"""
        rule_type_stats = {}
        
        for node_id, details in rule_alignment_details.items():
            rule_type = details['type']
            if rule_type not in rule_type_stats:
                rule_type_stats[rule_type] = {'total': 0, 'aligned': 0, 'examples': []}
            
            rule_type_stats[rule_type]['total'] += 1
            if details['fully_aligned']:
                rule_type_stats[rule_type]['aligned'] += 1
            
            # 保存一些示例
            if len(rule_type_stats[rule_type]['examples']) < 3:
                rule_type_stats[rule_type]['examples'].append({
                    'code_snippet': details['code_snippet'][:50] + ('...' if len(details['code_snippet']) > 50 else ''),
                    'aligned': details['fully_aligned']
                })
        
        # 计算每种规则类型的对齐率
        for rule_type, stats in rule_type_stats.items():
            stats['alignment_rate'] = (stats['aligned'] / stats['total']) * 100
        
        return rule_type_stats
    
    def analyze_by_depth(self, rule_alignment_details: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """按嵌套深度分析对齐情况"""
        depth_stats = {}
        
        for node_id, details in rule_alignment_details.items():
            depth = details['depth']
            if depth not in depth_stats:
                depth_stats[depth] = {'total': 0, 'aligned': 0}
            
            depth_stats[depth]['total'] += 1
            if details['fully_aligned']:
                depth_stats[depth]['aligned'] += 1
        
        # 计算每个深度的对齐率
        for depth, stats in depth_stats.items():
            stats['alignment_rate'] = (stats['aligned'] / stats['total']) * 100
        
        return depth_stats
    
    def generate_report(self, code: str, output_dir: str = "results") -> Dict[str, Any]:
        """生成完整的分析报告"""
        
        # 创建输出目录
        Path(output_dir).mkdir(exist_ok=True)
        
        print(f"正在分析代码（使用模型: {self.model_name}）...")
        
        # 计算 rule-level alignment score
        rule_score, rule_details = self.calculate_rule_level_alignment(code)
        
        # 按规则类型分析
        rule_type_stats = self.analyze_by_rule_type(rule_details)
        
        # 按深度分析
        depth_stats = self.analyze_by_depth(rule_details)
        
        # 准备报告数据
        report = {
            'model_name': self.model_name,
            'rule_level_score': rule_score,
            'total_rules': len(rule_details),
            'aligned_rules': sum(1 for d in rule_details.values() if d['fully_aligned']),
            'rule_type_stats': rule_type_stats,
            'depth_stats': depth_stats,
            'rule_details': rule_details
        }
        
        # 保存详细报告
        report_file = Path(output_dir) / f"rule_level_report_{self.model_name.replace('/', '_')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            # 为了 JSON 序列化，需要转换一些数据类型
            serializable_report = report.copy()
            serializable_report['rule_details'] = {
                str(k): v for k, v in rule_details.items()
            }
            json.dump(serializable_report, f, ensure_ascii=False, indent=2)
        
        print(f"详细报告已保存到: {report_file}")
        
        # 生成可视化图表
        self._generate_visualizations(report, output_dir)
        
        return report
    
    def _generate_visualizations(self, report: Dict[str, Any], output_dir: str):
        """生成可视化图表"""
        
        # 1. 按规则类型的对齐率图表
        rule_type_stats = report['rule_type_stats']
        if rule_type_stats:
            # 按对齐率排序，只显示前20个
            sorted_types = sorted(rule_type_stats.items(), 
                                key=lambda x: x[1]['alignment_rate'], reverse=True)[:20]
            
            types = [item[0] for item in sorted_types]
            rates = [item[1]['alignment_rate'] for item in sorted_types]
            
            plt.figure(figsize=(12, 8))
            bars = plt.bar(range(len(types)), rates)
            plt.xlabel('规则类型')
            plt.ylabel('对齐率 (%)')
            plt.title(f'按规则类型的对齐率 - {report["model_name"]}')
            plt.xticks(range(len(types)), types, rotation=45, ha='right')
            
            # 添加数值标签
            for i, (bar, rate) in enumerate(zip(bars, rates)):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                        f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            plt.savefig(Path(output_dir) / f'rule_type_alignment_{report["model_name"].replace("/", "_")}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()
        
        # 2. 按深度的对齐率图表
        depth_stats = report['depth_stats']
        if depth_stats:
            depths = sorted(depth_stats.keys())
            rates = [depth_stats[d]['alignment_rate'] for d in depths]
            
            plt.figure(figsize=(10, 6))
            plt.plot(depths, rates, marker='o', linewidth=2, markersize=8)
            plt.xlabel('嵌套深度')
            plt.ylabel('对齐率 (%)')
            plt.title(f'按嵌套深度的对齐率 - {report["model_name"]}')
            plt.grid(True, alpha=0.3)
            
            # 添加数值标签
            for depth, rate in zip(depths, rates):
                plt.annotate(f'{rate:.1f}%', (depth, rate), 
                           textcoords="offset points", xytext=(0,10), ha='center')
            
            plt.tight_layout()
            plt.savefig(Path(output_dir) / f'depth_alignment_{report["model_name"].replace("/", "_")}.png', 
                       dpi=300, bbox_inches='tight')
            plt.close()
        
        print(f"可视化图表已保存到 {output_dir} 目录")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Rule-level Tokenization Alignment Score 计算器')
    parser.add_argument('--model', default='gpt2', help='要测试的模型名称 (默认: gpt2)')
    parser.add_argument('--code_file', help='要分析的 Python 代码文件路径')
    parser.add_argument('--code_dir', default='code_samples/python', help='Python 代码样本目录')
    parser.add_argument('--output_dir', default='results', help='输出目录 (默认: results)')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = RuleLevelAlignmentAnalyzer(args.model)
    
    # 准备要分析的代码
    codes_to_analyze = []
    
    if args.code_file:
        # 分析单个文件
        if Path(args.code_file).exists():
            with open(args.code_file, 'r', encoding='utf-8') as f:
                code = f.read()
            codes_to_analyze.append((args.code_file, code))
        else:
            print(f"错误: 文件 {args.code_file} 不存在")
            return
    else:
        # 分析目录中的所有 Python 文件
        code_dir = Path(args.code_dir)
        if code_dir.exists():
            for py_file in code_dir.glob('*.py'):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        code = f.read()
                    codes_to_analyze.append((str(py_file), code))
                except Exception as e:
                    print(f"警告: 无法读取文件 {py_file}: {e}")
        else:
            # 如果目录不存在，使用示例代码
            print(f"目录 {code_dir} 不存在，使用示例代码...")
            example_code = '''
def factorial(n):
    """计算阶乘"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

class Calculator:
    """简单计算器类"""
    
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def multiply(self, a, b):
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

# 使用示例
if __name__ == "__main__":
    calc = Calculator()
    print(f"5! = {factorial(5)}")
    print(f"fibonacci(10) = {fibonacci(10)}")
    print(f"3 + 4 = {calc.add(3, 4)}")
    print(f"5 * 6 = {calc.multiply(5, 6)}")
    print("计算历史:", calc.history)
'''
            codes_to_analyze.append(("示例代码", example_code))
    
    # 分析所有代码
    all_reports = []
    total_score = 0
    
    for file_name, code in codes_to_analyze:
        print(f"\n{'='*60}")
        print(f"正在分析: {file_name}")
        print(f"{'='*60}")
        
        try:
            report = analyzer.generate_report(code, args.output_dir)
            all_reports.append((file_name, report))
            total_score += report['rule_level_score']
            
            # 打印基本统计信息
            print(f"\n分析结果:")
            print(f"  Rule-level Alignment Score: {report['rule_level_score']:.2f}%")
            print(f"  总规则数: {report['total_rules']}")
            print(f"  对齐规则数: {report['aligned_rules']}")
            print(f"  不对齐规则数: {report['total_rules'] - report['aligned_rules']}")
            
            # 显示前5个最常见的规则类型
            rule_type_stats = report['rule_type_stats']
            if rule_type_stats:
                print(f"\n  前5个最常见的规则类型:")
                sorted_types = sorted(rule_type_stats.items(), 
                                    key=lambda x: x[1]['total'], reverse=True)[:5]
                for rule_type, stats in sorted_types:
                    print(f"    {rule_type}: {stats['aligned']}/{stats['total']} "
                          f"({stats['alignment_rate']:.1f}% 对齐)")
            
        except Exception as e:
            print(f"分析 {file_name} 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    # 打印总结
    if all_reports:
        avg_score = total_score / len(all_reports)
        print(f"\n{'='*60}")
        print(f"总结 (模型: {args.model})")
        print(f"{'='*60}")
        print(f"分析文件数: {len(all_reports)}")
        print(f"平均 Rule-level Alignment Score: {avg_score:.2f}%")
        
        # 保存汇总报告
        summary_file = Path(args.output_dir) / f"summary_{args.model.replace('/', '_')}.json"
        summary = {
            'model_name': args.model,
            'analyzed_files': len(all_reports),
            'average_score': avg_score,
            'file_scores': [(name, report['rule_level_score']) for name, report in all_reports]
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"汇总报告已保存到: {summary_file}")


if __name__ == "__main__":
    main()