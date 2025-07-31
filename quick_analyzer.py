#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速版多语言分析器 - 使用已有的编译库
"""

import os
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

from tree_sitter import Language, Parser
from transformers import AutoTokenizer
import warnings
warnings.filterwarnings('ignore')

class QuickMultiLanguageAnalyzer:
    """快速版多语言分析器 - 使用已编译的库"""
    
    def __init__(self, model_name: str = "gpt2"):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # 语言配置
        self.language_configs = {
            'python': {'symbol': 'python', 'extensions': ['.py']},
            'javascript': {'symbol': 'javascript', 'extensions': ['.js']},
            'typescript': {'symbol': 'typescript', 'extensions': ['.ts']},
            'java': {'symbol': 'java', 'extensions': ['.java']},
            'c': {'symbol': 'c', 'extensions': ['.c', '.h']},
            'cpp': {'symbol': 'cpp', 'extensions': ['.cpp', '.cc', '.cxx', '.hpp']},
            'csharp': {'symbol': 'c_sharp', 'extensions': ['.cs']},
            'go': {'symbol': 'go', 'extensions': ['.go']},
            'ruby': {'symbol': 'ruby', 'extensions': ['.rb']},
            'rust': {'symbol': 'rust', 'extensions': ['.rs']},
            'scala': {'symbol': 'scala', 'extensions': ['.scala']}
        }
        
        self.parsers = {}
        self.languages = {}
        self._setup_parsers()
    
    def _setup_parsers(self):
        """设置解析器 - 使用已有的编译库"""
        build_dir = Path('./build')
        
        if not build_dir.exists():
            print("错误: build 目录不存在")
            return
        
        print("正在加载已编译的语言库...")
        
        # 尝试初始化每种语言
        for lang_name, config in self.language_configs.items():
            try:
                # 查找对应的语言库文件
                possible_paths = [
                    build_dir / f"languages_{lang_name}.so",
                    build_dir / f"languages.so",
                    build_dir / f"multilang_languages.so"
                ]
                
                library_path = None
                for path in possible_paths:
                    if path.exists():
                        library_path = path
                        break
                
                if not library_path:
                    print(f"✗ {lang_name} 语言库文件不存在")
                    continue
                
                parser = Parser()
                language = Language(str(library_path), config['symbol'])
                parser.set_language(language)
                
                self.parsers[lang_name] = parser
                self.languages[lang_name] = language
                print(f"✓ {lang_name} 解析器可用 (使用 {library_path.name})")
                
            except Exception as e:
                print(f"✗ {lang_name} 解析器不可用: {e}")
    
    def get_available_languages(self) -> List[str]:
        """获取可用语言列表"""
        return list(self.parsers.keys())
    
    def calculate_rule_level_alignment(self, code: str, language: str) -> Tuple[float, Dict]:
        """计算规则级别对齐分数"""
        if language not in self.parsers:
            raise ValueError(f"不支持的语言: {language}")
        
        parser = self.parsers[language]
        code_bytes = code.encode('utf-8')
        
        # 解析代码
        tree = parser.parse(code_bytes)
        
        # 提取规则
        def extract_rules(node, rules=None):
            if rules is None:
                rules = []
            
            if node.type and not node.type.startswith('ERROR'):
                rules.append({
                    'type': node.type,
                    'start_byte': node.start_byte,
                    'end_byte': node.end_byte,
                    'text': code_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')[:50]
                })
            
            for child in node.children:
                extract_rules(child, rules)
            
            return rules
        
        rules = extract_rules(tree.root_node)
        
        # Tokenization
        try:
            tokens = self.tokenizer.encode(code)
            token_texts = [self.tokenizer.decode([token]) for token in tokens]
        except Exception as e:
            print(f"Tokenization 错误: {e}")
            return 0.0, {}
        
        # 计算 token 边界
        token_boundaries = []
        current_pos = 0
        
        for token_text in token_texts:
            token_start = code.find(token_text, current_pos)
            if token_start != -1:
                token_end = token_start + len(token_text)
                token_boundaries.append((token_start, token_end))
                current_pos = token_end
            else:
                token_boundaries.append((current_pos, current_pos + 1))
                current_pos += 1
        
        # 计算对齐
        aligned_rules = 0
        rule_details = {}
        
        for rule in rules:
            rule_start = rule['start_byte']
            rule_end = rule['end_byte']
            
            start_aligned = any(abs(rule_start - tb[0]) <= 1 for tb in token_boundaries)
            end_aligned = any(abs(rule_end - tb[1]) <= 1 for tb in token_boundaries)
            
            fully_aligned = start_aligned and end_aligned
            if fully_aligned:
                aligned_rules += 1
            
            rule_key = f"{rule['type']}_{rule['start_byte']}_{rule['end_byte']}"
            rule_details[rule_key] = {
                'type': rule['type'],
                'start_aligned': start_aligned,
                'end_aligned': end_aligned,
                'fully_aligned': fully_aligned,
                'text_preview': rule['text'][:50]
            }
        
        alignment_score = (aligned_rules / len(rules) * 100) if rules else 0
        return alignment_score, rule_details
    
    def analyze_language_files(self, code_dir: str, language: str) -> Dict:
        """分析指定语言的所有文件"""
        if language not in self.parsers:
            print(f"跳过不支持的语言: {language}")
            return {}
        
        language_dir = Path(code_dir) / language
        if not language_dir.exists():
            print(f"语言目录不存在: {language_dir}")
            return {}
        
        # 查找文件
        extensions = self.language_configs[language]['extensions']
        code_files = []
        for ext in extensions:
            code_files.extend(language_dir.glob(f"*{ext}"))
        
        if not code_files:
            print(f"没有找到 {language} 文件")
            return {}
        
        print(f"\n分析 {language.upper()} ({len(code_files)} 个文件)")
        print("-" * 50)
        
        # 分析文件
        file_results = []
        total_rules = 0
        total_aligned = 0
        
        for file_path in code_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                if not code.strip():
                    continue
                
                score, details = self.calculate_rule_level_alignment(code, language)
                aligned_count = sum(1 for d in details.values() if d['fully_aligned'])
                
                file_results.append({
                    'file': file_path.name,
                    'score': score,
                    'total_rules': len(details),
                    'aligned_rules': aligned_count
                })
                
                total_rules += len(details)
                total_aligned += aligned_count
                
                print(f"  {file_path.name:<20} {score:6.2f}% ({aligned_count}/{len(details)})")
                
            except Exception as e:
                print(f"  {file_path.name:<20} 错误: {e}")
        
        if not file_results:
            return {}
        
        # 计算统计
        avg_score = sum(r['score'] for r in file_results) / len(file_results)
        overall_alignment = (total_aligned / total_rules * 100) if total_rules > 0 else 0
        
        result = {
            'language': language,
            'file_count': len(file_results),
            'avg_score': avg_score,
            'total_rules': total_rules,
            'total_aligned': total_aligned,
            'overall_alignment': overall_alignment,
            'files': file_results
        }
        
        print(f"\n{language.upper()} 总结:")
        print(f"  文件数: {result['file_count']}")
        print(f"  平均分数: {result['avg_score']:.2f}%")
        print(f"  总规则数: {result['total_rules']}")
        print(f"  总对齐数: {result['total_aligned']}")
        print(f"  整体对齐率: {result['overall_alignment']:.2f}%")
        
        return result
    
    def run_analysis(self, code_dir: str = "code_samples", 
                    target_languages: List[str] = None, 
                    output_dir: str = "results/multilang") -> Dict:
        """运行分析"""
        available_languages = self.get_available_languages()
        
        if not available_languages:
            print("错误: 没有可用的语言解析器")
            return {}
        
        if target_languages is None:
            target_languages = available_languages
        else:
            target_languages = [lang for lang in target_languages if lang in available_languages]
        
        print("=" * 80)
        print("快速多语言 Rule-level Alignment Score 分析")
        print("=" * 80)
        print(f"可用语言: {' '.join(available_languages)}")
        print(f"分析语言: {' '.join(target_languages)}")
        
        results = {}
        for language in target_languages:
            result = self.analyze_language_files(code_dir, language)
            if result:
                results[language] = result
        
        # 生成排名
        rankings = []
        if results:
            print(f"\n{'='*60}")
            print("语言排名 (按平均分数)")
            print(f"{'='*60}")
            
            rankings = sorted(results.items(), key=lambda x: x[1]['avg_score'], reverse=True)
            for i, (lang, result) in enumerate(rankings, 1):
                print(f"{i:2d}. {lang:<12} {result['avg_score']:6.2f}% "
                      f"(文件: {result['file_count']}, 规则: {result['total_rules']})")
        
        # 保存结果到文件
        self._save_results(results, rankings, output_dir)
        
        return results
    
    def _save_results(self, results: Dict, rankings: List, output_dir: str):
        """保存分析结果到文件"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存详细结果
        detailed_results = {
            'model': self.model_name,
            'timestamp': str(Path().resolve()),
            'summary': {
                'total_languages': len(results),
                'total_files': sum(r['file_count'] for r in results.values()),
                'total_rules': sum(r['total_rules'] for r in results.values()),
                'total_aligned': sum(r['total_aligned'] for r in results.values())
            },
            'languages': results,
            'rankings': [
                {
                    'rank': i + 1,
                    'language': lang,
                    'avg_score': result['avg_score'],
                    'file_count': result['file_count'],
                    'total_rules': result['total_rules'],
                    'total_aligned': result['total_aligned']
                }
                for i, (lang, result) in enumerate(rankings)
            ]
        }
        
        # 保存详细报告
        detailed_file = output_path / f"detailed_analysis_{self.model_name}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
        
        # 保存简化的排名报告
        ranking_report = {
            'model': self.model_name,
            'analysis_date': str(Path().resolve()),
            'rankings': detailed_results['rankings'],
            'summary': detailed_results['summary']
        }
        
        ranking_file = output_path / f"language_rankings_{self.model_name}.json"
        with open(ranking_file, 'w', encoding='utf-8') as f:
            json.dump(ranking_report, f, ensure_ascii=False, indent=2)
        
        # 生成跨语言报告（为可视化工具使用）
        cross_language_report = {
            "model": self.model_name,
            "analysis_date": str(output_path),
            "language_rankings": [
                {
                    "language": lang,
                    "avg_score": result["avg_score"],
                    "total_rules": result["total_rules"],
                    "aligned_rules": result["total_aligned"],
                    "alignment_rate": (result["total_aligned"] / result["total_rules"] * 100) if result["total_rules"] > 0 else 0
                }
                for lang, result in rankings
            ],
            "analysis_summary": {
                "analyzed_languages": len(rankings),
                "total_files": sum(result["file_count"] for _, result in rankings),
                "total_rules": sum(result["total_rules"] for _, result in rankings),
                "total_aligned_rules": sum(result["total_aligned"] for _, result in rankings),
                "average_score": sum(result["avg_score"] for _, result in rankings) / len(rankings) if rankings else 0,
                "overall_alignment_rate": (sum(result["total_aligned"] for _, result in rankings) / sum(result["total_rules"] for _, result in rankings) * 100) if sum(result["total_rules"] for _, result in rankings) > 0 else 0
            }
        }
        
        cross_lang_file = output_path / f"cross_language_report_{self.model_name}.json"
        with open(cross_lang_file, 'w', encoding='utf-8') as f:
            json.dump(cross_language_report, f, ensure_ascii=False, indent=2)
        
        # 为每种语言保存单独的详细报告
        for language, result in results.items():
            lang_dir = output_path / language
            lang_dir.mkdir(exist_ok=True)
            
            lang_file = lang_dir / f"analysis_report_{self.model_name}.json"
            with open(lang_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 分析结果已保存到:")
        print(f"  - 详细报告: {detailed_file}")
        print(f"  - 排名报告: {ranking_file}")
        print(f"  - 各语言报告: {output_path}/{{language}}/analysis_report_{self.model_name}.json")

def main():
    parser = argparse.ArgumentParser(description='快速多语言分析器')
    parser.add_argument('--language', help='指定语言')
    parser.add_argument('--all_languages', action='store_true', help='分析所有语言')
    parser.add_argument('--code_dir', default='code_samples', help='代码目录')
    parser.add_argument('--output_dir', default='results/multilang', help='输出目录')
    parser.add_argument('--model', default='gpt2', help='Tokenizer 模型')
    
    args = parser.parse_args()
    
    analyzer = QuickMultiLanguageAnalyzer(model_name=args.model)
    
    if args.language:
        target_languages = [args.language]
    elif args.all_languages:
        target_languages = None  # 分析所有可用语言
    else:
        target_languages = ['python']  # 默认只分析 Python
    
    analyzer.run_analysis(args.code_dir, target_languages, args.output_dir)

if __name__ == "__main__":
    main()