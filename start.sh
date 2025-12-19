#!/bin/bash
# Linux/Mac 啟動腳本

echo "啟動 Case 2 後端服務..."
echo ""

# 檢查虛擬環境
if [ -f "venv/bin/activate" ]; then
    echo "啟動虛擬環境..."
    source venv/bin/activate
fi

# 建立必要目錄
mkdir -p temp/maps
mkdir -p output
mkdir -p logs

# 啟動服務
echo "啟動 Flask 服務在 http://localhost:5001"
echo "按 Ctrl+C 停止服務"
echo ""
python app.py








