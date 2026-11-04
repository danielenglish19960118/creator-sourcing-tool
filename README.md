

# Creator Sourcing & Outreach SaaS / 企業級網紅篩選與聯繫系統（可承租／白標部署）



A compliance-first SaaS tool for sourcing creators/influencers, multi-tenant scoring, and AI-powered outreach draft generation. Designed for agencies, cross-border brands, and solo entrepreneurs looking to monetize or rent out automated workflows.

合規優先的企業級創作者／網紅篩選與 AI 聯繫草稿 SaaS 系統，支援月租訂閱、API/MCP 算力承租與白標貼牌部署。

---

## 繁體中文

### 💡 專案簡介與商業化定位

這是一套專為行銷代理商、跨境電商品牌及獨立經紀人設計的 **B2B SaaS 軟體與高價接案交付工具**。它不僅能自動化處理繁瑣的網紅搜尋與評分，更透過 **多租戶架構 (Multi-tenancy)** 與 **MCP (Model Context Protocol) 雲端算力端點**，讓您可以直接將此系統「出租」給企業客戶，創造穩定的被動或訂閱收入。

#### 主要變現模式 (Monetization Models)

1. **企業月租訂閱 (SaaS Subscription)**：提供客戶專屬登入帳號、進階評分權重自定義、無限次名單匯入與 PDF 專業報告產出。
2. **API / MCP 算力承租**：透過 A2MCP 協定與安全 Token 驗證，讓企業客戶的 AI 助理（如 Claude、OKX.AI）直接對接您的篩選引擎。


3. **白標貼牌 (White-label)**：協助代理商換上自家 Logo 與網域，收取高額的系統建置費與維護授權費。

---

### 🚀 核心功能模組

* **多租戶動態設定 (`config.py`)**：支援依據客戶方案（Free / Pro / Agency）動態調整評分權重、候選人數量上限與 AI 草稿呼叫額度。
* **安全雲端 MCP 服務 (`mcp_server.py`)**：內建 API 金鑰驗證機制，防止未授權存取，保障您的付費訂閱權益。


* **合規公開網頁爬蟲 (`scraper.py`)**：只抓取公開、靜態、`robots.txt` 允許的頁面，確保完全合規。


* **YouTube Data API v3 整合 (`social_apis.py`)**：取得頻道公開數據（訂閱數、觀看數、影片數、近似互動率）。


* **智慧評分引擎 (`scoring.py`)**：依粉絲數、互動率、內容關鍵詞、受眾地區與報價進行五維度加權評分。


* **LLM AI 聯繫草稿 (`draft_generator.py`)**：一鍵生成 3 種語氣（正式／親切／短版）的英文高效外聯草稿。



---

### 🔒 合規與安全邊界

| 可以做 (Allowed) | 不可以做 (Not Allowed) |
| --- | --- |
| 透過 API 驗證機制保護多租戶訂閱權益 | 允許未授權用戶任意消耗 AI 額度 |
| 抓取公開網頁標題、描述、OG 標籤

 | 抓取登入後頁面或私密個人資料

 |
| 透過官方 API 取得頻道與授權帳號資料

 | 使用非官方爬蟲大規模爬取社群私密數據

 |
| AI 生成草稿，強制人工審核後手動發送

 | 自動化群發私訊或進行騷擾式行銷

 |

---

### 💻 本機部署與測試

```bash
# 1. 安裝相依套件
pip install -r requirements.txt

# 2. 設定環境變數
export YOUTUBE_API_KEY="your_youtube_api_key"
export OPENAI_API_KEY="your_openai_api_key"
export SAAS_MASTER_TOKEN="your_secure_subscription_token"

# 3. 啟動 Streamlit 網頁介面
streamlit run app.py

# 4. 啟動 MCP 雲端伺服器 (供 AI 代理呼叫)
python mcp_server.py

```

---

### ☁️ 雲端部署與交付指南

1. **部署到 Streamlit Cloud**：
* 將專案推送到 GitHub 公開或私有儲存庫。


* 前往 [share.streamlit.io](https://share.streamlit.io) 建立 App，主檔案選擇 `app.py`。


* 在 **Advanced settings → Secrets** 中填入您的 API Key 與 `SAAS_MASTER_TOKEN`。




2. **包裝為接案服務**：
* 在 Upwork 或 Fiverr 上架「自動化網紅開發與外聯系統」服務，為客戶進行客製化部署。





---

## English

### 💡 Overview & Commercialization

This is an enterprise-grade, **compliance-first creator sourcing and AI outreach SaaS solution** built for marketing agencies, cross-border e-commerce brands, and independent talent managers. Beyond streamlining influencer discovery and weighted scoring, it is architected for **multi-tenancy** and **MCP cloud endpoints**, allowing you to seamlessly rent out the software or its computing power as a subscription service.

#### Monetization Options

1. **SaaS Subscription**: Offer clients dedicated workspaces, custom scoring weights, and PDF report generation.
2. **API / MCP Rental**: Securely expose your creator-sourcing backend via A2MCP protocols and token validation for enterprise AI agents.


3. **White-label Solutions**: Rebrand the platform for agencies and charge setup/licensing fees.

---

### 🚀 Key Features

* **Multi-Tenant Config (`config.py`)**: Dynamically manage subscription tiers (Free, Pro, Agency), candidate limits, and AI generation quotas.
* **Secure MCP Server (`mcp_server.py`)**: Protected by API token validation to secure your paid SaaS infrastructure.


* **Compliant Web Scraper (`scraper.py`)**: Strictly respects `robots.txt` and only targets public, accessible web pages.


* **YouTube Data API Integration**: Fetches public channel statistics, subscriber counts, and engagement estimates.


* **Weighted Scoring Engine (`scoring.py`)**: Multi-factor evaluation covering follower fit, engagement rate, content relevance, geography, and budget.


* **AI Outreach Draft Generator (`draft_generator.py`)**: Generates 3 customizable English outreach tones (formal, friendly, short).



---

### 📂 Project Structure

```text
creator-sourcing-saas/
├── app.py                     # Streamlit SaaS UI (Multi-tenant ready)
├── scraper.py                 # Compliant public web scraper
├── social_apis.py             # YouTube / Instagram / TikTok official APIs
├── scoring.py                 # Scoring and filtering engine
├── draft_generator.py         # LLM outreach draft generator
├── core_logic.py              # Pure business logic
├── config.py                  # SaaS tiers & scoring weights config
├── mcp_server.py              # Secure A2MCP endpoint for AI agents
├── report_generator.py        # PDF report generator
├── requirements.txt
└── README.md

```

---

### 📞 Contact & Partnership

Interested in renting this system, deploying a white-label version, or acquiring a custom AI marketing workflow?

📩 **Email us at**: `danielenglish19960118@gmail.com`

---

### ⚖️ License & Disclaimer

This tool is designed for compliant public-data sourcing and draft assistance only. Users and tenants are strictly responsible for complying with platform terms of service, local privacy laws, and regulations. Developers assume no liability for data sources, outreach behavior, or business outcomes.
