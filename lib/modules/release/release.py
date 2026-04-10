"""
lib/modules/release/release.py
阶段 8 — release：发布与归档。

职责：
  - 收集所有上游阶段的 release/output_file/ 产出
  - 计算 MD5 校验值并生成 CHECKSUMS.md5
  - 渲染 Release Notes（Markdown 格式）
  - 可选：打包至 tar.gz 或推送至中央库（IC Manage / Git）
"""
from __future__ import annotations

import datetime
import tarfile
from pathlib import Path

from lib.core.config_parser   import SparkConfig
from lib.core.template_engine import render_template
from lib.modules.base_component import BaseComponent
from lib.utils.file_utils     import collect_files, write_checksums, ensure_dir
from lib.utils.logger         import get_logger

logger = get_logger(__name__)

_UPSTREAM_STAGES = [
    "gen_gds",
    "gen_spice",
    "gen_lib",
    "gen_lef",
    "gen_dft",
]


class ReleaseComponent(BaseComponent):
    """发布与归档阶段。"""

    def __init__(self, config: SparkConfig):
        super().__init__("release", config)
        self.bundle_tar: bool = config.get("release", "bundle_tar", default=True)

    # ------------------------------------------------------------------
    def _generate_scripts(self) -> None:
        """渲染发布汇总脚本（可做额外的版本控制操作）。"""
        ctx = {
            "stage"       : self.stage_name,
            "project_name": self.config.project_name,
            "tech_node"   : self.config.tech_node,
            "description" : "发布与归档",
        }
        render_template("csh_wrapper.j2", self.run_dir / "run_release.csh", **ctx)

    # ------------------------------------------------------------------
    def run(self) -> None:
        """重写：Python 直接完成文件收集、校验与打包，无需调用外部 Shell。"""
        logger.info(f"[{self.stage_name}] 开始收集各阶段产出文件...")
        collected: list[Path] = self._collect_artifacts()

        if not collected:
            logger.warning(f"[{self.stage_name}] 未收集到任何产出文件，请确认上游阶段已完成。")
            return

        logger.info(f"[{self.stage_name}] 共收集 {len(collected)} 个文件。")

        release_out = self.stage_dir / "release" / "output_file"
        ensure_dir(release_out)

        checksum_file = write_checksums(collected, release_out / "CHECKSUMS.md5")
        notes_file    = self._write_release_notes(collected, release_out)

        if self.bundle_tar:
            self._create_tarball(collected, release_out)

        logger.info(f"[{self.stage_name}] 发布完成。")
        logger.info(f"  校验清单: {checksum_file}")
        logger.info(f"  发布说明: {notes_file}")

    # ------------------------------------------------------------------
    def _collect_artifacts(self) -> list[Path]:
        """从所有上游阶段的 release/output_file/ 目录中收集产出文件。"""
        artifacts: list[Path] = []
        for stage in _UPSTREAM_STAGES:
            stage_out = self.root_dir / stage / "release" / "output_file"
            if stage_out.is_dir():
                files = collect_files(stage_out, pattern="*", recursive=True)
                artifacts.extend(files)
                logger.debug(f"[{self.stage_name}] 从 {stage} 收集 {len(files)} 个文件。")
            else:
                logger.warning(f"[{self.stage_name}] 上游阶段输出目录不存在: {stage_out}")
        return artifacts

    def _write_release_notes(self, files: list[Path], out_dir: Path) -> Path:
        """生成 Markdown 格式的 Release Notes。"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# Release Notes — {self.config.project_name}",
            f"",
            f"**技术节点**: {self.config.tech_node}  ",
            f"**发布时间**: {now}  ",
            f"**PVT Corners**: {', '.join(self.config.pvt_corners)}  ",
            f"",
            f"## 产出文件清单",
            f"",
        ]
        for f in sorted(files):
            lines.append(f"- `{f.name}`")

        notes_path = out_dir / "RELEASE_NOTES.md"
        notes_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return notes_path

    def _create_tarball(self, files: list[Path], out_dir: Path) -> Path:
        """将所有产出文件打包为 tar.gz。"""
        project  = self.config.project_name
        tech     = self.config.tech_node
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        tar_path = out_dir / f"{project}_{tech}_{date_str}.tar.gz"

        with tarfile.open(tar_path, "w:gz") as tar:
            for f in files:
                tar.add(f, arcname=f.name)

        logger.info(f"[{self.stage_name}] 打包完成: {tar_path}")
        return tar_path
