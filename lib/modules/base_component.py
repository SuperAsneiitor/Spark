"""
lib/modules/base_component.py
所有流程阶段的抽象基类。

设计原则：
  - 单一职责：基类只定义"流程骨架"，子类负责"内容填充"
  - 开闭原则：新增阶段只需继承并实现 _generate_scripts，无需修改基类
  - 标准目录树：work/<case>/<version>/<stage>/ 下 run/scr/check/report/release 等
"""
from __future__ import annotations

import re
import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from lib.core.config_parser import SparkConfig
from lib.core.shell_runner  import ShellRunner
from lib.utils.logger       import get_logger
from lib.utils.file_utils   import ensure_dir, collect_files

logger = get_logger(__name__)

# 每个阶段下的标准子目录列表（按功能分组）
_STAGE_SUBDIRS = [
    "run",              # 执行脚本
    "run/log",          # 执行日志
    "scr",              # TCL / 工具配置脚本
    "check",            # 结果检查
    "check/log",        # 检查日志
    "check/rpt",        # 检查报告
    "report",           # 汇总报告
    "release/output_file",
    "release/extract_result",
]

# 日志扫描：通用错误 / 警告关键字模式
_DEFAULT_ERROR_PATTERNS   = [r"\bERROR\b", r"\bFATAL\b", r"\bFAILED\b", r"Segmentation fault"]
_DEFAULT_WARNING_PATTERNS = [r"\bWARNING\b", r"\bWARN\b", r"\bCaution\b"]


@dataclass
class StageResult:
    """
    check_result() 的返回值，记录阶段执行的健康状态。

    Attributes:
        stage:           阶段名称
        passed:          True = 无 error 且所有预期产出均存在
        errors:          日志中匹配到的 error 行列表
        warnings:        日志中匹配到的 warning 行列表
        missing_outputs: 声明了但不存在的产出文件列表
        checked_logs:    实际扫描的日志文件列表
    """
    stage:           str
    passed:          bool              = True
    errors:          list[str]         = field(default_factory=list)
    warnings:        list[str]         = field(default_factory=list)
    missing_outputs: list[Path]        = field(default_factory=list)
    checked_logs:    list[Path]        = field(default_factory=list)

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{self.stage}] {status} | "
            f"errors={len(self.errors)} "
            f"warnings={len(self.warnings)} "
            f"missing_outputs={len(self.missing_outputs)}"
        )


