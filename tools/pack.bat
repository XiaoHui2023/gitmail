@echo off
setlocal EnableExtensions
rem Pack onefile via PyInstaller; builds frontend/dist first; no staticx on Windows. ASCII rem only.
rem Usage from repo root: tools\pack.bat [src]
rem Outputs: dist\gitmail.exe and dist\gitmail-<version>-windows.zip
rem Spec: gitmail-cli.spec builds gitmail.exe
cd /d "%~dp0\.."

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=src"

if not exist ".venv\Scripts\python.exe" (
    echo 未找到 .venv，正在创建 ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo 错误: 无法创建 .venv，请确认已安装 Python。
        exit /b 1
    )
)

set "PY=%CD%\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo 错误: 未找到 %PY%
    exit /b 1
)

echo ==^> 使用虚拟环境: %PY%
"%PY%" -V

"%PY%" -m pip install -q -U pip setuptools wheel
if errorlevel 1 exit /b 1
"%PY%" -m pip install -q --upgrade --force-reinstall -e .
if errorlevel 1 exit /b 1
"%PY%" -m pip install -q --upgrade --force-reinstall "pyinstaller>=6.0"
if errorlevel 1 exit /b 1

echo ==^> 构建前端 frontend\dist
where npm >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 npm，无法构建 frontend\dist。
    exit /b 1
)
pushd frontend
call npm install
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1
popd

if /I not "%TARGET%"=="src" (
    echo 用法: tools\pack.bat [src] >&2
    exit /b 1
)

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

set "SPEC=%CD%\gitmail-cli.spec"
if not exist "%SPEC%" (
    echo 错误: 未找到 %SPEC% >&2
    exit /b 1
)

echo ==^> PyInstaller: %SPEC%
"%PY%" -m PyInstaller --clean --noconfirm "%SPEC%"
if errorlevel 1 exit /b 1

if exist "%CD%\dist\gitmail.exe" (
    echo 完成: %CD%\dist\gitmail.exe（Windows：无 staticx 步骤）
) else (
    echo 错误: 未在 dist 找到 gitmail.exe。 >&2
    exit /b 1
)

echo ==^> 组装发布压缩包
"%PY%" tools\bundle_release.py
if errorlevel 1 exit /b 1

echo PyInstaller 输出目录: %CD%\dist
exit /b 0
