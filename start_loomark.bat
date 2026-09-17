@echo off
chcp 65001 >nul
title Loomark - AI 协作式内容采集与分析平台
echo ==================================================
echo       Loomark - AI Web Intelligence Engine        
echo ==================================================

if exist .venv\Scripts\python.exe (
    set PYTHON_EXEC=.venv\Scripts\python.exe
) else (
    set PYTHON_EXEC=python
)

echo [*] 正在检查端口 8765 占用情况...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
    echo [*] 清理残留后端服务 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] 正在启动后端爬虫引擎服务 (端口: 8765)...
start "Loomark Engine" /B %PYTHON_EXEC% -m engine.main --port 8765

echo [*] 正在启动桌面端界面 (Vite 端口: 1420)...
call pnpm dev

echo [*] 正在清理后台服务进程...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
