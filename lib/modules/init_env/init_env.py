"""
lib/modules/init_env/init_env.py
init_env — 项目级工作区初始化（非子模块，作用于整个项目根目录）。

与其他阶段的本质区别：
  - 其他阶段在 <project_root>/work/<stage_name>/ 下建立独立沙箱
  - init_env 直接在 <project_root>（项目根）建立完整的项目目录树
  - run/ 存放贯穿全流程的主调度脚本（run_flow.csh）
  - cfg/ 存放 demo 配置文件供参考

生成的目录结构：
    <project_root>/                      # config.work_dir
    ├── work/                            # 子模块阶段工作目录
    │   ├── analysis/
    │   ├── gen_gds/
    │   └── ...
    ├── incoming/
    │   └── <case_name>/
    │       └── <case_version>/
    │           ├── timing_info/
    │           │   └── <corner>/
    │           │       ├── session/
    │           │       ├── timing_path/
    │           │       └── spef/
    │           └── netlist/
    ├── release/                         # 最终发布产出
    ├── cfg/
    │   └── proj_demo.yaml               # demo 配置文件
    └── run/
        ├── run_flow.csh                 # 全流程主调度脚本
        └── log/                         # 主调度日志
"""
from __future__ import annotations

import datetime
import shutil
from pathlib import Path

import yaml

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.file_utils     import ensure_dir
from lib.utils.logger         import get_logger

logger = get_logger(__name__)

_SUB_STAGES = [
    "analysis",
    "gen_gds",
    "gen_spice",
    "gen_lib",
    "gen_lef",
    "gen_dft",
    "release",
]


class InitEnvComponent(BaseComponent):
    """
    项目根目录初始化组件。

    路径约定（覆盖基类）：
      project_root → config.work_dir       (项目根，init_env 在此建立所有顶层目录)
      stage_dir    → project_root          (init_env 自身即项目根，无独立子目录)
      run_dir      → project_root/run
      cfg_dir      → project_root/cfg      (新增)
      root_dir     → project_root/work     (继承自基类，子模块落点，init_env 不直接使用)
    """

    def __init__(self, config: SparkConfig):
        super().__init__("init_env", config)

        self.stage_dir = self.project_root
        self.run_dir   = self.project_root / "run"
        self.log_dir   = self.project_root / "run" / "log"
        self.cfg_dir   = self.project_root / "cfg"

        from lib.core.shell_runner import ShellRunner
        self._runner = ShellRunner(shell="csh", log_dir=None)

        _spurious = self.root_dir / "init_env"
        if _spurious.exists():
            shutil.rmtree(_spurious)

        self.case_name    : str = config.get("project", "case_name",    default=config.project_name)
        self.case_version : str = config.get("project", "case_version", default="v1.0")

    # ------------------------------------------------------------------
    def _create_directories(self) -> None:
        """建立完整的项目根目录结构。"""
        for top in ("work", "release", "cfg"):
            ensure_dir(self.project_root / top)

        ensure_dir(self.run_dir / "log")

        incoming_base = self.project_root / "incoming" / self.case_name / self.case_version
        ensure_dir(incoming_base / "netlist")

        for corner in self.config.pvt_corners:
            corner_base = incoming_base / "timing_info" / corner
            for sub in ("session", "timing_path", "spef"):
                ensure_dir(corner_base / sub)

        logger.debug(f"[{self.stage_name}] 项目根目录结构创建完成: {self.project_root}")

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """在 run/ 下生成全流程主调度脚本 run_flow.csh。"""
        cfg_path = self.cfg_dir / "proj_demo.yaml"

        ctx = {
            "project_name"          : self.config.project_name,
            "tech_node"             : self.config.tech_node,
            "case_name"             : self.case_name,
            "case_version"          : self.case_version,
            "gen_time"              : datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cfg_path"              : str(cfg_path),
            "root_dir"              : str(self.project_root),
            "run_dir"               : str(self.run_dir),
            "stages"                : _SUB_STAGES,
            "from_stage_placeholder": False,
        }
        render_template("master_run.j2", self.run_dir / "run_flow.csh", **ctx)
        logger.debug(f"[{self.stage_name}] 主调度脚本生成: run/run_flow.csh")

    # ------------------------------------------------------------------
    def _extra_setup(self) -> None:
        """在 cfg/ 下生成 demo 配置文件 proj_demo.yaml。"""
        self._write_demo_config()

    # ------------------------------------------------------------------
    def run(self) -> None:
        """init_env 无外部工具调用，打印项目结构摘要即可。"""
        logger.info(f"[{self.stage_name}] 项目根目录初始化完成。")
        logger.info(f"  项目根目录 : {self.project_root}")
        logger.info(f"  子模块目录 : {self.root_dir}")
        logger.info(f"  主调度脚本 : {self.run_dir / 'run_flow.csh'}")
        logger.info(f"  Demo 配置  : {self.cfg_dir / 'proj_demo.yaml'}")
        logger.info(f"  Incoming   : {self.project_root / 'incoming' / self.case_name / self.case_version}")

    # ------------------------------------------------------------------
    def _write_demo_config(self) -> None:
        """将当前生效的配置以注释丰富的 YAML 格式写入 cfg/proj_demo.yaml。"""
        demo_path = self.cfg_dir / "proj_demo.yaml"

        demo: dict = {
            "project": {
                "name"        : self.config.project_name,
                "tech_node"   : self.config.tech_node,
                "case_name"   : self.case_name,
                "case_version": self.case_version,
                "pvt"         : self.config.pvt_corners,
            },
            "paths": {
                "work_dir"   : str(self.project_root),
                "gds_source" : str(self.config.gds_source),
                "netlist"    : str(self.config.netlist_source),
                "lef_source" : str(self.config.lef_source),
            },
            "tools": {
                "calibre" : self.config.tool_path("calibre"),
                "liberate": self.config.tool_path("liberate"),
                "innovus" : self.config.tool_path("innovus"),
                "abstract": self.config.tool_path("abstract"),
                "tetramax": self.config.tool_path("tetramax"),
            },
            "gen_spice": {"continue_on_drc_error": False},
            "gen_lib"  : {"parallel_corners"     : True},
            "gen_dft"  : {"format"               : "mdt"},
            "release"  : {"bundle_tar"            : True},
        }

        header = (
            "# =============================================================================\n"
            f"# proj_demo.yaml  —  Demo configuration for {self.config.project_name}\n"
            f"# Generated     : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "# Usage         : cp cfg/proj_demo.yaml cfg/proj.yaml  (then edit paths/tools)\n"
            "# =============================================================================\n\n"
        )

        body = yaml.dump(demo, default_flow_style=False, allow_unicode=True, sort_keys=False)
        demo_path.write_text(header + body, encoding="utf-8")
        logger.debug(f"[{self.stage_name}] Demo 配置已写入: {demo_path}")
