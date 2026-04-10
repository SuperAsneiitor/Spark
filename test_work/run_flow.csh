#!/bin/csh -f
# =============================================================================
# run_flow.csh  —  Spark 测试环境一键运行脚本
#
# 使用方式:
#   source /path/to/Altas/spark.csh   # 先初始化环境
#   csh -f /path/to/Altas/test_work/run_flow.csh [STAGE]
#
# 可选参数 STAGE（仅运行指定阶段及之后）:
#   init_env | analysis | gen_gds | gen_spice | gen_lib | gen_lef | gen_dft | release
#
# 示例:
#   csh -f run_flow.csh                  # 全流程运行
#   csh -f run_flow.csh gen_lib          # 从 gen_lib 开始运行
# =============================================================================

set SCRIPT_DIR = `dirname $0`
set PROJ_YAML  = "$SCRIPT_DIR/proj.yaml"
set SPARK_CMD  = "spark"

# ---- 校验 spark 命令可用 -----------------------------------------------------
which $SPARK_CMD >& /dev/null
if ( $status != 0 ) then
    echo "[ERROR] 'spark' command not found."
    echo "        Please run: source /path/to/Altas/spark.csh"
    exit 1
endif

# ---- 校验配置文件存在 ---------------------------------------------------------
if ( ! -f $PROJ_YAML ) then
    echo "[ERROR] Config file not found: $PROJ_YAML"
    exit 1
endif

# ---- 阶段顺序定义 ------------------------------------------------------------
set ALL_STAGES = ( init_env analysis gen_gds gen_spice gen_lib gen_lef gen_dft release )

# ---- 处理起始阶段参数 ---------------------------------------------------------
set START_STAGE = $1
if ( "$START_STAGE" == "" ) set START_STAGE = "init_env"

set STARTED = 0
foreach stage ( $ALL_STAGES )
    if ( "$stage" == "$START_STAGE" ) set STARTED = 1
    if ( $STARTED == 0 ) then
        echo "[SKIP]  $stage (before start stage)"
        continue
    endif

    echo ""
    echo "======================================================================"
    echo "  [START] Stage: $stage"
    echo "  Time  : `date '+%Y-%m-%d %H:%M:%S'`"
    echo "======================================================================"

    if ( "$stage" == "init_env" ) then
        # init_env 作为单条命令
        $SPARK_CMD -c $PROJ_YAML init_env
        if ( $status != 0 ) then
            echo "[ERROR] init_env failed. Aborting."
            exit 1
        endif
    else
        # 其余阶段：先 create_env，再 run，再 check
        $SPARK_CMD -c $PROJ_YAML create_${stage}_env
        if ( $status != 0 ) then
            echo "[ERROR] create_${stage}_env failed. Aborting."
            exit 1
        endif

        $SPARK_CMD -c $PROJ_YAML run_${stage}
        set RUN_STATUS = $status

        # 无论 run 是否成功都抽取报告
        $SPARK_CMD -c $PROJ_YAML report_${stage}

        if ( $RUN_STATUS != 0 ) then
            echo "[ERROR] run_${stage} failed (exit=$RUN_STATUS). Aborting."
            exit $RUN_STATUS
        endif

        # 结果校验
        $SPARK_CMD -c $PROJ_YAML check_${stage}
        if ( $status != 0 ) then
            echo "[WARN]  check_${stage} reported issues. See rpt/ for details."
            # 测试环境不中断，仅警告
        endif
    endif

    echo "  [DONE]  Stage: $stage  (`date '+%Y-%m-%d %H:%M:%S'`)"
end

echo ""
echo "======================================================================"
echo "  All stages completed."
echo "  Work directory: `cat $PROJ_YAML | grep work_dir | awk '{print $3}'`"
echo "======================================================================"
exit 0
