"""
lib/modules/gen_gds/gen_gds.py
阶段 3 — gen_gds：版图 GDSII 数据生成。

职责：
  - 生成驱动 Virtuoso (SKILL) 或 Innovus (TCL) 的版图导出脚本
  - 同时渲染 TCL 主脚本和 CSH 包装脚本
  - 产出 .gds 文件，存放于 release/output_file/
"""
from __future__ import annotations

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)


class GenGdsComponent(BaseComponent):
    """GDS 版图生成阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("gen_gds", config)

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """同时渲染 Innovus TCL 脚本和 CSH 驱动脚本。"""
        common_ctx = {
            "stage"         : self.stage_name,
            "project_name"  : self.config.project_name,
            "tech_node"     : self.config.tech_node,
            "pvt_corners"   : self.config.pvt_corners,
            "gds_source"    : str(self.config.gds_source),
            "output_gds"    : str(self.stage_dir / "release" / "output_file" / "stdcell_merge.gds"),
            "innovus_bin"   : self.config.tool_path("innovus"),
            "run_dir"       : str(self.run_dir),
            "log_dir"       : str(self.log_dir),
        }

        render_template(
            "tcl_innovus.j2",
            self.scr_dir / "gen_gds.tcl",
            **common_ctx,
        )

        csh_ctx = {
            **common_ctx,
            "tool_cmd"      : f"{self.config.tool_path('innovus')} -no_gui -batch -execute {self.scr_dir / 'gen_gds.tcl'}",
            "description"   : "GDS 版图生成",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_gen_gds.csh", **csh_ctx)
        logger.debug(f"[{self.stage_name}] 脚本生成: scr/gen_gds.tcl + run/run_gen_gds.csh")
