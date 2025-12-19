# Playwright 安裝說明

## 📦 安裝步驟

### 1. 安裝 Playwright Python 套件

```bash
pip install playwright
```

### 2. 安裝 Playwright 瀏覽器

安裝完成後，需要下載瀏覽器執行檔：

```bash
playwright install chromium
```

或者安裝所有瀏覽器：

```bash
playwright install
```

### 3. 驗證安裝

```bash
python -c "from playwright.sync_api import sync_playwright; print('Playwright 安裝成功')"
```

## ⚙️ 系統需求

- **Windows**: 需要 Windows 10 或更高版本
- **Python**: Python 3.8 或更高版本
- **網路連線**: 需要連接到 Google Maps（首次安裝瀏覽器時也需要網路）

## 🔧 疑難排解

### 問題 1: `playwright install` 失敗

**可能原因：**
- 網路連線問題
- 防火牆阻擋

**解決方案：**
- 檢查網路連線
- 使用代理伺服器（如果需要）
- 手動下載瀏覽器：https://playwright.dev/python/docs/browsers

### 問題 2: 執行時出現 "Executable doesn't exist"

**解決方案：**
```bash
playwright install chromium --force
```

### 問題 3: 在 Linux 伺服器上執行

如果是在 Linux 伺服器上執行，可能需要安裝額外的依賴：

```bash
# Ubuntu/Debian
sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

# CentOS/RHEL
sudo yum install -y nss atk cups-libs libdrm libxkbcommon libXcomposite libXdamage libXfixes libXrandr mesa-libgbm alsa-lib
```

## 📝 注意事項

1. **首次執行較慢**：第一次執行時，Playwright 需要啟動瀏覽器，可能會比較慢
2. **記憶體使用**：每個瀏覽器實例會使用約 100-200MB 記憶體
3. **並發限制**：建議不要同時開啟太多瀏覽器實例（建議最多 3-5 個）

## ✅ 安裝檢查清單

- [ ] 已安裝 `playwright` Python 套件
- [ ] 已執行 `playwright install chromium`
- [ ] 可以成功匯入 `playwright`
- [ ] 測試截圖功能可以正常運作
