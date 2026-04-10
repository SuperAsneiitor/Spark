"""
lib/modules/gen_lib/gen_lib.py
阶段 5 — gen_lib：时序与功耗库特征化生成。

职责：
  - 为每个 PVT Corner 渲染独立的 Liberate / SiliconSmart 特征化脚本
  - 支持并行多角点提交（通过 ShellRunner.submit()）
  - 产出 .lib 文件，存放于 release/output_file/<corner>/
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.core.shell_runner    import ShellRunner
from lib.modules.base_component import BaseComponent
from lib.utils.file_utils     import ensure_dir
from lib.utils.logger         import get_logger

logger = get_logger(__name__)


class GenLibComponent(BaseComponent):
    """时序与功耗库特征化阶段（多 Corner 并行）。"""

    def __init__(self, config: SparkConfig):
        super().__init__("gen_lib", config)
        self.parallel: bool = config.get("gen_lib", "parallel_corners", default=True)

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """为每个 PVT Corner 生成独立的特征化驱动脚本。"""
        for corner in self.config.pvt_corners:
            corner_out_dir = self.stage_dir / "release" / "output_file" / corner
            ensure_dir(corner_out_dir)

            ctx = {
                "stage"       : self.stage_name,
                "project_name": self.config.project_name,
                "tech_node"   : self.config.tech_node,
                "corner"      : corner,
                "tool_cmd"    : self.config.tool_path("liberate"),
                "netlist_source": str(self.config.netlist_source),
                "output_lib"  : str(corner_out_dir / f"{self.config.project_name}_{corner}.lib"),
                "run_dir"     : str(self.run_dir),
                "log_dir"     : str(self.log_dir),
                "description" : f"Liberate 特征化 [{corner}]",
            }
            render_template(
                "csh_wrapper.j2",
                self.run_dir / f"run_lib_{corner}.csh",
                **ctx,
            )
            logger.debug(f"[{self.stage_name}] 脚本生成: run/run_lib_{corner}.csh")

    # ------------------------------------------------------------------
    def run(self) -> None:
        """按 parallel 标志决定串行或并行执行多 Corner 特征化。"""
        if self.parallel:
            self._run_parallel()
        else:
            self._run_sequential()

    def _run_sequential(self) -> None:
        for corner in self.config.pvt_corners:
            logger.info(f"[{self.stage_name}] 串行执行 corner: {corner}")
            self._execute_csh(f"run_lib_{corner}.csh")

    def _run_parallel(self) -> None:
        """并行提交所有 Corner，集中等待并检查退出码。"""
        logger.info(f"[{self.stage_name}] 并行提交 {len(self.config.pvt_corners)} 个 Corner...")
        runner = ShellRunner(shell="csh", log_dir=self.log_dir)
        procs: list[tuple[str, subprocess.Popen]] = []

        for corner in self.config.pvt_corners:
            script = self.run_dir / f"run_lib_{corner}.csh"
            p = runner.submit(script=script, cwd=self.run_dir)
            procs.append((corner, p))

        failed: list[str] = []
        for corner, p in procs:
            p.wait()
            if p.returncode != 0:
                logger.error(f"[{self.stage_name}] Corner {corner} 失败 (rc={p.returncode})")
                failed.append(corner)
            else:
                logger.info(f"[{self.stage_name}] Corner {corner} 完成。")

        if failed:
            raise RuntimeError(
                f"[{self.stage_name}] 以下 Corner 特征化失败: {failed}"
            )
        logger.info(f"[{self.stage_name}] 所有 Corner 并行执行完成。")
