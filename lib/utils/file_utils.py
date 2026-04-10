"""
lib/utils/file_utils.py
目录管理、软链接、MD5 校验等通用文件操作工具。
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path
from typing import Iterator

from lib.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_dir(path: Path | str) -> Path:
    """确保目录存在，不存在则递归创建。返回 Path 对象。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_symlink(src: Path | str, dst: Path | str, force: bool = True) -> Path:
    """
    创建软链接 dst -> src。

    Args:
        src:   链接指向的真实路径（相对或绝对均可）
        dst:   软链接自身路径
        force: True 则先删除已有的 dst 再创建

    Returns:
        创建的软链接路径
    """
    src, dst = Path(src), Path(dst)
    if not src.exists():
        raise FileNotFoundError(f"软链接源不存在: {src}")
    if dst.exists() or dst.is_symlink():
        if force:
            dst.unlink()
        else:
            logger.warning(f"软链接目标已存在，跳过: {dst}")
            return dst
    dst.symlink_to(src)
    logger.debug(f"软链接已创建: {dst} -> {src}")
    return dst


def md5sum(file_path: Path | str) -> str:
    """计算文件 MD5 校验值，以 hex 字符串返回（大写）。"""
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在，无法计算 MD5: {file_path}")
    hasher = hashlib.md5()
    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest().upper()


def collect_files(
    directory: Path | str,
    pattern: str = "*",
    recursive: bool = True,
) -> list[Path]:
    """
    收集目录下匹配 glob 模式的所有文件（不含目录）。

    Args:
        directory: 搜索根目录
        pattern:   glob 模式，如 "*.lib"、"**/*.gds"
        recursive: True 则使用 rglob，False 则 glob（仅一级）

    Returns:
        排序后的 Path 列表
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"目录不存在: {directory}")
    matcher = directory.rglob if recursive else directory.glob
    return sorted(p for p in matcher(pattern) if p.is_file())


def clean_dir(directory: Path | str, recreate: bool = True) -> Path:
    """
    清空并可选重建目录（用于 release 阶段重置输出）。

    Args:
        directory: 待清空的目录
        recreate:  True 则清空后重建空目录

    Returns:
        处理后的目录 Path 对象
    """
    directory = Path(directory)
    if directory.exists():
        shutil.rmtree(directory)
        logger.debug(f"目录已清空: {directory}")
    if recreate:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_checksums(
    files: list[Path],
    output: Path | str,
) -> Path:
    """
    生成 MD5 校验清单文件（格式与 `md5sum` 命令输出兼容）。

    Args:
        files:  待校验的文件列表
        output: 校验清单输出路径（如 release/output_file/CHECKSUMS.md5）

    Returns:
        校验清单文件路径
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for f in files:
        try:
            checksum = md5sum(f)
            lines.append(f"{checksum}  {f.name}")
        except FileNotFoundError:
            lines.append(f"{'MISSING':32s}  {f.name}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info(f"MD5 校验清单已生成: {output}")
    return output
