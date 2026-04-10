"""
lib/core/shell_runner.py
封装 subprocess 调用逻辑，提供统一的 C-Shell / bash 进程调度接口。

职责：
  - 同步执行：等待脚本执行完毕，实时捕获并输出 stdout/stderr
  - 异步执行：提交后台进程，返回 Popen 对象供调用者管理
  - 日志落盘：将 stdout 和 stderr 写入指定 log 目录
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import IO

from lib.utils.logger import get_logger

logger = get_logger(__name__)


class ShellRunner:
    """
    通用 Shell 脚本执行器。

    Args:
        shell: 解释器路径或名称，默认 "csh"（EDA 环境标准）
        log_dir: 日志落盘目录；若为 None 则不写文件
    """

    def __init__(self, shell: str = "csh", log_dir: Path | None = None):
        self.shell = shell
        self.log_dir = Path(log_dir) if log_dir else None
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 同步执行
    # ------------------------------------------------------------------
    def run(
        self,
        script: Path,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
        tag: str = "",
    ) -> int:
        """
        同步执行脚本，阻塞直到进程退出。

        Args:
            script:    待执行的 .csh 脚本路径
            cwd:       工作目录，默认为脚本所在目录
            extra_env: 追加的环境变量（与父进程 env 合并）
            tag:       日志标识前缀，用于日志落盘文件名

        Returns:
            进程退出码（0 = 成功）

        Raises:
            FileNotFoundError: 脚本文件不存在
            subprocess.CalledProcessError: 进程以非 0 退出
        """
        script = Path(script)
        if not script.exists():
            raise FileNotFoundError(f"脚本文件不存在: {script}")

        run_cwd = Path(cwd) if cwd else script.parent
        env = self._build_env(extra_env)

        log_file = self._open_log(tag or script.stem)

        cmd = [self.shell, "-f", str(script)]
        logger.info(f"[ShellRunner] 执行: {' '.join(cmd)}  (cwd={run_cwd})")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(run_cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self._stream_output(proc.stdout, log_file)
            proc.wait()

            if proc.returncode != 0:
                logger.error(
                    f"[ShellRunner] 脚本 {script.name} 退出码={proc.returncode}"
                )
                raise subprocess.CalledProcessError(proc.returncode, cmd)

            logger.info(f"[ShellRunner] 脚本 {script.name} 执行成功。")
            return proc.returncode

        finally:
            if log_file:
                log_file.close()

    # ------------------------------------------------------------------
    # 异步执行
    # ------------------------------------------------------------------
    def submit(
        self,
        script: Path,
        cwd: Path | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.Popen:
        """
        异步提交脚本，立即返回 Popen 对象（适用于并行多角点仿真场景）。

        调用者负责通过 popen.wait() 或 popen.communicate() 回收进程。
        """
        script = Path(script)
        if not script.exists():
            raise FileNotFoundError(f"脚本文件不存在: {script}")

        run_cwd = Path(cwd) if cwd else script.parent
        env = self._build_env(extra_env)
        cmd = [self.shell, "-f", str(script)]

        logger.info(f"[ShellRunner] 异步提交: {' '.join(cmd)}  (cwd={run_cwd})")
        return subprocess.Popen(cmd, cwd=str(run_cwd), env=env)

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------
    def _build_env(self, extra: dict[str, str] | None) -> dict[str, str] | None:
        if not extra:
            return None
        import os
        merged = dict(os.environ)
        merged.update(extra)
        return merged

    def _open_log(self, stem: str) -> IO[str] | None:
        if not self.log_dir:
            return None
        log_path = self.log_dir / f"{stem}.log"
        return open(log_path, "w", encoding="utf-8")

    def _stream_output(self, stream: IO[str] | None, log_file: IO[str] | None) -> None:
        """逐行读取进程输出，同步打印并写入日志文件。"""
        if stream is None:
            return
        for line in stream:
            line = line.rstrip("\n")
            logger.debug(f"  {line}")
            if log_file:
                log_file.write(line + "\n")
                log_file.flush()
