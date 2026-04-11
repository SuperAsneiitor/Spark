# Spark 接口级开发规范

## 1. 目的与边界

本文档定义 Spark 的接口契约，目标是保证：

- 模块可替换：新增/重构阶段不破坏 CLI 与调度层
- 结果可验证：每个阶段都可被 `check_*` 和 `report_*` 标准化处理
- 故障可定位：统一异常、日志和产物路径

适用范围：

- `lib/core/*`（含 `spark_system.yaml` 加载与 `license_guard`）
- `lib/modules/base_component.py`
- `lib/modules/<stage>/<stage>.py`
- `bin/spark`

---

## 2. 核心对象与职责

## 2.0 系统配置与 License

- 文件：默认 `<SPARK_HOME>/spark_system.yaml`，或 `SPARK_SYSTEM_CONFIG`。
- `license_check.enabled`：为真时 `bin/spark` 在加载项目 YAML 前调用 `run_pre_command_license_check`。
- 扩展：实现 `LicenseAllowlistProvider` 并 `set_license_allowlist_provider()`。

## 2.1 `SparkConfig`

- 输入：YAML 文件路径（或 Fernet 密文文件路径，见下）
- 输出：强类型配置访问能力
- 密文（内部机制，无对外加解密命令）：当环境变量 `SPARK_ENCRYPTED_CONFIG` 为真且已设置 `SPARK_FERNET_KEY` 时，由 `lib.utils.config_crypto` 解密后再 `yaml.safe_load`。
- 约束：
  - 缺失必填字段必须抛 `ConfigKeyError`
  - 路径字段返回 `Path` 对象
  - 工具路径允许回退到工具名本身

关键接口：

- `get(*keys, default=None) -> Any`
- `require(*keys) -> Any`
- `project_name -> str`
- `tech_node -> str`
- `pvt_corners -> list[str]`
- `work_dir/gds_source/netlist_source/lef_source -> Path`
- `tool_path(tool_name: str) -> str`

## 2.2 `BaseComponent`

生命周期接口（固定顺序）：

1. `create_env()`
2. `run()`
3. `check_result()`
4. `extract_report()`

子类实现接口：

- 必须实现：`_generate_scripts()`
- 可选重写：`run()`、`_extra_setup()`、`_expected_outputs()`、`_extra_report_patterns()`

目录契约（阶段根为 `work/<case_name>/<case_version>/<stage>/`）：

- `run/`, `run/log/`
- `scr/`
- `check/log/`, `check/rpt/`
- `report/`
- `release/output_file/`, `release/extract_result/`

---

## 3. CLI 契约

命令分组：

- 项目初始化：`init_env`
- 阶段命令：`create_<stage>_env`、`run_<stage>`、`check_<stage>`、`report_<stage>`
- 全流程：`run_all [--from-stage <stage>]`

行为约束：

- `check_<stage>` 返回码：
  - `0`：检查通过
  - `1`：检查失败
- 其余命令异常即失败退出（非 0）

---

## 4. 阶段接口契约（必须遵守）

## 4.1 `create_env()`

- 必须幂等：重复执行不应破坏已有产物
- 最低保证：
  - 目录结构完整
  - 运行脚本可生成（`run/*.csh`）
  - 所需模板渲染成功

## 4.2 `run()`

- 默认行为：执行 `run/run_<stage>.csh`
- 若重写：
  - 必须在日志中记录子步骤边界
  - 子步骤失败策略需明确（中断/继续）

## 4.3 `check_result() -> StageResult`

- 必须完成：
  - 扫描 `run/log/*.log`
  - 校验 `_expected_outputs()`
  - 写出 `check/rpt/<stage>_check.rpt`

`StageResult` 字段定义：

- `stage: str`
- `passed: bool`
- `errors: list[str]`
- `warnings: list[str]`
- `missing_outputs: list[Path]`
- `checked_logs: list[Path]`

## 4.4 `extract_report() -> Path`

- 必须写出：`report/<stage>_summary.rpt`
- 可扩展：
  - 用 `_extra_report_patterns()` 增加特定关键字抽取

---

## 5. 异常规范

推荐异常分层：

- 配置层：`ConfigKeyError`, `FileNotFoundError`, `ValueError`
- 执行层：`RuntimeError`（脚本执行失败、并行任务失败）
- 输入层：`ValueError`（参数不合法，例如不支持的格式）

约束：

- 不吞异常根因；日志保留原始异常信息
- 阶段重写 `run()` 时，必须明确“失败是否继续”

---

## 6. 日志规范

日志前缀统一：`[<stage>]`

最低日志点：

- `create_env` 开始/完成
- `run` 开始/完成
- 子步骤开始/完成（如 `gen_spice` 的 pv/rc）
- `check_result` PASS/FAIL 摘要
- `extract_report` 输出路径

路径规范：

- 运行日志：`run/log/`
- 检查报告：`check/rpt/`
- 汇总报告：`report/`

---

## 7. 新增阶段模板（开发脚手架）

目录：

- `lib/modules/gen_xxx/__init__.py`
- `lib/modules/gen_xxx/gen_xxx.py`

最小实现：

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

注册：

- `bin/spark` 的 `STAGE_MAP` 增加 `"gen_xxx"`

---

## 8. 测试规范（建议最低覆盖）

单元测试：

- `SparkConfig`：
  - 缺字段报错
  - 类型与默认值行为
- `BaseComponent`：
  - 目录创建幂等性
  - `check_result` 对 error/warning 匹配
  - `_expected_outputs` 缺失判定
- 各阶段：
  - `_generate_scripts` 产出脚本存在
  - 特殊 `run()` 分支（如 continue_on_drc_error）

冒烟测试：

- 使用 `test_work/proj.yaml` 执行：
  - `init_env`
  - 单阶段 create/run/check/report
  - `run_all --from-stage`

---

## 9. 版本演进建议

- 向后兼容优先：
  - 导入路径通过子包 `__init__.py` 做稳定出口
  - 报告字段新增尽量追加，不破坏既有解析器
- 变更必须同步：
  - `share/doc/USER_GUIDE.md`
  - `share/doc/DEVELOPER_GUIDE.md`
  - `share/doc/DEMO.md`

