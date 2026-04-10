"""
lib/modules/gen_spice/gen_spice.py
阶段 4 — gen_spice：物理验证与寄生参数提取。

子步骤（顺序执行）：
  1. run_pv  — DRC + LVS（调用 Calibre 或 PVS）
  2. run_rc  — RC Extraction / PEX（生成带寄生参数的 SPICE 网表）

设计要点：
  - 重写 run() 以实现两阶段顺序调度
  - 每个子步骤独立拥有 .csh 脚本，方便单独重跑
  - run_pv 失败时可配置 continue_on_drc_error 标志
"""
from __future__ import annotations

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)


class GenSpiceComponent(BaseComponent):
    """SPICE 网表与寄生参数提取阶段（含 PV + RC 两子步骤）。"""

    def __init__(self, config: SparkConfig):
        super().__init__("gen_spice", config)
        self.continue_on_drc_error: bool = config.get(
            "gen_spice", "continue_on_drc_error", default=False
        )

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """分别渲染 PV 和 RC 的 C-Shell 脚本。"""
        base_ctx = {
            "stage"        : self.stage_name,
            "project_name" : self.config.project_name,
            "tech_node"    : self.config.tech_node,
            "pvt_corners"  : self.config.pvt_corners,
            "gds_source"   : str(self.config.gds_source),
            "netlist_source": str(self.config.netlist_source),
            "run_dir"      : str(self.run_dir),
            "log_dir"      : str(self.log_dir),
            "rpt_dir"      : str(self.report_dir),
            "output_dir"   : str(self.stage_dir / "release" / "output_file"),
        }

        pv_ctx = {
            **base_ctx,
            "sub_stage"   : "pv",
            "tool_cmd"    : self.config.tool_path("calibre"),
            "description" : "物理验证 (DRC + LVS)",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_pv.csh", **pv_ctx)

        rc_ctx = {
            **base_ctx,
            "sub_stage"   : "rc",
            "tool_cmd"    : self.config.tool_path("calibre"),
            "description" : "RC 寄生参数提取 (PEX)",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_rc.csh", **rc_ctx)
        logger.debug(f"[{self.stage_name}] 脚本生成: run/run_pv.csh + run/run_rc.csh")

    # ------------------------------------------------------------------
    def run(self) -> None:
        """重写：顺序执行 PV → RC 两子步骤。"""
        logger.info(f"[{self.stage_name}] ── 子步骤 1/2: 物理验证 (PV) ──")
        try:
            self._execute_csh("run_pv.csh")
        except Exception as exc:
            if self.continue_on_drc_error:
                logger.warning(
                    f"[{self.stage_name}] PV 失败（continue_on_drc_error=True），继续执行 RC。原因: {exc}"
                )
            else:
                logger.error(f"[{self.stage_name}] PV 失败，终止后续步骤。")
                raise

        logger.info(f"[{self.stage_name}] ── 子步骤 2/2: RC 寄生参数提取 (RC) ──")
        self._execute_csh("run_rc.csh")
        logger.info(f"[{self.stage_name}] 全部子步骤执行完成。")
