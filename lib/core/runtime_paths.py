"""
lib/core/runtime_paths.py
解析 Spark 安装根目录（SPARK_HOME），兼容：

  - 开发树：bin/spark 上层为仓库根，存在 lib/ 与 share/template/
  - source spark.csh：SPARK_HOME 显式设置
  - Nuitka --standalone：可执行文件与 share/template/ 同目录，无磁盘上的 lib/ 包目录
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _spark_home_from_lib_package() -> Path | None:
    """
    根据已导入的 ``lib`` 包推断安装根（lib 的上一级目录含 share/template）。
    适用于 pytest、python -c 等入口（此时 sys.argv[0] 不是 bin/spark）。
    """
    try:
        import lib as _lib_pkg  # type: ignore[import-not-found]
        init = getattr(_lib_pkg, "__file__", None)
        if not init:
            return None
        root = Path(init).resolve().parent.parent
        if (root / "share" / "template").is_dir():
            return root
    except Exception:
        pass
    return None


def get_spark_home() -> Path:
    """
    返回安装根目录（含 share/template 的目录）。

    优先级：
      1. 环境变量 SPARK_HOME
      2. 由 ``lib`` 包路径推断（开发树 / 多数测试场景）
      3. 可执行文件同目录下存在 share/template（Nuitka standalone）
      4. 可执行文件上一级存在 share/template（bin/spark 开发布局）
      5. 回退为可执行文件上一级
    """
    env = os.environ.get("SPARK_HOME", "").strip()
    if env:
        return Path(env).resolve()

    from_pkg = _spark_home_from_lib_package()
    if from_pkg is not None:
        return from_pkg

    exe_dir = Path(sys.argv[0]).resolve().parent
    if (exe_dir / "share" / "template").is_dir():
        return exe_dir
    parent = exe_dir.parent
    if (parent / "share" / "template").is_dir():
        return parent
    return parent


def ensure_repo_on_syspath() -> None:
    """
    开发/源码运行时把仓库根加入 sys.path，以便 ``import lib``。
    Nuitka 编译后 ``lib`` 已打入二进制，磁盘上无 ``lib/`` 目录，此时不修改 sys.path。
    """
    root = get_spark_home()
    if (root / "lib").is_dir() and (root / "lib" / "__init__.py").exists():
        s = str(root)
        if s not in sys.path:
            sys.path.insert(0, s)
