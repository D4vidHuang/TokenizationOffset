import os
import argparse
import glob
from tree_sitter import Language, Parser
from transformers import AutoTokenizer
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- 1. 配置 ---
# 可以测试多个模型，尤其是为代码优化的模型
DEFAULT_MODELS = [
    "gpt2",                         # 通用模型作为基线
    "codellama/CodeLlama-7b-hf",    # Meta专门为代码优化的模型
    "bigcode/starcoder2-3b"         # BigCode项目（ServiceNow & Hugging Face）
]
DEFAULT_CODE_PATH = "code_samples/python"
DEFAULT_LANGUAGE = "python"

# --- 解析命令行参数 ---
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="分析LLM分词器与语法边界的对齐程度")
    parser.add_argument("--model", "-m", type=str, help="指定要测试的模型名称，如gpt2")
    parser.add_argument("--code_path", "-c", type=str, default=DEFAULT_CODE_PATH, 
                        help=f"指定代码文件或文件夹路径 (默认: {DEFAULT_CODE_PATH})")
    parser.add_argument("--language", "-l", type=str, default=DEFAULT_LANGUAGE,
                        help=f"指定代码语言 (默认: {DEFAULT_LANGUAGE})")
    return parser.parse_args()


# --- 2. 初始化 Tree-sitter 解析器 ---
def setup_tree_sitter_parser(language_name: str) -> Parser:
    """编译并加载指定语言的tree-sitter解析器"""
    library_path = 'build/languages.so'
    repo_path = f'vendor/tree-sitter-{language_name}'
    
    if not os.path.exists(repo_path):
        raise FileNotFoundError(f"Tree-sitter grammar for {language_name} not found in {repo_path}")
        
    Language.build_library(
        library_path,
        [repo_path]
    )
    lang = Language(library_path, language_name)
    parser = Parser()
    parser.set_language(lang)
    return parser

# --- 3. 提取所有语法节点的边界 ---
def get_grammar_node_boundaries(parser: Parser, code_bytes: bytes) -> set:
    """解析代码并返回所有语法节点（非终结符）的起始和结束字节位置"""
    tree = parser.parse(code_bytes)
    boundaries = set()
    
    # 使用tree-cursor进行高效遍历
    cursor = tree.walk()
    
    # 广度优先或深度优先遍历
    nodes_to_visit = [tree.root_node]
    while nodes_to_visit:
        node = nodes_to_visit.pop(0)
        # 我们只关心那些有实际文本范围的节点
        if node.start_byte != node.end_byte:
            boundaries.add(node.start_byte)
            boundaries.add(node.end_byte)
        
        nodes_to_visit.extend(node.children)
        
    return boundaries

# --- 4. 提取LLM分词器的边界 ---
def get_tokenizer_token_boundaries(model_name: str, code_string: str) -> set:
    """为指定模型分词，并返回所有词元的起始和结束字符位置"""
    # 使用 trust_remote_code=True 以支持StarCoder等需要自定义代码的模型
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # return_offsets_mapping=True 是关键，它能返回每个词元在原始字符串中的起止位置
    encoding = tokenizer(code_string, return_offsets_mapping=True)
    
    boundaries = set()
    for start, end in encoding['offset_mapping']:
        # (0, 0) 通常是特殊标记，如 [CLS] 或 [BOS]，可以忽略
        if start != end:
            boundaries.add(start)
            boundaries.add(end)
            
    return boundaries

# --- 5. 主分析流程 ---
def analyze_file(file_path, parser, models_to_test):
    """分析单个文件"""
    print(f"\n分析文件: {file_path}")
    
    with open(file_path, "rb") as f:
        code_bytes = f.read()
    code_string = code_bytes.decode("utf-8")
    
    # 获取基准边界：tree-sitter的语法边界
    grammar_boundaries = get_grammar_node_boundaries(parser, code_bytes)
    print(f"从tree-sitter找到{len(grammar_boundaries)}个唯一语法边界。")
    
    file_results = []
    
    for model_name in models_to_test:
        print(f"\n--- 分析模型: {model_name} ---")
        try:
            tokenizer_boundaries = get_tokenizer_token_boundaries(model_name, code_string)
            print(f"为{model_name}找到{len(tokenizer_boundaries)}个唯一词元边界。")
            
            # 计算错位（即存在于语法边界集合但不存在于分词边界集合中的点）
            mismatched_boundaries = grammar_boundaries.difference(tokenizer_boundaries)
            
            alignment_score = 0
            if grammar_boundaries:
                alignment_score = (1 - len(mismatched_boundaries) / len(grammar_boundaries)) * 100
            
            file_results.append({
                "file_name": os.path.basename(file_path),
                "model_name": model_name,
                "grammar_boundaries": len(grammar_boundaries),
                "tokenizer_boundaries": len(tokenizer_boundaries),
                "mismatched_boundaries": len(mismatched_boundaries),
                "alignment_score_percent": alignment_score
            })
            
            print(f"对齐分数: {alignment_score:.2f}%")
            
        except Exception as e:
            print(f"无法处理{model_name}。错误: {e}")
    
    return file_results

