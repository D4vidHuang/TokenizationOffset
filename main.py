import os
from tree_sitter import Language, Parser
from transformers import AutoTokenizer
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# --- 1. Configuration ---
# Multiple models can be tested, especially those optimized for code
MODELS_TO_TEST = [
    "gpt2",                         # 通用模型作为基线
    "codellama/CodeLlama-7b-hf",    # Meta专门为代码优化的模型
    "bigcode/starcoder2-3b"         # BigCode项目（ServiceNow & Hugging Face）
]
CODE_SAMPLE_PATH = "code_samples/example.py"
TARGET_LANGUAGE = "python"


# --- 2. Initialize Tree-sitter Parser ---
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

# --- 3. Extract All Grammar Node Boundaries ---
def get_grammar_node_boundaries(parser: Parser, code_bytes: bytes) -> set:
    """Parse code and return start and end byte positions of all grammar nodes (non-terminals)"""
    tree = parser.parse(code_bytes)
    boundaries = set()
    
    # Use tree-cursor for efficient traversal
    cursor = tree.walk()
    
    # Breadth-first or depth-first traversal
    nodes_to_visit = [tree.root_node]
    while nodes_to_visit:
        node = nodes_to_visit.pop(0)
        # We only care about nodes with actual text range
        if node.start_byte != node.end_byte:
            boundaries.add(node.start_byte)
            boundaries.add(node.end_byte)
        
        nodes_to_visit.extend(node.children)
        
    return boundaries

# --- 4. Extract LLM Tokenizer Boundaries ---
def get_tokenizer_token_boundaries(model_name: str, code_string: str) -> set:
    """Tokenize for the specified model and return start and end character positions of all tokens"""
    # Use trust_remote_code=True to support models like StarCoder that require custom code
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # return_offsets_mapping=True is key, it returns the start and end positions of each token in the original string
    encoding = tokenizer(code_string, return_offsets_mapping=True)
    
    boundaries = set()
    for start, end in encoding['offset_mapping']:
        # (0, 0) is usually a special token like [CLS] or [BOS], which can be ignored
        if start != end:
            boundaries.add(start)
            boundaries.add(end)
            
    return boundaries

# --- 5. Main Analysis Process ---
def main():
    """Main function, performs analysis and generates reports"""
    print("Starting analysis...")
    
    # Ensure build directory exists
    os.makedirs("build", exist_ok=True)
    
    # Clone tree-sitter-python repository (if it doesn't exist)
    if not os.path.exists("vendor/tree-sitter-python"):
        print("Cloning tree-sitter-python repository...")
        os.system("git clone https://github.com/tree-sitter/tree-sitter-python.git vendor/tree-sitter-python")
    
    parser = setup_tree_sitter_parser(TARGET_LANGUAGE)
    
    with open(CODE_SAMPLE_PATH, "rb") as f:
        code_bytes = f.read()
    code_string = code_bytes.decode("utf-8")
    
    # Get baseline boundaries: tree-sitter grammar boundaries
    grammar_boundaries = get_grammar_node_boundaries(parser, code_bytes)
    print(f"Found {len(grammar_boundaries)} unique grammar boundaries from tree-sitter.")
    
    results = []
    
    for model_name in MODELS_TO_TEST:
        print(f"\n--- Analyzing model: {model_name} ---")
        try:
            tokenizer_boundaries = get_tokenizer_token_boundaries(model_name, code_string)
            print(f"Found {len(tokenizer_boundaries)} unique token boundaries for {model_name}.")
            
            # Calculate misalignment (points that exist in grammar boundaries but not in tokenizer boundaries)
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
            
            print(f"Alignment score: {alignment_score:.2f}%")
            
        except Exception as e:
            print(f"Unable to process {model_name}. Error: {e}")

    # --- 6. Generate Reports and Visualizations ---
    if not results:
        print("No results to report.")
        return
        
    df = pd.DataFrame(results)
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    
    # Save CSV report
    report_path = "results/alignment_report.csv"
    df.to_csv(report_path, index=False)
    print(f"\nComplete report saved to {report_path}")

    # Visualization
    df_sorted = df.sort_values("alignment_score_percent", ascending=False)
    plt.figure(figsize=(12, 7))
    sns.barplot(x="alignment_score_percent", y="model_name", data=df_sorted, palette="viridis", hue="model_name", dodge=False)
    plt.title("LLM Tokenizer and Tree-sitter Grammar Boundary Alignment Analysis")
    plt.xlabel("Alignment Score (%)")
    plt.ylabel("Model")
    plt.xlim(0, 100)
    plt.tight_layout()
    
    chart_path = "results/alignment_chart.png"
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")


if __name__ == "__main__":
    main()