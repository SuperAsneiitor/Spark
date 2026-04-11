"""
tests/test_runtime_paths.py
runtime_paths：SPARK_HOME / Nuitka 布局 / 开发树 解析测试。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.core.runtime_paths as runtime_paths  # noqa: E402
from lib.core.runtime_paths import ensure_repo_on_syspath, get_spark_home  # noqa: E402


def test_get_spark_home_from_env(monkeypatch):
    monkeypatch.setenv("SPARK_HOME", str(ROOT))
    monkeypatch.setattr(sys, "argv", ["fake/spark"])
    assert get_spark_home() == ROOT.resolve()


def test_get_spark_home_dev_bin_layout(monkeypatch):
    monkeypatch.delenv("SPARK_HOME", raising=False)
    fake_bin = ROOT / "bin" / "spark"
    monkeypatch.setattr(sys, "argv", [str(fake_bin)])
    assert get_spark_home() == ROOT.resolve()


def test_get_spark_home_standalone_layout(tmp_path: Path, monkeypatch):
    """可执行与 share/template 同目录（模拟 Nuitka：无仓库 lib 路径可推断）。"""
    monkeypatch.delenv("SPARK_HOME", raising=False)
    # pytest 从仓库加载 lib，否则会优先走 _spark_home_from_lib_package
    monkeypatch.setattr(runtime_paths, "_spark_home_from_lib_package", lambda: None)
    dist = tmp_path / "spark.dist"
    (dist / "share" / "template").mkdir(parents=True)
    exe = dist / "spark"
    exe.write_text("#", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(exe)])
    assert get_spark_home() == dist.resolve()


def test_ensure_repo_on_syspath_when_disk_lib_exists(monkeypatch):
    monkeypatch.setenv("SPARK_HOME", str(ROOT))
    monkeypatch.setattr(sys, "argv", [str(ROOT / "bin" / "spark")])
    ensure_repo_on_syspath()
    assert str(ROOT.resolve()) in sys.path
