import io
import os
import json

import pandas as pd
import streamlit as st

from scraper import ComplianceScraper
from scoring import DEFAULT_CRITERIA
from core_logic import build_brief, normalize_weights, source_and_score, create_drafts
from report_generator import build_report
from config import TenantConfig

try:
    from social_apis import YouTubeClient
except ImportError:
    YouTubeClient = None


# ========== Page config ==========
st.set_page_config(
    page_title="Creator Sourcing & Outreach SaaS",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom SaaS Styling
st.markdown("""
<style>
    .stAppHeader {background-color: #f8f9fa;}
    .badge-tier {
        background-color: #4CAF50;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Main Title Header
col_title, col_tier = st.columns([4, 1])
with col_title:
    st.title("🚀 Creator Sourcing & Outreach SaaS Engine")
    st.caption(
        "Compliance-first influencer discovery and AI outreach automation built for global marketing agencies and brands."
    )
with col_tier:
    st.markdown('<br><span class="badge-tier">PRO AGENCY TIER</span>', unsafe_allow_html=True)


# ========== Sidebar: Tenant & API settings ==========
with st.sidebar:
    st.header("🏢 Tenant & API Settings")
    st.caption("Enter your subscription key and official API credentials.")

    tenant_key = st.text_input(
        "SaaS Subscription Key",
        value=os.environ.get("SAAS_MASTER_TOKEN", "demo-pro-tenant"),
        type="password"
    )
    
    youtube_key = st.text_input(
        "YouTube Data API Key",
        type="password",
        value=os.environ.get("YOUTUBE_API_KEY", ""),
    )
    openai_key = st.text_input(
        "OpenAI API Key (BYOK)",
        type="password",
        value=os.environ.get("OPENAI_API_KEY", ""),
    )

    st.divider()
    st.markdown(
        "**🛡️ Compliance & Privacy**\n"
        "- Strictly respects `robots.txt` and platform ToS.\n"
        "- NO auto-DM or bulk messaging. All drafts require manual review.\n"
        "- Multi-tenant data isolation; zero private data storage."
    )


# ========== 1. Campaign Brief ==========
st.header("1. Campaign Brief")

col1, col2 = st.columns(2)

with col1:
    product = st.text_input("Product / Service Name", value="Global Skincare Brand")
    target_market = st.text_input(
        "Target Market",
        value="Southeast Asia, North America",
    )
    goal = st.text_area(
        "Campaign Goal",
        value="Brand awareness, high-converting UGC content, regional market entry",
    )

with col2:
    budget_min = st.number_input("Budget Min (TWD/USD)", min_value=0, step=1000, value=5000)
    budget_max = st.number_input("Budget Max (TWD/USD)", min_value=0, step=1000, value=25000)
    follower_range = st.slider(
        "Target Follower Range",
        min_value=1000,
        max_value=1_000_000,
        value=(5000, 150_000),
        step=1000,
    )
    keywords_text = st.text_input(
        "Content Keywords (comma-separated)",
        value="skincare, beauty, glowing skin, sensitive skin",
    )


# ========== 2. Candidate Input ==========
st.header("2. Candidate Data Sourcing")

input_mode = st.radio(
    "Select Input Method",
    ["Paste Public URLs (Compliant Scraping)", "Enter Candidate Manually", "Load Demo Dataset"],
    horizontal=True,
)

if "candidates" not in st.session_state:
    st.session_state["candidates"] = []
candidates = st.session_state["candidates"]


if input_mode == "Paste Public URLs (Compliant Scraping)":
    st.info("Supports **public, static web pages allowing crawling via robots.txt**. Do not input login pages.")
    urls_text = st.text_area(
        "One public URL per line",
        placeholder="https://example-creator.com/about\nhttps://another-creator.com",
        height=120,
    )

    if st.button("🚀 Scrape Public Page Metadata", type="primary"):
        if not urls_text.strip():
            st.warning("Please enter at least one URL.")
        else:
            with st.spinner("Scraping metadata..."):
                scraper = ComplianceScraper()
                urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
                results = []
                progress = st.progress(0)
                for i, url in enumerate(urls):
                    res = scraper.scrape_page(url)
                    results.append(res)
                    progress.progress((i + 1) / len(urls))
                st.session_state["scraped_results"] = results
            st.success(f"Successfully scraped {len(results)} page(s).")

    if "scraped_results" in st.session_state:
        for idx, r in enumerate(st.session_state["scraped_results"]):
            if "error" in r:
                st.error(f"❌ {r['url']}: {r['error']}")
            else:
                with st.expander(f"✅ {r['url']}"):
                    st.write(f"**Title**: {r.get('page_title', '')}")
                    st.write(f"**OG Title**: {r.get('og_title', '')}")
                    st.write(f"**Meta Description**: {r.get('meta_description', '')}")
                    if st.button("Add to Candidates", key=f"add_scraped_{idx}"):
                        candidates.append({
                            "name": r.get("og_title") or r.get("page_title", r["url"]),
                            "platform": "website",
                            "followers": 15000,
                            "engagement_rate": 0.045,
                            "content_summary": r.get("body_excerpt", "")[:200],
                            "estimated_price": 8000,
                            "audience_region": target_market,
                            "content_keywords": ["beauty", "skincare"],
                            "source_url": r["url"],
                        })
                        st.success("Candidate added successfully.")

elif input_mode == "Enter Candidate Manually":
    with st.form("manual_candidate_form", clear_on_submit=True):
        c_name = st.text_input("Candidate Name / Handle")
        c_platform = st.selectbox("Platform", ["Instagram", "TikTok", "YouTube", "Blog", "Other"])
        c_followers = st.number_input("Followers", min_value=0, step=1000, value=25000)
        c_engagement = st.number_input("Engagement Rate (e.g., 0.042 = 4.2%)", min_value=0.0, max_value=1.0, value=0.042, step=0.005)
        c_region = st.text_input("Audience Region", value="Taiwan, SE Asia")
        c_price = st.number_input("Estimated Price (TWD/USD)", min_value=0, step=1000, value=12000)
        c_keywords = st.text_input("Content Keywords (comma-separated)", value="skincare, beauty, lifestyle")
        c_summary = st.text_area("Content Summary / Style Notes", value="Focuses on natural skincare routines and product reviews.")

        add_manual = st.form_submit_button("➕ Add Candidate")

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
        st.success(f"Candidate '{c_name}' added.")

else:
    st.caption("Load sample candidate dataset for instant testing:")
    if st.button("📥 Load Demo Candidates (3 Influencers)"):
        demo_data = [
            {
                "name": "BeautyWithEmma",
                "platform": "instagram",
                "followers": 45000,
                "engagement_rate": 0.048,
                "content_summary": "Skincare enthusiast focusing on East Asian beauty brands.",
                "estimated_price": 12000,
                "audience_region": "Southeast Asia, Taiwan",
                "content_keywords": ["skincare", "beauty", "glowing skin"]
            },
            {
                "name": "TechSkinLab",
                "platform": "youtube",
                "followers": 120000,
                "engagement_rate": 0.062,
                "content_summary": "In-depth ingredient analysis for sensitive skin.",
                "estimated_price": 22000,
                "audience_region": "North America",
                "content_keywords": ["sensitive skin", "beauty", "ingredient analysis"]
            },
            {
                "name": "GlowDaily_Official",
                "platform": "tiktok",
                "followers": 85000,
                "engagement_rate": 0.075,
                "content_summary": "Short-form video UGC style product reviews.",
                "estimated_price": 15000,
                "audience_region": "Taiwan",
                "content_keywords": ["ugc", "skincare", "beauty"]
            }
        ]
        st.session_state["candidates"] = demo_data
        st.rerun()

if candidates:
    st.subheader(f"Added Candidates ({len(candidates)})")
    st.dataframe(pd.DataFrame(candidates), use_container_width=True)
    if st.button("🗑️ Clear All Candidates"):
        st.session_state["candidates"] = []
        st.rerun()


# ========== 3. YouTube Auto-fill ==========
st.header("3. YouTube Data API Auto-Fill")

if youtube_key and YouTubeClient:
    yt_handle = st.text_input("YouTube @Handle or Channel ID", placeholder="@3Blue1Brown")
    if st.button("🔍 Fetch YouTube Data"):
        try:
            yt = YouTubeClient(youtube_key)
            info = yt.get_channel_by_handle(yt_handle)
            if info:
                st.json(info)
                if st.button("➕ Add YouTube Channel"):
                    candidates.append({
                        "name": info["title"],
                        "platform": "youtube",
                        "followers": info["subscribers"],
                        "engagement_rate": info["engagement_rate"],
                        "content_summary": info["description"],
                        "estimated_price": 18000,
                        "audience_region": info.get("country", "Global"),
                        "content_keywords": ["tech", "education"],
                    })
                    st.success("YouTube channel added successfully.")
            else:
                st.warning("Channel not found.")
        except Exception as e:
            st.error(f"Fetch failed: {e}")
elif not YouTubeClient:
    st.caption("YouTubeClient module unavailable.")
else:
    st.caption("💡 Enter your YouTube API Key in the sidebar to enable auto-fill.")


# ========== 4. Scoring ==========
st.header("4. Weighted Scoring & Filtering Engine")

with st.expander("⚙️ Customize Scoring Weights", expanded=False):
    st.caption("Adjust criteria weights. Weights are automatically normalized to sum to 1.0.")
    default_weights_df = pd.DataFrame([
        {"Criterion": item["criterion"], "Weight": item["weight"]}
        for item in DEFAULT_CRITERIA
    ])
    edited_weights = st.data_editor(
        default_weights_df,
        column_config={
            "Weight": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.05),
        },
        hide_index=True,
        use_container_width=True,
        key="weights_editor",
    )
    weight_map = dict(zip(edited_weights["Criterion"], edited_weights["Weight"]))
    normalized_weights = normalize_weights(weight_map)
    st.json({k: round(v, 3) for k, v in normalized_weights.items()})

if not candidates:
    st.warning("Please add at least one candidate in Section 2 or 3.")
else:
    brief = build_brief(
        product=product,
        target_market=target_market,
        goal=goal,
        budget_min=budget_min,
        budget_max=budget_max,
        follower_range=follower_range,
        keywords=[k.strip() for k in keywords_text.split(",") if k.strip()],
    )

    if st.button("🎯 Run Scoring Analysis", type="primary"):
        with st.spinner("Scoring candidates..."):
            results = source_and_score(candidates, brief, weights=normalized_weights)
            scored_df = pd.DataFrame(results)
            st.session_state["scored_df"] = scored_df
        st.success(f"Successfully scored {len(scored_df)} candidate(s).")

    if "scored_df" in st.session_state:
        df = st.session_state["scored_df"]
        st.subheader("📊 Scoring Results")
        st.dataframe(df, use_container_width=True)

        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download CSV Report",
                csv,
                "scored_creators_report.csv",
                "text/csv",
            )
        with col_xlsx:
            xlsx_buf = io.BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Candidates", index=False)
            st.download_button(
                "⬇️ Download Excel Report",
                xlsx_buf.getvalue(),
                "scored_creators_report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ========== 5. Outreach Drafts ==========
st.header("5. AI Outreach Draft Generator (Review Before Sending)")

if "drafts_by_candidate" not in st.session_state:
    st.session_state["drafts_by_candidate"] = {}

if "scored_df" in st.session_state and openai_key:
    df = st.session_state["scored_df"]
    selected_name = st.selectbox("Select a Scored Candidate", df["name"].tolist())

    if selected_name:
        selected_row = df[df["name"] == selected_name].iloc[0].to_dict()

        if st.button("✨ Generate 3 English Outreach Drafts (Formal / Friendly / Short)"):
            brief_for_draft = {
                "product": product,
                "target_market": target_market,
                "goal": goal,
                "budget_text": f"{budget_min} - {budget_max} TWD/USD",
            }
            candidate_info = {
                "name": selected_row.get("name", ""),
                "platform": selected_row.get("platform", ""),
                "followers": selected_row.get("followers", 0),
                "content_summary": selected_row.get("content_summary", ""),
                "estimated_price": selected_row.get("estimated_price", 0),
            }

            with st.spinner("Generating customized outreach drafts..."):
                drafts = create_drafts(
                    brief_for_draft,
                    candidate_info,
                    api_key=openai_key,
                )

            if drafts:
                st.session_state["drafts_by_candidate"][selected_name] = drafts
            else:
                st.warning("Draft generation failed. Please check your OpenAI API Key.")

    existing_drafts = st.session_state["drafts_by_candidate"].get(selected_name, [])
    if existing_drafts:
        for idx, d in enumerate(existing_drafts):
            st.markdown(f"**[{d.get('style', '').upper()} VERSION]**")
            st.text_input("Subject", d.get("subject", ""), key=f"subj_{selected_name}_{idx}")
            st.text_area("Body", d.get("body", ""), height=180, key=f"body_{selected_name}_{idx}")
            st.divider()

        st.download_button(
            "⬇️ Export JSON Drafts",
            json.dumps(existing_drafts, ensure_ascii=False, indent=2),
            f"outreach_{selected_name}.json",
        )
else:
    if "scored_df" not in st.session_state:
        st.caption("Please run scoring in Section 4 first.")
    if not openai_key:
        st.caption("💡 Enter your OpenAI API Key in the sidebar to generate outreach drafts.")


# ========== 6. Compliance Checklist ==========
st.header("6. Pre-Collaboration Compliance Checklist")

checklist = [
    "Confirmed candidate public data sources are legal and free of purchased follower lists.",
    "Read and complied with the target social platform's Terms of Service.",
    "Manually reviewed AI-generated outreach drafts for accuracy and transparency.",
    "Collaboration terms (compensation, deliverables, timeline) documented in writing.",
    "Included an opt-out mechanism allowing creators to decline further contact.",
    "Data handling complies with GDPR and local privacy regulations.",
]

for i, item in enumerate(checklist):
    st.checkbox(item, key=f"chk_{i}")


# ========== 7. PDF Report ==========
st.header("7. Export Enterprise PDF Report")

if "scored_df" not in st.session_state:
    st.caption("Run scoring first to generate the report.")
else:
    if st.button("📄 Generate PDF Report"):
        with st.spinner("Building enterprise PDF report..."):
            report_bytes = build_report(
                brief={
                    "Product": product,
                    "Target Market": target_market,
                    "Goal": goal,
                    "Budget": f"{budget_min} - {budget_max}",
                    "Follower Range": f"{follower_range[0]:,} - {follower_range[1]:,}",
                    "Keywords": keywords_text,
                },
                scored_df=st.session_state["scored_df"],
                drafts_by_candidate=st.session_state.get("drafts_by_candidate", {}),
                checklist=checklist,
            )
        st.download_button(
            "⬇️ Download PDF Report",
            report_bytes,
            "creator_sourcing_enterprise_report.pdf",
            "application/pdf",
        )


# ========== Footer ==========
st.divider()
st.caption(
    "⚠️ Disclaimer: This tool is for compliant public-data sourcing and draft assistance only. "
    "No automated DMs, bulk messaging, or private data scraping are performed. Users are fully responsible for platform compliance."
)
