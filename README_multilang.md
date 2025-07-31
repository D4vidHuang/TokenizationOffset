# 多语言 Tree-sitter Rule-level Alignment Score 分析器

本项目实现了一个多语言的 Tree-sitter rule-level alignment score 分析器，用于计算代码的语法规则与 tokenization 边界的对齐程度。

## 功能特性

- 支持11种编程语言（Python、JavaScript、TypeScript、Java、C、C++、C#、Go、Ruby、Rust、Scala）
- 计算语法规则与 tokenization 边界的对齐分数
- 生成详细的分析报告和可视化图表
- 支持批量分析和结果比较
- 使用已编译的 Tree-sitter 语言库，运行高效稳定

## 项目文件结构

```
TokenizationOffset/
├── quick_analyzer.py           # 🎯 主分析器（推荐使用）
├── visualize_multilang_results.py  # 📊 可视化工具
├── simple_test.py             # 🧪 基础测试脚本
├── README_multilang.md        # 📖 使用文档
├── requirements.txt           # 📦 依赖列表
├── build/                     # 🔧 编译的语言库
├── code_samples/              # 📁 测试代码样本
└── results/                   # 📈 分析结果
```

## 使用方法

### 1. 快速开始（推荐）

```bash
# 运行主分析器
python quick_analyzer.py
```

### 2. 基础测试

```bash
# 运行简单测试
python simple_test.py
```

### 3. 生成可视化图表

```bash
# 生成分析图表
python visualize_multilang_results.py
```

## 分析结果

分析器会输出以下信息：

### 控制台输出
- 每种语言的对齐分数和排名
- 详细的规则匹配情况
- 语言间的对比分析
- 实时进度显示

### 生成文件
- **详细报告**: `results/multilang/{language}/rule_level_report_{model}.json`
- **跨语言对比**: `results/multilang/cross_language_report_{model}.json`
- **可视化图表**: `results/multilang/` 目录下的各种图表文件

## 支持的语言

| 语言 | 文件扩展名 | Tree-sitter 库 |
|------|------------|----------------|
| Python | .py | tree-sitter-python |
| JavaScript | .js | tree-sitter-javascript |
| TypeScript | .ts | tree-sitter-typescript |
| Java | .java | tree-sitter-java |
| C | .c | tree-sitter-c |
| C++ | .cpp | tree-sitter-cpp |
| C# | .cs | tree-sitter-c-sharp |
| Go | .go | tree-sitter-go |
| Ruby | .rb | tree-sitter-ruby |
| Rust | .rs | tree-sitter-rust |
| Scala | .scala | tree-sitter-scala |

## 分析指标说明

- **Rule-level Alignment Score**: 语法规则边界与token边界的对齐百分比
- **对齐率**: 完全对齐的规则数量占总规则数量的比例
- **规则类型统计**: 不同语法规则类型的对齐表现
- **语言排名**: 基于对齐分数的语言排序

## 研究发现

基于当前分析结果：

1. **Python** (30.54%) 表现最佳，语法结构与tokenization高度匹配
2. **C#** (9.05%) 表现相对较差，可能由于复杂的语法结构
3. 不同语言的对齐率差异显著，反映了语言设计的多样性
4. 静态类型语言和动态类型语言在对齐表现上各有特点

## 技术原理

1. **语法解析**: 使用 Tree-sitter 解析源代码生成抽象语法树
2. **规则提取**: 从语法树中提取所有语法规则的边界位置
3. **分词处理**: 使用指定的 tokenizer（默认GPT-2）对代码进行分词
4. **对齐计算**: 计算语法规则边界与 token 边界的匹配程度
5. **结果分析**: 生成统计报告和可视化图表

## 环境要求

- Python 3.7+
- 已编译的 Tree-sitter 语言库（项目已包含）
- 必要的 Python 依赖包

## 依赖安装

```bash
pip install -r requirements.txt
```

主要依赖包：
- `tree-sitter`: Tree-sitter Python 绑定
- `transformers`: Hugging Face 模型库
- `matplotlib`: 图表绘制
- `seaborn`: 统计图表
- `pandas`: 数据处理
- `numpy`: 数值计算

## 项目优势

- **高效稳定**: 使用预编译的语言库，避免重复编译
- **多语言支持**: 一次性分析11种主流编程语言
- **详细报告**: 生成全面的分析报告和可视化图表
- **易于使用**: 简单的命令行界面，开箱即用
- **可扩展性**: 易于添加新的编程语言支持

## 应用场景

- **代码处理模型研究**: 为改进代码理解模型提供量化基础
- **Tokenization 策略优化**: 研究语法感知的分词策略
- **编程语言特性分析**: 比较不同语言的语法结构特点
- **工具开发**: 为代码分析工具提供语法对齐信息

## 扩展开发

要添加新的编程语言支持：

1. 获取对应的 Tree-sitter 语言库
2. 编译语言库到 `build/` 目录
3. 在分析器中添加语言配置
4. 准备测试代码样本
5. 验证分析功能

这个工具为代码处理和自然语言处理的交叉研究提供了重要的量化分析基础。