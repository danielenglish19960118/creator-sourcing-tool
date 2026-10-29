import io
import os
import json

import pandas as pd
import streamlit as st

from scraper import ComplianceScraper
from scoring import score_candidates, DEFAULT_CRITERIA
from draft_generator import generate_outreach_drafts
from report_generator import build_report

try:
    from social_apis import YouTubeClient
except ImportError:
    YouTubeClient = None


# ========== Page config ==========
st.set_page_config(
    page_title="Creator Sourcing & Outreach Draft Tool",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Creator Sourcing & Outreach Draft Tool")
st.caption(
    "Compliance-first: only public pages, respects robots.txt, no auto-DM, no bulk messaging. "
    "All outputs must be reviewed manually before use."
)


# ========== Error boundary helper ==========
def safe_section(label: str):
    """Decorator to isolate errors per UI section."""
    def wrapper(fn):
        def inner(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                st.error(f"Something went wrong in '{label}': {e}")
                return None
        return inner
    return wrapper


# ========== Sidebar: API keys ==========
with st.sidebar:
    st.header("🔑 API Settings (Optional)")
    st.caption("Keys are only used to call official APIs. Leave blank to enter data manually.")

    youtube_key = st.text_input(
        "YouTube Data API Key",
        type="password",
        value=os.environ.get("YOUTUBE_API_KEY", ""),
    )
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.environ.get("OPENAI_API_KEY", ""),
    )

    st.divider()
    st.markdown(
        "**Compliance Notes**\n"
        "- Instagram / TikTok official APIs are strict and only cover authorized business accounts.\n"
        "- This tool does NOT send any messages automatically.\n"
        "- Do NOT use this tool to scrape private or logged-in pages."
    )


# ========== 1. Brief ==========
st.header("1. Campaign Brief")

col1, col2 = st.columns(2)

with col1:
    product = st.text_input("Product / Service", placeholder="e.g., Taiwanese skincare brand")
    target_market = st.text_input("Target Market", placeholder="e.g., Southeast Asia (Chinese-speaking), North America")
    goal = st.text_area("Campaign Goal", placeholder="e.g., brand awareness, conversions, UGC content")

with col2:
    budget_min = st.number_input("Budget Min (TWD)", min_value=0, step=1000, value=5000)
    budget_max = st.number_input("Budget Max (TWD)", min_value=0, step=1000, value=15000)
    follower_range = st.slider(
        "Target Follower Range",
        min_value=1000,
        max_value=1_000_000,
        value=(5000, 100_000),
        step=1000,
    )
    keywords_text = st.text_input("Content Keywords (comma-separated)", placeholder="e.g., skincare, beauty, sensitive skin")


# ========== 2. Candidate input ==========
st.header("2. Candidate Data")

input_mode = st.radio(
    "Select input method",
    ["Paste public URLs (compliant scraping)", "Enter candidate info manually"],
    horizontal=True,
)

if "candidates" not in st.session_state:
    st.session_state["candidates"] = []
candidates = st.session_state["candidates"]


# ---------- Mode A: public URL scraping ----------
if input_mode == "Paste public URLs (compliant scraping)":
    st.info(
        "Only **public, accessible pages that allow crawling via robots.txt** are supported. "
        "**Do NOT** paste Instagram / TikTok / YouTube logged-in pages."
    )

    urls_text = st.text_area(
        "One public URL per line",
        placeholder="https://example-creator.com/about\nhttps://another-creator.com",
        height=120,
    )

    if st.button("Scrape public page metadata", type="primary"):
        if not urls_text.strip():
            st.warning("Please enter at least one URL.")
        else:
            with st.spinner("Scraping..."):
                scraper = ComplianceScraper()
                urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
                results = []

                progress = st.progress(0)
                for i, url in enumerate(urls):
                    res = scraper.scrape_page(url)
                    results.append(res)
                    progress.progress((i + 1) / len(urls))

                st.session_state["scraped_results"] = results
            st.success(f"Finished scraping {len(results)} page(s).")

    if "scraped_results" in st.session_state:
        for idx, r in enumerate(st.session_state["scraped_results"]):
            if "error" in r:
                st.error(f"❌ {r['url']}: {r['error']}")
            else:
                with st.expander(f"✅ {r['url']}"):
                    st.write(f"**Title**: {r.get('page_title', '')}")
                    st.write(f"**OG Title**: {r.get('og_title', '')}")
                    st.write(f"**Meta Description**: {r.get('meta_description', '')}")
                    st.write(f"**OG Description**: {r.get('og_description', '')}")
                    st.write(f"**Body Excerpt**: {r.get('body_excerpt', '')[:300]}...")

                    if st.button("Add as candidate", key=f"add_scraped_{idx}"):
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
                        st.success("Candidate added.")

# ---------- Mode B: manual input ----------
else:
    st.info("Manually enter publicly visible candidate data.")

    with st.form("manual_candidate_form", clear_on_submit=True):
        c_name = st.text_input("Candidate Name")
        c_platform = st.selectbox("Platform", ["Instagram", "TikTok", "YouTube", "Blog", "Other"])
        c_followers = st.number_input("Followers", min_value=0, step=1000)
        c_engagement = st.number_input(
            "Engagement Rate (0-1, e.g., 0.03 = 3%)",
            min_value=0.0, max_value=1.0, step=0.01, format="%.3f",
        )
        c_region = st.text_input("Audience Region", placeholder="e.g., Taiwan, North America")
        c_price = st.number_input("Estimated Price (TWD)", min_value=0, step=1000)
        c_keywords = st.text_input("Content Keywords (comma-separated)")
        c_summary = st.text_area("Content Summary (optional)", height=80)

        add_manual = st.form_submit_button("Add candidate")

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

if candidates:
    st.subheader("Added Candidates")
    st.dataframe(pd.DataFrame(candidates), use_container_width=True)
    if st.button("Clear all candidates"):
        st.session_state["candidates"] = []
        st.rerun()


# ========== 3. YouTube auto-fill ==========
st.header("3. YouTube Auto-Fill (Optional)")

if youtube_key and YouTubeClient:
    yt_handle = st.text_input("YouTube @handle or Channel ID", placeholder="@3Blue1Brown")
    if st.button("Fetch YouTube channel data"):
        try:
            yt = YouTubeClient(youtube_key)
            info = yt.get_channel_by_handle(yt_handle)
            if info:
                st.json(info)
                if st.button("Add YouTube channel as candidate"):
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
                    st.success("YouTube channel added.")
            else:
                st.warning("Channel not found.")
        except Exception as e:
            st.error(f"Fetch failed: {e}")
elif not YouTubeClient:
    st.caption("YouTubeClient module not available. Skipping YouTube auto-fill.")
else:
    st.caption("Enter a YouTube API Key to auto-fetch public channel data.")


# ========== 4. Scoring ==========
st.header("4. Scoring & Filtering")

with st.expander("⚙️ Adjust Scoring Weights", expanded=False):
    st.caption("Change how much each criterion matters. Weights are normalized to sum to 1.0.")
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
    total_w = sum(weight_map.values())
    if total_w > 0:
        normalized_weights = {k: v / total_w for k, v in weight_map.items()}
    else:
        normalized_weights = {item["criterion"]: item["weight"] for item in DEFAULT_CRITERIA}

    st.caption("Normalized weights used for scoring:")
    st.json({k: round(v, 3) for k, v in normalized_weights.items()})

if not candidates:
    st.warning("Please add at least one candidate first.")
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

    if st.button("Run scoring", type="primary"):
        with st.spinner("Scoring..."):
            scored_df = score_candidates(candidates, brief, weights=normalized_weights)
            st.session_state["scored_df"] = scored_df
        st.success(f"Scored {len(scored_df)} candidate(s).")

    if "scored_df" in st.session_state:
        df = st.session_state["scored_df"]
        st.subheader("Scoring Results")
        st.dataframe(df, use_container_width=True)

        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download CSV",
                csv,
                "scored_candidates.csv",
                "text/csv",
            )
        with col_xlsx:
            xlsx_buf = io.BytesIO()
            with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Candidates", index=False)
            st.download_button(
                "⬇️ Download Excel",
                xlsx_buf.getvalue(),
                "scored_candidates.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ========== 5. Outreach drafts ==========
st.header("5. Outreach Drafts (Review before sending)")

if "drafts_by_candidate" not in st.session_state:
    st.session_state["drafts_by_candidate"] = {}

if "scored_df" in st.session_state and openai_key:
    df = st.session_state["scored_df"]
    selected_name = st.selectbox("Select a candidate", df["name"].tolist())

    if selected_name:
        selected_row = df[df["name"] == selected_name].iloc[0].to_dict()

        if st.button("Generate 3 English outreach drafts"):
            brief_for_draft = {
                "product": product,
                "target_market": target_market,
                "goal": goal,
                "budget_text": f"{budget_min} - {budget_max} TWD",
            }
            candidate_info = {
                "name": selected_row.get("name", ""),
                "platform": selected_row.get("platform", ""),
                "followers": selected_row.get("followers", 0),
                "content_summary": "",
                "estimated_price": selected_row.get("estimated_price", 0),
            }

            with st.spinner("Generating drafts..."):
                drafts = generate_outreach_drafts(
                    brief_for_draft,
                    candidate_info,
                    api_key=openai_key,
                )

            if drafts:
                st.session_state["drafts_by_candidate"][selected_name] = drafts
            else:
                st.warning("Draft generation failed. Check your OpenAI API key.")

    # Render existing drafts for the selected candidate
    existing_drafts = st.session_state["drafts_by_candidate"].get(selected_name, [])
    if existing_drafts:
        for idx, d in enumerate(existing_drafts):
            st.markdown(f"**{d.get('style', '').upper()} Version**")
            st.text_input("Subject", d.get("subject", ""), key=f"subj_{selected_name}_{idx}")
            st.text_area("Body", d.get("body", ""), height=180, key=f"body_{selected_name}_{idx}")
            st.divider()

        st.download_button(
            "⬇️ Download drafts (JSON)",
            json.dumps(existing_drafts, ensure_ascii=False, indent=2),
            f"outreach_{selected_name}.json",
        )
else:
    if "scored_df" not in st.session_state:
        st.caption("Run scoring first.")
    if not openai_key:
        st.caption("Enter an OpenAI API Key in the sidebar to generate drafts.")


# ========== 6. Compliance checklist ==========
st.header("6. Pre-Collaboration Compliance Checklist")

checklist = [
    "Confirmed the candidate's public data source is legal (no private pages, no purchased lists).",
    "Read and complied with the target platform's Terms of Service.",
    "Reviewed the outreach draft manually; no misleading or false statements.",
    "Collaboration terms (compensation, deliverables, timeline) are documented in writing.",
    "Provided an opt-out mechanism; the other party can decline further contact at any time.",
    "Personal data handling complies with GDPR / local privacy laws.",
]

checklist_state = {}
for i, item in enumerate(checklist):
    checklist_state[item] = st.checkbox(item, key=f"chk_{i}")


# ========== 7. PDF Report ==========
st.header("7. Download PDF Report")

if "scored_df" not in st.session_state:
    st.caption("Run scoring first to generate a report.")
else:
    if st.button("Generate PDF report"):
        with st.spinner("Building PDF..."):
            report_bytes = build_report(
                brief={
                    "Product": product,
                    "Target Market": target_market,
                    "Goal": goal,
                    "Budget": f"{budget_min} - {budget_max} TWD",
                    "Follower Range": f"{follower_range[0]:,} - {follower_range[1]:,}",
                    "Keywords": keywords_text,
                },
                scored_df=st.session_state["scored_df"],
                drafts_by_candidate=st.session_state.get("drafts_by_candidate", {}),
                checklist=checklist,
            )
        st.download_button(
            "⬇️ Download PDF",
            report_bytes,
            "creator_sourcing_report.pdf",
            "application/pdf",
        )


# ========== Footer ==========
st.divider()
st.caption(
    "⚠️ This tool is for compliant public-data sourcing and draft assistance only. "
    "No auto-messaging, no private data scraping, no bulk outreach. "
    "Users are responsible for complying with platform terms and local laws."
)
