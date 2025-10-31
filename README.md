# YouTube 字幕提取工具

一個簡單易用的 GUI 應用程式，可以從 YouTube 影片中提取字幕。

## 功能特性

- 📥 輸入 YouTube 網址自動提取字幕
- 🌐 支持多語言字幕（優先中文、英文）
- 📋 一鍵複製字幕到剪貼板
- 💾 將字幕保存為 TXT 文件
- 🎨 簡潔直觀的圖形介面
- ⚡ 使用 yt-dlp 獲取最新的 YouTube 支持

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

- **GUI**: Tkinter（Python 內置）
- **YouTube 提取**: yt-dlp
- **HTTP 請求**: requests

## 許可證

MIT License

## 更新日誌

### v1.0.0 (2024-10-31)
- 初始版本發佈
- 基本的字幕提取功能
- 複製和保存功能

## 反饋和貢獻

如有建議或問題，歡迎在 GitHub 上提交 Issue 或 Pull Request。