class BaseComponent(ABC):
    """
    所有流程阶段组件的基类。

    生命周期：
        1. create_env()    → 创建目录树 + 渲染生成脚本
        2. run()           → 拉起 C-Shell 执行脚本
        3. check_result()  → 校验日志与产出文件，返回 StageResult
        4. extract_report() → 抽取关键信息，写入 report/<stage>_summary.rpt

    子类必须实现：
        _generate_scripts()  — 利用 Jinja2 模板渲染本阶段所需的 .csh / .tcl 脚本

    子类可选重写：
        run()                — 若阶段包含多子步骤（如 gen_spice 的 pv + rc）
        _extra_setup()       — 阶段特有的额外初始化（如创建软链接、写配置片段）
        _expected_outputs()  — 声明本阶段执行后应存在的产出文件列表
        _extra_report_patterns() — 追加阶段特有的报告抽取正则模式
    """

    def __init__(self, stage_name: str, config: SparkConfig):
        self.stage_name: str     = stage_name
        self.config: SparkConfig = config

        # project_root : 项目顶层（init_env 在此建立 work/ incoming/ run/ 等）
        # root_dir     : project_root/work/
        # case_root    : work/<case_name>/<case_version>/（除 init_env 外各阶段沙箱根）
        try:
            self.project_root: Path = config.work_dir
        except Exception:
            self.project_root = Path.cwd()

        self.root_dir: Path = self.project_root / "work"
        self.case_name: str = config.case_name
        self.case_version: str = config.case_version
        self.case_root: Path = self.root_dir / self.case_name / self.case_version
        self.stage_dir: Path = self.case_root / stage_name

        # ── 功能子目录（每个功能独立成目录）──────────────────────────────
        self.run_dir:     Path = self.stage_dir / "run"
        self.scr_dir:     Path = self.stage_dir / "scr"
        self.log_dir:     Path = self.stage_dir / "run" / "log"   # 执行日志
        self.check_dir:   Path = self.stage_dir / "check"          # 结果检查
        self.report_dir:  Path = self.stage_dir / "report"         # 汇总报告
        self.release_dir: Path = self.stage_dir / "release"
        # 向后兼容别名
        self.rpt_dir:     Path = self.report_dir

        self._runner = ShellRunner(shell="csh", log_dir=self.log_dir)

    # ------------------------------------------------------------------
    # 公开接口（流程入口）
    # ------------------------------------------------------------------
    def create_env(self) -> None:
        """
        阶段初始化入口：
          1. 创建标准目录树
          2. 调用子类实现的 _generate_scripts()
          3. 调用可选的 _extra_setup()
        """
        logger.info(f"[{self.stage_name}] 初始化阶段环境...")
        self._create_directories()
        self._generate_scripts()
        self._extra_setup()
        logger.info(f"[{self.stage_name}] 环境初始化完成。")

    def run(self) -> None:
        """
        阶段执行入口：拉起本阶段的主 C-Shell 脚本。
        子阶段（如 gen_spice）可重写此方法实现多步骤调度。
        """
        logger.info(f"[{self.stage_name}] 开始执行...")
        self._execute_csh(f"run_{self.stage_name}.csh")
        logger.info(f"[{self.stage_name}] 执行完成。")

    def check_result(self) -> StageResult:
        """
        阶段结果校验入口（check/ 功能目录），执行以下两项检查后返回 StageResult：

          1. 日志扫描：扫描 run/log/ 下所有 .log 文件，搜索 error / warning 关键字
          2. 产出校验：验证 _expected_outputs() 声明的文件是否全部存在
          3. 校验结果写入 check/rpt/<stage>_check.rpt

        Returns:
            StageResult —— passed=True 表示无 error 且产出完整
        """
        ensure_dir(self.check_dir / "log")
        ensure_dir(self.check_dir / "rpt")

        result = StageResult(stage=self.stage_name)

        # ---- 1. 日志扫描（run/log/）------------------------------------------
        log_files = collect_files(self.log_dir, pattern="*.log") if self.log_dir.exists() else []
        result.checked_logs = log_files

        error_re   = [re.compile(p, re.IGNORECASE) for p in _DEFAULT_ERROR_PATTERNS]
        warning_re = [re.compile(p, re.IGNORECASE) for p in _DEFAULT_WARNING_PATTERNS]

        for log_file in log_files:
            try:
                for lineno, line in enumerate(
                    log_file.read_text(encoding="utf-8", errors="ignore").splitlines(),
                    start=1,
                ):
                    tag = f"{log_file.name}:{lineno}"
                    if any(rx.search(line) for rx in error_re):
                        result.errors.append(f"{tag}  {line.strip()}")
                    elif any(rx.search(line) for rx in warning_re):
                        result.warnings.append(f"{tag}  {line.strip()}")
            except OSError as exc:
                logger.warning(f"[{self.stage_name}] 无法读取日志: {exc}")

        # ---- 2. 产出文件校验 -------------------------------------------------
        for expected in self._expected_outputs():
            if not expected.exists():
                result.missing_outputs.append(expected)

        # ---- 3. 综合判定 -----------------------------------------------------
        result.passed = (not result.errors) and (not result.missing_outputs)

        # ---- 4. 写入 check/rpt/ 校验报告 ------------------------------------
        check_rpt = self.check_dir / "rpt" / f"{self.stage_name}_check.rpt"
        self._write_check_report(result, check_rpt)

        if result.passed:
            logger.info(f"[{self.stage_name}] check_result: PASS  {result.summary()}")
        else:
            logger.error(f"[{self.stage_name}] check_result: FAIL  {result.summary()}")
            for err in result.errors[:10]:
                logger.error(f"  {err}")
            for mp in result.missing_outputs:
                logger.error(f"  缺失产出: {mp}")

        return result

    def extract_report(self) -> Path:
        """
        报告抽取入口（report/ 功能目录），从 run/log/ 中提炼关键信息，
        写入 report/<stage>_summary.rpt 并返回文件路径。

        抽取策略：
          - 通用：统计 error / warning 总数，列出所有产出文件
          - 扩展：调用 _extra_report_patterns() 追加阶段特有的正则匹配行

        Returns:
            生成的 summary 文件路径（report/<stage>_summary.rpt）
        """
        ensure_dir(self.report_dir)
        summary_path = self.report_dir / f"{self.stage_name}_summary.rpt"

        result      = self.check_result()
        output_files = collect_files(
            self.release_dir / "output_file"
        ) if (self.release_dir / "output_file").exists() else []

        # ---- 收集阶段特有的匹配行（扫描 run/log/）----------------------------
        extra_hits: dict[str, list[str]] = {}
        extra_patterns = self._extra_report_patterns()
        if extra_patterns and self.log_dir.exists():
            compiled = {
                label: re.compile(pattern, re.IGNORECASE)
                for label, pattern in extra_patterns.items()
            }
            for log_file in collect_files(self.log_dir, pattern="*.log"):
                try:
                    for line in log_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                        for label, rx in compiled.items():
                            if rx.search(line):
                                extra_hits.setdefault(label, []).append(line.strip())
                except OSError:
                    pass

        # ---- 写入 summary 文件 -----------------------------------------------
        now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "=" * 70,
            f"  Stage Summary Report : {self.stage_name}",
            f"  Generated            : {now}",
            f"  Status               : {'PASS' if result.passed else 'FAIL'}",
            "=" * 70,
            "",
            f"[Log Scan]",
            f"  Scanned logs : {len(result.checked_logs)}",
            f"  Errors       : {len(result.errors)}",
            f"  Warnings     : {len(result.warnings)}",
            "",
        ]

        if result.errors:
            lines.append("[Errors]")
            lines.extend(f"  {e}" for e in result.errors)
            lines.append("")

        if result.warnings:
            lines.append("[Warnings (first 20)]")
            lines.extend(f"  {w}" for w in result.warnings[:20])
            lines.append("")

        lines.append("[Output Files]")
        if output_files:
            lines.extend(f"  {f.name}" for f in output_files)
        else:
            lines.append("  (none)")
        lines.append("")

        if result.missing_outputs:
            lines.append("[Missing Outputs]")
            lines.extend(f"  MISSING: {p}" for p in result.missing_outputs)
            lines.append("")

        if extra_hits:
            lines.append("[Stage-Specific Metrics]")
            for label, hits in extra_hits.items():
                lines.append(f"  {label} ({len(hits)} hits):")
                lines.extend(f"    {h}" for h in hits[:5])
            lines.append("")

        lines.append("=" * 70)
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"[{self.stage_name}] 报告已写入: {summary_path}")
        return summary_path

    # ------------------------------------------------------------------
    # 私有 / 受保护方法
    # ------------------------------------------------------------------
    def _create_directories(self) -> None:
        """创建本阶段的标准目录树。"""
        for sub in _STAGE_SUBDIRS:
            ensure_dir(self.stage_dir / sub)
        logger.debug(f"[{self.stage_name}] 目录树创建完成: {self.stage_dir}")

    @abstractmethod
    def _generate_scripts(self) -> None:
        """
        (抽象) 生成本阶段所需的执行脚本。
        子类必须实现，通常调用 render_template() 输出 .csh / .tcl 文件。
        """

    def _extra_setup(self) -> None:
        """
        (可选) 阶段特有的额外初始化逻辑，如创建软链接、写辅助配置文件。
        默认空实现，子类按需重写。
        """

    def _expected_outputs(self) -> list[Path]:
        """
        (可选) 声明本阶段执行后应存在的产出文件列表，供 check_result() 校验。
        默认返回空列表（不做产出校验），子类按需重写。

        示例（gen_lib 子类）::

            def _expected_outputs(self) -> list[Path]:
                return [
                    self.release_dir / "output_file" / f"{self.config.project_name}_tt.lib"
                ]
        """
        return []

    def _extra_report_patterns(self) -> dict[str, str]:
        """
        (可选) 返回阶段特有的报告抽取正则模式字典，供 extract_report() 使用。
        键为可读标签，值为正则表达式字符串。
        默认返回空字典，子类按需重写。

        示例（gen_spice 子类）::

            def _extra_report_patterns(self) -> dict[str, str]:
                return {
                    "DRC Violations" : r"DRC\\s+violation",
                    "LVS Mismatch"   : r"LVS\\s+(mismatch|incorrect)",
                    "Extracted Nets" : r"Total nets extracted\\s*:",
                }
        """
        return {}

    def _write_check_report(self, result: "StageResult", path: Path) -> None:
        """将 check_result() 的结果写入 check/rpt/ 下的文本报告。"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "PASS" if result.passed else "FAIL"
        lines = [
            "=" * 60,
            f"  Check Report : {self.stage_name}",
            f"  Time         : {now}",
            f"  Status       : {status}",
            "=" * 60,
            f"Scanned logs : {len(result.checked_logs)}",
            f"Errors       : {len(result.errors)}",
            f"Warnings     : {len(result.warnings)}",
            f"Missing outs : {len(result.missing_outputs)}",
            "",
        ]
        if result.errors:
            lines.append("[Errors]")
            lines.extend(f"  {e}" for e in result.errors)
            lines.append("")
        if result.missing_outputs:
            lines.append("[Missing Outputs]")
            lines.extend(f"  {p}" for p in result.missing_outputs)
            lines.append("")
        lines.append("=" * 60)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _execute_csh(self, script_name: str, cwd: Path | None = None) -> None:
        """
        执行 run/ 目录下指定名称的 C-Shell 脚本。

        Args:
            script_name: 脚本文件名（如 "run_gen_lib.csh"）
            cwd:         执行工作目录，默认为 run_dir 自身
        """
        script_path = self.run_dir / script_name
        run_cwd     = cwd or self.run_dir

        if not script_path.exists():
            logger.error(f"[{self.stage_name}] 脚本不存在: {script_path}")
            raise FileNotFoundError(f"脚本不存在: {script_path}")

        self._runner.run(script=script_path, cwd=run_cwd)

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(stage={self.stage_name!r})"
