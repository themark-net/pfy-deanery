#!/bin/bash
set -euo pipefail
cd $HOME/DEVELOP/pfy-mentat/tmp/local-bench-5
Q36="/usr/share/ollama/.ollama/models/blobs/sha256-d372de8e934898a59e6ccfabc3368474711384d8f1fd4d22d87a3f0a45400cdc"
AIR="/usr/share/ollama/.ollama/models/blobs/sha256-a6a5f1eb99191da97aebe69aed2d53aa07c03236c082b9e5dfc1f6301cc88f16-partial"
echo "=== qwen36 rocm-noreason $(date -Iseconds) ==="
./pipelines/dogfood/local-bench-5/run_runtime_matrix.sh "$Q36" qwen36 rocm-noreason 18280 4096
echo "=== glm-air rebench $(date -Iseconds) ==="
./pipelines/dogfood/local-bench-5/run_runtime_matrix.sh "$AIR" glm-air rocm-noreason 18280 4096
echo "=== qwen36 vulkan $(date -Iseconds) ==="
./pipelines/dogfood/local-bench-5/run_runtime_matrix.sh "$Q36" qwen36 vulkan 18380 4096
echo ALL_MATRIX_DONE
