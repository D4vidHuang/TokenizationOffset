#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多语言 Rule-level Tokenization Alignment Score 计算器

该脚本支持11种编程语言的规则级别标记化对齐分数计算。
支持的语言：Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Ruby, Rust, Scala
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


class MultiLanguageTreeSitterSetup:
    """多语言 Tree-sitter 设置和管理类"""
    
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
    
    # 语言特定的跳过节点类型
    SKIP_NODE_TYPES = {
        'python': {'comment', 'string_content', 'escape_sequence'},
        'javascript': {'comment', 'string_fragment', 'escape_sequence'},
        'typescript': {'comment', 'string_fragment', 'escape_sequence'},
        'java': {'comment', 'string_fragment'},
        'c': {'comment', 'string_literal', 'char_literal'},
        'cpp': {'comment', 'string_literal', 'char_literal'},
        'csharp': {'comment', 'string_literal'},
        'go': {'comment', 'interpreted_string_literal', 'raw_string_literal'},
        'ruby': {'comment', 'string_content'},
        'rust': {'comment', 'string_content'},
        'scala': {'comment', 'string_content'}
    }
    
    def __init__(self):
        self.vendor_dir = Path("vendor")
        self.build_dir = Path("build")
        self.languages_so = self.build_dir / "multilang_languages.so"
        self._parsers_cache = {}
        
    def get_supported_languages(self) -> List[str]:
        """获取支持的语言列表"""
        return list(self.SUPPORTED_LANGUAGES.keys())
    
    def get_file_extensions(self, language: str) -> List[str]:
        """获取指定语言的文件扩展名"""
        return self.FILE_EXTENSIONS.get(language, [])
    
    def detect_language_from_file(self, file_path: str) -> str:
        """从文件路径检测编程语言"""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        for language, extensions in self.FILE_EXTENSIONS.items():
            if extension in extensions:
                return language
        
        raise ValueError(f"无法从文件扩展名 {extension} 检测语言")
    
    def setup_parser(self, language: str) -> Parser:
        """设置指定语言的 tree-sitter 解析器"""
        
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"不支持的语言: {language}. 支持的语言: {list(self.SUPPORTED_LANGUAGES.keys())}")
        
        # 检查缓存
        if language in self._parsers_cache:
            return self._parsers_cache[language]
        
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
            
            # 缓存解析器
            self._parsers_cache[language] = parser
            return parser
            
        except Exception as e:
            print(f"加载 {language} 语言失败: {e}")
            print("尝试重新编译...")
            self._build_all_languages()
            
            language_name = self.LANGUAGE_NAMES[language]
            lang = Language(str(self.languages_so), language_name)
            parser = Parser()
            parser.set_language(lang)
            
            # 缓存解析器
            self._parsers_cache[language] = parser
            return parser
    
    def _build_all_languages(self):
        """编译所有支持语言的 tree-sitter 库"""
        print("正在准备编译所有支持的语言...")
        
        # 克隆所有语言仓库
        repo_paths = []
        for language, repo_url in self.SUPPORTED_LANGUAGES.items():
            repo_path = self._get_repo_path(language)
            
            if not repo_path.exists():
                print(f"正在克隆 {language} 仓库...")
                result = os.system(f"git clone {repo_url} {repo_path}")
                if result != 0:
                    print(f"警告: 克隆 {language} 仓库失败")
                    continue
            
            # 特殊处理 TypeScript（需要处理子目录）
            if language == 'typescript':
                ts_path = repo_path / "typescript"
                if ts_path.exists():
                    repo_paths.append(str(ts_path))
                else:
                    repo_paths.append(str(repo_path))
            else:
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
    
    def _get_repo_path(self, language: str) -> Path:
        """获取语言仓库路径"""
        if language == 'csharp':
            return self.vendor_dir / "tree-sitter-c-sharp"
        else:
            return self.vendor_dir / f"tree-sitter-{language}"
    
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


