# Creator Sourcing & Outreach Draft Tool / 創作者篩選與聯繫草稿工具

[English](#english) | [繁體中文](#繁體中文)

A compliance-first tool for sourcing creators/influencers and generating outreach drafts.  
合規優先的創作者／網紅篩選與聯繫草稿工具。

---

## 繁體中文

### 專案簡介

這是一個給自由工作者、代理商、出海品牌使用的**創作者篩選輔助工具**。  
它可以協助你：

- 整理公開的創作者資料
- 依粉絲數、互動率、內容調性、受眾地區、報價做加權評分
- 產生 3 版英文聯繫草稿（正式／親切／短版）
- 匯出 CSV / Excel 給客戶
- 提供合作前合規檢查清單

> **重要：本工具不自動私訊、不群發、不爬取登入後或私密資料。所有聯繫草稿都需人工審核後手動發送。**

### 主要功能

- **合規公開網頁爬蟲**：只抓取公開、靜態、`robots.txt` 允許的頁面
- **YouTube Data API v3**：取得頻道公開數據（訂閱數、觀看數、影片數、近似互動率）
- **評分引擎**：粉絲數、互動率、內容關鍵詞、受眾地區、報價加權評分
- **LLM 聯繫草稿**：生成英文正式／親切／短版草稿
- **匯出**：CSV、Excel
- **合規檢查清單**：合作前逐項確認

### 合規邊界

| 可以做 | 不可以做 |
|---|---|
| 抓取公開網頁的標題、描述、OG 標籤 | 抓取登入後頁面、私密資料 |
| 用 YouTube 官方 API 取得頻道公開數據 | 用非官方爬蟲狂抓 YouTube |
| 用 Instagram Graph API 取得已授權商業帳號資料 | 搜尋任意個人帳號、抓取私訊 |
| 用 TikTok Display API 取得當前授權使用者資料 | 用非官方 API 搜尋任意使用者 |
| 手動輸入公開可見的粉絲數、互動率 | 購買名單、爬取私密社群 |
| LLM 生成草稿，人工審核後手動發送 | 自動私訊、群發、批量聯繫 |
| 輸出評分表與草稿給客戶 | 儲存客戶名單或個資到伺服器 |

### 本機部署

```bash
pip install -r requirements.txt
export YOUTUBE_API_KEY="your_youtube_api_key"
export OPENAI_API_KEY="your_openai_api_key"
streamlit run app.py
```

### 部署到 Streamlit Community Cloud

1. 將專案推送到 GitHub（建議 Public repo）
2. 前往 [share.streamlit.io](https://share.streamlit.io)，使用 GitHub 登入
3. 點擊 **Create app**
4. 選擇你的 repo，Branch 選 `main`，Main file path 填 `app.py`
5. 在 **Advanced settings → Secrets** 填入：

```toml
YOUTUBE_API_KEY = "your_youtube_api_key"
OPENAI_API_KEY = "your_openai_api_key"
```

6. 點擊 **Deploy**

> 不要把 API Key 寫死在 `app.py` 或提交到 GitHub。請使用 Streamlit Secrets 或環境變數。

### 放到接案平台

- **Upwork / Fiverr**：作為「創作者篩選＋聯繫草稿」服務的交付工具
- **Gumroad**：作為數位產品出售，附使用說明
- **白標**：讓代理商貼牌，收授權費
- **訂閱制**：每月固定名額，客戶自行使用，你提供支援

### 專案結構

```text
creator-sourcing-tool/
├── app.py                     # Streamlit 主介面
├── scraper.py                 # 合規公開網頁爬蟲
├── social_apis.py             # YouTube / Instagram / TikTok 官方 API
├── scoring.py                 # 評分與篩選引擎
├── draft_generator.py         # LLM 聯繫草稿生成
├── requirements.txt
└── README.md
```

### 授權與免責

本工具僅供合規的公開資料篩選與草稿輔助。  
使用者需自行確保遵守平台條款、當地法律與個資法規。  
開發者不對使用者的資料來源、聯繫行為或商業結果負責。

---

## English

### Overview

A **compliance-first creator sourcing tool** for freelancers, agencies, and brands going global.  
It helps you:

- Organize publicly available creator information
- Score candidates by followers, engagement, content fit, audience region, and price
- Generate three outreach drafts (formal / friendly / short)
- Export CSV / Excel for clients
- Provide a pre-collaboration compliance checklist

> **Important: This tool does NOT auto-DM, bulk-message, or scrape private/logged-in data. All outreach drafts must be reviewed and sent manually.**

### Features

- **Compliant public web scraper**: only public, static pages allowed by `robots.txt`
- **YouTube Data API v3**: public channel stats (subscribers, views, video count, approximate engagement)
- **Scoring engine**: weighted scoring on followers, engagement, content keywords, audience region, and price
- **LLM outreach drafts**: formal / friendly / short English drafts
- **Export**: CSV, Excel
- **Compliance checklist**: confirm before collaboration

### Compliance Boundaries

| Allowed | Not Allowed |
|---|---|
| Scrape public page titles, descriptions, OG tags | Scrape logged-in pages or private data |
| Use YouTube official API for public channel data | Use unofficial scrapers to crawl YouTube heavily |
| Use Instagram Graph API for authorized business accounts | Search arbitrary personal accounts or scrape DMs |
| Use TikTok Display API for the currently authorized user | Use unofficial APIs to search arbitrary users |
| Manually enter publicly visible follower/engagement data | Buy lists or scrape private communities |
| Generate drafts with LLM, review manually, send manually | Auto-DM, bulk messaging, mass outreach |
| Deliver scored sheets and drafts to clients | Store client lists or personal data on a server |

### Local Deployment

```bash
pip install -r requirements.txt
export YOUTUBE_API_KEY="your_youtube_api_key"
export OPENAI_API_KEY="your_openai_api_key"
streamlit run app.py
```

### Deploy to Streamlit Community Cloud

1. Push the project to GitHub (Public repo recommended)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **Create app**
4. Select your repo, set Branch to `main`, and Main file path to `app.py`
5. In **Advanced settings → Secrets**, add:

```toml
YOUTUBE_API_KEY = "your_youtube_api_key"
OPENAI_API_KEY = "your_openai_api_key"
```

6. Click **Deploy**

> Never hardcode API keys in `app.py` or commit them to GitHub. Use Streamlit Secrets or environment variables.

### Selling on Freelance Platforms

- **Upwork / Fiverr**: deliver as a “creator sourcing + outreach draft” service
- **Gumroad**: sell as a digital product with usage instructions
- **White-label**: let agencies rebrand it and pay you a license fee
- **Subscription**: monthly quota, clients use it themselves, you provide support

### Project Structure

```text
creator-sourcing-tool/
├── app.py                     # Streamlit main UI
├── scraper.py                 # Compliant public web scraper
├── social_apis.py             # YouTube / Instagram / TikTok official APIs
├── scoring.py                 # Scoring and filtering engine
├── draft_generator.py         # LLM outreach draft generator
├── requirements.txt
└── README.md
```

### License & Disclaimer

This tool is for compliant public-data sourcing and draft assistance only.  
Users are responsible for complying with platform terms, local laws, and privacy regulations.  
The developer is not responsible for users’ data sources, outreach behavior, or business outcomes.
