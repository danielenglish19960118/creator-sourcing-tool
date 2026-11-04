"""
Multi-Channel Automated Payment & Tenant Provisioning Microservice.

Supports:
- Local (Taiwan): ECPay (綠界), NewebPay (藍新), LINE Pay
- Global: Stripe, Lemon Squeezy (MoR), Gumroad, PayPal
"""

import os
import secrets
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client, Client

app = FastAPI(title="SaaS Payment Webhook Automation Server")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


def provision_tenant(email: str, tier: str = "pro", provider: str = "unknown") -> str:
    """Helper function to create a new active tenant and save to Supabase."""
    token = f"saas_{tier}_{secrets.token_hex(16)}"
    if supabase:
        supabase.table("tenants").insert({
            "email": email,
            "api_token": token,
            "tier": tier,
            "provider": provider,
            "ai_drafts_quota": 50 if tier == "pro" else 200,
            "is_active": True
        }).execute()
        print(f"[{provider.upper()} Automation] Provisioned {token} for {email}")
    return token


# ==================== LOCAL PAYMENT CHANNELS (TAIWAN) ====================

@app.post("/webhook/ecpay")
async def webhook_ecpay(request: Request):
    """綠界科技 ECPay Webhook 端點"""
    form_data = await request.form()
    data = dict(form_data)
    if data.get("RtnCode") == "1":
        email = data.get("CustomField1", "customer@example.com")
        tier = data.get("CustomField2", "pro")
        provision_tenant(email, tier, provider="ecpay")
        return "1|OK"
    raise HTTPException(status_code=400, detail="ECPay payment unverified")


@app.post("/webhook/newebpay")
async def webhook_newebpay(request: Request):
    """藍新金流 NewebPay Webhook 端點"""
    form_data = await request.form()
    data = dict(form_data)
    if data.get("Status") == "SUCCESS":
        email = data.get("Email", "customer@example.com")
        provision_tenant(email, "pro", provider="newebpay")
        return "SUCCESS"
    raise HTTPException(status_code=400, detail="NewebPay payment failed")


@app.post("/webhook/linepay")
async def webhook_linepay(request: Request):
    """LINE Pay 確認成功端點"""
    body = await request.json()
    if body.get("returnCode") == "0000":
        email = body.get("info", {}).get("email", "linepay_user@example.com")
        provision_tenant(email, "pro", provider="linepay")
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail="LINE Pay failed")


# ==================== GLOBAL PAYMENT CHANNELS ====================

@app.post("/webhook/stripe")
async def webhook_stripe(request: Request):
    """Stripe Webhook 端點"""
    event = await request.json()
    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        tier = session.get("metadata", {}).get("tier", "pro")
        provision_tenant(email, tier, provider="stripe")
        return {"status": "success"}
    return {"status": "ignored"}


@app.post("/webhook/lemonsqueezy")
async def webhook_lemonsqueezy(request: Request):
    """Lemon Squeezy (MoR 免 Stripe) Webhook 端點"""
    body = await request.json()
    event_name = body.get("meta", {}).get("event_name")
    if event_name in ["order_created", "subscription_created"]:
        email = body.get("data", {}).get("attributes", {}).get("user_email")
        provision_tenant(email, "pro", provider="lemonsqueezy")
        return {"status": "success"}
    return {"status": "ignored"}


@app.post("/webhook/gumroad")
async def webhook_gumroad(request: Request):
    """Gumroad 數位商品出售 Webhook 端點"""
    form_data = await request.form()
    data = dict(form_data)
    email = data.get("email")
    if email:
        provision_tenant(email, "pro", provider="gumroad")
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Invalid Gumroad payload")


@app.post("/webhook/paypal")
async def webhook_paypal(request: Request):
    """PayPal Subscriptions Webhook 端點"""
    body = await request.json()
    if body.get("event_type") in ["PAYMENT.SALE.COMPLETED", "BILLING.SUBSCRIPTION.CREATED"]:
        email = body.get("resource", {}).get("subscriber", {}).get("email_address", "paypal_user@example.com")
        provision_tenant(email, "pro", provider="paypal")
        return {"status": "success"}
    return {"status": "ignored"}
