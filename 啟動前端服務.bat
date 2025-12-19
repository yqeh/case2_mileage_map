@echo off
chcp 65001 >nul
title 前端服務 - Case 2 里程地圖系統
color 0A

echo ========================================
echo   啟動前端服務
echo   Case 2: 地點里程與地圖報表系統
echo ========================================
echo.

REM 檢查 Python 是否可用（先嘗試 py，再嘗試 python）
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ 錯誤：找不到 Python
        echo 請先安裝 Python 3.7 或以上版本
        pause
        exit /b 1
    )
    set PYTHON_CMD=python
) else (
    set PYTHON_CMD=py
)

REM 切換到專案根目錄
cd /d "%~dp0"

echo ✅ 環境檢查完成
echo.
echo ========================================
echo   前端服務資訊
echo ========================================
echo   前端地址: http://localhost:3200
echo   後端 API: http://localhost:5001/api
echo.
echo ========================================
echo   正在啟動前端服務...
echo ========================================
echo.

REM 等待一秒後自動開啟瀏覽器
timeout /t 1 /nobreak >nul
start http://localhost:3200/index.html

echo 💡 提示：按 Ctrl+C 可停止服務
echo.
echo ========================================
echo.

REM 啟動簡單的 HTTP 伺服器
%PYTHON_CMD% -m http.server 3200

REM 如果服務意外停止，顯示訊息
echo.
echo ========================================
echo   服務已停止
echo ========================================
echo.
pause
