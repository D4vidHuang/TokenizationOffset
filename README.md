# 语法边界与分词边界对齐分析工具

这个项目旨在量化不同大型语言模型(LLM)的分词边界与tree-sitter定义的语法边界之间的错位程度。

## 问题背景

当我们使用tree-sitter将代码按语法结构分割成块，然后将这些块作为提示输入给LLM时，这个块的起始点或结束点很可能恰好位于一个LLM词元的中间。这种错位可能会影响模型的生成质量。

## 项目结构

```
TokenizationOffset/
├── main.py                   # 主分析脚本
├── code_samples/             # 存放用于分析的源代码文件
│   ├── python/               # Python代码示例
│   │   ├── example.py
│   │   ├── algorithms.py
│   │   ├── async_example.py
│   │   ├── data_structures.py
│   │   ├── decorators.py
│   │   ├── file_operations.py
│   │   ├── generators.py
│   │   ├── oop_example.py
│   │   └── recursion_example.py
│   └── javascript/           # JavaScript代码示例
│       └── example.js
├── requirements.txt          # 项目依赖
├── results/                  # 存放分析结果 (CSV, 图表)
└── vendor/                   # 用于存放 tree-sitter 语言库
```

## 安装与使用

1. 安装依赖:
```bash
pip install -r requirements.txt
```

2. 运行分析:

基本用法:
```bash
python main.py
```

指定模型:
```bash
python main.py --model gpt2
```
或
```bash
python main.py -m codellama/CodeLlama-7b-hf
```

指定代码路径:
```bash
python main.py --code_path code_samples/python
```
或
```bash
python main.py -c path/to/your/code.py
```

指定语言:
```bash
python main.py --language javascript
```
或
```bash
python main.py -l python
```

组合使用:
```bash
python main.py -m gpt2 -c code_samples/javascript -l javascript
```

3. 查看结果:
分析结果将保存在`results/`目录下，包括CSV报告和可视化图表。

## 结果解读

- **CSV 报告** (alignment_report.csv):
  - file_name: 分析的文件名
  - model_name: 被测试的LLM
  - grammar_boundaries: tree-sitter识别出的独立语法边界总数
  - tokenizer_boundaries: LLM分词器产生的独立词元边界总数
  - mismatched_boundaries: 错位的边界点数量
  - alignment_score_percent: 对齐分数，计算公式为(1 - 错位数 / 语法边界总数) * 100

- **图表**:
  - alignment_chart_by_model.png: 各模型的平均对齐分数
  - alignment_chart_by_file.png: 各文件的模型对齐分数对比（当分析多个文件时）

## 预期发现

为代码特别训练或微调的模型（如Code Llama, StarCoder）通常会比通用语言模型（如GPT-2）有更高的对齐分数，因为它们的词汇表和分词策略更适合代码结构。