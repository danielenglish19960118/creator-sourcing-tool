import io
import os
import json

import pandas as pd
import streamlit as st

from scraper import ComplianceScraper
from social_apis import YouTubeClient, InstagramClient, TikTokClient
from scoring import score_candidates, DEFAULT_CRITERIA
from draft_generator import generate_outreach_drafts


# ========== 页面设置 ==========
st.set_page_config(
    page_title="创作者筛选与联系草稿工具",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 创作者筛选与联系草稿工具")
st.caption(
    "合规版：只抓取公开网页、遵守 robots.txt、不自动私讯、不群发。"
    "所有输出请人工审核后使用。"
)


# ========== 侧边栏：API Keys ==========
with st.sidebar:
    st.header("🔑 API 设置（可选）")
    st.caption("YouTube API Key 用于自动抓取频道数据；不填则只能手动输入。")

    youtube_key = st.text_input(
        "YouTube Data API Key",
        type="password",
        value=os.environ.get("YOUTUBE_API_KEY", ""),
    )

    st.divider()
    st.markdown(
        "**合规提醒**\n"
        "- Instagram / TikTok 官方 API 限制严格，仅能获取已授权商业账号。\n"
        "- 本工具不自动发送任何消息。\n"
        "- 请勿用本工具抓取私密或登录后页面。"
    )


# ========== 1. 填写 Brief ==========
st.header("1. 填写合作需求")

col1, col2 = st.columns(2)

with col1:
    product = st.text_input(
        "产品 / 服务名称",
        placeholder="例如：台湾地区製保养品",
    )
    target_market = st.text_input(
        "目标市场",
        placeholder="例如：东南亚华语市场、北美",
    )
    goal = st.text_area(
        "合作目标",
        placeholder="例如：提升品牌知名度、导购、取得 UGC 内容",
    )

with col2:
    budget_min = st.number_input(
        "预算下限（新台币）", min_value=0, step=1000, value=5000
    )
    budget_max = st.number_input(
        "预算上限（新台币）", min_value=0, step=1000, value=15000
    )
    follower_range = st.slider(
        "目标粉丝数区间",
        min_value=1000,
        max_value=1_000_000,
        value=(5000, 100_000),
        step=1000,
    )
    keywords_text = st.text_input(
        "内容关键词（逗号分隔）",
        placeholder="例如：保养, 护肤, 敏感肌",
    )


# ========== 2. 候选人输入 ==========
st.header("2. 候选人数据")

input_mode = st.radio(
    "选择输入方式",
    ["手动粘贴公开 URL（合规爬取）", "直接粘贴候选人信息"],
    horizontal=True,
)

candidates = []

# ---------- 模式 A：公开 URL 爬取 ----------
if input_mode == "手动粘贴公开 URL（合规爬取）":
    st.info(
        "只支持**公开可访问、robots.txt 允许抓取**的创作者页面（如个人博客、公开的创作者介绍页）。"
        "**不要**粘贴 Instagram / TikTok / YouTube 的登录后页面或需要绕过验证的 URL。"
    )

    urls_text = st.text_area(
        "每行一个公开 URL",
        placeholder="https://example-creator.com/about\nhttps://another-creator.com",
        height=120,
    )

    if st.button("爬取公开页面元数据", type="primary"):
        if not urls_text.strip():
            st.warning("请至少输入一个 URL")
        else:
            scraper = ComplianceScraper()
            urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
            results = []

            progress = st.progress(0)
            for i, url in enumerate(urls):
                res = scraper.scrape_page(url)
                results.append(res)
                progress.progress((i + 1) / len(urls))

            st.session_state["scraped_results"] = results
            st.success(f"完成 {len(results)} 个页面的抓取")

    # 展示爬取结果
    if "scraped_results" in st.session_state:
        for r in st.session_state["scraped_results"]:
            if "error" in r:
                st.error(f"❌ {r['url']}：{r['error']}")
            else:
                with st.expander(f"✅ {r['url']}"):
                    st.write(f"**标题**：{r.get('page_title', '')}")
                    st.write(f"**OG 标题**：{r.get('og_title', '')}")
                    st.write(f"**Meta Description**：{r.get('meta_description', '')}")
                    st.write(f"**OG Description**：{r.get('og_description', '')}")
                    st.write(f"**内容摘要**：{r.get('body_excerpt', '')[:300]}...")

                    # 用爬取结果填充候选人
                    if st.button("加入候选人", key=f"add_{r['url']}"):
                        candidates.append({
                            "name": r.get("og_title") or r.get("page_title", r["url"]),
                            "platform": "website",
                            "followers": 0,
                            "engagement_rate": 0,
                            "content_summary": r.get("body_excerpt", "")[:200],
                            "estimated_price": 0,
                            "audience_region": target_market,
                            "content_keywords": [],
                            "source_url": r["url"],
                        })

# ---------- 模式 B：直接粘贴信息 ----------
else:
    st.info("手动输入候选人的公开数据（粉丝数、互动率等）。这些数据可以来自平台公开页面。")

    with st.form("manual_candidate_form"):
        c_name = st.text_input("候选人名称")
        c_platform = st.selectbox("平台", ["Instagram", "TikTok", "YouTube", "博客", "其他"])
        c_followers = st.number_input("粉丝数", min_value=0, step=1000)
        c_engagement = st.number_input(
            "互动率（0-1，例如 0.03 表示 3%）",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            format="%.3f",
        )
        c_region = st.text_input("受众主要地区", placeholder="例如：台湾地区、北美")
        c_price = st.number_input("预估报价（新台币）", min_value=0, step=1000)
        c_keywords = st.text_input("内容关键词（逗号分隔）")
        c_summary = st.text_area("内容摘要（可选）", height=80)

        add_manual = st.form_submit_button("加入候选人")

    if add_manual and c_name:
        candidates.append({
            "name": c_name,
            "platform": c_platform.lower(),
            "followers": c_followers,
            "engagement_rate": c_engagement,
            "content_summary": c_summary,
            "estimated_price": c_price,
            "audience_region": c_region,
            "content_keywords": [k.strip() for k in c_keywords.split(",") if k.strip()],
        })

# 展示已加入的候选人
if candidates:
    st.subheader("已加入的候选人")
    st.dataframe(pd.DataFrame(candidates), use_container_width=True)


# ========== 3. YouTube 自动补全（可选） ==========
st.header("3. YouTube 数据自动补全（可选）")

if youtube_key:
    yt_handle = st.text_input(
        "输入 YouTube @handle 或频道 ID",
        placeholder="@3Blue1Brown",
    )
    if st.button("获取 YouTube 频道数据"):
        try:
            yt = YouTubeClient(youtube_key)
            info = yt.get_channel_by_handle(yt_handle)
            if info:
                st.json(info)
                if st.button("将 YouTube 频道加入候选人"):
                    candidates.append({
                        "name": info["title"],
                        "platform": "youtube",
                        "followers": info["subscribers"],
                        "engagement_rate": info["engagement_rate"],
                        "content_summary": info["description"],
                        "estimated_price": 0,
                        "audience_region": info.get("country", ""),
                        "content_keywords": [],
                    })
            else:
                st.warning("找不到该频道")
        except Exception as e:
            st.error(f"获取失败：{e}")
else:
    st.caption("填写 YouTube API Key 后，可自动获取频道公开数据。")


# ========== 4. 评分与筛选 ==========
st.header("4. 评分与筛选")

if not candidates:
    st.warning("请先加入至少一个候选人")
else:
    brief = {
        "product": product,
        "target_market": target_market,
        "goal": goal,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "follower_range": follower_range,
        "keywords": [k.strip() for k in keywords_text.split(",") if k.strip()],
    }

    if st.button("开始评分", type="primary"):
        scored_df = score_candidates(candidates, brief)
        st.session_state["scored_df"] = scored_df

    if "scored_df" in st.session_state:
        df = st.session_state["scored_df"]
        st.subheader("评分结果")
        st.dataframe(df, use_container_width=True)

        # 下载 CSV
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ 下载评分表 CSV",
            csv,
            "scored_candidates.csv",
            "text/csv",
        )

        # 下载 Excel
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Candidates", index=False)
        st.download_button(
            "⬇️ 下载评分表 Excel",
            xlsx_buf.getvalue(),
            "scored_candidates.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ========== 5. 联系草稿生成 ==========
st.header("5. 联系草稿（需人工审核后发送）")

openai_key = st.text_input(
    "OpenAI API Key（用于生成草稿，不会存储）",
    type="password",
    value=os.environ.get("OPENAI_API_KEY", ""),
)

if "scored_df" in st.session_state and openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key

    df = st.session_state["scored_df"]
    selected_name = st.selectbox("选择候选人", df["name"].tolist())

    if selected_name:
        selected_row = df[df["name"] == selected_name].iloc[0].to_dict()

        if st.button("生成 3 版英文联系草稿"):
            brief = {
                "product": product,
                "target_market": target_market,
                "goal": goal,
                "budget_text": f"{budget_min} - {budget_max} 新台币",
            }
            candidate_info = {
                "name": selected_row.get("name", ""),
                "platform": selected_row.get("platform", ""),
                "followers": selected_row.get("followers", 0),
                "content_summary": "",
                "estimated_price": selected_row.get("estimated_price", 0),
            }

            with st.spinner("生成中..."):
                drafts = generate_outreach_drafts(brief, candidate_info)

            if drafts:
                for d in drafts:
                    st.markdown(f"**{d.get('style', '').upper()} 版**")
                    st.text_input(
                        "主旨",
                        d.get("subject", ""),
                        key=f"subj_{d.get('style')}_{selected_name}",
                    )
                    st.text_area(
                        "内容",
                        d.get("body", ""),
                        height=180,
                        key=f"body_{d.get('style')}_{selected_name}",
                    )
                    st.divider()

                st.download_button(
                    "⬇️ 下载草稿 JSON",
                    json.dumps(drafts, ensure_ascii=False, indent=2),
                    "outreach_drafts.json",
                )
            else:
                st.warning("草稿生成失败，请检查 API Key 或重试。")
else:
    if "scored_df" not in st.session_state:
        st.caption("请先完成评分步骤。")
    if not openai_key:
        st.caption("填写 OpenAI API Key 后可生成草稿。")


# ========== 6. 合规检查清单 ==========
st.header("6. 合作前合规检查清单")

checklist = [
    "已确认候选人的公开数据来源合法（非私密页面、非购买名单）",
    "已阅读并遵守目标平台的服务条款",
    "联系草稿已人工审核，确认无误导或虚假陈述",
    "合作条件（报酬、交付物、时间）已在书面中明确",
    "已提供退出机制，对方可随时拒绝后续联系",
    "涉及个资的处理符合《个人资料保护法》/ GDPR 要求",
]

for item in checklist:
    st.checkbox(item, key=f"chk_{item}")


# ========== Footer ==========
st.divider()
st.caption(
    "⚠️ 本工具仅供合规的公开数据筛选与草稿辅助。"
    "不自动发送消息、不爬取私密数据、不群发。"
    "使用者需自行确保遵守平台条款与当地法律。"
)
