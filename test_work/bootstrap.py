"""
test_work/bootstrap.py
在本机（Windows/Linux）直接调用框架 Python API，
为所有阶段生成完整的目录树和渲染好的脚本文件。

运行方式:
    python test_work/bootstrap.py
"""
import sys
import traceback
from pathlib import Path

# 将项目根目录加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.utils.logger import setup_rich_logging, get_logger
from lib.core.config_parser import SparkConfig
from lib.modules.init_env   import InitEnvComponent
from lib.modules.analysis   import AnalysisComponent
from lib.modules.gen_gds    import GenGdsComponent
from lib.modules.gen_spice  import GenSpiceComponent
from lib.modules.gen_lib    import GenLibComponent
from lib.modules.gen_lef    import GenLefComponent
from lib.modules.gen_dft    import GenDftComponent
from lib.modules.release    import ReleaseComponent

setup_rich_logging()
logger = get_logger("bootstrap")

CFG_PATH = Path(__file__).resolve().parent / "proj.yaml"

STAGES = [
    ("init_env",  InitEnvComponent),
    ("analysis",  AnalysisComponent),
    ("gen_gds",   GenGdsComponent),
    ("gen_spice", GenSpiceComponent),
    ("gen_lib",   GenLibComponent),
    ("gen_lef",   GenLefComponent),
    ("gen_dft",   GenDftComponent),
    ("release",   ReleaseComponent),
]


def run_bootstrap():
    config = SparkConfig(CFG_PATH)
    logger.info(f"Project : {config.project_name}  Tech: {config.tech_node}")
    logger.info(f"Work dir: {config.work_dir}")

    results: list[tuple[str, str]] = []

    for stage_name, cls in STAGES:
        logger.info(f"\n{'='*60}")
        logger.info(f"  [{stage_name}] create_env ...")
        comp = cls(config)

        # ---- create_env：目录创建 + 脚本渲染 ---------------------------------
        try:
            # 对 init_env 的 _extra_setup 做容错（Windows 无 symlink 权限）
            comp._create_directories()
            comp._generate_scripts()
            try:
                comp._extra_setup()
            except (OSError, NotImplementedError) as exc:
                logger.warning(f"  [SKIP] _extra_setup: {exc}")
            logger.info(f"  [{stage_name}] create_env OK")
            results.append((stage_name, "create_env: OK"))
        except Exception as exc:
            logger.error(f"  [{stage_name}] create_env FAILED: {exc}")
            traceback.print_exc()
            results.append((stage_name, f"create_env: FAILED ({exc})"))
            continue

        # ---- analysis 阶段：run() 是纯 Python（无需 csh），直接执行 ----------
        if stage_name == "analysis":
            try:
                comp.run()
                logger.info(f"  [{stage_name}] run() OK")
                results.append((stage_name, "run: OK"))
            except Exception as exc:
                logger.warning(f"  [{stage_name}] run() skipped: {exc}")
                results.append((stage_name, f"run: SKIP ({exc})"))

    # ---- 汇总 ----------------------------------------------------------------
    logger.info(f"\n{'='*60}")
    logger.info("  Bootstrap Summary")
    logger.info(f"{'='*60}")
    for stage, status in results:
        mark = "✓" if "OK" in status else ("~" if "SKIP" in status else "✗")
        logger.info(f"  {mark}  {stage:<15s}  {status}")
    logger.info(f"{'='*60}\n")
    logger.info(f"Work directory: {config.work_dir}")


if __name__ == "__main__":
    run_bootstrap()
