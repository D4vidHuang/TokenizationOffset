#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版多语言 Rule-level Alignment Score 分析脚本
"""

import argparse
from pathlib import Path
from multilang_rule_analysis import MultiLanguageRuleLevelAnalyzer
import json

def main():
    parser = argparse.ArgumentParser(description='多语言 Rule-level Alignment Score 分析')
    parser.add_argument('--model', default='gpt2', help='要测试的模型名称')
    parser.add_argument('--language', help='指定单一语言进行分析')
    parser.add_argument('--code_dir', default='code_samples', help='代码样本根目录')
    parser.add_argument('--output_dir', default='results/multilang', help='输出目录')
    parser.add_argument('--all_languages', action='store_true', help='分析所有支持的语言')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("多语言 Rule-level Alignment Score 分析")
    print("=" * 80)
    print(f"模型: {args.model}")
    print(f"代码根目录: {args.code_dir}")
    print(f"输出目录: {args.output_dir}")
    print()
    
    # 创建分析器
    analyzer = MultiLanguageRuleLevelAnalyzer(args.model)
    
    # 支持的语言列表
    supported_languages = [
        'python', 'javascript', 'typescript', 'java', 'c', 'cpp', 
        'csharp', 'go', 'ruby', 'rust', 'scala'
    ]
    
    if args.language:
        # 分析单一语言
        if args.language not in supported_languages:
            print(f"错误: 不支持的语言 '{args.language}'")
            print(f"支持的语言: {', '.join(supported_languages)}")
            return
        
        languages_to_analyze = [args.language]
    elif args.all_languages:
        # 分析所有语言
        languages_to_analyze = supported_languages
    else:
        # 默认分析代码目录中存在的语言
        code_dir = Path(args.code_dir)
        if not code_dir.exists():
            print(f"错误: 代码目录 '{args.code_dir}' 不存在")
            return
        
        # 检查哪些语言目录存在
        languages_to_analyze = []
        for lang in supported_languages:
            lang_dir = code_dir / lang
            if lang_dir.exists() and any(lang_dir.iterdir()):
                languages_to_analyze.append(lang)
        
        if not languages_to_analyze:
            print(f"在目录 '{args.code_dir}' 中没有找到支持的语言代码")
            return
    
    print(f"将要分析的语言: {', '.join(languages_to_analyze)}")
    print()
    
    # 分析结果汇总
    all_results = {}
    
    # 分析每种语言
    for language in languages_to_analyze:
        print(f"{'='*60}")
        print(f"正在分析语言: {language.upper()}")
        print(f"{'='*60}")
        
        # 修复：直接使用语言目录，不再嵌套
        lang_code_dir = Path(args.code_dir) / language
        
        if not lang_code_dir.exists():
            print(f"警告: 语言目录 '{lang_code_dir}' 不存在，跳过")
            continue
        
        # 获取该语言的所有代码文件
        extensions = get_file_extensions(language)
        code_files = []
        for ext in extensions:
            code_files.extend(lang_code_dir.glob(f"*{ext}"))
        
        if not code_files:
            print(f"在目录 '{lang_code_dir}' 中没有找到 {language} 代码文件")
            continue
        
        print(f"找到 {len(code_files)} 个 {language} 文件")
        
        # 分析该语言的所有文件
        try:
            lang_output_dir = Path(args.output_dir) / language
            lang_output_dir.mkdir(parents=True, exist_ok=True)
            
            file_results = {}
            total_score = 0
            total_rules = 0
            total_aligned = 0
            
            for code_file in code_files:
                print(f"正在分析: {code_file.name}")
                
                try:
                    with open(code_file, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    score, details = analyzer.calculate_rule_level_alignment(code, language)
                    
                    aligned_count = sum(1 for d in details.values() if d['fully_aligned'])
                    
                    file_results[str(code_file)] = {
                        'language': language,
                        'rule_level_score': score,
                        'total_rules': len(details),
                        'aligned_rules': aligned_count,
                        'rule_details': details
                    }
                    
                    total_score += score
                    total_rules += len(details)
                    total_aligned += aligned_count
                    
                    print(f"  Rule-level Alignment Score: {score:.2f}%")
                    print(f"  规则数: {len(details)}, 对齐: {aligned_count}")
                    
                except Exception as e:
                    print(f"  分析文件 {code_file.name} 时出错: {e}")
                    continue
            
            if file_results:
                avg_score = total_score / len(file_results)
                
                summary = {
                    'model_name': args.model,
                    'language': language,
                    'analyzed_files': len(file_results),
                    'average_score': avg_score,
                    'total_rules': total_rules,
                    'total_aligned_rules': total_aligned,
                    'overall_alignment_rate': (total_aligned / total_rules * 100) if total_rules > 0 else 0,
                    'file_results': file_results
                }
                
                all_results[language] = summary
                
                # 保存详细报告
                report_file = lang_output_dir / f"rule_level_report_{args.model}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                
                print(f"\n{language.upper()} 分析完成:")
                print(f"  文件数: {len(file_results)}")
                print(f"  平均 Rule-level Alignment Score: {avg_score:.2f}%")
                print(f"  总规则数: {total_rules}")
                print(f"  总对齐规则数: {total_aligned}")
                print(f"  整体对齐率: {(total_aligned/total_rules*100):.2f}%")
                
                # 显示表现最好和最差的文件
                file_scores = [(Path(f).name, r['rule_level_score']) for f, r in file_results.items()]
                if len(file_scores) > 1:
                    file_scores.sort(key=lambda x: x[1], reverse=True)
                    best_file, best_score = file_scores[0]
                    worst_file, worst_score = file_scores[-1]
                    
                    print(f"  最佳文件: {best_file} ({best_score:.2f}%)")
                    print(f"  最差文件: {worst_file} ({worst_score:.2f}%)")
                
                print(f"  详细报告已保存到: {report_file}")
            else:
                print(f"语言 '{language}' 没有成功分析任何文件")
                
        except Exception as e:
            print(f"分析语言 '{language}' 时出错: {e}")
            continue
        
        print()
    
    # 生成跨语言对比报告
    if len(all_results) > 1:
        generate_cross_language_report(all_results, args.output_dir, args.model)
    
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)


def get_file_extensions(language):
    """获取语言对应的文件扩展名"""
    extensions_map = {
        'python': ['.py'],
        'javascript': ['.js'],
        'typescript': ['.ts'],
        'java': ['.java'],
        'c': ['.c', '.h'],
        'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx'],
        'csharp': ['.cs'],
        'go': ['.go'],
        'ruby': ['.rb'],
        'rust': ['.rs'],
        'scala': ['.scala']
    }
    return extensions_map.get(language, [])


def generate_cross_language_report(all_results, output_dir, model_name):
    """生成跨语言对比报告"""
    
    print(f"{'='*60}")
    print("跨语言对比分析")
    print(f"{'='*60}")
    
    # 计算每种语言的统计信息
    language_stats = {}
    
    for language, summary in all_results.items():
        language_stats[language] = {
            'files': summary['analyzed_files'],
            'avg_score': summary['average_score'],
            'total_rules': summary['total_rules'],
            'total_aligned': summary['total_aligned_rules'],
            'overall_alignment_rate': summary['overall_alignment_rate']
        }
    
    # 按平均分数排序
    sorted_languages = sorted(language_stats.items(), key=lambda x: x[1]['avg_score'], reverse=True)
    
    print("各语言 Rule-level Alignment Score 排名:")
    print("-" * 50)
    for i, (language, stats) in enumerate(sorted_languages, 1):
        print(f"{i:2d}. {language:<12} {stats['avg_score']:>6.2f}% "
              f"(文件数: {stats['files']}, 规则数: {stats['total_rules']})")
    
    # 计算总体统计
    total_files = sum(stats['files'] for stats in language_stats.values())
    total_rules = sum(stats['total_rules'] for stats in language_stats.values())
    total_aligned = sum(stats['total_aligned'] for stats in language_stats.values())
    overall_avg = sum(stats['avg_score'] for stats in language_stats.values()) / len(language_stats)
    
    print(f"\n总体统计:")
    print(f"  分析语言数: {len(language_stats)}")
    print(f"  总文件数: {total_files}")
    print(f"  总规则数: {total_rules}")
    print(f"  总对齐规则数: {total_aligned}")
    print(f"  整体对齐率: {(total_aligned/total_rules*100):.2f}%")
    print(f"  平均分数: {overall_avg:.2f}%")
    
    # 保存跨语言对比报告
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    cross_lang_report = {
        'model_name': model_name,
        'analysis_summary': {
            'analyzed_languages': len(language_stats),
            'total_files': total_files,
            'total_rules': total_rules,
            'total_aligned_rules': total_aligned,
            'overall_alignment_rate': total_aligned/total_rules*100 if total_rules > 0 else 0,
            'average_score': overall_avg
        },
        'language_rankings': [
            {
                'rank': i,
                'language': lang,
                'avg_score': stats['avg_score'],
                'files': stats['files'],
                'total_rules': stats['total_rules'],
                'aligned_rules': stats['total_aligned'],
                'alignment_rate': stats['overall_alignment_rate']
            }
            for i, (lang, stats) in enumerate(sorted_languages, 1)
        ],
        'detailed_results': all_results
    }
    
    report_file = output_path / f"cross_language_report_{model_name}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(cross_lang_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n跨语言对比报告已保存到: {report_file}")


if __name__ == "__main__":
    main()