import os
from tree_sitter import Language, Parser
from transformers import AutoTokenizer
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- 1. 配置 ---
# 可以测试多个模型，尤其是为代码优化的模型
MODELS_TO_TEST = [
    "gpt2",                         # 通用模型作为基线
    "codellama/CodeLlama-7b-hf",    # Meta专门为代码优化的模型
    "bigcode/starcoder2-3b"         # BigCode项目（ServiceNow & Hugging Face）
]
CODE_SAMPLE_PATH = "code_samples/example.py"
TARGET_LANGUAGE = "python"


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
def main():
    """主函数，执行分析并生成报告"""
    print("开始分析...")
    
    # 确保build目录存在
    os.makedirs("build", exist_ok=True)
    
    # 克隆tree-sitter-python仓库（如果不存在）
    if not os.path.exists("vendor/tree-sitter-python"):
        print("克隆tree-sitter-python仓库...")
        os.system("git clone https://github.com/tree-sitter/tree-sitter-python.git vendor/tree-sitter-python")
    
    parser = setup_tree_sitter_parser(TARGET_LANGUAGE)
    
    with open(CODE_SAMPLE_PATH, "rb") as f:
        code_bytes = f.read()
    code_string = code_bytes.decode("utf-8")
    
    # 获取基准边界：tree-sitter的语法边界
    grammar_boundaries = get_grammar_node_boundaries(parser, code_bytes)
    print(f"从tree-sitter找到{len(grammar_boundaries)}个唯一语法边界。")
    
    results = []
    
    for model_name in MODELS_TO_TEST:
        print(f"\n--- 分析模型: {model_name} ---")
        try:
            tokenizer_boundaries = get_tokenizer_token_boundaries(model_name, code_string)
            print(f"为{model_name}找到{len(tokenizer_boundaries)}个唯一词元边界。")
            
            # 计算错位（即存在于语法边界集合但不存在于分词边界集合中的点）
            mismatched_boundaries = grammar_boundaries.difference(tokenizer_boundaries)
            
            alignment_score = 0
            if grammar_boundaries:
                alignment_score = (1 - len(mismatched_boundaries) / len(grammar_boundaries)) * 100
            
            results.append({
                "model_name": model_name,
                "grammar_boundaries": len(grammar_boundaries),
                "tokenizer_boundaries": len(tokenizer_boundaries),
                "mismatched_boundaries": len(mismatched_boundaries),
                "alignment_score_percent": alignment_score
            })
            
            print(f"对齐分数: {alignment_score:.2f}%")
            
        except Exception as e:
            print(f"无法处理{model_name}。错误: {e}")

    # --- 6. 生成报告和可视化 ---
    if not results:
        print("没有结果可报告。")
        return
        
    df = pd.DataFrame(results)
    
    # 创建结果目录
    os.makedirs("results", exist_ok=True)
    
    # 保存CSV报告
    report_path = "results/alignment_report.csv"
    df.to_csv(report_path, index=False)
    print(f"\n完整报告已保存到{report_path}")

    # 可视化
    df_sorted = df.sort_values("alignment_score_percent", ascending=False)
    plt.figure(figsize=(12, 7))
    sns.barplot(x="alignment_score_percent", y="model_name", data=df_sorted, palette="viridis", hue="model_name", dodge=False)
    plt.title("LLM分词器与Tree-sitter语法边界对齐分析")
    plt.xlabel("对齐分数 (%)")
    plt.ylabel("模型")
    plt.xlim(0, 100)
    plt.tight_layout()
    
    chart_path = "results/alignment_chart.png"
    plt.savefig(chart_path)
    print(f"图表已保存到{chart_path}")


if __name__ == "__main__":
    main()