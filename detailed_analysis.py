import os
import json
from tree_sitter import Language, Parser
from transformers import AutoTokenizer
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def setup_tree_sitter_parser(language_name: str) -> Parser:
    """Compile and load tree-sitter parser for the specified language"""
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
    """Get detailed information about the node"""
    return {
        "type": node.type,
        "start_byte": node.start_byte,
        "end_byte": node.end_byte,
        "start_point": (node.start_point[0], node.start_point[1]),
        "end_point": (node.end_point[0], node.end_point[1]),
        "text": code_bytes[node.start_byte:node.end_byte].decode('utf-8')
    }

def analyze_grammar_structure(parser, code_bytes):
    """Analyze the grammatical structure of code, return detailed node information"""
    tree = parser.parse(code_bytes)
    
    # 收集所有节点信息
    nodes_info = []
    
    def traverse(node, depth=0):
        if node.start_byte != node.end_byte:  # Skip empty nodes
            nodes_info.append({
                **get_node_details(node, code_bytes),
                "depth": depth
            })
        
        for child in node.children:
            traverse(child, depth + 1)
    
    traverse(tree.root_node)
    return nodes_info

def analyze_tokenization(model_name, code_string):
    """Analyze the tokenization results of the model"""
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    encoding = tokenizer(code_string, return_offsets_mapping=True)
    
    tokens_info = []
    for i, (start, end) in enumerate(encoding['offset_mapping']):
        if start != end:  # Skip special tokens
            token = tokenizer.convert_ids_to_tokens([encoding['input_ids'][i]])[0]
            tokens_info.append({
                "token": token,
                "start_byte": start,
                "end_byte": end,
                "text": code_string[start:end]
            })
    
    return tokens_info

def find_misalignments(grammar_nodes, token_boundaries):
    """Find misalignments between grammar nodes and tokenization boundaries"""
    # Collect all tokenization boundaries
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
    """Analyze which types of nodes are most prone to misalignment"""
    type_counts = {}
    for node in misalignments:
        node_type = node["type"]
        if node_type not in type_counts:
            type_counts[node_type] = 0
        type_counts[node_type] += 1
    
    return type_counts

def main():
    """Main function, performs detailed analysis"""
    print("Starting detailed analysis...")
    
    # Ensure build directory exists
    os.makedirs("build", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    
    # Clone tree-sitter-python repository (if it doesn't exist)
    if not os.path.exists("vendor/tree-sitter-python"):
        print("Cloning tree-sitter-python repository...")
        os.system("git clone https://github.com/tree-sitter/tree-sitter-python.git vendor/tree-sitter-python")
    
    # Set up parser
    parser = setup_tree_sitter_parser("python")
    
    # Read code sample
    code_path = "code_samples/example.py"
    with open(code_path, "rb") as f:
        code_bytes = f.read()
    code_string = code_bytes.decode("utf-8")
    
    # Analyze grammatical structure
    print("Analyzing grammatical structure...")
    grammar_nodes = analyze_grammar_structure(parser, code_bytes)
    print(f"Found {len(grammar_nodes)} grammar nodes")
    
    # Models to analyze
    models = ["gpt2", "codellama/CodeLlama-7b-hf", "bigcode/starcoder2-3b"]
    
    all_results = []
    
    for model_name in models:
        print(f"\nAnalyzing model: {model_name}")
        try:
            # Analyze tokenization
            tokens_info = analyze_tokenization(model_name, code_string)
            token_boundaries = [(token["start_byte"], token["end_byte"]) for token in tokens_info]
            
            # Find misalignments
            misalignments = find_misalignments(grammar_nodes, token_boundaries)
            
            # Analyze misaligned node types
            type_counts = analyze_node_types(misalignments)
            
            # Calculate misalignment rate
            misalignment_rate = len(misalignments) / len(grammar_nodes) * 100
            
            result = {
                "model": model_name,
                "total_nodes": len(grammar_nodes),
                "misaligned_nodes": len(misalignments),
                "misalignment_rate": misalignment_rate,
                "type_counts": type_counts
            }
            
            all_results.append(result)
            
            print(f"Total nodes: {len(grammar_nodes)}")
            print(f"Misaligned nodes: {len(misalignments)}")
            print(f"Misalignment rate: {misalignment_rate:.2f}%")
            
            # Save detailed results
            with open(f"results/{model_name.replace('/', '_')}_detailed.json", "w") as f:
                json.dump({
                    "grammar_nodes": grammar_nodes,
                    "tokens": tokens_info,
                    "misalignments": misalignments,
                    "type_counts": type_counts
                }, f, indent=2)
            
        except Exception as e:
            print(f"Error analyzing {model_name}: {e}")
    
    # Create comparison charts
    if all_results:
        # Misalignment rate comparison
        plt.figure(figsize=(10, 6))
        df = pd.DataFrame([(r["model"], r["misalignment_rate"]) for r in all_results], 
                          columns=["Model", "Misalignment Rate (%)"])
        sns.barplot(x="Misalignment Rate (%)", y="Model", data=df, palette="viridis")
        plt.title("Grammar-Tokenization Misalignment Rate for Different Models")
        plt.tight_layout()
        plt.savefig("results/misalignment_rates.png")
        
        # Node type analysis
        for result in all_results:
            model = result["model"].replace('/', '_')
            if result["type_counts"]:
                plt.figure(figsize=(12, 8))
                types = list(result["type_counts"].keys())
                counts = list(result["type_counts"].values())
                
                # Sort by count
                sorted_indices = sorted(range(len(counts)), key=lambda i: counts[i], reverse=True)
                types = [types[i] for i in sorted_indices]
                counts = [counts[i] for i in sorted_indices]
                
                # Only show top 15 types
                if len(types) > 15:
                    types = types[:15]
                    counts = counts[:15]
                
                sns.barplot(x=counts, y=types, palette="viridis")
                plt.title(f"Most Frequently Misaligned Node Types in {model}")
                plt.xlabel("Number of Misaligned Nodes")
                plt.tight_layout()
                plt.savefig(f"results/{model}_node_types.png")
    
    print("\nDetailed analysis complete. Results saved in the results directory.")

if __name__ == "__main__":
    main()