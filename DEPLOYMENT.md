# YouTube 字幕提取工具 - 部署指南

## ⚠️ 重要更新：YouTube Bot Detection 修復方案 (2025)

YouTube 現在需要 PO Token（Proof-of-Origin Token）來繞過機器人檢測。本專案已整合解決方案。

### 新增服務架構：
```
前端: subtitles.kokonut.us.kg → Cloudflare Pages
API:  api.kokonut.us.kg → Render (Python FastAPI)
PO Token Provider: youtube-pot-provider → Render (Docker)  ← 新增
```

**必須先部署 PO Token Provider，否則會出現 "Sign in to confirm you're not a bot" 錯誤！**

詳細說明見下方 **步驟 2.5：部署 PO Token Provider**

---

## 架構概覽

```
前端: subtitles.kokonut.us.kg → Cloudflare Pages
API:  api.kokonut.us.kg → Render (Python FastAPI)
```

---

## 部署步驟

### 1️⃣ **前置準備**

#### 所需帳戶：
- GitHub 帳號
- Render.com 帳號（免費層）
- Cloudflare 帳號（已有 kokonut.us.kg）

---

### 2️⃣ **部署後端到 Render**

#### Step A: 推送到 GitHub
```bash
git push origin main
```

#### Step B: 在 Render 上建立新 Web Service
1. 訪問 https://dashboard.render.com/
2. 點擊 "New +" → "Web Service"
3. 連接你的 GitHub 倉庫
4. 配置：
   - **Name**: `youtube-subtitle-extractor-api`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - **Region**: 選擇離你最近的地區
   - **Plan**: Free
5. 點擊 "Create Web Service"

#### Step C: 獲取 API URL
部署完成後，你會得到類似這樣的 URL：
```
https://youtube-subtitle-extractor-api.onrender.com
```

記下這個 URL，稍後會用到。

---

### 2️⃣.5 **部署 PO Token Provider 到 Render** ⚠️ 必要步驟

#### 為什麼需要這個服務？
YouTube 在 2024-2025 開始強制要求 PO Token 來防止機器人，沒有這個服務會出現：
```
ERROR: [youtube] Sign in to confirm you're not a bot
```

#### Step A: 在 Render 上建立 Docker Web Service
1. 訪問 https://dashboard.render.com/
2. 點擊 "New +" → "Web Service"
3. **選擇 "Deploy an existing image from a registry"**
4. 配置基本資訊：
   - **Image URL**: `brainicism/bgutil-ytdlp-pot-provider:latest`
   - **Name**: `youtube-pot-provider`
   - **Region**: 選擇與後端相同的地區（降低延遲）
   - **Plan**: Free（建議升級到 $7/月以避免 cold start）
5. 向下滾動到 **Advanced** 部分
6. 添加環境變數（Environment Variables）：
   - **Key**: `PORT`
   - **Value**: `4416`
7. 點擊 "Create Web Service"

#### Step B: 等待部署完成
部署完成後，你會得到類似這樣的 URL：
```
https://youtube-pot-provider.onrender.com
```
**記下這個 URL，下一步會用到！**

#### Step C: 在後端服務添加環境變數
1. 返回你的後端服務（`youtube-subtitle-extractor-api`）
2. 進入 "Environment" 標籤
3. 點擊 "Add Environment Variable"
4. 添加：
   - **Key**: `POT_PROVIDER_URL`
   - **Value**: `https://youtube-pot-provider.onrender.com`（使用你的實際 URL）
5. 保存後，後端會自動重新部署

#### Step D: 驗證配置
在後端的 logs 中，應該能看到：
```
INFO: Extracting subtitles from: https://www.youtube.com/watch?v=...
[youtube] Extracting URL: ...
```
而不是 bot detection 錯誤。

---

### 3️⃣ **部署前端到 Cloudflare Pages**

#### Step A: 在 Cloudflare 上建立 Pages 專案
1. 登錄 https://dash.cloudflare.com/
2. 選擇你的域名 `kokonut.us.kg`
3. 在左側選擇 "Pages"
4. 點擊 "Connect to Git"
5. 授權 GitHub，選擇你的倉庫
6. 配置：
   - **Project Name**: `youtube-subtitle-extractor`
   - **Branch**: `main`
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Build Output Directory**: `frontend/dist`

#### Step B: 設置環境變數
1. 在 Pages 項目設置中，找到 "Environment"
2. 添加環境變數：
   ```
   VITE_API_URL = https://youtube-subtitle-extractor-api.onrender.com
   ```

#### Step C: 設置自定義域名
1. 在 Pages 項目設置中，找到 "Custom Domains"
2. 添加自定義域名：
   ```
   subtitles.kokonut.us.kg
   ```

   注意：Cloudflare Pages 自動設置 DNS 記錄，無需手動添加。

---

### 4️⃣ **配置 DNS 和 CORS**

#### 在 Cloudflare DNS 中添加 API 子域名：
1. 登錄 Cloudflare
2. 選擇 `kokonut.us.kg`
3. 進入 "DNS"
4. 添加 A 記錄（或 CNAME）：
   - **Name**: `api`
   - **Type**: `CNAME`
   - **Content**: `youtube-subtitle-extractor-api.onrender.com`
   - **TTL**: Auto
   - **Proxy Status**: DNS Only（灰雲）

