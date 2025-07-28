import sys
from transformers import AutoTokenizer
import colorama
from colorama import Fore, Style

def visualize_tokens(model_name, code_string):
    """可视化模型对代码的分词结果"""
    colorama.init()
    
    print(f"\n{Fore.CYAN}===== 模型 {model_name} 的分词可视化 ====={Style.RESET_ALL}")
    
    try:
        # 加载分词器
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # 获取分词和偏移映射
        encoding = tokenizer(code_string, return_offsets_mapping=True)
        tokens = tokenizer.convert_ids_to_tokens(encoding['input_ids'])
        offsets = encoding['offset_mapping']
        
        # 打印原始代码
        print(f"\n{Fore.WHITE}原始代码:{Style.RESET_ALL}")
        print(code_string)
        
        # 打印分词结果
        print(f"\n{Fore.WHITE}分词结果:{Style.RESET_ALL}")
        
        # 跳过特殊标记
        start_idx = 0
        while start_idx < len(tokens) and offsets[start_idx] == (0, 0):
            start_idx += 1
            
        # 为每个词元创建彩色显示
        colors = [Fore.RED, Fore.GREEN, Fore.YELLOW, Fore.BLUE, Fore.MAGENTA]
        
        for i in range(start_idx, len(tokens)):
            token = tokens[i]
            start, end = offsets[i]
            
            if start == end:  # 特殊标记
                continue
                
            color = colors[(i - start_idx) % len(colors)]
            print(f"{color}[{token}]{Style.RESET_ALL}", end=" ")
            
            # 每10个词元换行
            if (i - start_idx + 1) % 10 == 0:
                print()
                
        print("\n")
        
        # 打印带有边界标记的代码
        print(f"\n{Fore.WHITE}带有边界标记的代码:{Style.RESET_ALL}")
        
        # 创建一个字符列表，用于插入边界标记
        chars = list(code_string)
        
        # 收集所有边界位置
        boundaries = set()
        for start, end in offsets:
            if start != end:  # 跳过特殊标记
                boundaries.add(start)
                boundaries.add(end)
        
        # 从后向前插入边界标记，避免位置偏移
        for pos in sorted(boundaries, reverse=True):
            if pos > 0 and pos < len(chars):
                chars.insert(pos, f"{Fore.RED}|{Style.RESET_ALL}")
        
        print(''.join(chars))
        
    except Exception as e:
        print(f"{Fore.RED}错误: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python visualize_tokens.py <model_name> [code_file]")
        print("例如: python visualize_tokens.py gpt2 code_samples/example.py")
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