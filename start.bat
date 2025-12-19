@echo off
REM Windows 啟動腳本
echo 啟動 Case 2 後端服務...
echo.

REM 檢查虛擬環境
if exist venv\Scripts\activate.bat (
    echo 啟動虛擬環境...
    call venv\Scripts\activate.bat
)

REM 建立必要目錄
if not exist temp\maps mkdir temp\maps
if not exist output mkdir output
if not exist logs mkdir logs

REM 啟動服務
echo 啟動 Flask 服務在 http://localhost:5001
echo 按 Ctrl+C 停止服務
echo.
py app.py

pause

