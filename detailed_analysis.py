import os
import json
from tree_sitter import Language, Parser
from transformers import AutoTokenizer
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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

def get_node_details(node, code_bytes):
    """获取节点的详细信息"""
    return {
        "type": node.type,
        "start_byte": node.start_byte,
        "end_byte": node.end_byte,
        "start_point": (node.start_point[0], node.start_point[1]),
        "end_point": (node.end_point[0], node.end_point[1]),
        "text": code_bytes[node.start_byte:node.end_byte].decode('utf-8')
    }

def analyze_grammar_structure(parser, code_bytes):
    """分析代码的语法结构，返回详细的节点信息"""
    tree = parser.parse(code_bytes)
    
    # 收集所有节点信息
    nodes_info = []
    
    def traverse(node, depth=0):
        if node.start_byte != node.end_byte:  # 跳过空节点
            nodes_info.append({
                **get_node_details(node, code_bytes),
                "depth": depth
            })
        
        for child in node.children:
            traverse(child, depth + 1)
    
    traverse(tree.root_node)
    return nodes_info

def analyze_tokenization(model_name, code_string):
    """分析模型的分词结果"""
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    encoding = tokenizer(code_string, return_offsets_mapping=True)
    
    tokens_info = []
    for i, (start, end) in enumerate(encoding['offset_mapping']):
        if start != end:  # 跳过特殊标记
            token = tokenizer.convert_ids_to_tokens([encoding['input_ids'][i]])[0]
            tokens_info.append({
                "token": token,
                "start_byte": start,
                "end_byte": end,
                "text": code_string[start:end]
            })
    
    return tokens_info

def find_misalignments(grammar_nodes, token_boundaries):
    """找出语法节点与分词边界的错位情况"""
    # 收集所有分词边界
    token_boundary_points = set()
    for start, end in token_boundaries:
        token_boundary_points.add(start)
        token_boundary_points.add(end)
    
    misalignments = []
    
    for node in grammar_nodes:
        start_misaligned = node["start_byte"] not in token_boundary_points
        end_misaligned = node["end_byte"] not in token_boundary_points
        
        if start_misaligned or end_misaligned:
            misalignments.append({
                **node,
                "start_misaligned": start_misaligned,
                "end_misaligned": end_misaligned
            })
    
    return misalignments

def analyze_node_types(misalignments):
    """分析哪些类型的节点最容易发生错位"""
    type_counts = {}
    for node in misalignments:
        node_type = node["type"]
        if node_type not in type_counts:
            type_counts[node_type] = 0
        type_counts[node_type] += 1
    
    return type_counts

def main():
    """主函数，执行详细分析"""
    print("开始详细分析...")
    
    # 确保build目录存在
    os.makedirs("build", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    # 克隆tree-sitter-python仓库（如果不存在）
    if not os.path.exists("vendor/tree-sitter-python"):
        print("克隆tree-sitter-python仓库...")
        os.system("git clone https://github.com/tree-sitter/tree-sitter-python.git vendor/tree-sitter-python")
    
    # 设置解析器
    parser = setup_tree_sitter_parser("python")
    
    # 读取代码样本
    code_path = "code_samples/example.py"
    with open(code_path, "rb") as f:
        code_bytes = f.read()
    code_string = code_bytes.decode("utf-8")
    
    # 分析语法结构
    print("分析语法结构...")
    grammar_nodes = analyze_grammar_structure(parser, code_bytes)
    print(f"找到{len(grammar_nodes)}个语法节点")
    
    # 要分析的模型
    models = ["gpt2", "codellama/CodeLlama-7b-hf", "bigcode/starcoder2-3b"]
    
    all_results = []
    
    for model_name in models:
        print(f"\n分析模型: {model_name}")
        try:
            # 分析分词
            tokens_info = analyze_tokenization(model_name, code_string)
            token_boundaries = [(token["start_byte"], token["end_byte"]) for token in tokens_info]
            
            # 找出错位
            misalignments = find_misalignments(grammar_nodes, token_boundaries)
            
            # 分析错位的节点类型
            type_counts = analyze_node_types(misalignments)
            
            # 计算错位率
            misalignment_rate = len(misalignments) / len(grammar_nodes) * 100
            
            result = {
                "model": model_name,
                "total_nodes": len(grammar_nodes),
                "misaligned_nodes": len(misalignments),
                "misalignment_rate": misalignment_rate,
                "type_counts": type_counts
            }
            
            all_results.append(result)
            
            print(f"总节点数: {len(grammar_nodes)}")
            print(f"错位节点数: {len(misalignments)}")
            print(f"错位率: {misalignment_rate:.2f}%")
            
            # 保存详细结果
            with open(f"results/{model_name.replace('/', '_')}_detailed.json", "w") as f:
                json.dump({
                    "grammar_nodes": grammar_nodes,
                    "tokens": tokens_info,
                    "misalignments": misalignments,
                    "type_counts": type_counts
                }, f, indent=2)
            
        except Exception as e:
            print(f"分析{model_name}时出错: {e}")
    
    # 创建比较图表
    if all_results:
        # 错位率比较
        plt.figure(figsize=(10, 6))
        df = pd.DataFrame([(r["model"], r["misalignment_rate"]) for r in all_results], 
                          columns=["Model", "Misalignment Rate (%)"])
        sns.barplot(x="Misalignment Rate (%)", y="Model", data=df, palette="viridis")
        plt.title("不同模型的语法-分词错位率")
        plt.tight_layout()
        plt.savefig("results/misalignment_rates.png")
        
        # 节点类型分析
        for result in all_results:
            model = result["model"].replace('/', '_')
            if result["type_counts"]:
                plt.figure(figsize=(12, 8))
                types = list(result["type_counts"].keys())
                counts = list(result["type_counts"].values())
                
                # 按计数排序
                sorted_indices = sorted(range(len(counts)), key=lambda i: counts[i], reverse=True)
                types = [types[i] for i in sorted_indices]
                counts = [counts[i] for i in sorted_indices]
                
                # 只显示前15种类型
                if len(types) > 15:
                    types = types[:15]
                    counts = counts[:15]
                
                sns.barplot(x=counts, y=types, palette="viridis")
                plt.title(f"{model} 模型中错位最多的节点类型")
                plt.xlabel("错位节点数")
                plt.tight_layout()
                plt.savefig(f"results/{model}_node_types.png")
    
    print("\n详细分析完成。结果保存在results目录中。")

if __name__ == "__main__":
    main()