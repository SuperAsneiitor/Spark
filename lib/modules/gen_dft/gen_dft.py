"""
lib/modules/gen_dft/gen_dft.py
阶段 7 — gen_dft：可测性设计（DFT）模型生成。

职责：
  - 生成用于 ATPG 的单元模型（MDT / Tetramax 格式）
  - 驱动 Synopsys TetraMAX 或兼容工具读入 netlist 并输出 .stil / .spf 模型
  - 产出 DFT 模型文件，存放于 release/output_file/
"""
from __future__ import annotations

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)

_SUPPORTED_DFT_FORMATS = ["mdt", "stil", "tetramax"]


class GenDftComponent(BaseComponent):
    """DFT 可测性模型生成阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("gen_dft", config)
        self.dft_format: str = config.get(
            "gen_dft", "format", default="mdt"
        ).lower()
        if self.dft_format not in _SUPPORTED_DFT_FORMATS:
            raise ValueError(
                f"不支持的 DFT 格式: {self.dft_format!r}，"
                f"可选: {_SUPPORTED_DFT_FORMATS}"
            )

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """渲染 DFT 工具调用脚本。"""
        ctx = {
            "stage"         : self.stage_name,
            "project_name"  : self.config.project_name,
            "tech_node"     : self.config.tech_node,
            "netlist_source": str(self.config.netlist_source),
            "dft_format"    : self.dft_format,
            "output_dft"    : str(
                self.stage_dir / "release" / "output_file" /
                f"{self.config.project_name}.{self.dft_format}"
            ),
            "tool_cmd"      : self.config.tool_path("tetramax"),
            "run_dir"       : str(self.run_dir),
            "log_dir"       : str(self.log_dir),
            "description"   : f"DFT 模型生成 (格式: {self.dft_format.upper()})",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_gen_dft.csh", **ctx)
        logger.debug(f"[{self.stage_name}] 脚本生成: run/run_gen_dft.csh")
