"""
tests/test_config_parser.py
SparkConfig 配置解析器单元测试。
"""
import sys
from pathlib import Path
import pytest

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.core.config_parser import SparkConfig, ConfigKeyError

# ---------- Fixtures ----------------------------------------------------------

VALID_YAML = """
project:
  name: test_lib
  tech_node: "7nm"
  pvt:
    - ff_0p63v_m40c
    - tt_0p7v_25c
    - ss_0p77v_125c

paths:
  work_dir:   /tmp/spark_test_work
  gds_source: /tmp/fake.gds
  netlist:    /tmp/fake.cdl
  lef_source: /tmp/fake.lef

tools:
  calibre:  /eda/calibre/bin/calibre
  liberate: /eda/liberate/bin/liberate
"""

MISSING_REQUIRED_YAML = """
project:
  name: incomplete_proj
"""


@pytest.fixture
def valid_config(tmp_path: Path) -> SparkConfig:
    cfg_file = tmp_path / "test_proj.yaml"
    cfg_file.write_text(VALID_YAML, encoding="utf-8")
    return SparkConfig(cfg_file)


@pytest.fixture
def missing_config(tmp_path: Path) -> SparkConfig:
    cfg_file = tmp_path / "incomplete.yaml"
    cfg_file.write_text(MISSING_REQUIRED_YAML, encoding="utf-8")
    return SparkConfig(cfg_file)


# ---------- Tests -------------------------------------------------------------

class TestSparkConfigLoad:
    def test_load_valid_file(self, valid_config: SparkConfig):
        assert valid_config.project_name == "test_lib"

    def test_file_not_found_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            SparkConfig(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_type_raises(self, tmp_path: Path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="顶层必须为 YAML Mapping"):
            SparkConfig(bad_file)


class TestSparkConfigProperties:
    def test_project_name(self, valid_config: SparkConfig):
        assert valid_config.project_name == "test_lib"

    def test_tech_node(self, valid_config: SparkConfig):
        assert valid_config.tech_node == "7nm"

    def test_pvt_corners_is_list(self, valid_config: SparkConfig):
        corners = valid_config.pvt_corners
        assert isinstance(corners, list)
        assert len(corners) == 3
        assert "tt_0p7v_25c" in corners

    def test_work_dir_is_path(self, valid_config: SparkConfig):
        assert isinstance(valid_config.work_dir, Path)
        assert valid_config.work_dir == Path("/tmp/spark_test_work")

    def test_gds_source_is_path(self, valid_config: SparkConfig):
        assert isinstance(valid_config.gds_source, Path)

    def test_tool_path_returns_configured(self, valid_config: SparkConfig):
        assert valid_config.tool_path("calibre") == "/eda/calibre/bin/calibre"

    def test_tool_path_fallback(self, valid_config: SparkConfig):
        assert valid_config.tool_path("unknown_tool") == "unknown_tool"

    def test_case_name_defaults_to_project_name(self, valid_config: SparkConfig):
        assert valid_config.case_name == "test_lib"
        assert valid_config.case_version == "v1.0"


class TestSparkConfigGet:
    def test_get_existing_key(self, valid_config: SparkConfig):
        assert valid_config.get("project", "name") == "test_lib"

    def test_get_missing_key_returns_default(self, valid_config: SparkConfig):
        assert valid_config.get("project", "nonexistent", default="fallback") == "fallback"

    def test_require_raises_on_missing(self, missing_config: SparkConfig):
        with pytest.raises(ConfigKeyError):
            missing_config.require("paths", "work_dir")

    def test_require_returns_value(self, valid_config: SparkConfig):
        assert valid_config.require("project", "name") == "test_lib"
