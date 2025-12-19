# Google Maps 截圖功能說明

## 📋 功能概述

本功能使用 Playwright 自動化瀏覽器，截取 Google Maps 的完整路線頁面，包含：
- **左側路線面板**：顯示起點、終點、多條路線選項、時間和距離資訊
- **右側地圖**：顯示完整的路線地圖

輸出結果與在瀏覽器中按 PrintScreen 的效果相同。

## 🔧 安裝步驟

### 1. 安裝 Playwright

```bash
pip install playwright
```

### 2. 安裝瀏覽器

安裝 Playwright 後，需要下載 Chromium 瀏覽器：

```bash
playwright install chromium
```

**注意**：首次安裝會下載約 100-200 MB 的瀏覽器檔案，需要一些時間。

### 3. 驗證安裝

執行以下命令驗證安裝是否成功：

```bash
python -c "from playwright.sync_api import sync_playwright; print('Playwright 安裝成功！')"
```

## 📝 使用方式

### 自動使用

功能已整合到里程計算流程中。當您呼叫 `/api/calculate/batch` 計算路線時，系統會自動：

1. 嘗試使用 Playwright 截取 Google Maps 完整路線頁面
2. 如果 Playwright 截圖成功，使用該截圖作為 `StaticMapImage`
3. 如果 Playwright 截圖失敗，自動回退使用原本的靜態地圖

### 手動呼叫

如果需要手動截圖，可以使用以下方式：

```python
from services.gmap_screenshot_service import capture_route_screenshot_sync

# 同步版本（推薦）
screenshot_path = capture_route_screenshot_sync(
    origin="804高雄市鼓山區裕誠路1091號",
    destination="832高雄市林園區石化二路10號",
    output_path="output/route_screenshot.png"
)

if screenshot_path:
    print(f"截圖成功: {screenshot_path}")
else:
    print("截圖失敗")
```

## ⚙️ 設定選項

### 視窗大小

預設視窗大小為 1500x750 像素，可以透過參數調整：

```python
screenshot_path = capture_route_screenshot_sync(
    origin="...",
    destination="...",
    output_path="...",
    viewport_width=1500,  # 寬度
    viewport_height=750,   # 高度
    wait_timeout=10000     # 等待超時時間（毫秒）
)
```

## 🐛 疑難排解

### 問題 1: 截圖失敗或超時

**可能原因：**
- Google Maps 無法訪問（網路問題或地區限制）
- 頁面載入時間過長
- Playwright 瀏覽器未正確安裝

**解決方案：**
- 檢查網路連線
- 增加 `wait_timeout` 參數值
- 確認已執行 `playwright install chromium`
- 系統會自動回退使用靜態地圖

### 問題 2: 截圖中沒有左側面板

**可能原因：**
- 頁面載入不完整
- Google Maps 介面變更

**解決方案：**
- 檢查日誌中的錯誤訊息
- 增加等待時間
- 確認視窗大小設定正確

### 問題 3: Playwright 安裝失敗

**解決方案：**
- 確認 Python 版本 >= 3.8
- 檢查系統權限（Windows 可能需要管理員權限）
- 嘗試手動安裝：`python -m playwright install chromium`

## 📊 輸出格式

截圖檔案為 PNG 格式，包含：
- **尺寸**：1500x750 像素（預設）
- **內容**：
  - 左側：路線面板（起點、終點、路線選項、時間/距離）
  - 右側：完整地圖路線

## 🔄 與現有流程整合

### 計算流程

在 `routes/calculate.py` 的 `calculate_batch()` 函式中：

1. 計算路線距離後，會自動呼叫 `capture_route_screenshot_sync()`
2. 如果截圖成功，將截圖路徑存入 `record['StaticMapImage']`
3. 如果截圖失敗，回退使用原本的靜態地圖

### Word 報表生成

在 `services/word_service.py` 的 `generate_report()` 函式中：

1. 檢查 `StaticMapImage` 是否為 Playwright 截圖（檔名包含 `gmap_route`）
2. 如果是 Playwright 截圖，直接使用（已包含左側面板和距離資訊）
3. 如果是舊的靜態地圖，可選擇疊加距離資訊框

## ⚠️ 注意事項

1. **網路需求**：需要能夠訪問 Google Maps
2. **執行時間**：每次截圖約需 5-10 秒（取決於網路速度）
3. **資源使用**：Playwright 會啟動 headless 瀏覽器，需要一定的系統資源
4. **自動回退**：如果 Playwright 失敗，系統會自動使用原本的靜態地圖功能

## 📞 技術支援

如有問題，請檢查：
1. `logs/app.log` 日誌檔案
2. Playwright 是否正確安裝
3. 網路連線是否正常
4. Google Maps 是否可以正常訪問

