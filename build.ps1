param(
    [string]$PythonExe = '',
    [switch]$Installer,
    [string]$InnoSetupCompiler = ''
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path '.venv\Scripts\python.exe')) {
        if ($PythonExe) { & $PythonExe -m venv .venv }
        else { py -3 -m venv .venv }
        if ($LASTEXITCODE -ne 0) { throw '无法创建 Python 环境，请先安装官方 Windows Python 3.12 或更新版本。' }
    }
    $taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    & $taskPython -m pip install --disable-pip-version-check --index-url https://pypi.org/simple -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
    & $taskPython tools\generate_icon.py
    if ($LASTEXITCODE -ne 0) { throw '图标生成失败' }
    & $taskPython -m PyInstaller --noconfirm --clean TranslatorByGPT.spec
    if ($LASTEXITCODE -ne 0) { throw '打包失败' }
    Write-Host '构建完成：dist\TranslatorByGPT.exe'
    if ($Installer) {
        if (-not $InnoSetupCompiler) {
            $compilerCandidates = @(
                (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 7\ISCC.exe'),
                (Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe'),
                (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
                (Join-Path $PSScriptRoot '.build-tmp\installer-tools\inno\ISCC.exe')
            )
            $InnoSetupCompiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        }
        if (-not $InnoSetupCompiler) { throw '请先安装 Inno Setup，或通过 -InnoSetupCompiler 指定 ISCC.exe 的位置。' }
        & $InnoSetupCompiler installer\TranslatorByGPT.iss
        if ($LASTEXITCODE -ne 0) { throw '安装包构建失败' }
        Write-Host '安装包构建完成：dist\TranslatorByGPT-Setup-1.0.0-x64.exe'
    }
}
finally { Pop-Location }
