# Google Maps 截圖功能使用說明

## 📋 概述

本功能使用 Playwright 自動截取 Google Maps 的完整路線頁面，包含：
- **左側路線面板**：顯示起點、終點、多條路線選項，每條路線的時間和距離
- **右側地圖**：顯示完整的地圖路線

## 🔧 安裝步驟

### 1. 安裝 Playwright

```bash
pip install playwright
```

### 2. 安裝瀏覽器

```bash
playwright install chromium
```

**注意**：首次安裝需要下載瀏覽器（約 100-200MB），需要網路連線。

### 3. 驗證安裝

```bash
python -c "from playwright.sync_api import sync_playwright; print('Playwright 安裝成功')"
```

## 📦 功能說明

### 主要函數

#### `capture_route_screenshot_sync()`

同步版本的截圖函數，可在現有的同步程式碼中直接呼叫。

**參數：**
- `origin`: 起點地址或名稱
- `destination`: 終點地址或名稱
- `output_path`: 輸出圖片路徑
- `viewport_width`: 瀏覽器視窗寬度（預設 1500）
- `viewport_height`: 瀏覽器視窗高度（預設 750）
- `wait_timeout`: 等待頁面載入的超時時間（毫秒，預設 10000）

**回傳值：**
- 成功：截圖檔案路徑（字串）
- 失敗：`None`

### 使用範例

```python
from services.gmap_screenshot_service import capture_route_screenshot_sync
from pathlib import Path

# 截取 Google Maps 路線截圖
screenshot_path = capture_route_screenshot_sync(
    origin="804高雄市鼓山區裕誠路1091號",
    destination="832高雄市林園區石化二路10號",
    output_path="temp/maps/route_screenshot.png",
    viewport_width=1500,
    viewport_height=750
)

if screenshot_path:
    print(f"截圖成功: {screenshot_path}")
else:
    print("截圖失敗，使用備用方案")
```

## 🔄 整合流程

### 在計算距離時自動截圖

在 `routes/calculate.py` 的 `calculate_batch()` 函數中，已經整合了截圖功能：

1. **優先使用 Playwright 截圖**：
   - 呼叫 `capture_route_screenshot_sync()` 截取完整 Google Maps 頁面
   - 包含左側路線面板和右側地圖

2. **Fallback 機制**：
   - 如果 Playwright 截圖失敗，自動回退使用原本的靜態地圖 API
   - 確保即使截圖失敗，系統仍可正常運作

3. **儲存路徑**：
   - 截圖儲存在 `temp/maps/` 目錄
   - 檔名格式：`gmap_route_YYYYMMDD_HHMMSS_mmm.png`
   - 路徑會儲存在記錄的 `StaticMapImage` 欄位

### 在 Word 報表中使用

`WordService.generate_report()` 會自動檢測圖片類型：

- **Playwright 截圖**（檔名包含 `gmap_route`）：
  - 直接使用，不需要疊加資訊框
  - 使用較大的寬度（4.5 英吋）以完整顯示

- **靜態地圖**（舊格式）：
  - 會自動疊加距離資訊框
  - 使用較小的寬度（3.5 英吋）

## ⚙️ 設定選項

### 視窗大小

預設視窗大小為 1500 x 750，可以根據需求調整：

```python
screenshot_path = capture_route_screenshot_sync(
    origin=origin,
    destination=destination,
    output_path=output_path,
    viewport_width=1600,  # 調整寬度
    viewport_height=800,  # 調整高度
)
```

### 等待時間

如果網路較慢或 Google Maps 載入較慢，可以增加等待時間：

```python
screenshot_path = capture_route_screenshot_sync(
    origin=origin,
    destination=destination,
    output_path=output_path,
    wait_timeout=15000,  # 增加到 15 秒
)
```

## 🐛 疑難排解

### 問題 1: 截圖失敗，回退使用靜態地圖

**可能原因：**
- Google Maps 無法連線
- 頁面載入超時
- Playwright 瀏覽器未正確安裝

**解決方案：**
1. 檢查網路連線
2. 確認 Playwright 已正確安裝：`playwright install chromium`
3. 檢查日誌檔案查看詳細錯誤訊息

### 問題 2: 截圖中沒有左側面板

**可能原因：**
- 頁面載入時間不足
- Google Maps 介面變更

**解決方案：**
1. 增加等待時間：`wait_timeout=15000`
2. 檢查日誌確認是否有警告訊息
3. 手動測試 Google Maps URL 是否正常

### 問題 3: 截圖空白或只有部分內容

**可能原因：**
- 視窗大小不適合
- 頁面元素未完全載入

**解決方案：**
1. 調整視窗大小
2. 增加等待時間
3. 檢查日誌確認載入狀態

## 📝 注意事項

1. **首次執行較慢**：第一次執行時，Playwright 需要啟動瀏覽器，可能需要 10-20 秒
2. **記憶體使用**：每個瀏覽器實例約使用 100-200MB 記憶體
3. **並發限制**：建議不要同時開啟太多瀏覽器實例（建議最多 3-5 個）
4. **網路需求**：需要能夠連接到 Google Maps
5. **Fallback 機制**：即使截圖失敗，系統仍會使用靜態地圖，不會中斷流程

## ✅ 檢查清單

- [ ] 已安裝 `playwright` Python 套件
- [ ] 已執行 `playwright install chromium`
- [ ] 可以成功匯入 `gmap_screenshot_service`
- [ ] 測試截圖功能可以正常運作
- [ ] 截圖包含左側路線面板和右側地圖
- [ ] Fallback 機制正常運作

