"""
lib/core/config_parser.py
解析项目 YAML 配置文件，提供强类型访问接口。
"""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any


class ConfigKeyError(KeyError):
    """配置字段缺失时抛出，提供精准的字段路径提示。"""
    pass


class SparkConfig:
    """
    项目配置中心，所有模块通过本类获取参数，不直接读取文件。

    配置 YAML 示例结构::

        project:
          name: my_stdcell_lib
          tech_node: "28nm"
          pvt: ["ff_0p99v_m40c", "tt_1p1v_25c", "ss_1p21v_125c"]

        paths:
          work_dir:   /data/proj/work
          gds_source: /data/pdk/gds/stdcell.gds
          netlist:    /data/pdk/netlist/stdcell.cdl
          lef_source: /data/pdk/lef/tech.lef

        tools:
          calibre:    /eda/calibre/bin/calibre
          liberate:   /eda/liberate/bin/liberate
          innovus:    /eda/innovus/bin/innovus
    """

    def __init__(self, cfg_path: str | Path):
        self.cfg_file = Path(cfg_path).resolve()
        self.data: dict[str, Any] = self._load_yaml()

    # ------------------------------------------------------------------
    # 内部加载
    # ------------------------------------------------------------------
    def _load_yaml(self) -> dict[str, Any]:
        if not self.cfg_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.cfg_file}")
        with open(self.cfg_file, "r", encoding="utf-8") as fh:
            result = yaml.safe_load(fh)
        if not isinstance(result, dict):
            raise ValueError(f"配置文件格式错误，顶层必须为 YAML Mapping: {self.cfg_file}")
        return result

    # ------------------------------------------------------------------
    # 通用深层 get 工具
    # ------------------------------------------------------------------
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        按路径获取配置值，支持任意深度。
        示例: config.get("paths", "work_dir")
        """
        node = self.data
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node

    def require(self, *keys: str) -> Any:
        """同 get，但若字段不存在则抛出 ConfigKeyError。"""
        value = self.get(*keys)
        if value is None:
            path = " -> ".join(keys)
            raise ConfigKeyError(f"必填配置字段缺失: [{path}]")
        return value

    # ------------------------------------------------------------------
    # 常用快捷属性
    # ------------------------------------------------------------------
    @property
    def project_name(self) -> str:
        return self.get("project", "name", default="default_proj")

    @property
    def tech_node(self) -> str:
        return self.get("project", "tech_node", default="unknown")

    @property
    def pvt_corners(self) -> list[str]:
        corners = self.get("project", "pvt", default=[])
        return corners if isinstance(corners, list) else [corners]

    @property
    def work_dir(self) -> Path:
        wd = self.require("paths", "work_dir")
        return Path(wd)

    @property
    def gds_source(self) -> Path:
        return Path(self.require("paths", "gds_source"))

    @property
    def netlist_source(self) -> Path:
        return Path(self.require("paths", "netlist"))

    @property
    def lef_source(self) -> Path:
        return Path(self.require("paths", "lef_source"))

    def tool_path(self, tool_name: str) -> str:
        """返回指定 EDA 工具的可执行路径（未配置则返回工具名本身作为回退）。"""
        return self.get("tools", tool_name, default=tool_name)

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"SparkConfig(project={self.project_name!r}, "
            f"tech={self.tech_node!r}, "
            f"corners={self.pvt_corners})"
        )
