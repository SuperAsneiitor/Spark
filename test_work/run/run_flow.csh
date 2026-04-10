#!/bin/csh -f
# =============================================================================
# run_flow.csh  —  Master Run Script
# Project     : fake_stdcell_28nm
# Tech Node   : 28nm
# Case        : fake_stdcell / v1.0
# Generated   : 2026-04-10 17:01:28
#
# 使用方式:
#   csh -f C:\Users\Asneiitor\Desktop\AI_exploree\Altas\test_work\run/run_flow.csh [--from STAGE]
#
# 可选参数 --from STAGE: 跳过该阶段之前的所有阶段
#   可选值: analysis gen_gds gen_spice gen_lib gen_lef gen_dft release
# =============================================================================
# DO NOT EDIT MANUALLY — regenerate via: spark -c <cfg> init_env
# =============================================================================

# ---------- 环境检查 -----------------------------------------------------------
if ( ! $?SPARK_HOME ) then
    echo "[ERROR] SPARK_HOME is not set. Please run: source <path>/spark.csh"
    exit 1
endif

# ---------- 配置文件路径 -------------------------------------------------------
set CFG      = "C:\Users\Asneiitor\Desktop\AI_exploree\Altas\test_work\cfg\proj_demo.yaml"
set ROOT_DIR = "C:\Users\Asneiitor\Desktop\AI_exploree\Altas\test_work"
set LOG_DIR  = "$ROOT_DIR/run/log"

if ( ! -d $LOG_DIR ) mkdir -p $LOG_DIR
set MASTER_LOG = "$LOG_DIR/run_flow_`date '+%Y%m%d_%H%M%S'`.log"

# ---------- 起始阶段解析 -------------------------------------------------------
set FROM_STAGE = ""
if ( "$1" == "--from" ) then
    set FROM_STAGE = "$2"
endif

# ---------- 工具函数 -----------------------------------------------------------
alias log_info  'echo "[INFO]  [`date +%H:%M:%S`] \!*" | tee -a $MASTER_LOG'
alias log_error 'echo "[ERROR] [`date +%H:%M:%S`] \!*" | tee -a $MASTER_LOG'
alias log_sep   'echo "======================================================" | tee -a $MASTER_LOG'

log_info "Master run started: fake_stdcell_28nm"
log_info "Config : $CFG"
log_info "Root   : $ROOT_DIR"
log_info "Log    : $MASTER_LOG"

# ---------- 阶段执行宏 ---------------------------------------------------------
# 用法: run_stage <stage_name>
# 依次执行 create_<stage>_env → run_<stage> → report_<stage> → check_<stage>
set _SKIP = 1

# ---- Stage: analysis -------------------------------------------------------
log_sep
log_info "Stage [1/7]: analysis"

if ( "$FROM_STAGE" == "analysis" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] analysis (before --from stage)"
    goto next_analysis
endif

log_info "  => create_analysis_env"
spark -c $CFG create_analysis_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_analysis_env failed. Aborting."
    exit 1
endif

log_info "  => run_analysis"
spark -c $CFG run_analysis >>& $MASTER_LOG
set _RC = $status

log_info "  => report_analysis"
spark -c $CFG report_analysis >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_analysis failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_analysis"
spark -c $CFG check_analysis >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_analysis reported issues — see rpt/ for details."
endif

log_info "Stage analysis completed."
next_analysis:

# ---- Stage: gen_gds -------------------------------------------------------
log_sep
log_info "Stage [2/7]: gen_gds"

if ( "$FROM_STAGE" == "gen_gds" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] gen_gds (before --from stage)"
    goto next_gen_gds
endif

log_info "  => create_gen_gds_env"
spark -c $CFG create_gen_gds_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_gen_gds_env failed. Aborting."
    exit 1
endif

log_info "  => run_gen_gds"
spark -c $CFG run_gen_gds >>& $MASTER_LOG
set _RC = $status

log_info "  => report_gen_gds"
spark -c $CFG report_gen_gds >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_gen_gds failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_gen_gds"
spark -c $CFG check_gen_gds >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_gen_gds reported issues — see rpt/ for details."
endif

log_info "Stage gen_gds completed."
next_gen_gds:

# ---- Stage: gen_spice -------------------------------------------------------
log_sep
log_info "Stage [3/7]: gen_spice"

if ( "$FROM_STAGE" == "gen_spice" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] gen_spice (before --from stage)"
    goto next_gen_spice
