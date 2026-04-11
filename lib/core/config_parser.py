"""
lib/core/config_parser.py
解析项目 YAML 配置文件，提供强类型访问接口。
"""
from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Any

# 为 1/true/yes 时，-c 指向的文件按 Fernet 密文读取（由 lib.utils.config_crypto 解密，无对外 CLI）
_SPARK_ENCRYPTED_CONFIG_ENV = "SPARK_ENCRYPTED_CONFIG"


class ConfigKeyError(KeyError):
    """配置字段缺失时抛出，提供精准的字段路径提示。"""
    pass


class SparkConfig:
    """
    项目配置中心，所有模块通过本类获取参数，不直接读取文件。

    若环境变量 ``SPARK_ENCRYPTED_CONFIG`` 为真且 ``SPARK_FERNET_KEY`` 已设置，
    则 ``cfg_path`` 指向的文件按 Fernet 密文读取并在内存中解析（无对外加解密 CLI）。

    配置 YAML 示例结构::

        project:
          name: my_stdcell_lib
          tech_node: "28nm"
          case_name: my_case
          case_version: v1.0
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
    @staticmethod
    def _encrypted_config_env_enabled() -> bool:
        v = os.environ.get(_SPARK_ENCRYPTED_CONFIG_ENV, "").strip().lower()
        return v in ("1", "true", "yes", "on")

    def _load_yaml(self) -> dict[str, Any]:
        if not self.cfg_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.cfg_file}")

        if self._encrypted_config_env_enabled():
            from lib.utils.config_crypto import ConfigCryptoError, decrypt_file_to_text
            try:
                text = decrypt_file_to_text(self.cfg_file)
            except ConfigCryptoError as exc:
                raise ValueError(str(exc)) from exc
            result = yaml.safe_load(text)
        else:
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
    def case_name(self) -> str:
        """与 incoming/ 及 work/ 下 case 沙箱目录名一致；未配置时回退为 project.name。"""
        return self.get("project", "case_name", default=self.project_name)

    @property
    def case_version(self) -> str:
        """case 版本子目录名；未配置时默认为 v1.0。"""
        return self.get("project", "case_version", default="v1.0")

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
