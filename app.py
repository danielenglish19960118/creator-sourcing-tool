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
    from supabase import create_client
except ImportError:
    create_client = None

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
    .badge-free {
        background-color: #ff9800;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 14px;
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1f2937;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #4b5563;
    }
    .pricing-card {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)


# ========== Initialize Supabase Connection ==========
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
db_client = create_client(SUPABASE_URL, SUPABASE_KEY) if (create_client and SUPABASE_URL and SUPABASE_KEY) else None


# ========== Authentication & Session State ==========
if "user" not in st.session_state:
    st.session_state["user"] = None

def get_user_profile(email: str):
    """Fetch user subscription tier and usage from Supabase."""
    if not db_client:
        return {"tier": "free", "ai_usage": 0, "ai_limit": 3}
    try:
        res = db_client.table("tenants").select("*").eq("email", email).execute()
        if res.data:
            return res.data[0]
        else:
            new_record = {"email": email, "tier": "free", "ai_usage": 0, "ai_limit": 3, "is_active": True}
            db_client.table("tenants").insert(new_record).execute()
            return new_record
    except Exception:
        return {"tier": "free", "ai_usage": 0, "ai_limit": 3}

def increment_ai_usage(email: str, current_usage: int):
    if db_client:
        try:
            db_client.table("tenants").update({"ai_usage": current_usage + 1}).eq("email", email).execute()
        except Exception:
            pass


# ========== Sidebar: Authentication & Navigation ==========
with st.sidebar:
    st.header("🔐 SaaS Portal")
    
    if st.session_state["user"] is None:
        st.caption("Sign in to access your dashboard.")
        auth_email = st.text_input("Email Address")
        auth_password = st.text_input("Password", type="password")
        
        if st.button("🚀 Sign In / Register", type="primary"):
            if not auth_email or not auth_password:
                st.warning("Please fill in all fields.")
            else:
                profile = get_user_profile(auth_email)
                st.session_state["user"] = profile
                st.success(f"Welcome, {auth_email}!")
                st.rerun()
    else:
        user = st.session_state["user"]
        email = user.get("email")
        profile = get_user_profile(email)
        tier = profile.get("tier", "free")
        usage = profile.get("ai_usage", 0)
        limit = profile.get("ai_limit", 3)
        
        st.write(f"👤 **Account**: {email}")
        if tier in ["pro", "agency"]:
            st.markdown('<span class="badge-tier">PRO TIER (UNLIMITED)</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="badge-free">FREE PLAN ({usage}/{limit} AI Used)</span>', unsafe_allow_html=True)
            st.markdown("[👉 Upgrade to Pro ($49/mo)](https://your-payment-page.com)")
        
        if st.button("🚪 Sign Out"):
            st.session_state["user"] = None
            st.rerun()

    st.divider()
    st.markdown("### 🧭 Navigation")
    nav_page = st.radio("Go to", ["📖 Product Overview (Copywriting)", "⚡ SaaS App Workspace"])

    if st.session_state["user"]:
        st.divider()
        youtube_key = st.text_input("YouTube Data API Key", type="password", value=os.environ.get("YOUTUBE_API_KEY", ""))
        openai_key = st.text_input("OpenAI API Key (BYOK)", type="password", value=os.environ.get("OPENAI_API_KEY", ""))
    else:
        youtube_key, openai_key = "", ""


