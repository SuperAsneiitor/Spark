"""
lib/utils/logger.py
全局日志配置模块。

策略：
  - 标准 logging 模块负责落盘（写文件），保证日志可审计
  - rich.logging.RichHandler 负责终端高亮输出（颜色 + 时间戳）
  - setup_rich_logging() 在程序入口调用一次即可
  - get_logger(name) 在各模块顶部调用获取子 logger
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_RICH_AVAILABLE = False
try:
    from rich.logging import RichHandler  # type: ignore[import-untyped]
    from rich.console import Console      # type: ignore[import-untyped]
    _RICH_AVAILABLE = True
except ImportError:
    pass

_ROOT_LOGGER_NAME = "spark"
_LOG_FORMAT_FILE  = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_FORMAT_PLAIN = "[%(levelname)s] %(name)s: %(message)s"


def setup_rich_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    verbose: bool = False,
) -> None:
    """
    初始化根 logger，应在程序入口（bin/spark）调用一次。

    Args:
        level:    控制台输出最低级别（verbose=True 时自动降为 DEBUG）
        log_file: 若提供，则同时将 INFO+ 日志写入文件
        verbose:  True 则开启 DEBUG 输出
    """
    if verbose:
        level = logging.DEBUG

    root = logging.getLogger(_ROOT_LOGGER_NAME)
    root.setLevel(logging.DEBUG)  # root 始终 DEBUG，由 handler 过滤级别
    root.handlers.clear()

    # ---- 终端 Handler --------------------------------------------------------
    if _RICH_AVAILABLE:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(logging.Formatter(_LOG_FORMAT_PLAIN))

    console_handler.setLevel(level)
    root.addHandler(console_handler)

    # ---- 文件 Handler --------------------------------------------------------
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT_FILE))
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取具名子 logger，自动以 spark 为根前缀。

    Args:
        name: 通常传入 __name__，如 "lib.modules.gen_spice"

    Returns:
        logging.Logger 实例
    """
    if name.startswith(_ROOT_LOGGER_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
