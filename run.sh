#!/bin/bash

# =======================================================
# 路径配置
# =======================================================
BASE_DIR="${HOME}/work"
OUTPUT_ROOT="${HOME}/work/results"
LOGS_DIR="${OUTPUT_ROOT}/logs"

# 确保输出目录和日志目录存在
mkdir -p ${LOGS_DIR} 

# =======================================================
# 实验参数
# 注意：串行执行时，你可以考虑将 workers 设为 128 来加速单个任务。
# =======================================================
MODELS="gpt2 roberta-base bert-base-uncased"
COMMON_ARGS="--workers 128 --per_file_timeout 10 --batch_size 10000 --max_files 1000000" 

# =======================================================
# 定义执行函数
# = 这个函数将执行单个任务并检查其状态
# =======================================================
run_analysis() {
    local LANGUAGE="$1"
    local CODE_PATH="$2"
    local OUTPUT_PATH="$3"
    local LOG_PATH="${LOGS_DIR}/${LANGUAGE}_analyzer.log"
    
    echo "======================================================"
    echo "Starting analysis for language: ${LANGUAGE}"
    
    # 执行命令，将所有输出重定向到日志文件
    python ${BASE_DIR}/TokenizationOffset/analyzer.py \
        --language ${LANGUAGE} \
        --code_dir ${CODE_PATH} \
        --output_dir ${OUTPUT_PATH} \
        --models ${MODELS} \
        ${COMMON_ARGS} \
        > "${LOG_PATH}" 2>&1
    
    # 检查上一个命令的退出状态
    if [ $? -eq 0 ]; then
        echo "Analysis for ${LANGUAGE} completed successfully."
    else
        echo "****************************************************"
        echo "WARNING: Analysis for ${LANGUAGE} FAILED (Exit Code: $?). Skipping to next language."
        echo "Check log file: ${LOG_PATH}"
        echo "****************************************************"
    fi
}

# =======================================================
# 任务列表 (顺序执行)
# =======================================================

# 1. Python
run_analysis "python" \
    "${BASE_DIR}/python_aise_code_output" \
    "${BASE_DIR}/pythonResNew"

# 2. Java
run_analysis "java" \
    "${BASE_DIR}/java_aise_code_output" \
    "${OUTPUT_ROOT}/JavaRES"

# 3. C
run_analysis "c" \
    "${BASE_DIR}/c_aise_code_output" \
    "${OUTPUT_ROOT}/C_RES"

# 4. C++
run_analysis "cpp" \
    "${BASE_DIR}/cpp_aise_code_output" \
    "${OUTPUT_ROOT}/CPP_RES"

# 5. Rust
run_analysis "rust" \
    "${BASE_DIR}/rust_aise_code_output" \
    "${OUTPUT_ROOT}/RUST_RES"

# 6. CSharp
run_analysis "csharp" \
    "${BASE_DIR}/csharp_aise_code_output" \
    "${OUTPUT_ROOT}/CSHARP_RES"

# 7. Go
run_analysis "go" \
    "${BASE_DIR}/go_aise_code_output" \
    "${OUTPUT_ROOT}/GO_RES"

# 8. JavaScript
run_analysis "javascript" \
    "${BASE_DIR}/javascript_aise_code_output" \
    "${OUTPUT_ROOT}/JAVASCRIPT_RES"

# 9. Scala
run_analysis "scala" \
    "${BASE_DIR}/scala_aise_code_output" \
    "${OUTPUT_ROOT}/SCALA_RES"

# =======================================================
# 结束提示
# =======================================================
echo "======================================================"
echo "All sequential experiments finished."
echo "Check the log files in ${LOGS_DIR} for individual status."