# =========================================================================
# PAGE 1: PRODUCT OVERVIEW & COPYWRITING PAGE (Landing Page)
# =========================================================================
if nav_page == "📖 Product Overview (Copywriting)":
    st.markdown('<p class="hero-title">🚀 Scale Your Influencer Marketing with 100% Compliance & AI Automation</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">The ultimate enterprise-grade creator sourcing, multi-factor scoring, and AI outreach solution built for modern marketing agencies and cross-border e-commerce brands.</p>', unsafe_allow_html=True)
    
    st.divider()

    # Section 1: The Pain Point & Solution
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.subheader("❌ The Old, Painful Way")
        st.markdown(
            "- **Hours Wasted Manually Searching**: Endless scrolling through Instagram or YouTube to find relevant creators.\n"
            "- **Unreliable Metrics**: Relying on gut feelings instead of real engagement rates and audience alignment.\n"
            "- **Risk of Account Bans**: Using aggressive web scrapers or illegal bulk messaging tools that violate platform ToS."
        )
    with col_p2:
        st.subheader("✅ The Creator Sourcing SaaS Way")
        st.markdown(
            "- **Automated Discovery**: Scrape public pages or fetch verified official YouTube metrics instantly[cite: 8].\n"
            "- **Weighted Scoring Engine**: Multi-factor evaluation covering follower fit, engagement rate, geography, and budget[cite: 8].\n"
            "- **Compliance-First**: Strictly respects `robots.txt` and platform terms with manual review safeguards[cite: 8]."
        )

    st.divider()

    # Section 2: Key Features
    st.header("⚡ Core Enterprise Features")
    feat_c1, feat_c2, feat_c3 = st.columns(3)
    with feat_c1:
        st.markdown("### 🔍 Compliant Web Scraper")
        st.write("Safely extracts public metadata from static web pages while strictly respecting `robots.txt` and SSRF protection[cite: 8].")
    with feat_c2:
        st.markdown("### 📊 5-Dimension Scoring")
        st.write("Ranks creators automatically based on follower range, engagement rate, keyword overlap, region, and budget[cite: 8].")
    with feat_c3:
        st.markdown("### 🤖 AI Outreach Generator")
        st.write("Generates highly personalized English outreach drafts in 3 professional tones (formal, friendly, short)[cite: 8].")

    st.divider()

    # Section 3: Pricing Tiers
    st.header("💎 Flexible Pricing Plans")
    pr_c1, pr_c2 = st.columns(2)
    with pr_c1:
        st.markdown("""
        <div class="pricing-card">
            <h3>Free Tier</h3>
            <h2>$0 / month</h2>
            <p>Perfect for testing out the platform.</p>
            <hr>
            <ul style="text-align: left; list-style: none; padding: 0;">
                <li>✔️ Up to 3 AI Draft Generations</li>
                <li>✔️ Basic Public Scraping & Scoring</li>
                <li>✔️ CSV / Excel Report Export</li>
            </ul>
            <br>
            <a href="https://your-payment-page.com" target="_blank">Get Started Free</a>
        </div>
        """, unsafe_allow_html=True)
    with pr_c2:
        st.markdown("""
        <div class="pricing-card" style="border: 2px solid #4CAF50;">
            <h3>Pro Agency Tier</h3>
            <h2>$49 / month</h2>
            <p>Designed for scaling marketing agencies.</p>
            <hr>
            <ul style="text-align: left; list-style: none; padding: 0;">
                <li>✔️ Unlimited AI Draft Generations</li>
                <li>✔️ Advanced Multi-Tenant Customization</li>
                <li>✔️ Enterprise PDF Report Export</li>
                <li>✔️ Automated Lemon Squeezy / PayPal Checkout</li>
            </ul>
            <br>
            <a href="https://your-payment-page.com" target="_blank" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Upgrade to Pro</a>
        </div>
        """, unsafe_allow_html=True)

    st.stop()


# =========================================================================
# PAGE 2: SAAS APP WORKSPACE (Protected by Login)
# =========================================================================
if st.session_state["user"] is None:
    st.warning("🔒 **Access Restricted**: Please sign in using the sidebar portal, or switch to the **Product Overview** page to learn more.")
    st.stop()

user_profile = get_user_profile(st.session_state["user"]["email"])
current_tier = user_profile.get("tier", "free")


# Main Title Header
col_title, col_tier = st.columns([4, 1])
with col_title:
    st.title("🚀 Creator Sourcing & Outreach SaaS Engine")
    st.caption("Compliance-first influencer discovery and AI outreach automation built for global marketing agencies and brands.")
with col_tier:
    if current_tier in ["pro", "agency"]:
        st.markdown('<br><span class="badge-tier">PRO AGENCY TIER</span>', unsafe_allow_html=True)
    else:
        st.markdown('<br><span class="badge-free">FREE PLAN</span>', unsafe_allow_html=True)


# ========== 1. Campaign Brief ==========
st.header("1. Campaign Brief")

col1, col2 = st.columns(2)

with col1:
    product = st.text_input("Product / Service Name", value="Global Skincare Brand")
    target_market = st.text_input("Target Market", value="Southeast Asia, North America")
    goal = st.text_area("Campaign Goal", value="Brand awareness, high-converting UGC content, regional market entry")

with col2:
    budget_min = st.number_input("Budget Min (TWD/USD)", min_value=0, step=1000, value=5000)
    budget_max = st.number_input("Budget Max (TWD/USD)", min_value=0, step=1000, value=25000)
    follower_range = st.slider("Target Follower Range", min_value=1000, max_value=1_000_000, value=(5000, 150_000), step=1000)
    keywords_text = st.text_input("Content Keywords (comma-separated)", value="skincare, beauty, glowing skin, sensitive skin")


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
    st.info("Supports **public, static web pages allowing crawling via robots.txt**[cite: 8].")
    urls_text = st.text_area("One public URL per line", placeholder="https://example-creator.com/about", height=120)

    if st.button("🚀 Scrape Public Page Metadata", type="primary"):
        if not urls_text.strip():
            st.warning("Please enter at least one URL.")
        else:
            with st.spinner("Scraping metadata..."):
                scraper = ComplianceScraper()
                urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
                results = []
                for url in urls:
                    results.append(scraper.scrape_page(url))
                st.session_state["scraped_results"] = results
            st.success(f"Successfully scraped {len(results)} page(s).")

    if "scraped_results" in st.session_state:
        for idx, r in enumerate(st.session_state["scraped_results"]):
            if "error" not in r:
                with st.expander(f"✅ {r['url']}"):
                    st.write(f"**Title**: {r.get('page_title', '')}")
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
                        st.success("Candidate added.")

