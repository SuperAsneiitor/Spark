"""
tests/test_file_utils.py
file_utils 工具函数单元测试。
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.utils.file_utils import (
    ensure_dir,
    md5sum,
    collect_files,
    clean_dir,
    write_checksums,
)


class TestEnsureDir:
    def test_creates_nested_dirs(self, tmp_path: Path):
        target = tmp_path / "a" / "b" / "c"
        result = ensure_dir(target)
        assert result.is_dir()

    def test_idempotent(self, tmp_path: Path):
        target = tmp_path / "existing"
        ensure_dir(target)
        ensure_dir(target)  # 不应报错
        assert target.is_dir()


class TestMd5Sum:
    def test_known_content(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"hello world")
        result = md5sum(f)
        assert result == "5EB63BBBE01EEED093CB22BB8F5ACDC3"

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            md5sum(tmp_path / "nonexistent.txt")


class TestCollectFiles:
    def test_collects_by_pattern(self, tmp_path: Path):
        (tmp_path / "a.lib").write_text("lib1")
        (tmp_path / "b.lib").write_text("lib2")
        (tmp_path / "c.txt").write_text("ignored")
        files = collect_files(tmp_path, pattern="*.lib")
        assert len(files) == 2
        assert all(f.suffix == ".lib" for f in files)

    def test_recursive(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.gds").write_text("gds")
        files = collect_files(tmp_path, pattern="*.gds", recursive=True)
        assert len(files) == 1

    def test_missing_dir_raises(self, tmp_path: Path):
        with pytest.raises(NotADirectoryError):
            collect_files(tmp_path / "nonexistent")


class TestCleanDir:
    def test_clears_contents(self, tmp_path: Path):
        d = tmp_path / "to_clean"
        d.mkdir()
        (d / "file.txt").write_text("data")
        clean_dir(d)
        assert d.is_dir()
        assert list(d.iterdir()) == []

    def test_recreate_false(self, tmp_path: Path):
        d = tmp_path / "to_remove"
        d.mkdir()
        clean_dir(d, recreate=False)
        assert not d.exists()


class TestWriteChecksums:
    def test_generates_md5_file(self, tmp_path: Path):
        f1 = tmp_path / "output" / "a.lib"
        f1.parent.mkdir(parents=True)
        f1.write_text("timing data")
        checksum_file = write_checksums([f1], tmp_path / "CHECKSUMS.md5")
        content = checksum_file.read_text()
        assert "a.lib" in content
        assert len(content.split()[0]) == 32  # MD5 hex 长度
