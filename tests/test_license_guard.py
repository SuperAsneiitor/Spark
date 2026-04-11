"""
tests/test_license_guard.py
License 门禁与系统配置加载测试。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.core.license_guard import (  # noqa: E402
    LicenseAllowlistProvider,
    get_os_username,
    run_pre_command_license_check,
    set_license_allowlist_provider,
)
from lib.core.spark_system import load_spark_system_dict, resolve_spark_system_path  # noqa: E402


@pytest.fixture(autouse=True)
def reset_custom_provider():
    set_license_allowlist_provider(None)
    yield
    set_license_allowlist_provider(None)


def test_load_spark_system_default_file_exists():
    data = load_spark_system_dict(ROOT)
    assert "license_check" in data
    assert data["license_check"].get("enabled") is False


def test_resolve_system_config_env(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "x.yaml"
    cfg.write_text("license_check:\n  enabled: false\n")
    monkeypatch.setenv("SPARK_SYSTEM_CONFIG", str(cfg))
    p = resolve_spark_system_path(tmp_path)
    assert p == cfg.resolve()


def test_license_disabled_noop(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SPARK_SYSTEM_CONFIG", raising=False)
    run_pre_command_license_check(tmp_path)


def test_license_enabled_denies_unknown(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "spark_system.yaml"
    cfg.write_text(
        "license_check:\n  enabled: true\n  allowed_users:\n    - alice\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPARK_SYSTEM_CONFIG", str(cfg))
    monkeypatch.setattr(
        "lib.core.license_guard.get_os_username",
        lambda: "bob",
    )
    with pytest.raises(SystemExit) as exc:
        run_pre_command_license_check(tmp_path)
    assert exc.value.code == 2


def test_license_enabled_allows_listed(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "spark_system.yaml"
    cfg.write_text(
        "license_check:\n  enabled: true\n  allowed_users:\n    - alice\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPARK_SYSTEM_CONFIG", str(cfg))
    monkeypatch.setattr(
        "lib.core.license_guard.get_os_username",
        lambda: "alice",
    )
    run_pre_command_license_check(tmp_path)


def test_custom_provider(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "spark_system.yaml"
    cfg.write_text(
        "license_check:\n  enabled: true\n  allowed_users: []\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SPARK_SYSTEM_CONFIG", str(cfg))

    class _P(LicenseAllowlistProvider):
        def is_allowed(self, username: str) -> bool:
            return username == "ghost"

    set_license_allowlist_provider(_P())
    monkeypatch.setattr(
        "lib.core.license_guard.get_os_username",
        lambda: "ghost",
    )
    run_pre_command_license_check(tmp_path)


def test_get_os_username_nonempty():
    u = get_os_username()
    assert isinstance(u, str)
