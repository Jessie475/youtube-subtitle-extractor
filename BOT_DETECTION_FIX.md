# YouTube Bot Detection 修復方案

## 問題

您遇到的錯誤：
```
ERROR: [youtube] 7DOnMQAT_cU: Sign in to confirm you're not a bot. This helps protect our community.
```

這是因為 YouTube 在 2024-2025 年加強了機器人檢測，現在要求 **PO Token（Proof-of-Origin Token）** 才能正常訪問。

## 解決方案概要

已實施三個關鍵更改：

### 1️⃣ 更新 Backend 依賴

**檔案**: [backend/requirements.txt](backend/requirements.txt)

```diff
- yt-dlp==2024.11.4
+ yt-dlp>=2025.05.22
+ bgutil-ytdlp-pot-provider>=2024.0.0
```

**說明**：
- 升級 yt-dlp 到支援 PO Token 的版本
- 添加 PO Token 提供器插件

### 2️⃣ 更新 Backend 配置

**檔案**: [backend/app/main.py](backend/app/main.py#L78-L98)

```python
# 新增：從環境變數讀取 PO Token Provider URL
pot_provider_url = os.getenv("POT_PROVIDER_URL", "http://localhost:4416")

ydl_opts = {
    # ... 其他配置 ...
    "extractor_args": {
        "youtube": {
            "player_client": ["ios", "android", "mweb"],  # 添加 mweb
            "skip": ["hls", "dash"]
        },
        # 新增：配置 PO Token Provider
        "youtubepot-bgutilhttp": {
            "base_url": pot_provider_url
        }
    }
}
```

**說明**：
- 添加對 `POT_PROVIDER_URL` 環境變數的支援
- 配置 yt-dlp 使用 PO Token Provider

### 3️⃣ 部署 PO Token Provider 服務

**需要在 Render 上部署新服務**

**使用的 Docker 映像**: `brainicism/bgutil-ytdlp-pot-provider:latest`

## 部署步驟（快速版）

### Step 1: 在 Render 部署 PO Token Provider

1. 前往 [Render Dashboard](https://dashboard.render.com/)
2. New + → Web Service
3. **選擇 "Deploy an existing image from a registry"**
4. 配置基本資訊：
   - Image URL: `brainicism/bgutil-ytdlp-pot-provider:latest`
   - Name: `youtube-pot-provider`
   - Plan: Free（建議 Starter $7/月）
5. 向下滾動到 **Advanced** 部分
6. 添加環境變數：
   - Key: `PORT`
   - Value: `4416`
7. 點擊 "Create Web Service"
8. 部署完成後，複製服務 URL（例如：`https://youtube-pot-provider.onrender.com`）

### Step 2: 更新後端環境變數

1. 前往您的後端服務頁面
2. Environment 標籤
3. 添加環境變數：
   - Key: `POT_PROVIDER_URL`
   - Value: `https://youtube-pot-provider.onrender.com`（使用您的實際 URL）
4. 保存（會自動重新部署）

### Step 3: 推送代碼更新

```bash
git add .
git commit -m "fix: Add PO Token provider to bypass YouTube bot detection"
git push origin main
```

Render 會自動檢測更改並重新部署後端。

### Step 4: 驗證修復

測試字幕提取：

```bash
curl -X POST https://your-backend.onrender.com/subtitles/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=7DOnMQAT_cU"
  }'
```

檢查後端 logs，應該看到：
- ✅ 成功提取字幕
- ❌ 不再出現 "Sign in to confirm you're not a bot" 錯誤

## 架構圖

```
┌─────────────────────┐
│   Cloudflare Pages  │  前端
│ subtitles.kokonut   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Render FastAPI    │  後端 API
│    (Python)         │
└──────────┬──────────┘
           │
           │ HTTP Request
           ▼
┌─────────────────────┐
│  PO Token Provider  │  ← 新增服務
│   (Docker/Node.js)  │
└─────────────────────┘
           │
           │ 生成 PO Token
           ▼
      YouTube API
```

## 注意事項

### 免費層限制

如果使用 Render 免費層：
- 服務會在 15 分鐘無活動後休眠
- 第一次請求需要 30-50 秒喚醒
- 可能導致首次字幕提取失敗

**建議**：至少將 PO Token Provider 升級到 $7/月 Starter 方案

### 成功率

- PO Token 可以顯著提高成功率，但不保證 100% 成功
- YouTube 仍可能阻擋頻繁請求
- 如果仍遇到問題，可能需要：
  - 使用代理服務
  - 實施請求重試邏輯
  - 添加請求間隔限制

## 故障排查

### 問題 1: 仍然出現 bot detection 錯誤

**檢查清單**：
- [ ] PO Token Provider 服務正在運行
- [ ] `POT_PROVIDER_URL` 環境變數已正確設置
- [ ] 後端已重新部署並應用了新代碼
- [ ] yt-dlp 版本 >= 2025.05.22

**測試 Provider**：
```bash
curl https://your-pot-provider.onrender.com
```

### 問題 2: Provider 服務超時

**原因**：免費層服務休眠

**解決方法**：
1. 等待 30-50 秒讓服務喚醒
2. 升級到付費層
3. 實施 warmup 機制（定期 ping 服務）

### 問題 3: 後端無法連接到 Provider

**檢查**：
1. Provider URL 是否正確（包括 https://）
2. 兩個服務是否都在運行
3. 查看後端 logs 的連接錯誤訊息

## 參考資源

- [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- [bgutil-ytdlp-pot-provider GitHub](https://github.com/Brainicism/bgutil-ytdlp-pot-provider)
- [完整部署指南](./DEPLOYMENT.md)

## 技術細節

### PO Token 是什麼？

PO Token（Proof-of-Origin Token）是 YouTube 要求的驗證參數，用於：
- 驗證請求來自合法客戶端
- 防止自動化抓取
- 保護 YouTube 基礎設施

### bgutil-ytdlp-pot-provider 如何工作？

1. Provider 服務使用 LuanRT 的 Botguard 庫
2. 生成符合 YouTube 要求的 PO Token
3. yt-dlp 在請求時自動使用這些 token
4. 使流量看起來像真實用戶訪問

## 成本

| 配置 | 月費 | 適用場景 |
|------|------|---------|
| 全免費層 | $0 | 測試/低流量 |
| Provider 付費 | $7 | 推薦方案 |
| 全付費層 | $14 | 生產環境 |

---

需要幫助？查看 [DEPLOYMENT.md](./DEPLOYMENT.md) 或提交 Issue。
