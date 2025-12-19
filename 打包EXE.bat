@echo off
chcp 65001 >nul
echo ========================================
echo Case 2: 地點里程與地圖報表系統 - 打包成 EXE
echo ========================================
echo.

REM 檢查 PyInstaller 是否安裝
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [錯誤] 未安裝 PyInstaller
    echo 正在安裝 PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [錯誤] PyInstaller 安裝失敗
        pause
        exit /b 1
    )
)

echo [資訊] 開始打包...
echo.

REM 執行打包
pyinstaller build_exe.spec

if errorlevel 1 (
    echo.
    echo [錯誤] 打包失敗，請檢查錯誤訊息
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo [成功] 打包完成！
    echo ========================================
    echo.
    echo EXE 檔案位置: dist\Case2_里程地圖系統.exe
    echo.
    echo 您可以將 dist 目錄複製到任何位置使用
    echo.
    pause
)

