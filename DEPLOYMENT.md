# YouTube 字幕提取工具 - 部署指南

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

| 服務 | 層級 | 每月成本 |
|------|------|--------|
| Cloudflare Pages | Free | $0 |
| Cloudflare Workers | Free (100k req/day) | $0 |
| Render | Free | $0 |
| 域名 (kokonut.us.kg) | 已有 | $0 |
| **總計** | | **$0/月** ✅ |

---

需要幫助？檢查 [README.md](./README.md) 或提交 Issue。
