@echo off
chcp 65001 >nul
title Loomark - Web Intelligence Engine

cd /d "%~dp0"

if exist .venv\Scripts\python.exe (
    set PYTHON_EXEC=.venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

netstat -ano | findstr ":8765" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [*] 正在启动后端引擎服务 (127.0.0.1:8765)...
    start "Loomark Engine" /B %PYTHON_EXEC% -m engine.main --port 8765
    timeout /t 2 /nobreak >nul
) else (
    echo [*] 后端引擎已在运行中 (127.0.0.1:8765)
)

echo [*] 正在启动 Loomark 桌面客户端...
start "" "dist_release\Loomark_Portable.exe"
