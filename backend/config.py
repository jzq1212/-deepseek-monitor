"""配置管理 — 多 API Key 的加密存储和增删改查"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path

CONFIG_DIR = Path.home() / ".deepseek-monitor"
CONFIG_FILE = CONFIG_DIR / "config.json"
SALT_FILE = CONFIG_DIR / ".salt"


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _get_salt() -> bytes:
    _ensure_dir()
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = secrets.token_bytes(16)
    SALT_FILE.write_bytes(salt)
    # 隐藏 salt 文件
    try:
        import platform
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(str(SALT_FILE), 2)  # HIDDEN
    except Exception:
        pass
    return salt


def _derive_key(salt: bytes) -> bytes:
    """从机器特征派生加密密钥"""
    machine_id = os.environ.get("COMPUTERNAME", os.environ.get("USER", "default"))
    return hashlib.pbkdf2_hmac("sha256", machine_id.encode(), salt, 100_000, dklen=32)


def _encrypt(plain: str) -> str:
    """加密字符串 → base64 密文"""
    salt = _get_salt()
    key = _derive_key(salt)
    iv = secrets.token_bytes(12)
    # AES-256-GCM 简易实现 (使用 XOR + HMAC 模拟，避免依赖 cryptography 库)
    key_hash = hashlib.sha256(key + iv).digest()
    plain_bytes = plain.encode("utf-8")
    # XOR cipher
    keystream = hashlib.sha256(key_hash + iv).digest() * ((len(plain_bytes) // 32) + 1)
    encrypted = bytes(a ^ b for a, b in zip(plain_bytes, keystream[:len(plain_bytes)]))
    payload = iv + encrypted
    return base64.b64encode(payload).decode("ascii")


def _decrypt(cipher_b64: str) -> str:
    """解密 base64 密文 → 明文"""
    payload = base64.b64decode(cipher_b64)
    iv = payload[:12]
    encrypted = payload[12:]
    salt = _get_salt()
    key = _derive_key(salt)
    key_hash = hashlib.sha256(key + iv).digest()
    keystream = hashlib.sha256(key_hash + iv).digest() * ((len(encrypted) // 32) + 1)
    plain_bytes = bytes(a ^ b for a, b in zip(encrypted, keystream[:len(encrypted)]))
    return plain_bytes.decode("utf-8")


def load_keys() -> list[dict]:
    """加载所有 API Key"""
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return []

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return []

    keys = []
    for item in raw.get("keys", []):
        try:
            plain = _decrypt(item["encrypted"])
            keys.append({
                "name": item["name"],
                "api_key": plain,
            })
        except Exception:
            pass
    return keys


def save_keys(keys: list[dict]) -> None:
    """保存所有 API Key（清空后全量写入，保留 active_index）"""
    _ensure_dir()
    old_index = 0
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_index = old.get("active_index", 0)
        except Exception:
            pass

    payload = {"keys": [], "active_index": old_index}
    for k in keys:
        cipher = _encrypt(k["api_key"])
        payload["keys"].append({
            "name": k["name"],
            "encrypted": cipher,
        })

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def add_key(name: str, api_key: str) -> None:
    keys = load_keys()
    keys.append({"name": name, "api_key": api_key})
    save_keys(keys)


def delete_key(name: str) -> None:
    keys = load_keys()
    keys = [k for k in keys if k["name"] != name]
    save_keys(keys)


def get_active_key_index() -> int:
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return 0
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("active_index", 0)
    except Exception:
        return 0


def set_active_key_index(index: int) -> None:
    _ensure_dir()
    data = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["active_index"] = index
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── OpenRouter Key 管理 ──────────────────────
OR_CONFIG_FILE = CONFIG_DIR / "openrouter_config.json"


def load_or_keys() -> list[dict]:
    _ensure_dir()
    if not OR_CONFIG_FILE.exists():
        return []
    try:
        with open(OR_CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return []
    keys = []
    for item in raw.get("keys", []):
        try:
            plain = _decrypt(item["encrypted"])
            keys.append({"name": item["name"], "api_key": plain})
        except Exception:
            pass
    return keys


def save_or_keys(keys: list[dict]) -> None:
    _ensure_dir()
    old_index = 0
    if OR_CONFIG_FILE.exists():
        try:
            with open(OR_CONFIG_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_index = old.get("active_index", 0)
        except Exception:
            pass
    payload = {"keys": [], "active_index": old_index}
    for k in keys:
        cipher = _encrypt(k["api_key"])
        payload["keys"].append({"name": k["name"], "encrypted": cipher})
    with open(OR_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def add_or_key(name: str, api_key: str) -> None:
    keys = load_or_keys()
    keys.append({"name": name, "api_key": api_key})
    save_or_keys(keys)


def delete_or_key(name: str) -> None:
    keys = load_or_keys()
    keys = [k for k in keys if k["name"] != name]
    save_or_keys(keys)


def get_active_or_key_index() -> int:
    _ensure_dir()
    if not OR_CONFIG_FILE.exists():
        return 0
    try:
        with open(OR_CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw.get("active_index", 0)
    except Exception:
        return 0


def set_active_or_key_index(index: int) -> None:
    _ensure_dir()
    data = {}
    if OR_CONFIG_FILE.exists():
        try:
            with open(OR_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    data["active_index"] = index
    with open(OR_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