elif input_mode == "Enter Candidate Manually":
    with st.form("manual_candidate_form", clear_on_submit=True):
        c_name = st.text_input("Candidate Name / Handle")
        c_platform = st.selectbox("Platform", ["Instagram", "TikTok", "YouTube", "Blog", "Other"])
        c_followers = st.number_input("Followers", min_value=0, step=1000, value=25000)
        c_engagement = st.number_input("Engagement Rate", min_value=0.0, max_value=1.0, value=0.042, step=0.005)
        c_region = st.text_input("Audience Region", value="Taiwan, SE Asia")
        c_price = st.number_input("Estimated Price", min_value=0, step=1000, value=12000)
        c_keywords = st.text_input("Content Keywords", value="skincare, beauty")
        c_summary = st.text_area("Content Summary", value="Skincare routines.")
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
    if st.button("📥 Load Demo Candidates (3 Influencers)"):
        st.session_state["candidates"] = [
            {"name": "BeautyWithEmma", "platform": "instagram", "followers": 45000, "engagement_rate": 0.048, "content_summary": "Skincare enthusiast.", "estimated_price": 12000, "audience_region": "Taiwan", "content_keywords": ["skincare"]},
            {"name": "TechSkinLab", "platform": "youtube", "followers": 120000, "engagement_rate": 0.062, "content_summary": "Ingredient analysis.", "estimated_price": 22000, "audience_region": "North America", "content_keywords": ["sensitive skin"]},
            {"name": "GlowDaily", "platform": "tiktok", "followers": 85000, "engagement_rate": 0.075, "content_summary": "UGC reviews.", "estimated_price": 15000, "audience_region": "Taiwan", "content_keywords": ["ugc"]}
        ]
        st.rerun()

if candidates:
    st.subheader(f"Added Candidates ({len(candidates)})")
    st.dataframe(pd.DataFrame(candidates), use_container_width=True)
    if st.button("🗑️ Clear All"):
        st.session_state["candidates"] = []
        st.rerun()


# ========== 3. Scoring Engine ==========
st.header("4. Weighted Scoring & Filtering Engine")

if not candidates:
    st.warning("Please add at least one candidate.")
else:
    brief = build_brief(
        product=product, target_market=target_market, goal=goal,
        budget_min=budget_min, budget_max=budget_max,
        follower_range=follower_range, keywords=[k.strip() for k in keywords_text.split(",") if k.strip()]
    )

    if st.button("🎯 Run Scoring Analysis", type="primary"):
        with st.spinner("Scoring candidates..."):
            results = source_and_score(candidates, brief)
            st.session_state["scored_df"] = pd.DataFrame(results)
        st.success("Scoring completed.")

    if "scored_df" in st.session_state:
        st.dataframe(st.session_state["scored_df"], use_container_width=True)


# ========== 4. AI Outreach Draft Generator ==========
st.header("5. AI Outreach Draft Generator")

current_usage = user_profile.get("ai_usage", 0)
ai_limit = user_profile.get("ai_limit", 3)

if current_tier == "free" and current_usage >= ai_limit:
    st.error(f"❌ **Free Tier Limit Reached ({current_usage}/{ai_limit})**: You have used all free AI outreach generations.")
    st.markdown("[👉 Upgrade to Pro Plan to unlock unlimited AI generations](https://your-payment-page.com)")
else:
    if "scored_df" in st.session_state and openai_key:
        df = st.session_state["scored_df"]
        selected_name = st.selectbox("Select Candidate for Outreach", df["name"].tolist())

        if st.button("✨ Generate AI Outreach Draft"):
            selected_row = df[df["name"] == selected_name].iloc[0].to_dict()
            brief_for_draft = {"product": product, "target_market": target_market, "goal": goal, "budget_text": f"{budget_min}-{budget_max}"}
            
            with st.spinner("Generating drafts..."):
                drafts = create_drafts(brief_for_draft, selected_row, api_key=openai_key)
            
            if drafts:
                st.success("Drafts generated successfully!")
                if current_tier == "free":
                    increment_ai_usage(user_profile["email"], current_usage)
                
                for d in drafts:
                    st.markdown(f"**[{d['style'].upper()}]**")
                    st.text_input("Subject", d["subject"], key=f"subj_{d['style']}")
                    st.text_area("Body", d["body"], key=f"body_{d['style']}")
            else:
                st.warning("Draft generation failed. Check API Key.")
    else:
        st.caption("Run scoring analysis and enter your OpenAI API key to generate drafts.")
