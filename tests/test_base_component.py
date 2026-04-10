"""
tests/test_base_component.py
BaseComponent 基类及子类实例化的单元测试。
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.core.config_parser  import SparkConfig
from lib.modules.gen_spice   import GenSpiceComponent
from lib.modules.analysis    import AnalysisComponent
from lib.modules.release     import ReleaseComponent

# ---------- Fixtures ----------------------------------------------------------

FULL_YAML = """
project:
  name: mock_stdcell
  tech_node: "28nm"
  pvt:
    - ff_0p99v_m40c
    - tt_1p1v_25c

paths:
  work_dir:   {work_dir}
  gds_source: {work_dir}/fake.gds
  netlist:    {work_dir}/fake.cdl
  lef_source: {work_dir}/fake.lef

tools:
  calibre:  calibre
  liberate: liberate

gen_spice:
  continue_on_drc_error: false

gen_lib:
  parallel_corners: false

gen_dft:
  format: mdt

release:
  bundle_tar: false
"""


@pytest.fixture
def config(tmp_path: Path) -> SparkConfig:
    cfg_text = FULL_YAML.format(work_dir=str(tmp_path).replace("\\", "/"))
    cfg_file = tmp_path / "proj.yaml"
    cfg_file.write_text(cfg_text, encoding="utf-8")
    return SparkConfig(cfg_file)


# ---------- Tests: GenSpiceComponent ------------------------------------------

class TestGenSpiceComponent:
    def test_instantiation(self, config: SparkConfig):
        comp = GenSpiceComponent(config)
        assert comp.stage_name == "gen_spice"

    def test_create_env_creates_dirs(self, config: SparkConfig):
        """create_env 应当在工作目录下创建标准子目录树。"""
        with patch("lib.core.template_engine.render_template") as mock_render:
            mock_render.return_value = Path("/fake/path")
            comp = GenSpiceComponent(config)
            comp.create_env()
        assert (comp.stage_dir / "run").exists()
        assert (comp.stage_dir / "scr").exists()
        assert (comp.stage_dir / "log").exists()
        assert (comp.stage_dir / "rpt").exists()
        assert (comp.stage_dir / "release" / "output_file").exists()

    def test_run_calls_pv_then_rc(self, config: SparkConfig):
        """run() 应顺序调用 PV 和 RC 子步骤。"""
        comp = GenSpiceComponent(config)
        call_order = []

        def fake_execute(script_name, cwd=None):
            call_order.append(script_name)

        comp._execute_csh = fake_execute
        comp.run()
        assert call_order == ["run_pv.csh", "run_rc.csh"]

    def test_run_continues_on_drc_error_when_flag_set(self, config: SparkConfig, tmp_path: Path):
        """continue_on_drc_error=True 时，PV 失败不应阻止 RC 执行。"""
        cfg_text = FULL_YAML.format(
            work_dir=str(tmp_path).replace("\\", "/")
        ).replace("continue_on_drc_error: false", "continue_on_drc_error: true")
        cfg_file = tmp_path / "proj2.yaml"
        cfg_file.write_text(cfg_text, encoding="utf-8")
        cfg2 = SparkConfig(cfg_file)

        comp = GenSpiceComponent(cfg2)
        call_order = []

        def fake_execute(script_name, cwd=None):
            call_order.append(script_name)
            if script_name == "run_pv.csh":
                raise RuntimeError("模拟 PV 失败")

        comp._execute_csh = fake_execute
        comp.run()
        assert "run_rc.csh" in call_order


# ---------- Tests: AnalysisComponent ------------------------------------------

class TestAnalysisComponent:
    CDL_CONTENT = """.SUBCKT INVX1 A ZN VDD VSS
M1 ZN A VDD VDD PMOS w=0.5u l=0.1u
.ENDS

.SUBCKT DFFX1 D CLK Q QN VDD VSS
M1 Q CLK VDD VDD PMOS w=1u l=0.1u
.ENDS

.SUBCKT FILL4 VDD VSS
.ENDS
"""

    def test_cell_classification(self, config: SparkConfig, tmp_path: Path):
        """解析 CDL 应正确分类 Combinational / Sequential / Filler。"""
        netlist = tmp_path / "fake.cdl"
        netlist.write_text(self.CDL_CONTENT, encoding="utf-8")

        comp = AnalysisComponent(config)
        cells = comp._parse_netlist(netlist)

        types = {c.name: c.cell_type for c in cells}
        assert types.get("INVX1") == "combinational"
        assert types.get("DFFX1") == "sequential"
        assert types.get("FILL4") == "filler"

    def test_run_creates_reports(self, config: SparkConfig, tmp_path: Path):
        """run() 应在 rpt/ 下生成 target_list.txt 和 analysis_report.txt。"""
        netlist = tmp_path / "fake.cdl"
        netlist.write_text(self.CDL_CONTENT, encoding="utf-8")

        comp = AnalysisComponent(config)
        comp._create_directories()
        comp.run()

        assert (comp.rpt_dir / "target_list.txt").exists()
        assert (comp.rpt_dir / "analysis_report.txt").exists()


# ---------- Tests: ReleaseComponent -------------------------------------------

class TestReleaseComponent:
    def test_collect_artifacts_empty_when_no_upstream(self, config: SparkConfig):
        """上游目录不存在时 _collect_artifacts 应返回空列表。"""
        comp = ReleaseComponent(config)
        result = comp._collect_artifacts()
        assert result == []

    def test_write_release_notes(self, config: SparkConfig, tmp_path: Path):
        """Release Notes 应包含项目名和技术节点。"""
        comp = ReleaseComponent(config)
        comp._create_directories()
        notes = comp._write_release_notes(
            files=[tmp_path / "sample.lib"],
            out_dir=comp.stage_dir / "release" / "output_file",
        )
        content = notes.read_text(encoding="utf-8")
        assert "mock_stdcell" in content
        assert "28nm" in content
