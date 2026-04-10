"""
lib/modules/analysis/analysis.py
阶段 2 — analysis：标准单元扫描与分类。

职责：
  - 解析 CDL/Netlist 文件，枚举所有 Cell 实例
  - 按类型分类：Combinational / Sequential / Clock / Filler / Tap
  - 输出 target_list.txt 供后续阶段引用
  - 生成阶段汇报（analysis_report.txt）
"""
from __future__ import annotations

import re
from pathlib import Path
from dataclasses import dataclass, field

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.logger         import get_logger

logger = get_logger(__name__)

# CDL .SUBCKT 行匹配模式（简化版）
_SUBCKT_RE = re.compile(r"^\s*\.SUBCKT\s+(\S+)", re.IGNORECASE)

# 单元类型关键字映射（可按项目定制扩展）
_CELL_TYPE_KEYWORDS: dict[str, list[str]] = {
    "sequential" : ["DFF", "LATCH", "FF", "REG", "SDQ"],
    "clock"      : ["CK", "CLK", "BUF_CLK", "CLKBUF", "CLKINV"],
    "filler"     : ["FILL", "DECAP", "WELL"],
    "tap"        : ["TAP", "ENDCAP", "CORNER"],
}


@dataclass
class CellInfo:
    name: str
    cell_type: str = "combinational"


class AnalysisComponent(BaseComponent):
    """单元分析与目标列表生成阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("analysis", config)
        self.cells: list[CellInfo] = []

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """渲染分析驱动脚本（预留，实际分析由 Python 内部完成）。"""
        context = {
            "stage"       : self.stage_name,
            "project_name": self.config.project_name,
            "tech_node"   : self.config.tech_node,
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_analysis.csh", **context)

    # ------------------------------------------------------------------
    # 重写 run：分析逻辑由 Python 内部完成，无需启动外部进程
    # ------------------------------------------------------------------
    def run(self) -> None:
        logger.info(f"[{self.stage_name}] 开始单元扫描与分类...")
        netlist = self.config.netlist_source
        if not netlist.exists():
            logger.warning(f"[{self.stage_name}] 网表文件不存在，跳过分析: {netlist}")
            return

        self.cells = self._parse_netlist(netlist)
        self._write_target_list()
        self._write_analysis_report()
        logger.info(
            f"[{self.stage_name}] 分析完成，共发现 {len(self.cells)} 个单元。"
        )

    # ------------------------------------------------------------------
    def _parse_netlist(self, netlist: Path) -> list[CellInfo]:
        """从 CDL 网表中提取所有 .SUBCKT 定义并分类。"""
        cells: list[CellInfo] = []
        with open(netlist, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = _SUBCKT_RE.match(line)
                if m:
                    name = m.group(1)
                    cells.append(CellInfo(name=name, cell_type=self._classify(name)))
        return cells

    def _classify(self, cell_name: str) -> str:
        """按名称关键字推断单元类型，未匹配则归为 combinational。"""
        upper = cell_name.upper()
        for ctype, keywords in _CELL_TYPE_KEYWORDS.items():
            if any(kw in upper for kw in keywords):
                return ctype
        return "combinational"

    def _write_target_list(self) -> None:
        """将目标单元列表写入 report/target_list.txt。"""
        target_file = self.report_dir / "target_list.txt"
        lines = [f"{c.name}\t{c.cell_type}" for c in self.cells]
        target_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"[{self.stage_name}] 目标列表: {target_file}")

    def _write_analysis_report(self) -> None:
        """生成分类汇总报告 report/analysis_report.txt。"""
        from collections import Counter
        counts = Counter(c.cell_type for c in self.cells)
        report_file = self.report_dir / "analysis_report.txt"
        lines = [
            f"Project : {self.config.project_name}",
            f"TechNode: {self.config.tech_node}",
            f"Total   : {len(self.cells)}",
            "",
            "--- Cell Type Distribution ---",
        ]
        for ctype, cnt in sorted(counts.items()):
            lines.append(f"  {ctype:<20s}: {cnt}")
        report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"[{self.stage_name}] 分析报告: {report_file}")