endif

log_info "  => create_gen_spice_env"
spark -c $CFG create_gen_spice_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_gen_spice_env failed. Aborting."
    exit 1
endif

log_info "  => run_gen_spice"
spark -c $CFG run_gen_spice >>& $MASTER_LOG
set _RC = $status

log_info "  => report_gen_spice"
spark -c $CFG report_gen_spice >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_gen_spice failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_gen_spice"
spark -c $CFG check_gen_spice >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_gen_spice reported issues — see rpt/ for details."
endif

log_info "Stage gen_spice completed."
next_gen_spice:

# ---- Stage: gen_lib -------------------------------------------------------
log_sep
log_info "Stage [4/7]: gen_lib"

if ( "$FROM_STAGE" == "gen_lib" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] gen_lib (before --from stage)"
    goto next_gen_lib
endif

log_info "  => create_gen_lib_env"
spark -c $CFG create_gen_lib_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_gen_lib_env failed. Aborting."
    exit 1
endif

log_info "  => run_gen_lib"
spark -c $CFG run_gen_lib >>& $MASTER_LOG
set _RC = $status

log_info "  => report_gen_lib"
spark -c $CFG report_gen_lib >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_gen_lib failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_gen_lib"
spark -c $CFG check_gen_lib >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_gen_lib reported issues — see rpt/ for details."
endif

log_info "Stage gen_lib completed."
next_gen_lib:

# ---- Stage: gen_lef -------------------------------------------------------
log_sep
log_info "Stage [5/7]: gen_lef"

if ( "$FROM_STAGE" == "gen_lef" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] gen_lef (before --from stage)"
    goto next_gen_lef
endif

log_info "  => create_gen_lef_env"
spark -c $CFG create_gen_lef_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_gen_lef_env failed. Aborting."
    exit 1
endif

log_info "  => run_gen_lef"
spark -c $CFG run_gen_lef >>& $MASTER_LOG
set _RC = $status

log_info "  => report_gen_lef"
spark -c $CFG report_gen_lef >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_gen_lef failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_gen_lef"
spark -c $CFG check_gen_lef >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_gen_lef reported issues — see rpt/ for details."
endif

log_info "Stage gen_lef completed."
next_gen_lef:

# ---- Stage: gen_dft -------------------------------------------------------
log_sep
log_info "Stage [6/7]: gen_dft"

if ( "$FROM_STAGE" == "gen_dft" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] gen_dft (before --from stage)"
    goto next_gen_dft
endif

log_info "  => create_gen_dft_env"
spark -c $CFG create_gen_dft_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_gen_dft_env failed. Aborting."
    exit 1
endif

log_info "  => run_gen_dft"
spark -c $CFG run_gen_dft >>& $MASTER_LOG
set _RC = $status

log_info "  => report_gen_dft"
spark -c $CFG report_gen_dft >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_gen_dft failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_gen_dft"
spark -c $CFG check_gen_dft >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_gen_dft reported issues — see rpt/ for details."
endif

log_info "Stage gen_dft completed."
next_gen_dft:

# ---- Stage: release -------------------------------------------------------
log_sep
log_info "Stage [7/7]: release"

if ( "$FROM_STAGE" == "release" ) set _SKIP = 0
if ( $_SKIP ) then
    log_info "[SKIP] release (before --from stage)"
    goto next_release
endif

log_info "  => create_release_env"
spark -c $CFG create_release_env >>& $MASTER_LOG
if ( $status != 0 ) then
    log_error "create_release_env failed. Aborting."
    exit 1
endif

log_info "  => run_release"
spark -c $CFG run_release >>& $MASTER_LOG
set _RC = $status

log_info "  => report_release"
spark -c $CFG report_release >>& $MASTER_LOG

if ( $_RC != 0 ) then
    log_error "run_release failed (rc=$_RC). Aborting."
    exit $_RC
endif

log_info "  => check_release"
spark -c $CFG check_release >>& $MASTER_LOG
if ( $status != 0 ) then
    log_info "  [WARN] check_release reported issues — see rpt/ for details."
endif

log_info "Stage release completed."
next_release:

# ---------- 完成 ---------------------------------------------------------------
log_sep
log_info "All stages completed successfully."
log_info "Release artifacts: $ROOT_DIR/release/"
log_info "Master log       : $MASTER_LOG"
exit 0
