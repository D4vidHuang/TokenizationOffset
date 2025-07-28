# 语法边界与分词边界对齐分析

这个项目旨在量化不同大型语言模型(LLM)的分词边界与tree-sitter定义的语法边界之间的错位程度。

## 问题背景

当我们使用tree-sitter将代码按语法结构分割成块，然后将这些块作为提示输入给LLM时，这个块的起始点或结束点很可能恰好位于一个LLM词元的中间。这种错位可能会影响模型的生成质量。

## 项目结构

```
llm-grammar-token-alignment/
├── main.py                   # 主分析脚本
├── code_samples/             # 存放用于分析的源代码文件
│   └── example.py
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
```bash
python main.py
```

3. 查看结果:
分析结果将保存在`results/`目录下，包括CSV报告和可视化图表。

## 结果解读

- **CSV 报告** (alignment_report.csv):
  - model_name: 被测试的LLM
  - grammar_boundaries: tree-sitter识别出的独立语法边界总数
  - tokenizer_boundaries: LLM分词器产生的独立词元边界总数
  - mismatched_boundaries: 错位的边界点数量
  - alignment_score_percent: 对齐分数，计算公式为(1 - 错位数 / 语法边界总数) * 100

- **图表** (alignment_chart.png):
  条形图直观展示各模型的对齐分数。

## 预期发现

为代码特别训练或微调的模型（如Code Llama, StarCoder）通常会比通用语言模型（如GPT-2）有更高的对齐分数，因为它们的词汇表和分词策略更适合代码结构。