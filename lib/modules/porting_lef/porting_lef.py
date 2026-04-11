"""
lib/modules/porting_lef/porting_lef.py
阶段 — porting_lef：LEF 迁移 / 再输出（格式与 gen_gds 一致：Innovus TCL + CSH）。

职责：
  - 读入工艺/单元 LEF（paths.lef_source），写出至本阶段 release/output_file/
  - 具体 write_lef 选项依赖 PDK 与 Innovus 版本，可在生成 TCL 上按需微调
"""
from __future__ import annotations

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)


class PortingLefComponent(BaseComponent):
    """LEF Porting 阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("porting_lef", config)

    def _generate_scripts(self) -> None:
        out_lef = (
            self.stage_dir / "release" / "output_file" /
            f"{self.config.project_name}_ported.lef"
        )
        common_ctx = {
            "stage"         : self.stage_name,
            "project_name"  : self.config.project_name,
            "tech_node"     : self.config.tech_node,
            "pvt_corners"   : self.config.pvt_corners,
            "lef_source"    : str(self.config.lef_source),
            "output_lef"    : str(out_lef),
            "innovus_bin"   : self.config.tool_path("innovus"),
            "run_dir"       : str(self.run_dir),
            "log_dir"       : str(self.log_dir),
        }

        render_template(
            "tcl_innovus.j2",
            self.scr_dir / "porting_lef.tcl",
            **common_ctx,
        )

        csh_ctx = {
            **common_ctx,
            "tool_cmd": (
                f"{self.config.tool_path('innovus')} -no_gui -batch "
                f"-execute {self.scr_dir / 'porting_lef.tcl'}"
            ),
            "description": "LEF Porting（迁移/再输出）",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_porting_lef.csh", **csh_ctx)
        logger.debug(
            f"[{self.stage_name}] 脚本生成: scr/porting_lef.tcl + run/run_porting_lef.csh"
        )