#### 配置 CORS（在後端 app/main.py 中）：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://subtitles.kokonut.us.kg"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### 5️⃣ **可選：設置 Cloudflare Workers（用於 API 路由）**

如果未來想添加多個 API 服務，可以使用 Cloudflare Workers 作為路由層：

```javascript
// wrangler.toml
[env.production]
name = "api-gateway"
routes = [
  { pattern = "api.kokonut.us.kg/*", zone_name = "kokonut.us.kg" }
]
```

---

## 測試部署

### 測試前端
訪問：`https://subtitles.kokonut.us.kg`

### 測試後端 API
```bash
curl https://api.kokonut.us.kg/health
```

應該返回：
```json
{
  "status": "ok",
  "timestamp": "2025-10-31T12:00:00"
}
```

---

## CI/CD 自動部署

已配置 GitHub Actions（`.github/workflows/deploy.yml`），每次 push 到 main 分支時：
1. 自動構建並部署前端到 Cloudflare Pages
2. 自動部署後端到 Render

需要設置 GitHub Secrets：
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `RENDER_SERVICE_ID`
- `RENDER_API_KEY`

---

## 故障排查

### ⚠️ YouTube Bot Detection 錯誤（最常見）

**症狀**：出現 `ERROR: [youtube] Sign in to confirm you're not a bot`

**解決方法**：
1. 確認 PO Token Provider 服務正在運行：
   ```bash
   curl https://your-pot-provider.onrender.com
   ```
   應該返回服務資訊

2. 檢查後端環境變數 `POT_PROVIDER_URL` 是否正確設置

3. 查看後端 logs 確認是否能連接到 PO Token Provider

4. 如果使用免費層，第一次請求可能需要 30-50 秒啟動時間

5. 確認 yt-dlp 版本 >= 2024.08.06（已在 requirements.txt 中指定）

6. **新增：使用 YouTube Cookies（進階解決方案）**

   如果 PO Token Provider 仍然無法解決問題，可以添加 YouTube cookies：

   **方法 A：使用 Cookie 檔案**
   1. 在本地瀏覽器登入 YouTube
   2. 使用瀏覽器擴充功能匯出 cookies（如 "Get cookies.txt LOCALLY"）
   3. 將 `cookies.txt` 上傳到安全位置（如 Render 的 Persistent Disk 或環境變數）
   4. 在 Render 環境變數中添加：
      - **Key**: `YOUTUBE_COOKIES_FILE`
      - **Value**: `/path/to/cookies.txt`

   **方法 B：在本地開發時使用瀏覽器 Cookies**
   - 本地開發時，後端會自動嘗試從 Chrome 讀取 cookies
   - 確保 Chrome 已登入 YouTube
   - 不需要額外配置

   **注意事項**：
   - Cookie 檔案包含敏感資訊，請妥善保管
   - Cookie 可能會過期，需要定期更新
   - 使用 cookies 違反 YouTube TOS，僅供個人使用

### PO Token Provider 無回應

**症狀**：後端無法連接到 PO Token Provider

**解決方法**：
1. Render 免費層會在 15 分鐘後休眠，首次請求會較慢
2. 檢查 Provider 服務的 logs 是否有錯誤
3. 考慮升級到 $7/月 付費層以保持服務始終運行

### 前端無法連接到 API
- 檢查 `.env` 文件中的 `VITE_API_URL`
- 確保後端 URL 正確
- 檢查 CORS 配置

### Render 免費層休眠
- Render 免費層在 15 分鐘無流量後會休眠
- 首次訪問會有 30 秒延遲
- 如需穩定運行，升級到付費層

### DNS 沒有生效
- DNS 變更可能需要 24 小時才能完全生效
- 使用 `nslookup api.kokonut.us.kg` 檢查

---

## 未來擴展

由於使用了模組化架構，添加新工具很簡單：

### 添加新工具示例（圖片轉換）：
```
kokonut.us.kg/
├── subtitles.kokonut.us.kg    ✅ 已有
├── image-converter.kokonut.us.kg
├── video-tools.kokonut.us.kg
└── docs.kokonut.us.kg
```

### 後端 API 路由：
```
api.kokonut.us.kg/
├── /subtitles/*
├── /image-converter/*
└── /video-tools/*
```

---

## 成本估計

### 免費方案（有限制）
| 服務 | 層級 | 每月成本 | 限制 |
|------|------|--------|------|
| Cloudflare Pages | Free | $0 | 無限請求 |
| Cloudflare Workers | Free | $0 | 100k req/day |
| Render - 後端 API | Free | $0 | 15分鐘後休眠 |
| Render - PO Token Provider | Free | $0 | 15分鐘後休眠 |
| 域名 (kokonut.us.kg) | 已有 | $0 | - |
| **總計** | | **$0/月** | ⚠️ 首次請求慢 |

### 推薦生產方案
| 服務 | 層級 | 每月成本 | 優勢 |
|------|------|--------|------|
| Cloudflare Pages | Free | $0 | 無限請求 |
| Render - 後端 API | Starter | $7 | 始終運行 |
| Render - PO Token Provider | Starter | $7 | 始終運行 |
| 域名 (kokonut.us.kg) | 已有 | $0 | - |
| **總計** | | **$14/月** | ✅ 穩定可靠 |

**建議**：至少將 PO Token Provider 升級到付費層（$7/月），因為它是關鍵服務，休眠會導致 bot detection 錯誤。

---

需要幫助？檢查 [README.md](./README.md) 或提交 Issue。
