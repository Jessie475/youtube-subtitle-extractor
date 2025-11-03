# YouTube 字幕提取工具

一個簡單易用的 GUI 應用程式，可以從 YouTube 影片中提取字幕。

## 功能特性

- 📥 輸入 YouTube 網址自動提取字幕
- 🌐 支持多語言字幕（優先中文、英文）
- 📋 一鍵複製字幕到剪貼板
- 💾 將字幕保存為 TXT 文件
- 🎨 現代化的網頁介面
- ⚡ 使用 YouTube 官方 InnerTube API，可靠性高
- 🔄 自動備援機制（InnerTube API 失敗時自動切換至 yt-dlp）

## 系統需求

- Python 3.8+
- macOS / Windows / Linux

## 安裝步驟

### 1. 克隆或進入項目目錄

```bash
cd ~/Desktop/Forfun/youtube-subtitle-extractor
```

### 2. 創建虛擬環境（已有可跳過）

```bash
python3 -m venv venv
```

### 3. 啟動虛擬環境

**macOS / Linux：**
```bash
source venv/bin/activate
```

**Windows：**
```bash
venv\Scripts\activate
```

### 4. 安裝依賴

```bash
pip install -r requirements.txt
```

## 使用方法

### 啟動應用程式

```bash
python main.py
```

### 使用步驟

1. 在文本框中粘貼 YouTube 網址
2. 點擊「提取字幕」按鈕
3. 等待字幕加載（可能需要數秒）
4. 字幕加載成功後，可以：
   - 📋 點擊「複製全部」複製到剪貼板
   - 💾 點擊「儲存為 TXT」保存到本地文件

## 支持的 YouTube 網址格式

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/watch?v=VIDEO_ID&t=123s`

## 故障排除

### ⚠️ YouTube Bot Detection（機器人檢測）

**症狀**：出現 `ERROR: [youtube] Sign in to confirm you're not a bot`

這是 YouTube 最新的反爬蟲機制。**解決方案**：

1. **本地開發**：後端會自動嘗試使用 Chrome 瀏覽器的 cookies
   - 確保 Chrome 已登入 YouTube
   - 在登入狀態下重新啟動後端

2. **生產環境**：需要使用 Cookie 檔案
   - 從瀏覽器匯出 cookies（使用擴充功能如 "Get cookies.txt LOCALLY"）
   - 設置環境變數 `YOUTUBE_COOKIES_FILE=/path/to/cookies.txt`
   - 參考 [DEPLOYMENT.md](./DEPLOYMENT.md) 獲取詳細說明

3. **確保 PO Token Provider 運行**（已部署的情況）
   - 檢查 `POT_PROVIDER_URL` 環境變數

### 無法提取字幕

- 確保 YouTube 影片有字幕（手動上傳或自動生成）
- 某些私人或受限制的影片可能無法提取
- 檢查網絡連接

### 虛擬環境問題

如果虛擬環境無法激活，嘗試重新創建：

```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 技術棧

### Frontend
- **框架**: React + Vite
- **樣式**: Tailwind CSS
- **部署**: Cloudflare Pages

### Backend
- **框架**: FastAPI
- **字幕提取**:
  - 主要方法：youtube-transcript-api（使用 YouTube InnerTube API）
  - 備用方法：yt-dlp（當 InnerTube API 無法使用時）
- **部署**: Render.com

## 許可證

MIT License

## 更新日誌

### v1.1.0 (2025-11-04)
- 🎯 採用 YouTube InnerTube API 作為主要字幕提取方法
- 🔄 實作智能雙重備援策略（InnerTube API → yt-dlp）
- 🛡️ 自動處理雲端環境 IP 封鎖問題
- ⚡ 本地開發環境提升提取速度
- 🐛 改善錯誤處理和日誌記錄

### v1.0.0 (2024-10-31)
- 初始版本發佈
- 基本的字幕提取功能
- 複製和保存功能

## 反饋和貢獻

如有建議或問題，歡迎在 GitHub 上提交 Issue 或 Pull Request。
