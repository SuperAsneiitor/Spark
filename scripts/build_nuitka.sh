#!/usr/bin/env bash
# =============================================================================
# Linux: 使用 Nuitka 生成 --standalone 单目录发行包（与 spark 可执行文件同目录含 share/template）
#
# 依赖: Python3.9+、gcc、patchelf、pip 已安装 requirements.txt 与 nuitka
#   sudo apt install -y python3-dev build-essential patchelf
#   pip install nuitka ordered-set zstandard
#
# 用法:
#   ./scripts/build_nuitka.sh
# 产物:
#   dist/nuitka/spark.dist/   — 整目录交付用户，运行 ./spark -c proj.yaml ...
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_BASE="${OUT_BASE:-dist/nuitka}"
PY="${PYTHON:-python3}"

if ! "$PY" -c "import nuitka" 2>/dev/null; then
  echo "[ERROR] Nuitka 未安装。请执行: pip install nuitka ordered-set zstandard" >&2
  exit 1
fi

rm -rf "${OUT_BASE}"
mkdir -p "${OUT_BASE}"

echo "[INFO] Building Nuitka standalone from ${ROOT} ..."

# --include-package-data=jinja2: 部分环境需要 Jinja2 资源
"$PY" -m nuitka \
  --standalone \
  --output-dir="${OUT_BASE}" \
  --output-filename=spark \
  --assume-yes-for-downloads \
  --include-package=lib \
  --include-package-data=jinja2 \
  --include-data-dir=share/template=share/template \
  --include-data-files=spark_system.yaml=spark_system.yaml \
  --nofollow-import-to=pytest \
  --nofollow-import-to=test \
  bin/spark

DIST_DIR="${OUT_BASE}/spark.dist"
if [[ -d "$DIST_DIR" ]]; then
  echo "[OK] Build finished: ${DIST_DIR}"
  echo "     Run: ${DIST_DIR}/spark --help   (仍需 -c 与子命令)"
else
  echo "[WARN] Expected ${DIST_DIR} not found; check ${OUT_BASE} for actual output name." >&2
fi
