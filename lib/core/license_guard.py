"""
lib/core/license_guard.py
CLI 执行前的 License / 账户授权检查（可选，由 spark_system.yaml 控制）。

- Linux 等环境优先通过 ``whoami`` 获取当前账号名；Windows 回退 ``USERNAME`` / ``USER``。
- 默认名单来自 ``license_check.allowed_users`` 与可选 ``allowed_users_file``。
- 二次开发：实现 ``LicenseAllowlistProvider`` 并调用 ``set_license_allowlist_provider()`` 覆盖默认逻辑。
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from lib.core.spark_system import load_spark_system_dict
from lib.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 扩展点：自定义名单（优先级高于 YAML 静态名单）
# ---------------------------------------------------------------------------
_custom_provider: "LicenseAllowlistProvider | None" = None


class LicenseAllowlistProvider(ABC):
    """授权名单接口：子类实现后通过 ``set_license_allowlist_provider`` 注册。"""

    @abstractmethod
    def is_allowed(self, username: str) -> bool:
        """返回当前用户是否允许使用 Spark CLI。"""


def set_license_allowlist_provider(provider: LicenseAllowlistProvider | None) -> None:
    """
    注册自定义授权逻辑；传入 None 则恢复为仅使用系统配置中的静态名单。

    典型用法（二次开发入口）::

        from lib.core.license_guard import LicenseAllowlistProvider, set_license_allowlist_provider

        class LdapAllowlist(LicenseAllowlistProvider):
            def is_allowed(self, username: str) -> bool:
                ...

        set_license_allowlist_provider(LdapAllowlist())
    """
    global _custom_provider
    _custom_provider = provider


def get_os_username() -> str:
    """
    解析当前 OS 用户名。Linux/Unix 优先 ``whoami``；失败时用 USER/LOGNAME；Windows 用 USERNAME。
    """
    try:
        proc = subprocess.run(
            ["whoami"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            line = proc.stdout.strip().splitlines()[-1].strip()
            # 可能为 domain\\user，保留整串作为账号标识，与名单一致即可
            if line:
                return line
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if platform.system() == "Windows":
        u = os.environ.get("USERNAME", "").strip()
        if u:
            return u
    for key in ("USER", "LOGNAME"):
        u = os.environ.get(key, "").strip()
        if u:
            return u
    return ""


def _collect_static_allowlist(section: dict[str, Any], spark_root: Path) -> set[str]:
    names: set[str] = set()
    raw = section.get("allowed_users")
    if isinstance(raw, list):
        for u in raw:
            if isinstance(u, str) and u.strip():
                names.add(u.strip())

    fspec = section.get("allowed_users_file")
    if isinstance(fspec, str) and fspec.strip():
        fp = Path(fspec.strip())
        if not fp.is_absolute():
            fp = spark_root / fp
        if fp.is_file():
            try:
                text = fp.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                pass
            else:
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        names.add(line)
    return names


def run_pre_command_license_check(spark_root: Path) -> None:
    """
    在加载项目配置、执行业务命令之前调用。

    - ``license_check.enabled`` 为假或未配置：直接通过。
    - 为真：必须能解析用户名，且通过自定义 Provider 或静态名单校验。
    """
    data = load_spark_system_dict(spark_root)
    section = data.get("license_check")
    if not isinstance(section, dict):
        return
    if not bool(section.get("enabled", False)):
        return

    user = get_os_username()
    if not user:
        logger.error(
            "[license] 已启用 License 检查，但无法获取当前用户名（whoami / 环境变量）。"
        )
        sys.exit(2)

    if _custom_provider is not None:
        ok = _custom_provider.is_allowed(user)
    else:
        allowed = _collect_static_allowlist(section, spark_root)
        ok = user in allowed

    if not ok:
        logger.error(
            f"[license] 用户 {user!r} 未授权使用 Spark（请配置 spark_system.yaml 或自定义 Provider）。"
        )
        sys.exit(2)

    logger.debug(f"[license] 用户 {user!r} 已通过授权检查。")


__all__ = [
    "LicenseAllowlistProvider",
    "set_license_allowlist_provider",
    "get_os_username",
    "run_pre_command_license_check",
]
