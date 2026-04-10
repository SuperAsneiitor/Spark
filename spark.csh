#!/bin/csh -f
# =============================================================================
# spark.csh - Spark EDA 环境初始化脚本
# 使用方式: source spark.csh
# =============================================================================

# ---------- 定位脚本自身所在目录（兼容 source 调用）--------------------------
set _SPARK_SOURCE = `readlink -f ${0:a}`
set SPARK_HOME    = `dirname $_SPARK_SOURCE`

# ---------- 核心环境变量 -------------------------------------------------------
setenv SPARK_HOME    $SPARK_HOME
setenv SPARK_BIN     $SPARK_HOME/bin
setenv SPARK_LIB     $SPARK_HOME/lib
setenv SPARK_SHARE   $SPARK_HOME/share
setenv SPARK_TMPL    $SPARK_HOME/share/template

# ---------- Python 路径注入 ---------------------------------------------------
# 将 lib 目录加入 PYTHONPATH，使 "from lib.xxx import yyy" 可全局解析
if ( $?PYTHONPATH ) then
    setenv PYTHONPATH ${SPARK_HOME}:${PYTHONPATH}
else
    setenv PYTHONPATH ${SPARK_HOME}
endif

# ---------- PATH 注入 ---------------------------------------------------------
if ( $?PATH ) then
    setenv PATH ${SPARK_BIN}:${PATH}
else
    setenv PATH ${SPARK_BIN}
endif

# ---------- 提示信息 ----------------------------------------------------------
echo "=========================================="
echo "  Spark StdCell Automation Env Loaded"
echo "  SPARK_HOME : $SPARK_HOME"
echo "  Python     : `which python3` (`python3 --version`)"
echo "=========================================="
