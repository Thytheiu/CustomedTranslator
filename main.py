from __future__ import annotations

import ctypes
import json
import threading
import time
from pathlib import Path

import pystray
import webview
from PIL import Image

from settings import SettingsStore
from translator import translate_stream

ROOT = Path(__file__).resolve().parent
APP_NAME = "译间 · 中英互译"


class Bridge:
    def __init__(self, store):
        self._store = store
        self._window = None
        self._tray = None
        self._tray_ready = threading.Event()
        self._allow_exit = False
        self._maximized = False
        self._lock = threading.Lock()
        self._job = None

    def get_state(self):
        return self._store.public()

    def save_settings(self, payload):
        try:
            return {"ok": True, **self._store.save(payload)}
        except (ValueError, OSError) as error:
            return {"ok": False, "error": str(error)}

    def translate(self, payload):
        if not isinstance(payload, dict):
            return {"ok": False, "error": "请求格式有误。"}
        text, direction, request_id = (payload.get(k) for k in ("text", "direction", "request_id"))
        if not isinstance(text, str) or not text.strip():
            return {"ok": False, "error": "先输入需要翻译的内容。"}
        if len(text) > 20000:
            return {"ok": False, "error": "一次最多翻译 20,000 个字符，请分段翻译。"}
        if direction not in ("zh-en", "en-zh") or not isinstance(request_id, str):
            return {"ok": False, "error": "翻译方向或请求编号无效。"}
        settings = self._store.get()
        if not settings["api_key"]:
            return {"ok": False, "error": "请先在设置中填写 DeepSeek API Key。", "needs_key": True}
        cancel = threading.Event()
        with self._lock:
            if self._job and not self._job[1].is_set():
                return {"ok": False, "error": "上一段内容还在翻译中。"}
            self._job = (request_id, cancel)
        started = time.monotonic()

        def emit(chunk):
            if cancel.is_set() or self._allow_exit:
                return
            event = {"request_id": request_id, **chunk}
            try:
                self._window.evaluate_js("window.receiveTranslation(" + json.dumps(event) + ")")
            except Exception:
                cancel.set()

        def work():
            try:
                result = translate_stream(text, direction, settings, cancel, emit)
                result.update(model=settings["model"], elapsed=round(time.monotonic() - started, 1))
                emit({"phase": "done", "result": result})
            finally:
                with self._lock:
                    if self._job and self._job[0] == request_id:
                        self._job = None

        # Network waits must never hold the GUI bridge or delay tray exit.
        threading.Thread(target=work, name="translation", daemon=True).start()
        return {"ok": True, "started": True}

    def cancel_translation(self, request_id):
        with self._lock:
            if self._job and self._job[0] == request_id:
                self._job[1].set()
        return {"ok": True}

    def minimize(self):
        self._window.minimize()

    def toggle_maximize(self):
        if self._maximized:
            self._window.restore()
        else:
            self._window.maximize()

    def hide_window(self):
        if not self._tray_ready.is_set():
            return {"ok": False, "error": "托盘尚未就绪，请稍后再试。"}
        self._window.hide()
        return {"ok": True}

    def _closing(self):
        if self._allow_exit:
            return True
        self.hide_window()
        return False

    def _show(self, *_):
        from System import Action
        self._window.show()
        self._window.native.Invoke(Action(self._restore_minimized))

    def _restore_minimized(self):
        from System.Windows.Forms import FormWindowState
        if self._window.native.WindowState == FormWindowState.Minimized:
            self._window.native.WindowState = FormWindowState.Normal
        self._window.native.Activate()

    def _exit(self, *_):
        self._allow_exit = True
        with self._lock:
            if self._job:
                self._job[1].set()
        if self._tray:
            self._tray.stop()
        self._window.destroy()

    def _start_tray(self):
        def ready(icon):
            icon.visible = True
            self._tray_ready.set()

        self._tray = pystray.Icon(
            "TranslatorByGPT", Image.open(ROOT / "assets" / "translator.ico"), APP_NAME,
            pystray.Menu(
                pystray.MenuItem("打开译间", self._show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出程序", self._exit),
            ),
        )
        self._tray.run(setup=ready)


def run(store=None, on_started=None):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TranslatorByGPT.Desktop")
    store = store or SettingsStore()
    bridge = Bridge(store)
    webview.settings["DRAG_REGION_SELECTOR"] = ".window-drag"
    window = webview.create_window(
        APP_NAME, str(ROOT / "web" / "index.html"), js_api=bridge,
        width=1120, height=760, min_size=(820, 600), frameless=True,
        easy_drag=False, shadow=True, background_color="#F5F6F8", text_select=True,
    )
    bridge._window = window
    window.events.closing += bridge._closing
    window.events.maximized += lambda: setattr(bridge, "_maximized", True)
    window.events.restored += lambda: setattr(bridge, "_maximized", False)

    def started():
        threading.Thread(target=bridge._start_tray, name="tray", daemon=True).start()
        if on_started:
            on_started(window, bridge)

    try:
        webview.start(started, gui="edgechromium", icon=str(ROOT / "assets" / "translator.ico"))
    finally:
        if bridge._tray:
            bridge._tray.stop()


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        ctypes.windll.user32.MessageBoxW(
            None, "程序未能启动。请确认已安装 Microsoft Edge WebView2 运行时。\n\n" + str(error),
            "译间", 0x10,
        )