# 在main.py中添加一个文件扩展名映射
def get_file_extension(language):
    """根据语言名称返回对应的文件扩展名"""
    extension_map = {
        "python": ".py",
        "javascript": ".js",
        "typescript": ".ts",
        "java": ".java",
        "c": ".c",
        "cpp": ".cpp",
        "csharp": ".cs",
        "go": ".go",
        "ruby": ".rb",
        "rust": ".rs",
        "php": ".php",
        "swift": ".swift"
    }
    return extension_map.get(language, f".{language}")

def main():
    """主函数，执行分析并生成报告"""
    args = parse_args()
    print("开始分析...")
    
    # 打印当前配置
    print(f"使用模型: {args.model if args.model else '默认模型列表'}")
    print(f"代码路径: {args.code_path}")
    print(f"代码语言: {args.language}")
    
    # 确保build目录存在
    os.makedirs("build", exist_ok=True)
    
    # 确定要测试的模型
    models_to_test = [args.model] if args.model else DEFAULT_MODELS
    
    # 确定语言和解析器
    language = args.language
    
    # 克隆tree-sitter语言仓库（如果不存在）
    repo_path = f"vendor/tree-sitter-{language}"
    if not os.path.exists(repo_path):
        print(f"克隆tree-sitter-{language}仓库...")
        os.system(f"git clone https://github.com/tree-sitter/tree-sitter-{language}.git {repo_path}")
    
    parser = setup_tree_sitter_parser(language)
    
    # 确定要分析的文件
    code_path = args.code_path
    all_results = []
    
    if os.path.isdir(code_path):
        # 如果是目录，分析目录中所有相应语言的文件
        #file_extension = ".py" if language == "python" else f".{language}"
        file_extension = get_file_extension(language)
        # 自动在code_samples下查找对应语言的文件夹
        if "code_samples" in code_path:
            language_specific_path = os.path.join("code_samples", language)
            if os.path.exists(language_specific_path) and os.path.isdir(language_specific_path):
                code_path = language_specific_path
                print(f"自动切换到语言特定文件夹: {code_path}")
        
        code_files = glob.glob(os.path.join(code_path, f"*{file_extension}"))
        
        if not code_files:
            print(f"在{code_path}中没有找到{file_extension}文件")
            return
            
        for file_path in code_files:
            file_results = analyze_file(file_path, parser, models_to_test)
            all_results.extend(file_results)
    else:
        # 如果是单个文件
        if not os.path.exists(code_path):
            print(f"文件{code_path}不存在")
            return
            
        file_results = analyze_file(code_path, parser, models_to_test)
        all_results.extend(file_results)
    
    # --- 6. 生成报告和可视化 ---
    if not all_results:
        print("没有结果可报告。")
        return
        
    df = pd.DataFrame(all_results)
    
    # 创建结果目录
    os.makedirs("results", exist_ok=True)
    
    # Save CSV report
    report_path = "results/alignment_report.csv"
    df.to_csv(report_path, index=False)
    print(f"\nComplete report has been saved to {report_path}")

    # Calculate average alignment scores grouped by model
    model_avg = df.groupby('model_name')['alignment_score_percent'].mean().reset_index()
    model_avg_sorted = model_avg.sort_values("alignment_score_percent", ascending=False)
    
    # Visualization - Model average alignment scores
    plt.figure(figsize=(12, 7))
    sns.barplot(x="alignment_score_percent", y="model_name", data=model_avg_sorted, palette="viridis", hue="model_name", dodge=False)
    plt.title("LLM Tokenizer and Tree-sitter Grammar Boundary Alignment Analysis (Model Average)")
    plt.xlabel("Alignment Score (%)")
    plt.ylabel("Model")
    plt.xlim(0, 100)
    plt.tight_layout()
    
    chart_path = "results/alignment_chart_by_model.png"
    plt.savefig(chart_path)
    print(f"Model comparison chart has been saved to {chart_path}")


    # If multiple files were analyzed, generate a chart by file
    if len(df['file_name'].unique()) > 1:
        plt.figure(figsize=(14, 8))
        sns.barplot(x="alignment_score_percent", y="file_name", hue="model_name", data=df, palette="viridis")
        plt.title("Model Alignment Score Comparison by File")
        plt.xlabel("Alignment Score (%)")
        plt.ylabel("File")
        plt.xlim(0, 100)
        plt.tight_layout()
        
        file_chart_path = "results/alignment_chart_by_file.png"
        plt.savefig(file_chart_path)
        print(f"File comparison chart has been saved to {file_chart_path}")



if __name__ == "__main__":
    main()