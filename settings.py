"""Local preferences; API keys are protected by Windows for the current user."""
import base64
import ctypes
import json
import os
import threading
from ctypes import wintypes
from pathlib import Path

DEFAULT_MODEL = "deepseek-flash"
LEVELS = {"none", "low", "high", "max"}


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def protect(data: bytes, decrypt=False) -> bytes:
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


class SettingsStore:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else Path(os.environ["APPDATA"]) / "TranslatorByGPT"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "settings.json"
        self._lock = threading.Lock()
        self._data = {"api_key": "", "model": DEFAULT_MODEL, "thinking": "low"}
        self._notice = ""
        if self.path.exists():
            try:
                stored = json.loads(self.path.read_text(encoding="utf-8"))
                model, thinking = stored.get("model"), stored.get("thinking")
                if isinstance(model, str) and model.strip():
                    self._data["model"] = model.strip()
                if thinking in LEVELS:
                    self._data["thinking"] = thinking
                if stored.get("protected_key"):
                    self._data["api_key"] = protect(base64.b64decode(stored["protected_key"]), True).decode()
            except (OSError, ValueError, TypeError, AttributeError):
                self._notice = "上次保存的设置无法读取，请重新填写。"

    def get(self):
        with self._lock:
            return dict(self._data)

    def public(self):
        data = self.get()
        return {"has_api_key": bool(data.pop("api_key")), **data, "notice": self._notice}

    def save(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("设置格式有误。")
        model, thinking, key = (payload.get(k) for k in ("model", "thinking", "api_key"))
        if not isinstance(model, str) or not model.strip() or len(model) > 200:
            raise ValueError("请填写有效的模型 ID。")
        if not isinstance(thinking, str) or thinking not in LEVELS:
            raise ValueError("请选择思考强度。")
        if not isinstance(key, str) or any(ord(c) < 32 or ord(c) > 126 for c in key):
            raise ValueError("API Key 只能包含英文字符，请检查是否带有换行或中文。")
        with self._lock:
            key = key.strip() or self._data["api_key"]
            if not key:
                raise ValueError("请填写 DeepSeek API Key。")
            data = {"model": model.strip(), "thinking": thinking, "api_key": key}
            encoded = base64.b64encode(protect(key.encode())).decode()
            stored = {"model": data["model"], "thinking": thinking, "protected_key": encoded}
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
            self._data, self._notice = data, ""
        return self.public()
