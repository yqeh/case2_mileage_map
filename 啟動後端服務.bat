@echo off
chcp 65001 >nul
title 後端服務 - Case 2 里程地圖系統
color 0A

echo ========================================
echo   啟動後端服務
echo   Case 2: 地點里程與地圖報表系統
echo ========================================
echo.

REM 切換到後端目錄
cd /d "%~dp0backend"
if errorlevel 1 (
    echo ❌ 錯誤：無法切換到後端目錄
    pause
    exit /b 1
)

REM 檢查目錄
if not exist "temp\maps" mkdir temp\maps
if not exist "output" mkdir output
if not exist "logs" mkdir logs

REM 檢查 .env 檔案
if not exist ".env" (
    echo ⚠️  警告：找不到 .env 檔案
    echo 正在從範本建立 .env 檔案...
    if exist "env_template.txt" (
        copy env_template.txt .env >nul
        echo ✅ 已建立 .env 檔案，請記得設定 Google Maps API Key
    ) else (
        echo ❌ 錯誤：找不到 env_template.txt
    )
    echo.
)

echo ✅ 環境檢查完成
echo.
echo ========================================
echo   服務資訊
echo ========================================
echo   服務地址: http://localhost:5001
echo   健康檢查: http://localhost:5001/health
echo   API 端點: http://localhost:5001/api
echo.
echo ========================================
echo   正在啟動服務...
echo ========================================
echo.
echo 💡 提示：按 Ctrl+C 可停止服務
echo.
echo ========================================
echo.

REM 啟動服務
py app.py

REM 如果服務意外停止，顯示訊息
echo.
echo ========================================
echo   服務已停止
echo ========================================
echo.
pause




