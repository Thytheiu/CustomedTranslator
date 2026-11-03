"""Runs the real WebView2 UI with isolated preferences and simulated API packets."""
import io
import json
import sys
import time
import traceback
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from main import run
from settings import SettingsStore

report = {"checks": [], "errors": []}
store = SettingsStore(ROOT / ".qa" / ("desktop-" + uuid4().hex))


def simulated_response(request, **kwargs):
    payload = json.loads(request.data)
    if payload["messages"][1]["content"] == "__slow__":
        time.sleep(30)
    output = "Hello, world.\n\nKeep every meaning." if "英语" in payload["messages"][0]["content"] else "你好，世界。"
    lines = []
    for part in [output[:6], output[6:], ""]:
        finish = "stop" if not part else None
        lines.append("data: " + json.dumps({"choices": [{"delta": {"content": part}, "finish_reason": finish}]}) + "\n\n")
    return io.BytesIO(("".join(lines) + "data: [DONE]\n").encode())


def started(window, bridge):
    def js(code): return window.evaluate_js(code)
    def wait(code, seconds=12):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if js(code): return
            time.sleep(.1)
        raise AssertionError("Timed out: " + code)
    def check(label, code):
        assert js(code), label
        report["checks"].append(label)

    try:
        assert window.events.loaded.wait(20), "WebView page load"
        wait("state.ready")
        check("First run opens API key guide", "document.getElementById('settingsDialog').open")
        check("Icon resource loads", "document.querySelector('.app-icon').naturalWidth > 0")
        js("$('apiKey').value='sk-local-fixture'; $('modelId').value='custom-model'; chooseEffort('max'); $('settingsForm').requestSubmit(); true")
        wait("!$('settingsDialog').open")
        check("Settings save updates chips", "$('modelSummary').textContent==='custom-model' && $('thinkingSummary').textContent==='极高思考'")
        assert SettingsStore(store.directory).get()["api_key"] == "sk-local-fixture"
        report["checks"].append("Encrypted key survives reload")
        js("openSettings(); chooseEffort('none'); $('settingsDialog').close(); true")
        check("Discarding settings keeps saved effort", "state.thinking==='max'")
        js("$('sourceText').value='你好，世界。'; count(); translate(); true")
        wait("!state.busy")
        check("Real JS-to-Python streaming translation", "state.result==='Hello, world.\\n\\nKeep every meaning.' && state.resultValid")
        js("swap(); true")
        check("Swap uses completed translation", "state.direction==='en-zh' && $('sourceText').value.startsWith('Hello')")
        js("translate(); true")
        wait("!state.busy")
        check("Reverse translation completes", "state.result==='你好，世界。'")
        js("$('sourceText').value='__slow__'; translate(); true")
        wait("state.busy")
        time.sleep(.2)
        js("stop(); true")
        wait("!state.busy", 2)
        check("Stop returns promptly during blocked network", "$('statusText').textContent==='已停止'")
        js("$('sourceText').value='Hello'; translate(); true")
        wait("!state.busy")
        check("New translation works after cancellation", "state.result==='你好，世界。'")
        for width, height in [(820,600), (1120,760)]:
            window.resize(width, height)
            time.sleep(.2)
            check(f"No page overflow at {width}x{height}", "document.documentElement.scrollWidth<=innerWidth && document.documentElement.scrollHeight<=innerHeight")
        assert bridge._tray_ready.wait(10), "tray ready"
        window.destroy()  # Same closing event as Alt+F4 / OS close; it must cancel destruction.
        time.sleep(.4)
        assert not window.native.Visible
        assert not window.events.closed.is_set()
        report["checks"].append("OS close hides window without exiting")
        bridge._tray.menu.items[0](bridge._tray)
        time.sleep(.3)
        assert window.native.Visible
        report["checks"].append("Tray Open callback restores window")
        assert bridge.hide_window()["ok"]
        assert not window.native.Visible
        report["checks"].append("Custom close button hides window")
        bridge._tray.menu.items[0](bridge._tray)
        js("$('sourceText').value='__slow__'; translate(); true")
        wait("state.busy")
        time.sleep(.2)
        report["checks"].append("Exit tested with a network request still waiting")
    except Exception:
        report["errors"].append(traceback.format_exc())
    finally:
        if bridge._tray:
            bridge._tray.menu.items[-1](bridge._tray)
        else:
            bridge._allow_exit = True
            window.destroy()


with patch("translator.urllib.request.urlopen", side_effect=simulated_response):
    run(store, started)
report["checks"].append("Tray Exit callback shuts down GUI")
(ROOT / ".qa" / "desktop-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(bool(report["errors"]))
