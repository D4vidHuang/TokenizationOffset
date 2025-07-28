import sys
from transformers import AutoTokenizer
import colorama
from colorama import Fore, Style

def visualize_tokens(model_name, code_string):
    """Visualize the tokenization results of the model on code"""
    colorama.init()
    
    print(f"\n{Fore.CYAN}===== Tokenization Visualization for Model {model_name} ====={Style.RESET_ALL}")
    
    try:
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Get tokenization and offset mapping
        encoding = tokenizer(code_string, return_offsets_mapping=True)
        tokens = tokenizer.convert_ids_to_tokens(encoding['input_ids'])
        offsets = encoding['offset_mapping']
        
        # Print original code
        print(f"\n{Fore.WHITE}Original Code:{Style.RESET_ALL}")
        print(code_string)
        
        # Print tokenization results
        print(f"\n{Fore.WHITE}Tokenization Results:{Style.RESET_ALL}")
        
        # Skip special tokens
        start_idx = 0
        while start_idx < len(tokens) and offsets[start_idx] == (0, 0):
            start_idx += 1
            
        # Create colored display for each token
        colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA]
        
        for i in range(start_idx, len(tokens)):
            token = tokens[i]
            start, end = offsets[i]
            
            if start == end:  # 特殊标记
                continue
                
            color = colors[(i - start_idx) % len(colors)]
            print(f"{color}[{token}]{Style.RESET_ALL}", end=" ")
            
            # Line break every 10 tokens
            if (i - start_idx + 1) % 10 == 0:
                print()
                
        print("\n")
        
        # Print code with boundary markers
        print(f"\n{Fore.WHITE}Code with Boundary Markers:{Style.RESET_ALL}")
        
        # Create a character list for inserting boundary markers
        chars = list(code_string)
        
        # Collect all boundary positions
        boundaries = set()
        for start, end in offsets:
            if start != end:  # Skip special tokens
                boundaries.add(start)
                boundaries.add(end)
        
        # Insert boundary markers from back to front to avoid position shifts
        for pos in sorted(boundaries, reverse=True):
            if pos > 0 and pos < len(chars):
                chars.insert(pos, f"{Fore.RED}|{Style.RESET_ALL}")
        
        print(''.join(chars))
        
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_tokens.py <model_name> [code_file]")
        print("Example: python visualize_tokens.py gpt2 code_samples/example.py")
        sys.exit(1)
        
    model_name = sys.argv[1]
    
    # 从文件读取代码或使用示例代码
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'r') as f:
            code = f.read()
    else:
        code = """
def hello_world():
    print("Hello, world!")
    return 42
"""
    
    visualize_tokens(model_name, code)