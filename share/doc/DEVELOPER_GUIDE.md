# Spark 开发者文档（架构与扩展方案）

## 1. 第一性原理：为什么这样设计

流程引擎在长期演进中最怕三件事：

- 阶段耦合：一个阶段改动影响全链路
- 状态不透明：失败后无法定位
- 结果不可验证：跑完但不知是否可信

Spark 的约束是：

- 固定生命周期：`create_env -> run -> check_result -> extract_report`
- 固定目录契约：每个阶段都有 run/scr/check/report/release
- 固定扩展点：只在子类实现 `_generate_scripts()`，必要时重写 `run()`

---

## 2. 代码分层

- `lib/core/`
  - `config_parser.py`：配置解析与强类型访问
  - `template_engine.py`：Jinja2 渲染
  - `shell_runner.py`：外部命令执行与日志
- `lib/modules/`
  - `base_component.py`：流程骨架与通用能力
  - 各阶段子包：`analysis/`, `porting_gds/`, `porting_lef/`, `gen_gds/`, `gen_spice/`, ...
- `lib/utils/`
  - `logger.py`, `file_utils.py`
- `bin/spark`
  - CLI 命令解析与调度

---

## 3. 当前模块组织（下沉一级）

现在每个模块都是子包，例如：

- `lib/modules/analysis/analysis.py`
- `lib/modules/porting_gds/porting_gds.py`
- `lib/modules/porting_lef/porting_lef.py`
- `lib/modules/gen_gds/gen_gds.py`
- `lib/modules/init_env/init_env.py`

每个子包通过 `__init__.py` 对外导出组件类，兼容以下导入：

```python
from lib.modules.analysis import AnalysisComponent
from lib.modules.gen_spice import GenSpiceComponent
```

---

## 4. BaseComponent 关键能力

`lib/modules/base_component.py` 已提供：

- 阶段根目录：`work/<case_name>/<case_version>/<stage>/`（与 `project.case_name` / `project.case_version` 及 `incoming/` 对齐）
- 标准目录创建（含 `run/log`, `check/rpt`, `report`）
- 默认 `run`（执行 `run_<stage>.csh`）
- `check_result()`：
  - 扫描 `run/log/*.log` 的 error/warning
  - 校验 `_expected_outputs()` 声明的目标文件
  - 输出 `check/rpt/<stage>_check.rpt`
- `extract_report()`：
  - 生成 `report/<stage>_summary.rpt`
  - 支持 `_extra_report_patterns()` 扩展抽取规则

---

## 5. 新增一个阶段（推荐流程）

## 5.1 创建子包

在 `lib/modules/` 下创建 `gen_xxx/`：

- `gen_xxx/__init__.py`
- `gen_xxx/gen_xxx.py`

## 5.2 继承基类实现

```python
from lib.core.config_parser import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent

class GenXxxComponent(BaseComponent):
    def __init__(self, config: SparkConfig):
        super().__init__("gen_xxx", config)

    def _generate_scripts(self) -> None:
        render_template(
            "csh_wrapper.j2",
            self.run_dir / "run_gen_xxx.csh",
            stage=self.stage_name,
            project_name=self.config.project_name,
            tech_node=self.config.tech_node,
            description="gen_xxx stage",
        )
```

## 5.3 注册 CLI

更新 `bin/spark`：

- `STAGE_MAP` 增加 `"gen_xxx": GenXxxComponent`
- `ALL_STAGES` 自动包含后，`create_/run_/check_/report_` 会自动生成

---

## 6. 检查与报告扩展建议

如果阶段有强约束输出，建议重写：

- `_expected_outputs()`：声明产出文件路径列表
- `_extra_report_patterns()`：定义需要抽取的关键日志正则

这样 `check_*` 与 `report_*` 会直接得到高价值结果。

---

## 7. 质量与测试建议

- 单元测试：`tests/` 覆盖 config 解析、路径组装、报告生成
- 冒烟测试：使用 `test_work/proj.yaml` 执行 create/run/check/report
- 评审重点：
  - 新阶段是否遵循目录契约
  - 日志是否落在 `run/log/`
  - `check_result` 是否可定位失败原因

---

## 8. Nuitka 打包与运行时路径

如果你在做以下改动，建议同步查看 `share/doc/NUITKA_BUILD.md`：

- `bin/spark`
- `lib/core/runtime_paths.py`
- `lib/core/template_engine.py`
- `share/template/`
- `spark_system.yaml`
- 新增第三方依赖或动态资源文件

原因是这些改动会直接影响源码运行与 Nuitka `spark.dist` 运行是否保持一致。`NUITKA_BUILD.md` 中已经补充了：

- 开发树与发行目录的结构对照
- `get_spark_home()` 的详细流程图
- `scripts/build_nuitka.sh` 的打包流程
- 用户交付、验证与排障建议

