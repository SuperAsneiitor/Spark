"""
lib/utils/config_crypto.py
配置文件对称加密/解密（Fernet：AES-128-CBC + HMAC，带时间戳防篡改）。

仅供框架内部调用（如 ``SparkConfig`` 在 ``SPARK_ENCRYPTED_CONFIG`` 开启时解密）。
不对外提供独立 CLI；离线加密封装由业务侧自建脚本或运维流程完成。

密钥勿入库；运行时通过环境变量 ``SPARK_FERNET_KEY`` 注入。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union

from cryptography.fernet import Fernet, InvalidToken  # type: ignore[import-untyped]

# 环境变量名：值为 Fernet.generate_key() 产出的 url-safe base64 字符串
DEFAULT_KEY_ENV = "SPARK_FERNET_KEY"


class ConfigCryptoError(RuntimeError):
    """加密/解密或密钥相关错误。"""


def generate_fernet_key() -> bytes:
    """生成新 Fernet 密钥（32 字节经 url-safe base64 编码）。"""
    return Fernet.generate_key()


def normalize_key(key: Union[str, bytes]) -> bytes:
    """接受 str 或 bytes，返回 Fernet 可用的 key bytes。"""
    if isinstance(key, str):
        key = key.strip().encode("utf-8")
    if not isinstance(key, bytes):
        raise ConfigCryptoError(f"密钥类型无效: {type(key)!r}")
    try:
        Fernet(key)  # 校验格式
    except ValueError as exc:
        raise ConfigCryptoError(
            "密钥不是有效的 Fernet key（须为 url-safe base64，见 cryptography.fernet.Fernet.generate_key）"
        ) from exc
    return key


def resolve_key(explicit: Union[str, bytes, None] = None) -> bytes:
    """
    解析密钥：优先 ``explicit``，否则环境变量 ``SPARK_FERNET_KEY``（或 ``DEFAULT_KEY_ENV``）。
    """
    if explicit is not None:
        return normalize_key(explicit)
    env = os.environ.get(DEFAULT_KEY_ENV, "").strip()
    if not env:
        raise ConfigCryptoError(
            f"未提供密钥：请设置环境变量 {DEFAULT_KEY_ENV}，或在 API 中传入 key="
        )
    return normalize_key(env.encode("utf-8") if env.isascii() else env)


def encrypt_bytes(plain: bytes, key: Union[str, bytes, None] = None) -> bytes:
    """使用 Fernet 加密二进制内容。"""
    f = Fernet(resolve_key(key))
    return f.encrypt(plain)


def decrypt_bytes(token: bytes, key: Union[str, bytes, None] = None) -> bytes:
    """解密 Fernet 密文；密钥错误或内容被篡改时抛出 ConfigCryptoError。"""
    f = Fernet(resolve_key(key))
    try:
        return f.decrypt(token)
    except InvalidToken as exc:
        raise ConfigCryptoError("解密失败：密钥错误或密文已损坏") from exc


def encrypt_file(
    src: Union[str, Path],
    dst: Union[str, Path],
    *,
    key: Union[str, bytes, None] = None,
) -> Path:
    """读取明文文件，写入加密文件。"""
    src_p, dst_p = Path(src), Path(dst)
    if not src_p.is_file():
        raise FileNotFoundError(f"明文文件不存在: {src_p}")
    plain = src_p.read_bytes()
    dst_p.write_bytes(encrypt_bytes(plain, key=key))
    return dst_p.resolve()


def decrypt_file(
    src: Union[str, Path],
    *,
    key: Union[str, bytes, None] = None,
) -> bytes:
    """读取加密文件，返回明文 bytes。"""
    src_p = Path(src)
    if not src_p.is_file():
        raise FileNotFoundError(f"密文文件不存在: {src_p}")
    return decrypt_bytes(src_p.read_bytes(), key=key)


def decrypt_file_to_text(
    src: Union[str, Path],
    *,
    key: Union[str, bytes, None] = None,
    encoding: str = "utf-8",
) -> str:
    """解密为文本（用于 YAML 等）。"""
    return decrypt_file(src, key=key).decode(encoding)


__all__ = [
    "DEFAULT_KEY_ENV",
    "ConfigCryptoError",
    "generate_fernet_key",
    "normalize_key",
    "resolve_key",
    "encrypt_bytes",
    "decrypt_bytes",
    "encrypt_file",
    "decrypt_file",
    "decrypt_file_to_text",
]
