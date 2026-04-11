"""
tests/test_config_crypto.py
config_crypto 内部工具与 SparkConfig 密文加载（环境变量）单元测试。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.core.config_parser import SparkConfig
from lib.utils.config_crypto import (
    ConfigCryptoError,
    decrypt_bytes,
    decrypt_file_to_text,
    encrypt_bytes,
    encrypt_file,
    generate_fernet_key,
    resolve_key,
)


MIN_YAML = """
project:
  name: enc_proj
  tech_node: "7nm"
  pvt: [tt]

paths:
  work_dir: /tmp/w
  gds_source: /tmp/a.gds
  netlist: /tmp/a.cdl
  lef_source: /tmp/a.lef

tools:
  calibre: cal
"""


def test_encrypt_decrypt_roundtrip_bytes():
    key = generate_fernet_key()
    plain = b"hello spark"
    token = encrypt_bytes(plain, key=key)
    assert decrypt_bytes(token, key=key) == plain


def test_decrypt_wrong_key():
    key_a = generate_fernet_key()
    key_b = generate_fernet_key()
    token = encrypt_bytes(b"x", key=key_a)
    with pytest.raises(ConfigCryptoError, match="解密失败"):
        decrypt_bytes(token, key=key_b)


def test_resolve_key_requires_env(monkeypatch):
    monkeypatch.delenv("SPARK_FERNET_KEY", raising=False)
    with pytest.raises(ConfigCryptoError, match="未提供密钥"):
        resolve_key(None)


def test_spark_config_loads_encrypted_when_env_set(tmp_path: Path, monkeypatch):
    key = generate_fernet_key()
    monkeypatch.setenv("SPARK_FERNET_KEY", key.decode("ascii"))
    monkeypatch.setenv("SPARK_ENCRYPTED_CONFIG", "1")

    plain = tmp_path / "p.yaml"
    enc = tmp_path / "p.yaml.enc"
    plain.write_text(MIN_YAML, encoding="utf-8")
    encrypt_file(plain, enc, key=key)

    text = decrypt_file_to_text(enc)
    assert "enc_proj" in text

    cfg = SparkConfig(enc)
    assert cfg.project_name == "enc_proj"
    assert cfg.tech_node == "7nm"
