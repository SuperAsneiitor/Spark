"""
lib/modules/gen_lef/gen_lef.py
阶段 6 — gen_lef：物理抽象 LEF 文件生成。

职责：
  - 从 GDS 中提取用于布局布线的物理抽象信息
  - 调用 Abstract Generator 等工具输出 .lef
  - 产出 .lef 存放于 release/output_file/
"""
from __future__ import annotations

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)


class GenLefComponent(BaseComponent):
    """LEF 物理抽象生成阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("gen_lef", config)

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """渲染 Abstract Generator 调用脚本。"""
        ctx = {
            "stage"       : self.stage_name,
            "project_name": self.config.project_name,
            "tech_node"   : self.config.tech_node,
            "gds_source"  : str(self.config.gds_source),
            "lef_source"  : str(self.config.lef_source),
            "output_lef"  : str(
                self.stage_dir / "release" / "output_file" /
                f"{self.config.project_name}.lef"
            ),
            "tool_cmd"    : self.config.tool_path("abstract"),
            "run_dir"     : str(self.run_dir),
            "log_dir"     : str(self.log_dir),
            "description" : "LEF 物理抽象生成",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_gen_lef.csh", **ctx)
        logger.debug(f"[{self.stage_name}] 脚本生成: run/run_gen_lef.csh")