class MultiLanguageRuleLevelAnalyzer:
    """多语言规则级别对齐分析器"""
    
    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tree_sitter_setup = MultiLanguageTreeSitterSetup()
        
        # 如果 tokenizer 没有 pad_token，设置一个
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def calculate_rule_level_alignment(self, code: str, language: str) -> Tuple[float, Dict[str, Any]]:
        """
        计算给定代码的 rule-level alignment score
        
        Args:
            code: 源代码字符串
            language: 编程语言名称
        
        Returns:
            rule_level_score: 规则级别的对齐分数
            rule_alignment_details: 每个规则的对齐详情
        """
        # 1. 获取对应语言的解析器
        parser = self.tree_sitter_setup.setup_parser(language)
        
        # 2. 使用 tree-sitter 解析代码
        tree = parser.parse(bytes(code, 'utf8'))
        
        # 3. 使用 tokenizer 对代码进行标记化
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
        
        # 4. 获取语言特定的跳过节点类型
        skip_types = self.tree_sitter_setup.SKIP_NODE_TYPES.get(language, {'comment'})
        
        # 5. 遍历语法树，检查每个规则节点的对齐情况
        rule_alignment_details = {}
        
        def traverse_tree(node, depth=0):
            # 只考虑命名节点（规则节点），排除一些不重要的节点
            if not node.is_named:
                for child in node.children:
                    traverse_tree(child, depth)
                return
            
            # 跳过语言特定的不重要节点类型
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
                'parent_type': node.parent.type if node.parent else None,
                'language': language
            }
            
            # 递归处理子节点
            for child in node.children:
                traverse_tree(child, depth + 1)
        
        # 从根节点开始遍历
        traverse_tree(tree.root_node)
        
        # 6. 计算 rule-level alignment score
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
    
    def analyze_directory(self, directory: str, language: str = None, output_dir: str = "results") -> Dict[str, Any]:
        """分析目录中的所有代码文件"""
        
        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"目录不存在: {directory}")
        
        # 创建输出目录
        Path(output_dir).mkdir(exist_ok=True)
        
        # 收集要分析的文件
        files_to_analyze = []
        
        if language:
            # 指定语言，查找对应扩展名的文件
            extensions = self.tree_sitter_setup.get_file_extensions(language)
            for ext in extensions:
                files_to_analyze.extend(directory.glob(f"*{ext}"))
        else:
            # 自动检测所有支持的文件
            for lang in self.tree_sitter_setup.get_supported_languages():
                extensions = self.tree_sitter_setup.get_file_extensions(lang)
                for ext in extensions:
                    files_to_analyze.extend(directory.glob(f"*{ext}"))
        
        if not files_to_analyze:
            print(f"在目录 {directory} 中没有找到可分析的代码文件")
            return {}
        
        # 分析每个文件
        all_results = {}
        total_score = 0
        file_count = 0
        
        for file_path in files_to_analyze:
            try:
                # 检测或使用指定的语言
                if language:
                    file_language = language
                else:
                    file_language = self.tree_sitter_setup.detect_language_from_file(str(file_path))
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                print(f"正在分析 {file_path} ({file_language})...")
                
                # 计算对齐分数
                score, details = self.calculate_rule_level_alignment(code, file_language)
                
                # 保存结果
                file_result = {
                    'file_path': str(file_path),
                    'language': file_language,
                    'rule_level_score': score,
                    'total_rules': len(details),
                    'aligned_rules': sum(1 for d in details.values() if d['fully_aligned']),
                    'rule_type_stats': self.analyze_by_rule_type(details),
                    'depth_stats': self.analyze_by_depth(details),
                    'rule_details': details
                }
                
                all_results[str(file_path)] = file_result
                total_score += score
                file_count += 1
                
                print(f"  Rule-level Alignment Score: {score:.2f}%")
                print(f"  总规则数: {len(details)}")
                print(f"  对齐规则数: {sum(1 for d in details.values() if d['fully_aligned'])}")
                
            except Exception as e:
                print(f"分析文件 {file_path} 时出错: {e}")
                continue
        
        # 生成汇总报告
        if file_count > 0:
            summary = {
                'model_name': self.model_name,
                'analyzed_files': file_count,
                'average_score': total_score / file_count,
                'file_results': all_results
            }
            
            # 保存汇总报告
            summary_file = Path(output_dir) / f"multilang_summary_{self.model_name.replace('/', '_')}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                # 为了 JSON 序列化，需要转换一些数据类型
                serializable_summary = summary.copy()
                serializable_file_results = {}
                
                for file_path, result in all_results.items():
                    serializable_result = result.copy()
                    serializable_result['rule_details'] = {
                        str(k): v for k, v in result['rule_details'].items()
                    }
                    serializable_file_results[file_path] = serializable_result
                
                serializable_summary['file_results'] = serializable_file_results
                json.dump(serializable_summary, f, ensure_ascii=False, indent=2)
            
            print(f"\n汇总报告已保存到: {summary_file}")
            print(f"平均 Rule-level Alignment Score: {summary['average_score']:.2f}%")
            
            return summary
        
        return {}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多语言 Rule-level Tokenization Alignment Score 计算器')
    parser.add_argument('--model', default='gpt2', help='要测试的模型名称 (默认: gpt2)')
    parser.add_argument('--language', choices=['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'csharp', 'go', 'ruby', 'rust', 'scala'], 
                       help='指定要分析的编程语言')
    parser.add_argument('--code_file', help='要分析的单个代码文件路径')
    parser.add_argument('--code_dir', default='code_samples', help='代码样本目录 (默认: code_samples)')
    parser.add_argument('--output_dir', default='results', help='输出目录 (默认: results)')
    parser.add_argument('--list_languages', action='store_true', help='列出支持的编程语言')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = MultiLanguageRuleLevelAnalyzer(args.model)
    
    # 列出支持的语言
    if args.list_languages:
        print("支持的编程语言:")
        for lang in analyzer.tree_sitter_setup.get_supported_languages():
            extensions = analyzer.tree_sitter_setup.get_file_extensions(lang)
            print(f"  {lang}: {', '.join(extensions)}")
        return
    
    if args.code_file:
        # 分析单个文件
        if not Path(args.code_file).exists():
            print(f"错误: 文件 {args.code_file} 不存在")
            return
        
        try:
            # 检测或使用指定的语言
            if args.language:
                language = args.language
            else:
                language = analyzer.tree_sitter_setup.detect_language_from_file(args.code_file)
            
            # 读取文件内容
            with open(args.code_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            print(f"正在分析文件: {args.code_file} ({language})")
            print(f"使用模型: {args.model}")
            print("=" * 60)
            
            # 计算对齐分数
            score, details = analyzer.calculate_rule_level_alignment(code, language)
            
            print(f"Rule-level Alignment Score: {score:.2f}%")
            print(f"总规则数: {len(details)}")
            print(f"对齐规则数: {sum(1 for d in details.values() if d['fully_aligned'])}")
            
            # 按规则类型分析
            rule_type_stats = analyzer.analyze_by_rule_type(details)
            print(f"\n前5个最常见的规则类型:")
            sorted_types = sorted(rule_type_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:5]
            
            for rule_type, stats in sorted_types:
                print(f"  {rule_type}: {stats['aligned']}/{stats['total']} ({stats['alignment_rate']:.1f}% 对齐)")
            
        except Exception as e:
            print(f"分析文件时出错: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        # 分析目录
        print(f"正在分析目录: {args.code_dir}")
        print(f"使用模型: {args.model}")
        if args.language:
            print(f"指定语言: {args.language}")
        print("=" * 60)
        
        try:
            summary = analyzer.analyze_directory(args.code_dir, args.language, args.output_dir)
            
            if summary:
                print(f"\n总结:")
                print(f"分析文件数: {summary['analyzed_files']}")
                print(f"平均 Rule-level Alignment Score: {summary['average_score']:.2f}%")
                
                # 按语言统计
                lang_stats = {}
                for file_path, result in summary['file_results'].items():
                    lang = result['language']
                    if lang not in lang_stats:
                        lang_stats[lang] = {'files': 0, 'total_score': 0}
                    lang_stats[lang]['files'] += 1
                    lang_stats[lang]['total_score'] += result['rule_level_score']
                
                print(f"\n按语言统计:")
                for lang, stats in lang_stats.items():
                    avg_score = stats['total_score'] / stats['files']
                    print(f"  {lang}: {stats['files']} 个文件, 平均分数: {avg_score:.2f}%")
            
        except Exception as e:
            print(f"分析目录时出错: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()