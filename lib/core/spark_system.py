"""
lib/core/spark_system.py
全框架级系统配置（与项目 YAML 分离），默认从仓库根目录 spark_system.yaml 读取。

路径解析顺序：
  1. 环境变量 SPARK_SYSTEM_CONFIG（绝对路径，或相对于 SPARK 安装根目录的相对路径）
  2. <spark_root>/spark_system.yaml（存在则加载）

文件不存在时返回空 dict，各子系统使用各自默认值。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ENV_SYSTEM_CONFIG = "SPARK_SYSTEM_CONFIG"
DEFAULT_FILENAME = "spark_system.yaml"


def resolve_spark_system_path(spark_root: Path) -> Path | None:
    """返回应加载的系统配置文件路径；无可用文件时返回 None。"""
    env = os.environ.get(ENV_SYSTEM_CONFIG, "").strip()
    if env:
        p = Path(env)
        if not p.is_absolute():
            p = (spark_root / p).resolve()
        return p if p.is_file() else None
    candidate = (spark_root / DEFAULT_FILENAME).resolve()
    return candidate if candidate.is_file() else None


def load_spark_system_dict(spark_root: Path) -> dict[str, Any]:
    """加载系统配置 YAML，失败或缺失时返回空 dict。"""
    path = resolve_spark_system_path(spark_root)
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except OSError:
        return {}
    return raw if isinstance(raw, dict) else {}
