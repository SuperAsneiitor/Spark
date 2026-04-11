"""
lib/modules/porting_gds/porting_gds.py
阶段 — porting_gds：GDS 迁移 / 再输出（格式与 gen_gds 一致：Innovus TCL + CSH）。

职责：
  - 读入参考 GDS（paths.gds_source），经 Innovus 流程写出至本阶段 release/output_file/
  - 脚本形态与 gen_gds 相同，便于与后续 gen_gds 区分职责（迁移 vs 生成）
"""
from __future__ import annotations

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)


class PortingGdsComponent(BaseComponent):
    """GDS Porting 阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("porting_gds", config)

    def _generate_scripts(self) -> None:
        common_ctx = {
            "stage"         : self.stage_name,
            "project_name"  : self.config.project_name,
            "tech_node"     : self.config.tech_node,
            "pvt_corners"   : self.config.pvt_corners,
            "gds_source"    : str(self.config.gds_source),
            "output_gds"    : str(
                self.stage_dir / "release" / "output_file" / "stdcell_ported.gds"
            ),
            "innovus_bin"   : self.config.tool_path("innovus"),
            "run_dir"       : str(self.run_dir),
            "log_dir"       : str(self.log_dir),
        }

        render_template(
            "tcl_innovus.j2",
            self.scr_dir / "porting_gds.tcl",
            **common_ctx,
        )

        csh_ctx = {
            **common_ctx,
            "tool_cmd": (
                f"{self.config.tool_path('innovus')} -no_gui -batch "
                f"-execute {self.scr_dir / 'porting_gds.tcl'}"
            ),
            "description": "GDS Porting（迁移/再输出）",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_porting_gds.csh", **csh_ctx)
        logger.debug(
            f"[{self.stage_name}] 脚本生成: scr/porting_gds.tcl + run/run_porting_gds.csh"
        )
