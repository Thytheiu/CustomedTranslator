# 译间 · 中英互译

Windows 桌面翻译工具。前端使用 pywebview / WebView2，固定连接 DeepSeek 官方接口，只提供中文与英文互译。

## 直接使用

前往 [Release 下载页](https://github.com/Thytheiu/CustomedTranslator/releases/latest)：

- `TranslatorByGPT-Setup-1.0.0-x64.exe`：安装版，按提示安装后从开始菜单打开“译间”，可在 Windows 设置中卸载。
- `TranslatorByGPT-Portable-1.0.0-x64.zip`：免安装版，解压后双击 `TranslatorByGPT.exe`。
- `SHA256SUMS.txt`：上述文件的 SHA-256 校验值。

首次打开会引导填写 DeepSeek API Key、模型 ID 和思考强度。可以关闭引导先查看界面，首次翻译前仍需填写密钥。安装包和免安装包都不包含 API Key 或个人设置。

- 模型 ID 可自由填写，默认 `deepseek-flash`。
- 思考强度：关闭、低、高、极高，对应 `none`、`low`、`high`、`max`。
- 点击中间的双向箭头交换语言；已有完整译文时，同时交换原文和译文。
- `Ctrl + Enter` 开始翻译；译文逐步显示，可以停止、复制。
- 每次最多输入 20,000 个字符。若服务端截断输出，会明确标注未完成。
- 最小化按钮正常最小化；关闭按钮和 `Alt + F4` 都只隐藏到托盘。
- 点击托盘图标或右键选择“打开译间”恢复窗口；只有托盘右键菜单中的“退出程序”会正常退出。

API Key 只需填写并保存一次，之后启动自动读取，不再弹出填写引导。密钥使用 Windows 当前用户的 DPAPI 加密，保存于 `%APPDATA%\TranslatorByGPT\settings.json`；不随 exe 分发，不写入翻译历史。设置页会显示“密钥已保存”，点击“更换”才会展开输入框；留空保存会保留已有密钥。

请求固定发送到 `https://api.deepseek.com/chat/completions`。API Key 的有效性和账户余额在实际翻译时由 DeepSeek 验证；停止后保留已显示的内容，服务端已产生的用量仍按服务商规则计费。

## 系统要求

Windows 10 / 11，64 位，已安装 Microsoft Edge WebView2 Runtime。exe 包含 Python 及应用依赖，无需自行安装 Python。构建产物为一个 exe 文件，可单独移动；首次启动需要短暂解包。

安装版默认安装在当前用户目录，无需管理员权限。升级或卸载前，请通过托盘菜单退出程序。卸载会保留本机设置；需要清除密钥时，可在退出后手动删除 `%APPDATA%\TranslatorByGPT` 文件夹。当前发布文件未做代码签名。

## 从源码运行与构建

建议使用官方 Windows Python 3.12 或更新版本，不使用 MSYS2 Python。

```powershell
# 已有项目环境时
.\.venv\Scripts\python.exe main.py

# 安装依赖并生成单文件 exe
.\build.ps1

# 指定 Python 来创建项目环境
.\build.ps1 -PythonExe 'C:\path\to\python.exe'

# 同时生成安装包（需要 Inno Setup 6.3 或更新版本）
.\build.ps1 -Installer

# 手动指定安装包编译工具
.\build.ps1 -Installer -InnoSetupCompiler 'C:\path\to\ISCC.exe'
```

脚本只在项目 `.venv` 内安装 Python 依赖。单文件程序输出为 `dist\TranslatorByGPT.exe`；加上 `-Installer` 后还会生成 `dist\TranslatorByGPT-Setup-1.0.0-x64.exe`。

## 本地验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\qa_desktop.py
```

单元测试覆盖接口参数、流式内容、截断与错误、取消以及密钥加密读写。桌面测试打开真实 WebView2 窗口，使用隔离设置和模拟响应检查双向翻译、取消、布局、隐藏/恢复及托盘菜单回调；不使用真实密钥，不发出 DeepSeek 请求。

## 代码位置

- `main.py`：窗口、托盘、网页与 Python 之间的连接。
- `translator.py`：固定 DeepSeek 接口和流式翻译。
- `settings.py`：本地设置与 Windows 密钥加密。
- `web/`：界面、交互和矢量图标。
- `tools/generate_icon.py`：生成与界面一致的 PNG / ICO。

接口参数参考 DeepSeek 官方 Chat Completions 与 Thinking Mode 文档（2026-10-29 核对）。
